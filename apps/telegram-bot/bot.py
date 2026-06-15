import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from loguru import logger
import httpx
from shared.config.settings import settings

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
API_SERVER_URL = os.getenv("API_SERVER_URL", "http://api-server:8000")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "Welcome to Content Creation Automation Bot!\nUse /create <prompt> to generate content."
    await update.message.reply_text(welcome_text)

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Please provide a prompt. Example: /create explain quantum computing")
        return

    user_id = str(update.effective_user.id)
    await update.message.reply_text("Analyzing prompt...")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{API_SERVER_URL}/jobs", json={"user_id": user_id, "prompt": prompt})
            resp.raise_for_status()
            job_data = resp.json()
            job_id = job_data["job_id"]
            
            while True:
                status_resp = await client.get(f"{API_SERVER_URL}/jobs/{job_id}")
                status_resp.raise_for_status()
                status_data = status_resp.json()
                
                status = status_data["status"]
                
                if status == "analyzing":
                    await asyncio.sleep(1)
                elif status == "generating_script":
                    niche = status_data.get("niche", "unknown")
                    await update.message.reply_text(f"{niche.capitalize()} content detected. Generating script...")
                    await asyncio.sleep(2)
                elif status == "done":
                    result = status_data.get("result", {})
                    await update.message.reply_text("Script generated ✅")
                    message = f"**{result.get('title', 'Title')}**\n\n{result.get('script', '')}\n\n{' '.join(result.get('hashtags', []))}"
                    await update.message.reply_text(message, parse_mode='Markdown')
                    break
                elif status == "failed":
                    error_msg = status_data.get("error_message")
                    if error_msg == "not accessible":
                        await update.message.reply_text("not accessible")
                    else:
                        await update.message.reply_text("Failed to generate content.")
                    break
                else:
                    await asyncio.sleep(1)
                    
    except Exception as e:
        logger.error(f"Error calling API server: {e}")
        await update.message.reply_text("An error occurred while communicating with the server.")

def main():
    if TELEGRAM_BOT_TOKEN == "mock_token":
        logger.warning("Using mock token. Bot will run but cannot connect to Telegram.")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("create", create))
    
    logger.info("Starting bot...")
    app.run_polling()

if __name__ == "__main__":
    main()\n