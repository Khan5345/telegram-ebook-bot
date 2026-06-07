import os
import logging
import threading
import telebot
from flask import Flask
from telebot import types
from catalog import CATALOG, FREE_CATALOG, PREMIUM_CATALOG, find_book, search_books

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

BOOKS_DIR = os.path.join(os.path.dirname(__file__), "books")
BOOKS_PER_PAGE = 5
STARS_PRICE = 75


# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------

def make_catalog_keyboard(page: int = 0) -> types.InlineKeyboardMarkup:
    """All-books catalog with free/premium indicators."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    start = page * BOOKS_PER_PAGE
    end = start + BOOKS_PER_PAGE
    page_books = CATALOG[start:end]

    for book in page_books:
        icon = "⭐" if book["premium"] else "📖"
        markup.add(types.InlineKeyboardButton(
            f"{icon}  {book['title']}  —  {book['author']}",
            callback_data=f"book_{book['id']}",
        ))

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("◀ Prev", callback_data=f"page_{page - 1}"))
    if end < len(CATALOG):
        nav.append(types.InlineKeyboardButton("Next ▶", callback_data=f"page_{page + 1}"))
    if nav:
        markup.row(*nav)

    markup.add(types.InlineKeyboardButton("⭐ View Premium Catalog", callback_data="prem_0"))
    return markup


def make_premium_catalog_keyboard(page: int = 0) -> types.InlineKeyboardMarkup:
    """Premium-only catalog."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    start = page * BOOKS_PER_PAGE
    end = start + BOOKS_PER_PAGE
    page_books = PREMIUM_CATALOG[start:end]

    for book in page_books:
        markup.add(types.InlineKeyboardButton(
            f"⭐  {book['title']}  —  {book['author']}",
            callback_data=f"book_{book['id']}",
        ))

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("◀ Prev", callback_data=f"prem_{page - 1}"))
    if end < len(PREMIUM_CATALOG):
        nav.append(types.InlineKeyboardButton("Next ▶", callback_data=f"prem_{page + 1}"))
    if nav:
        markup.row(*nav)

    markup.add(types.InlineKeyboardButton("📚 Full Catalog", callback_data="page_0"))
    return markup


def make_book_keyboard(book: dict) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    if book["premium"]:
        markup.add(
            types.InlineKeyboardButton(
                f"⭐  Buy for {STARS_PRICE} Stars",
                callback_data=f"buy_{book['id']}",
            ),
        )
    else:
        markup.add(
            types.InlineKeyboardButton("📥  Download Ebook", callback_data=f"download_{book['id']}"),
        )
    markup.add(types.InlineKeyboardButton("◀  Back to Catalog", callback_data="page_0"))
    return markup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def book_detail_text(book: dict) -> str:
    badge = "⭐ *PREMIUM — 75 Stars*\n" if book["premium"] else "✅ *FREE*\n"
    return (
        f"📖 *{escape_md(book['title'])}*\n"
        f"✍️  {escape_md(book['author'])}\n"
        f"🗂  {escape_md(book['genre'])}\n"
        f"📅  {escape_md(str(book['year']))}\n"
        f"{badge}\n"
        f"_{escape_md(book['description'])}_"
    )


def escape_md(text: str) -> str:
    """Escape special characters for Markdown (v1)."""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def catalog_header(page: int) -> str:
    total_pages = (len(CATALOG) + BOOKS_PER_PAGE - 1) // BOOKS_PER_PAGE
    return (
        f"📚 *Book Catalog*  \\({len(CATALOG)} books\\)\n"
        f"Page {page + 1} of {total_pages}\n\n"
        "📖 Free   ⭐ Premium \\(75 Stars\\)\n\n"
        "Tap a title to see details:"
    )


def premium_header(page: int) -> str:
    total_pages = (len(PREMIUM_CATALOG) + BOOKS_PER_PAGE - 1) // BOOKS_PER_PAGE
    return (
        f"⭐ *Premium Catalog*  \\({len(PREMIUM_CATALOG)} books\\)\n"
        f"Page {page + 1} of {total_pages}\n\n"
        f"Each book costs *{STARS_PRICE} Telegram Stars*\\.\n\n"
        "Tap a title to see details and purchase:"
    )


