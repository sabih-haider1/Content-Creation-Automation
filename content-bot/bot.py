import os
import asyncio
import uuid
import json
import logging
import httpx
from datetime import datetime, timedelta, UTC
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    TypeHandler
)
from telegram.request import HTTPXRequest
import config
import db
import pipeline
import youtube_uploader

# Force environment variables if proxy is enabled
if config.USE_PROXY:
    os.environ["HTTP_PROXY"] = config.TOR_PROXY
    os.environ["HTTPS_PROXY"] = config.TOR_PROXY
    os.environ["http_proxy"] = config.TOR_PROXY
    os.environ["https_proxy"] = config.TOR_PROXY

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Track active pipeline tasks for cancellation
active_tasks = {}

async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Global handler to log EVERY incoming update to the console for debugging.
    """
    if update.message:
        logger.info(f"Update: Message '{update.message.text}' from {update.effective_user.id}")
    elif update.callback_query:
        logger.info(f"Update: Callback '{update.callback_query.data}' from {update.effective_user.id}")
    else:
        logger.info(f"Update: Received update of type {type(update)}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global handler to catch crashes and prevent bot shutdown."""
    logger.error(f"Update {update} caused error {context.error}")
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("❌ An unexpected error occurred. Please try again.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 *Welcome to the Gemini Veo 2 Automation Bot!*\n\n"
        "I can help you generate high-quality AI videos and upload them to YouTube Shorts.\n\n"
        "📜 *Commands:*\n"
        "/create <prompt> - Generate a new AI video\n"
        "/status - Check status of your last job\n"
        "/jobs - View your recent jobs\n"
        "/upload - Upload a generated video manually\n"
        "/schedule - Schedule a video for later\n"
        "/connect - Link your YouTube account\n"
        "/platforms - View connected platforms\n"
        "/settings - Manage preferences\n"
        "/cancel - Cancel an active job\n"
        "/help - Show usage guide"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *How to use:*\n"
        "1. Run `/connect` to link your YouTube channel.\n"
        "2. Run `/create <topic>` (e.g., `/create a cyberpunk city in rain`).\n"
        "3. Wait for the AI to script, generate video, and render.\n"
        "4. Choose to upload immediately or schedule for later.\n\n"
        "💡 *Pro Tip:* Use `/jobs` to see everything you've created!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    job = await db.get_latest_job(user_id)
    if not job:
        await update.message.reply_text("No jobs found.")
        return
    status_text = f"📊 *Status:* {job['status'].upper()}\n📝 *Prompt:* {job['prompt']}"
    if job['youtube_url']:
        status_text += f"\n🔗 *YouTube:* {job['youtube_url']}"
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    recent_jobs = await db.get_recent_jobs(user_id, limit=5)
    if not recent_jobs:
        await update.message.reply_text("No recent jobs found.")
        return
    
    msg = "📂 *Recent Jobs:*\n\n"
    for job in recent_jobs:
        status_emoji = "✅" if job['status'] == 'done' else "⏳" if job['status'] in ['scripting', 'assets', 'rendering'] else "❌"
        msg += f"{status_emoji} `{job['id'][:8]}` - {job['prompt'][:30]}... ({job['status']})\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ Checking YouTube connection...")
    try:
        channel_name = await asyncio.to_thread(youtube_uploader.check_connection, user_id)
        if channel_name:
            await update.message.reply_text(f"✅ Already connected to: *{channel_name}*", parse_mode="Markdown")
        else:
            await update.message.reply_text("🔗 *YouTube Connection Flow:*\n\n1. Open the link below on your phone.\n2. Authorize the application.\n3. You will be redirected to a page that says 'This site can't be reached' (localhost).\n4. *Copy that full URL* from your browser's address bar and paste it here.", parse_mode="Markdown")
            auth_url, flow = await asyncio.to_thread(youtube_uploader.get_authorization_url, user_id)
            context.user_data['oauth_flow'] = flow
            await update.message.reply_text(f"[Click here to authorize]({auth_url})", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Connection error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles regular text messages, specifically for the OAuth redirect URL.
    """
    text = update.message.text
    user_id = update.effective_user.id
    
    # Check if we are waiting for an OAuth redirect URL
    if 'oauth_flow' in context.user_data and ("localhost" in text or "code=" in text):
        flow = context.user_data['oauth_flow']
        status_msg = await update.message.reply_text("⏳ Completing authorization...")
        try:
            creds = await asyncio.to_thread(youtube_uploader.complete_authorization, user_id, flow, text)
            if creds:
                channel_name = await asyncio.to_thread(youtube_uploader.check_connection, user_id)
                await status_msg.edit_text(f"✅ Successfully connected to: *{channel_name}*", parse_mode="Markdown")
                del context.user_data['oauth_flow']
            else:
                await status_msg.edit_text("❌ Failed to complete authorization.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error during authorization: {str(e)}")
            logger.error(f"Auth error: {e}")
    else:
        # Default behavior for other messages
        if not text.startswith('/'):
            await update.message.reply_text("Please use the commands provided in /help.")

async def platforms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ Checking connections...")
    channel_name = await asyncio.to_thread(youtube_uploader.check_connection, user_id)
    yt_status = f"✅ Connected: *{channel_name}*" if channel_name else "❌ Not Linked"
    await update.message.reply_text(f"🌐 *Connected Platforms:*\n\n🔴 YouTube: {yt_status}\n📸 Instagram: Not Linked ❌\n🎵 TikTok: Not Linked ❌", parse_mode="Markdown")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ *Settings:*\n\nDefault Niche: `General`\nVideo Duration: `60s`\nVoice Model: `Standard-A`\n\n(Use buttons to change - *Coming Soon*)", parse_mode="Markdown")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_tasks:
        task = active_tasks[user_id]
        task.cancel()
        del active_tasks[user_id]
        await update.message.reply_text("🛑 Active job has been cancelled.")
    else:
        await update.message.reply_text("No active job to cancel.")

async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = " ".join(context.args)
    user_id = update.effective_user.id
    if not user_prompt:
        await update.message.reply_text("Please provide a prompt. Example: `/create a futuristic city`", parse_mode="Markdown")
        return
    
    if user_id in active_tasks:
        await update.message.reply_text("⚠️ You already have a job running. Use /cancel to stop it.")
        return

    job_id = str(uuid.uuid4())
    status_msg = await update.message.reply_text("⏳ Initializing Gemini Veo 2 Pipeline...")
    
    async def status_callback(status: str, data: dict):
        texts = {
            "classifying": "🔍 Analyzing niche...",
            "scripting": "📝 Writing cinematic script...",
            "assets": "🎬 Generating high-quality clips with Veo 2...",
            "rendering": "🎞️ Rendering final production...",
            "done": "✅ Video generation complete!"
        }
        try:
            await status_msg.edit_text(texts.get(status, "⏳ Processing..."))
        except: pass

    async def run_pipeline():
        try:
            result = await pipeline.run_content_pipeline(user_prompt, user_id, job_id, status_callback=status_callback)
            video_path = result["video_path"]
            caption = f"🎬 *{result['title']}*\n\n{result['description']}"
            
            with open(video_path, "rb") as video_file:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=video_file, caption=caption[:1024], parse_mode="Markdown")
                
            keyboard = [
                [InlineKeyboardButton("🚀 Publish Now", callback_data=f"yt_now:{job_id}")],
                [InlineKeyboardButton("📅 Schedule (in 1 hour)", callback_data=f"yt_sched:{job_id}")]
            ]
            await update.message.reply_text("What would you like to do next?", reply_markup=InlineKeyboardMarkup(keyboard))
        except asyncio.CancelledError:
            await db.cancel_job(job_id)
            logger.info(f"Job {job_id} cancelled by user.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        finally:
            if user_id in active_tasks:
                del active_tasks[user_id]

    task = asyncio.create_task(run_pipeline())
    active_tasks[user_id] = task

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    job = await db.get_latest_job(user_id)
    if not job or job['status'] != 'done':
        await update.message.reply_text("No completed video found to upload.")
        return
    
    await update.message.reply_text(f"🚀 Uploading latest video: *{job['title']}*...", parse_mode="Markdown")
    try:
        url = await asyncio.to_thread(youtube_uploader.upload_video, user_id, job["video_path"], job["title"], job["description"], json.loads(job["hashtags"]))
        await db.update_job(job['id'], youtube_url=url)
        await update.message.reply_text(f"✅ Published!\n🔗 {url}")
    except Exception as e:
        await update.message.reply_text(f"❌ Upload failed: {str(e)}")

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    job = await db.get_latest_job(user_id)
    if not job or job['status'] != 'done':
        await update.message.reply_text("No completed video found to schedule.")
        return

    # Use modern UTC datetime
    sched_time = (datetime.now(UTC) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    await update.message.reply_text(f"📅 Scheduling latest video for {sched_time}...")
    try:
        url = await asyncio.to_thread(youtube_uploader.upload_video, user_id, job["video_path"], job["title"], job["description"], json.loads(job["hashtags"]), publish_at=sched_time)
        await db.update_job(job['id'], youtube_url=url)
        await update.message.reply_text(f"✅ Scheduled! Video will go public at {sched_time}.\n🔗 {url}")
    except Exception as e:
        await update.message.reply_text(f"❌ Scheduling failed: {str(e)}")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    logger.info(f"Processing callback: {data} for user {user_id}")
    
    try:
        action, job_id = data.split(":")
    except ValueError:
        logger.error(f"Invalid callback data: {data}")
        return
    
    job = await db.get_job(job_id)
    if not job:
        await query.edit_message_text("Error: Job record not found in database.")
        return

    if action == "yt_now":
        await query.edit_message_text("🚀 Uploading to YouTube...")
        try:
            url = await asyncio.to_thread(youtube_uploader.upload_video, user_id, job["video_path"], job["title"], job["description"], json.loads(job["hashtags"]))
            await db.update_job(job_id, youtube_url=url)
            await query.edit_message_text(f"✅ Published!\n🔗 {url}")
        except Exception as e:
            await query.edit_message_text(f"❌ Upload failed: {str(e)}")
            
    elif action == "yt_sched":
        sched_time = (datetime.now(UTC) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        await query.edit_message_text(f"📅 Scheduling for {sched_time}...")
        try:
            url = await asyncio.to_thread(youtube_uploader.upload_video, user_id, job["video_path"], job["title"], job["description"], json.loads(job["hashtags"]), publish_at=sched_time)
            await db.update_job(job_id, youtube_url=url)
            await query.edit_message_text(f"✅ Scheduled! Video will go public at {sched_time}.\n🔗 {url}")
        except Exception as e:
            await query.edit_message_text(f"❌ Scheduling failed: {str(e)}")

async def post_init(application):
    await db.init_db()

def main():
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found.")
        return

    # Setup conditional proxy
    proxy_request = HTTPXRequest(
        proxy=config.TOR_PROXY,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0
    ) if config.USE_PROXY else None
    
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).request(proxy_request).post_init(post_init).build()
    
    # Debug handler for ALL updates (Group -1 runs first)
    app.add_handler(TypeHandler(Update, log_all_updates), group=-1)

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("jobs", jobs_command))
    app.add_handler(CommandHandler("create", create_command))
    app.add_handler(CommandHandler("connect", connect_command))
    app.add_handler(CommandHandler("platforms", platforms_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("upload", upload_command))
    app.add_handler(CommandHandler("schedule", schedule_command))
    
    # Regular message handler for auth URL
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # CallbackQueryHandler for button clicks
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # CRITICAL: Add Global Error Handler
    app.add_error_handler(error_handler)
    
    print(f"Bot is starting (Proxy: {config.USE_PROXY})...")
    app.run_polling()

if __name__ == "__main__":
    main()
