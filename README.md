# Telegram Ebook Library Bot

  A Telegram bot that lets users browse a catalog of 28 public-domain ebooks and download them directly in chat.

  ## Features

  - `/start` — welcome message
  - `/books` — paginated catalog (📖 free · ⭐ premium)
  - `/premium` — premium-only catalog
  - `/search [query]` — search by title, author, or genre
  - **8 free books** — download instantly
  - **20 premium books** — unlock each for **75 Telegram Stars**

  ## Telegram Stars payment flow

  1. Tap a premium book → tap **Buy for 75 Stars**
  2. Telegram shows a native payment dialog
  3. Confirm → book PDF is sent immediately

  ## Deploy on Railway

  1. Fork / connect this repo in Railway
  2. Set environment variable: `TELEGRAM_BOT_TOKEN` = your bot token
  3. Railway will auto-run the build & start commands from `railway.toml`

  ## Local setup

  ```bash
  pip install -r requirements.txt
  python bot/create_samples.py   # downloads ebooks from Project Gutenberg
  python bot/bot.py
  ```

  ## Adding books

  1. Copy your PDF into `bot/books/`
  2. Add an entry to `CATALOG` in `bot/catalog.py` with `"premium": True/False`
  3. Restart the bot
  