def send_book_file(chat_id: int, book: dict) -> None:
    """Send the PDF for a book to the given chat."""
    file_path = os.path.join(BOOKS_DIR, book["filename"])
    if not os.path.exists(file_path):
        bot.send_message(
            chat_id,
            "⚠️ File not available right now\\. Please contact support\\.",
            parse_mode="MarkdownV2",
        )
        logger.warning("Missing file: %s", file_path)
        return

    bot.send_chat_action(chat_id, "upload_document")
    try:
        with open(file_path, "rb") as f:
            bot.send_document(
                chat_id,
                f,
                caption=f"📖 *{escape_md(book['title'])}*\n✍️  {escape_md(book['author'])}",
                parse_mode="MarkdownV2",
                visible_file_name=book["filename"],
            )
        logger.info("Sent '%s' (id=%d) to chat %d", book["title"], book["id"], chat_id)
    except Exception as e:
        logger.error("Failed to send '%s': %s", book["title"], e)
        bot.send_message(
            chat_id,
            "⚠️ Sorry, something went wrong while sending the file\\. Please try again\\.",
            parse_mode="MarkdownV2",
        )


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message) -> None:
    name = message.from_user.first_name or "there"
    text = (
        f"👋 Welcome, *{name}*\\!\n\n"
        "📚 *Ebook Library Bot*\n\n"
        "Browse our collection of classic public\\-domain books and download them straight to your chat\\.\n\n"
        "*Commands:*\n"
        "• /books — Browse all 28 books\n"
        "• /premium — Browse premium catalog \\(75 ⭐ Stars each\\)\n"
        "• /search \\[query\\] — Search by title or author\n"
        "• /help — Show this message\n\n"
        "📖 *8 books are free* — just tap Download\\.\n"
        "⭐ *20 books are premium* — unlock each for 75 Telegram Stars\\."
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2")


@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message) -> None:
    text = (
        "📖 *Ebook Library Bot — Help*\n\n"
        "*How to use:*\n"
        "1\\. Use /books to browse all available ebooks\n"
        "2\\. Tap any title to see book details\n"
        "3\\. Free books: tap *Download Ebook* to receive the file\n"
        "4\\. Premium books: tap *Buy for 75 Stars* to unlock and download\n\n"
        "*Commands:*\n"
        "• /books — Browse all books \\(free \\+ premium\\)\n"
        "• /premium — Browse premium books only\n"
        "• /search \\[query\\] — Search by title, author, or genre\n"
        "• /help — Show this message\n\n"
        "*About Telegram Stars:*\n"
        "Stars are Telegram's in\\-app currency\\. "
        "You can purchase them directly inside Telegram\\."
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2")


@bot.message_handler(commands=["books", "list"])
def cmd_books(message: types.Message) -> None:
    markup = make_catalog_keyboard(page=0)
    bot.send_message(
        message.chat.id,
        catalog_header(0),
        parse_mode="MarkdownV2",
        reply_markup=markup,
    )


@bot.message_handler(commands=["premium"])
def cmd_premium(message: types.Message) -> None:
    markup = make_premium_catalog_keyboard(page=0)
    bot.send_message(
        message.chat.id,
        premium_header(0),
        parse_mode="MarkdownV2",
        reply_markup=markup,
    )


@bot.message_handler(commands=["search"])
def cmd_search(message: types.Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(
            message.chat.id,
            "Please provide a search term\\.\nExample: `/search Alice`",
            parse_mode="MarkdownV2",
        )
        return

    query = parts[1].strip()
    results = search_books(query)

    if not results:
        bot.send_message(
            message.chat.id,
            f"❌ No books found for *{escape_md(query)}*\\.\n\nTry /books to browse the full catalog\\.",
            parse_mode="MarkdownV2",
        )
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for book in results:
        icon = "⭐" if book["premium"] else "📖"
        markup.add(types.InlineKeyboardButton(
            f"{icon}  {book['title']}  —  {book['author']}",
            callback_data=f"book_{book['id']}",
        ))

    bot.send_message(
        message.chat.id,
        f"🔍 Found *{len(results)}* result\\(s\\) for *{escape_md(query)}*:",
        parse_mode="MarkdownV2",
        reply_markup=markup,
    )


# ---------------------------------------------------------------------------
# Callback handlers — navigation
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def cb_page(call: types.CallbackQuery) -> None:
    page = int(call.data.split("_", 1)[1])
    markup = make_catalog_keyboard(page=page)
    try:
        bot.edit_message_text(
            catalog_header(page),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="MarkdownV2",
            reply_markup=markup,
        )
    except Exception:
        pass
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("prem_"))
def cb_prem_page(call: types.CallbackQuery) -> None:
    page = int(call.data.split("_", 1)[1])
    markup = make_premium_catalog_keyboard(page=page)
    try:
        bot.edit_message_text(
            premium_header(page),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="MarkdownV2",
            reply_markup=markup,
        )
    except Exception:
        pass
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_"))
def cb_book(call: types.CallbackQuery) -> None:
    book_id = int(call.data.split("_", 1)[1])
    book = find_book(book_id)
    if not book:
        bot.answer_callback_query(call.id, "Book not found.")
        return

    markup = make_book_keyboard(book)
    try:
        bot.edit_message_text(
            book_detail_text(book),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="MarkdownV2",
            reply_markup=markup,
        )
    except Exception:
        pass
    bot.answer_callback_query(call.id)


# ---------------------------------------------------------------------------
# Callback handlers — download (free books)
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("download_"))
def cb_download(call: types.CallbackQuery) -> None:
    book_id = int(call.data.split("_", 1)[1])
    book = find_book(book_id)
    if not book:
        bot.answer_callback_query(call.id, "Book not found.")
        return

    if book["premium"]:
        bot.answer_callback_query(
            call.id,
            f"This is a premium book. Tap 'Buy for {STARS_PRICE} Stars' to unlock it.",
            show_alert=True,
        )
        return

    bot.answer_callback_query(call.id, "Sending your ebook…")
    send_book_file(call.message.chat.id, book)


