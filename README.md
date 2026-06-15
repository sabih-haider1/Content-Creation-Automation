# Content Creation Automation

An AI-powered content creation pipeline triggered via Telegram bot.

## Setup

1. Copy `.env.example` to `.env` and fill in your keys (especially `TELEGRAM_BOT_TOKEN` for the MVP).
   ```bash
   cp .env.example .env
   ```
2. Build and start the services using Docker Compose:
   ```bash
   docker-compose up --build
   ```

## Architecture

- **Frontend:** Telegram Bot (python-telegram-bot)
- **API Gateway:** FastAPI server
- **Services:** Classifier, Script Generator, Web Search, Asset Generator, TTS, Subtitles, Renderer, Publisher
- **Databases:** PostgreSQL, Redis\n