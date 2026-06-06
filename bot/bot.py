import os
import logging
import threading
import telebot
from flask import Flask
from telebot import types
from catalog import CATALOG, find_book, search_books

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


# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------

def make_catalog_keyboard(page: int = 0) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    start = page * BOOKS_PER_PAGE
    end = start + BOOKS_PER_PAGE
    page_books = CATALOG[start:end]

    for book in page_books:
        markup.add(types.InlineKeyboardButton(
            f"📖  {book['title']}  —  {book['author']}",
            callback_data=f"book_{book['id']}",
        ))

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("◀ Prev", callback_data=f"page_{page - 1}"))
    if end < len(CATALOG):
        nav.append(types.InlineKeyboardButton("Next ▶", callback_data=f"page_{page + 1}"))
    if nav:
        markup.row(*nav)

    return markup


def make_book_keyboard(book_id: int) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📥  Download Ebook", callback_data=f"download_{book_id}"),
        types.InlineKeyboardButton("◀  Back to Catalog", callback_data="page_0"),
    )
    return markup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def book_detail_text(book: dict) -> str:
    return (
        f"📖 *{escape_md(book['title'])}*\n"
        f"✍️  {escape_md(book['author'])}\n"
        f"🗂  {escape_md(book['genre'])}\n"
        f"📅  {escape_md(str(book['year']))}\n\n"
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
        "Tap a title to see details and download:"
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
        "• /books — Browse the full catalog\n"
        "• /search \\[query\\] — Search by title or author\n"
        "• /help — Show this message"
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2")


@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message) -> None:
    text = (
        "📖 *Ebook Library Bot — Help*\n\n"
        "*How to use:*\n"
        "1\\. Use /books to browse all available ebooks\n"
        "2\\. Tap any title to see book details\n"
        "3\\. Tap *Download Ebook* to receive the file\n\n"
        "*Search:*\n"
        "Use /search followed by a title or author name\\.\n"
        "Example: `/search Sherlock Holmes`\n\n"
        "*Commands:*\n"
        "• /books — Browse catalog\n"
        "• /search \\[query\\] — Search books\n"
        "• /help — Show this message"
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
        markup.add(types.InlineKeyboardButton(
            f"📖  {book['title']}  —  {book['author']}",
            callback_data=f"book_{book['id']}",
        ))

    bot.send_message(
        message.chat.id,
        f"🔍 Found *{len(results)}* result\\(s\\) for *{escape_md(query)}*:",
        parse_mode="MarkdownV2",
        reply_markup=markup,
    )


# ---------------------------------------------------------------------------
# Callback handlers
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


@bot.callback_query_handler(func=lambda call: call.data.startswith("book_"))
def cb_book(call: types.CallbackQuery) -> None:
    book_id = int(call.data.split("_", 1)[1])
    book = find_book(book_id)
    if not book:
        bot.answer_callback_query(call.id, "Book not found.")
        return

    markup = make_book_keyboard(book_id)
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


@bot.callback_query_handler(func=lambda call: call.data.startswith("download_"))
def cb_download(call: types.CallbackQuery) -> None:
    book_id = int(call.data.split("_", 1)[1])
    book = find_book(book_id)
    if not book:
        bot.answer_callback_query(call.id, "Book not found.")
        return

    file_path = os.path.join(BOOKS_DIR, book["filename"])
    if not os.path.exists(file_path):
        bot.answer_callback_query(call.id, "File not available right now.", show_alert=True)
        logger.warning("Missing file: %s", file_path)
        return

    bot.answer_callback_query(call.id, "Sending your ebook…")
    bot.send_chat_action(call.message.chat.id, "upload_document")

    try:
        with open(file_path, "rb") as f:
            bot.send_document(
                call.message.chat.id,
                f,
                caption=f"📖 *{escape_md(book['title'])}*\n✍️  {escape_md(book['author'])}",
                parse_mode="MarkdownV2",
                visible_file_name=book["filename"],
            )
        logger.info(
            "Sent '%s' (id=%d) to user %d (@%s)",
            book["title"],
            book_id,
            call.from_user.id,
            call.from_user.username or "—",
        )
    except Exception as e:
        logger.error("Failed to send '%s': %s", book["title"], e)
        bot.send_message(
            call.message.chat.id,
            "⚠️ Sorry, something went wrong while sending the file\\. Please try again\\.",
            parse_mode="MarkdownV2",
        )


# ---------------------------------------------------------------------------
# Fallback
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
log.setLevel(logging.ERROR)  # silence Flask request logs


@health_app.route("/")
def health():
    return "Bot is running", 200


def start_health_server() -> None:
    port = int(os.environ.get("BOT_HEALTH_PORT", 5000))
    logger.info("Health server listening on port %d", port)
    health_app.run(host="0.0.0.0", port=port, use_reloader=False)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    threading.Thread(target=start_health_server, daemon=True).start()
    logger.info("Bot starting - polling for updates...")
    # none_stop=True: telebot catches all exceptions (including 409 conflicts) and retries
    # automatically without breaking. long_polling_timeout=10 means stale connections
    # from a previous instance expire within 10 s so 409 conflicts self-heal quickly.
    bot.infinity_polling(timeout=10, long_polling_timeout=10, none_stop=True)