# ---------------------------------------------------------------------------
# Callback handlers — Stars payment (premium books)
# ---------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def cb_buy(call: types.CallbackQuery) -> None:
    book_id = int(call.data.split("_", 1)[1])
    book = find_book(book_id)
    if not book:
        bot.answer_callback_query(call.id, "Book not found.")
        return

    bot.answer_callback_query(call.id)

    try:
        bot.send_invoice(
            chat_id=call.message.chat.id,
            title=book["title"],
            description=f"Download: {book['title']} by {book['author']} ({book['year']})",
            payload=f"premium_book_{book['id']}",
            provider_token="",
            currency="XTR",
            prices=[types.LabeledPrice(label="Premium Ebook", amount=STARS_PRICE)],
        )
        logger.info(
            "Sent Stars invoice for '%s' (id=%d) to user %d",
            book["title"], book["id"], call.from_user.id,
        )
    except Exception as e:
        logger.error("Failed to send invoice for '%s': %s", book["title"], e)
        bot.send_message(
            call.message.chat.id,
            "⚠️ Could not create payment invoice\\. Please try again\\.",
            parse_mode="MarkdownV2",
        )


@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(query: types.PreCheckoutQuery) -> None:
    """Telegram requires answering pre-checkout queries within 10 seconds."""
    bot.answer_pre_checkout_query(query.id, ok=True)
    logger.info(
        "Pre-checkout OK for user %d, payload=%s", query.from_user.id, query.invoice_payload
    )


@bot.message_handler(content_types=["successful_payment"])
def successful_payment(message: types.Message) -> None:
    """Fires after Telegram confirms the Stars payment. Send the book immediately."""
    payload = message.successful_payment.invoice_payload
    logger.info(
        "Successful payment from user %d (@%s), payload=%s, stars=%d",
        message.from_user.id,
        message.from_user.username or "—",
        payload,
        message.successful_payment.total_amount,
    )

    if not payload.startswith("premium_book_"):
        logger.warning("Unknown payment payload: %s", payload)
        return

    try:
        book_id = int(payload.split("_")[-1])
    except (ValueError, IndexError):
        logger.error("Could not parse book_id from payload: %s", payload)
        return

    book = find_book(book_id)
    if not book:
        logger.error("Book id=%d not found after payment", book_id)
        bot.send_message(
            message.chat.id,
            "⚠️ Payment received but book not found\\. Please contact support\\.",
            parse_mode="MarkdownV2",
        )
        return

    bot.send_message(
        message.chat.id,
        f"✅ *Payment confirmed\\!* Thank you for your {STARS_PRICE} Stars\\.\n\n"
        f"Sending *{escape_md(book['title'])}* now…",
        parse_mode="MarkdownV2",
    )
    send_book_file(message.chat.id, book)


# ---------------------------------------------------------------------------
# Fallback (must be last)
# ---------------------------------------------------------------------------

@bot.message_handler(func=lambda m: True)
def fallback(message: types.Message) -> None:
    bot.send_message(
        message.chat.id,
        "I didn't understand that\\. Use /books to browse the catalog or /help for instructions\\.",
        parse_mode="MarkdownV2",
    )


# ---------------------------------------------------------------------------
# Health check server (Flask)
# ---------------------------------------------------------------------------

health_app = Flask(__name__)
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)


@health_app.route("/")
def health():
    return "Bot is running", 200


def start_health_server() -> None:
    # Railway injects $PORT for web services; fall back to BOT_HEALTH_PORT or 5000
    port = int(os.environ.get("PORT", os.environ.get("BOT_HEALTH_PORT", 5000)))
    logger.info("Health server listening on port %d", port)
    health_app.run(host="0.0.0.0", port=port, use_reloader=False)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    threading.Thread(target=start_health_server, daemon=True).start()
    logger.info("Bot starting - polling for updates...")
    bot.infinity_polling(timeout=10, long_polling_timeout=10, none_stop=True)
