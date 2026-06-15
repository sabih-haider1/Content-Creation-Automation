import os
from dotenv import load_dotenv

# Load .env file and override any pre-existing environment variables
load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./content.db")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")

# Ensure output directories exist
os.makedirs("output", exist_ok=True)
os.makedirs("assets", exist_ok=True)
