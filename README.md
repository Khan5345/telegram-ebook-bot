# Telegram Ebook Library Bot

  A Telegram bot with 33 ebooks (8 free + 25 premium at 75 ⭐ Stars each).

  ## Commands
  - `/start` — welcome message
  - `/books` — full paginated catalog (📖 free · ⭐ premium)
  - `/premium` — premium-only catalog
  - `/search [query]` — search by title, author, or genre
  - `/stats` — unique users, total downloads, total Stars earned
  - `/help` — help message

  ## Deploy on Railway
  1. Connect this repo as a **Web Service**
  2. Set env var: `TELEGRAM_BOT_TOKEN` = your bot token
  3. Build/start commands are defined in `railway.toml`
  4. Health endpoint `GET /` keeps the service alive (Railway health-check)

  ## Adding your own books
  1. Copy your PDF into `bot/books/`
  2. Add an entry to `CATALOG` in `bot/catalog.py`
  3. Redeploy

  ## Stack
  - Python 3 + pyTelegramBotAPI + fpdf2 + Flask
  