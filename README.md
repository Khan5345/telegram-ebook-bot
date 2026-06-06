# Telegram Ebook Library Bot

  A Telegram bot that lets users browse a catalog of 28 public-domain ebooks and download them directly in chat.

  ## Features

  - `/start` — welcome message
  - `/books` — paginated inline-keyboard catalog (5 books per page)
  - `/search [query]` — search by title, author, or genre
  - Tapping a book shows details + Download button
  - Download sends the PDF directly in chat

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
  2. Add an entry to `CATALOG` in `bot/catalog.py`
  3. Restart the bot
  