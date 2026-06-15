import os
import asyncio
import uuid
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    MessageHandler, CallbackQueryHandler, filters, TypeHandler
)
from telegram.request import HTTPXRequest
import config
import db
import pipeline
import youtube_uploader

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Task Tracker
active_tasks = {}

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global handler to catch crashes and prevent bot shutdown."""
    logger.error(f"Update {update} caused error {context.error}")
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("❌ An unexpected error occurred. Please try again.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = "👋 *Gemini Veo 2 Bot Ready!*\n\nUse /create <prompt> to start generating videos."
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = " ".join(context.args)
    user_id = update.effective_user.id
    
    if not user_prompt:
        await update.message.reply_text("Usage: /create <your prompt>")
        return
    
    if user_id in active_tasks:
        await update.message.reply_text("⚠️ Job already running. Use /cancel.")
        return

    job_id = str(uuid.uuid4())
    status_msg = await update.message.reply_text("⏳ Initializing pipeline...")
    
    async def status_callback(status: str, data: dict):
        texts = {"classifying": "🔍 Analyzing...", "scripting": "📝 Scripting...", "assets": "🎬 Generating clips...", "rendering": "🎞️ Rendering...", "done": "✅ Finished!"}
        try: await status_msg.edit_text(texts.get(status, "⏳ Processing..."))
        except: pass

    async def run_pipeline():
        try:
            result = await pipeline.run_content_pipeline(user_prompt, user_id, job_id, status_callback)
            caption = f"🎬 *{result['title']}*\n\n{result['description']}"
            with open(result["video_path"], "rb") as f:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption=caption[:1024], parse_mode="Markdown")
            
            keyboard = [[InlineKeyboardButton("🚀 Publish Now", callback_data=f"yt_now:{job_id}")]]
            await update.message.reply_text("Video ready!", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            await update.message.reply_text(f"❌ Generation failed: {str(e)}")
        finally:
            active_tasks.pop(user_id, None)

    active_tasks[user_id] = asyncio.create_task(run_pipeline())

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, job_id = query.data.split(":")
    
    if action == "yt_now":
        await query.edit_message_text("🚀 Uploading to YouTube...")
        job = await db.get_job(job_id)
        try:
            # The youtube_uploader module should handle its own proxying internally
            url = await asyncio.to_thread(youtube_uploader.upload_video, query.from_user.id, job["video_path"], job["title"], job["description"], json.loads(job["hashtags"]))
            await query.edit_message_text(f"✅ Published!\n🔗 {url}")
        except Exception as e:
            await query.edit_message_text(f"❌ Upload failed: {str(e)}")

def main():
    # Setup conditional proxy
    proxy_request = HTTPXRequest(proxy=config.TOR_PROXY) if config.USE_PROXY else None
    
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).request(proxy_request).build()
    
    # Add Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("create", create_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # CRITICAL: Add Global Error Handler
    app.add_error_handler(error_handler)
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()