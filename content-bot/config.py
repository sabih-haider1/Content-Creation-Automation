import os
from dotenv import load_dotenv

# Load .env file
load_dotenv(override=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Infrastructure & Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./content.db")

# YouTube & OAuth
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")

# Proxy / VPN Settings
# Set USE_PROXY=True in your .env file if you are in a restricted region
USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
TOR_PROXY = os.getenv("TOR_PROXY", "socks5h://127.0.0.1:9150")

# Directories
OUTPUT_DIR = "output"
ASSETS_DIR = "assets"

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)