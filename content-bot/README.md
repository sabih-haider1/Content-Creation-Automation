# Content Creation Automation Telegram Bot

A self-contained, lightweight Python-based Telegram Bot that automatically generates styled 1080x1920 portrait vertical videos (9:16 Shorts/TikToks/Reels format) from a single user prompt.

It uses:
1. **Gemini AI** (`gemini-1.5-flash`) to analyze, classify, and generate a highly engaging 60-second, 6-scene script, optimized titles, and description.
2. **edge-tts** to generate professional voiceovers on-the-fly.
3. **Pillow (PIL)** to programmatically generate beautiful linear gradients and render crisp, translucent boxes with wrapped subtitle captions on top (no ImageMagick required!).
4. **MoviePy** to assemble and sync the final MP4 video.
5. **SQLite / aiosqlite** for async job tracking.
6. **YouTube API & google-auth-oauthlib** to optionally publish the video directly to YouTube Shorts with a single click in Telegram.

---

## Directory Structure

```text
content-bot/
  ├── bot.py              # Telegram bot entry point and handlers
  ├── pipeline.py         # Coordinates script, voiceover, frame generation, and compilation
  ├── gemini_client.py    # Gemini API client for classification and script generation
  ├── tts.py              # Text-to-speech engine using edge-tts
  ├── video_builder.py    # Pillow-based frame generator and MoviePy video compiler
  ├── youtube_uploader.py # YouTube Video Upload API wrapper (OAuth 2.0 flow)
  ├── db.py               # Job database setup and helpers
  ├── config.py           # Configuration variables and directories loader
  ├── requirements.txt    # Project dependencies
  ├── README.md           # Instructions
  └── .env                # API keys and environment variables
```

---

## Installation

1. Make sure you have python 3.9+ and pip installed.
2. Clone or navigate to this directory.
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

Ensure you have a `.env` file in the `content-bot/` directory with the following variables:

```env
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=sqlite:///./content.db
ENVIRONMENT=development
```

*(Note: A pre-configured `.env` is already created for you using your active workspace tokens).*

---

## Usage

1. Start the bot:
   ```bash
   python bot.py
   ```
2. Open Telegram and search for your bot. Click **Start** or type `/start`.
3. Generate a video by typing:
   ```text
   /create explain how black holes work
   ```
4. The bot will show real-time progress as it:
   - Classifies the prompt.
   - Generates the script.
   - Generates the voiceovers.
   - Compiles the final vertical video.
5. Once complete, the bot will send you the `.mp4` file directly in the chat with optimized descriptions and tags.

---

## Publishing to YouTube Shorts (Optional)

To enable publishing to YouTube Shorts directly from the bot:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project and enable the **YouTube Data API v3**.
3. Create an **OAuth 2.0 Client ID** (Application Type: Web Application or Desktop App).
4. Download the client credentials JSON file.
5. Rename the file to `client_secret.json` and place it in this `content-bot/` folder.
6. When you click the **Upload to YouTube Shorts** button in Telegram for the first time, a web browser window will open on your host machine prompting you to log in and authorize the app.
7. Subsequent runs will use the automatically created `token.json` file.
