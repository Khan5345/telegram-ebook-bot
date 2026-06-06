# Telegram Ebook Library Bot

A Python Telegram bot that lets users browse a catalog of ebooks and download them directly in chat.
It also runs a Flask health-check server so the deployment can be monitored by UptimeRobot or similar services.

## Run & Operate

- `Telegram Ebook Bot` workflow — starts the bot + Flask health server (web preview)
- `pip install -r bot/requirements.txt` — install/update Python dependencies
- `python bot/create_samples.py` — (re)generate sample PDF files in `bot/books/`
- Required secret: `TELEGRAM_BOT_TOKEN` — set via Replit Secrets

> **Note:** The `artifacts/api-server: Bot Health` workflow is intentionally **not started**.
> `bot.py` already runs both the Flask health server (port 5000) and the Telegram polling
> in a single process via the `Telegram Ebook Bot` workflow. Starting the Bot Health
> workflow separately would launch a second bot instance and cause 409 conflicts.

## Stack

- Python 3 + pyTelegramBotAPI (telebot)
- Flask — health-check web server embedded in the bot process
- fpdf2 — for generating sample PDF ebooks
- pnpm workspaces, Node.js 24, TypeScript 5.9 (monorepo scaffold)

## Where things live

- `bot/bot.py` — main bot logic (commands, callbacks, Flask health server)
- `bot/catalog.py` — book catalog definition; add new books here
- `bot/create_samples.py` — downloads real texts from Project Gutenberg, creates PDFs
- `bot/books/` — ebook files served by the bot (PDF/EPUB)
- `bot/requirements.txt` — Python dependencies

## Health check

- Endpoint: `GET /` → `200 Bot is running`
- Port: 5000 (proxied at `/` by the shared Replit reverse proxy)
- Use this URL with UptimeRobot: `https://<your-app>.replit.app/`

## Product

- `/start` — welcome message and instructions
- `/books` — paginated inline-keyboard catalog (5 books per page, 28 books total)
- `/search [query]` — search by title, author, or genre
- Tapping a book shows details (title, author, genre, year, description) + Download button
- Tapping Download sends the PDF file directly in the chat

## Adding Your Own Books

1. Copy your PDF (or EPUB) file into `bot/books/`
2. Add an entry to the `CATALOG` list in `bot/catalog.py` — copy an existing entry and fill in the fields
3. Restart the `Telegram Ebook Bot` workflow

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Sample PDFs are downloaded from Project Gutenberg on first run and skipped if they already exist
- fpdf2's built-in fonts are Latin-1 only — `create_samples.py` converts Unicode characters
- Replace any file in `bot/books/` with a real ebook of the same filename to use your own content

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
