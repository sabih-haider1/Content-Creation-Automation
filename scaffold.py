import os
from pathlib import Path

files = {
    "shared/models/job.py": """
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    prompt: str
    niche: Optional[str] = None
    content_type: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
""",
    "shared/models/script.py": """
from pydantic import BaseModel
from typing import List

class Script(BaseModel):
    job_id: str
    title: str
    script: str
    hashtags: List[str]
""",
    "shared/models/asset.py": """
from pydantic import BaseModel
from typing import List

class Asset(BaseModel):
    job_id: str
    images: List[str] = []
    videos: List[str] = []
    audio: str = ""
""",
    "shared/models/render.py": """
from pydantic import BaseModel

class Render(BaseModel):
    job_id: str
    video_url: str
    thumbnail_url: str
""",
    "shared/schemas/api_schemas.py": """
from pydantic import BaseModel
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    prompt: str

class AnalyzeResponse(BaseModel):
    niche: str
    content_type: str
    confidence: float

class GenerateScriptRequest(BaseModel):
    job_id: str
    prompt: str
    niche: str
    content_type: str

class GenerateScriptResponse(BaseModel):
    title: str
    script: str
    hashtags: List[str]

class JobCreateRequest(BaseModel):
    user_id: str
    prompt: str

class JobResponse(BaseModel):
    job_id: str
    status: str
""",
    "shared/config/settings.py": """
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    telegram_bot_token: str = "mock_token"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    tavily_api_key: str = ""
    database_url: str = "postgresql://user:pass@postgres:5432/content_db"
    redis_url: str = "redis://redis:6379"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
""",
    "shared/utils/retry.py": """
import asyncio
from functools import wraps
from loguru import logger

def async_retry(retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if i == retries - 1:
                        raise e
                    logger.warning(f"Retry {i+1}/{retries} for {func.__name__} after error: {e}")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
""",
    "shared/utils/validators.py": """
def validate_prompt(prompt: str) -> bool:
    return len(prompt.strip()) > 3
""",
    "apps/api-server/main.py": """
from fastapi import FastAPI, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
import httpx
from loguru import logger
from shared.schemas.api_schemas import JobCreateRequest, JobResponse, AnalyzeRequest, GenerateScriptRequest
from shared.models.job import Job
from apps.api_server.routes import jobs, auth, schedule

app = FastAPI(title="API Gateway")

app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(schedule.router, prefix="/schedule", tags=["schedule"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
""",
    "apps/api-server/routes/jobs.py": """
from fastapi import APIRouter, BackgroundTasks, HTTPException
import httpx
from loguru import logger
from shared.schemas.api_schemas import JobCreateRequest, JobResponse, GenerateScriptRequest
from shared.models.job import Job

router = APIRouter()
jobs_db = {}

CLASSIFIER_URL = "http://classifier:8000"
SCRIPT_GENERATOR_URL = "http://script-generator:8000"

async def process_job(job: Job):
    try:
        async with httpx.AsyncClient() as client:
            # 1. Analyze
            logger.info(f"Analyzing job {job.id}")
            jobs_db[job.id].status = "analyzing"
            analyze_resp = await client.post(f"{CLASSIFIER_URL}/analyze", json={"prompt": job.prompt}, timeout=30.0)
            analyze_resp.raise_for_status()
            analysis = analyze_resp.json()
            
            job.niche = analysis["niche"]
            job.content_type = analysis["content_type"]
            
            # 2. Generate Script
            logger.info(f"Generating script for job {job.id}")
            jobs_db[job.id].status = "generating_script"
            script_req = GenerateScriptRequest(
                job_id=job.id,
                prompt=job.prompt,
                niche=job.niche,
                content_type=job.content_type
            )
            script_resp = await client.post(f"{SCRIPT_GENERATOR_URL}/generate-script", json=script_req.model_dump(), timeout=30.0)
            script_resp.raise_for_status()
            script_data = script_resp.json()
            
            jobs_db[job.id].status = "done"
            jobs_db[job.id].result = script_data
            logger.info(f"Job {job.id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job.id} failed: {e}")
        jobs_db[job.id].status = "failed"


@router.post("", response_model=JobResponse)
async def create_job(req: JobCreateRequest, background_tasks: BackgroundTasks):
    job = Job(user_id=req.user_id, prompt=req.prompt)
    jobs_db[job.id] = job
    background_tasks.add_task(process_job, job)
    return JobResponse(job_id=job.id, status=job.status)

@router.get("/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs_db[job_id]
    response = {"id": job.id, "status": job.status}
    if hasattr(job, "result"):
        response["result"] = job.result
    if job.niche:
        response["niche"] = job.niche
    if job.content_type:
        response["content_type"] = job.content_type
    return response

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    jobs_db[job_id].status = "cancelled"
    return {"status": "cancelled"}
""",
    "apps/api-server/routes/auth.py": """
from fastapi import APIRouter

router = APIRouter()

@router.post("/token")
async def validate_token():
    return {"status": "valid"}
""",
    "apps/api-server/routes/schedule.py": """
from fastapi import APIRouter

router = APIRouter()

@router.post("")
async def schedule_job():
    return {"status": "scheduled"}
""",
    "apps/api-server/middleware.py": """
from fastapi import Request
from loguru import logger

async def logging_middleware(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    return response
""",
    "services/classifier/classifier.py": """
from fastapi import FastAPI
from loguru import logger
from shared.schemas.api_schemas import AnalyzeRequest, AnalyzeResponse
import asyncio

app = FastAPI(title="Classifier Service")

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    logger.info(f"Analyzing prompt: {req.prompt}")
    # TODO: Replace with real LLM call
    await asyncio.sleep(1)
    
    niche = "educational" if "explain" in req.prompt.lower() else "entertainment"
    content_type = "informative"
    
    return AnalyzeResponse(
        niche=niche,
        content_type=content_type,
        confidence=0.95
    )
""",
    "services/script-generator/script_generator.py": """
from fastapi import FastAPI
from loguru import logger
from shared.schemas.api_schemas import GenerateScriptRequest, GenerateScriptResponse
import asyncio

app = FastAPI(title="Script Generator Service")

@app.post("/generate-script", response_model=GenerateScriptResponse)
async def generate_script(req: GenerateScriptRequest):
    logger.info(f"Generating script for job {req.job_id}")
    # TODO: Replace with real LLM call
    await asyncio.sleep(2)
    
    title = f"The Truth About {req.prompt}"
    script = f"Hook: Have you ever wondered about {req.prompt}?\\nBody: It's a fascinating topic in the {req.niche} space.\\nCall to Action: Like and subscribe for more {req.content_type} content!"
    hashtags = [f"#{req.niche.replace(' ', '')}", f"#{req.content_type.replace(' ', '')}", "#shorts"]
    
    return GenerateScriptResponse(
        title=title,
        script=script,
        hashtags=hashtags
    )
""",
    "services/script-generator/metadata_generator.py": """
from fastapi import FastAPI

app = FastAPI()

@app.post("/generate-metadata")
async def generate_metadata():
    return {"description": "Auto generated description", "tags": ["video"]}
""",
    "services/web-search/search.py": """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Web Search Service")

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
async def search(req: SearchRequest):
    # TODO: Implement Tavily/Serper search
    return {"facts": [f"Fact about {req.query}"], "sources": ["https://example.com"]}
""",
    "services/asset-generator/image_gen.py": """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Image Gen Service")

class AssetRequest(BaseModel):
    prompt: str

@app.post("/generate-assets")
async def generate_assets(req: AssetRequest):
    # TODO: Implement Runway/Kling/Midjourney API
    return {"images": ["https://via.placeholder.com/1080x1920.png"]}
""",
    "services/asset-generator/music.py": """
from fastapi import FastAPI

app = FastAPI()

@app.post("/get-music")
async def get_music():
    return {"audio_url": "https://example.com/music.mp3"}
""",
    "services/tts/tts.py": """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="TTS Service")

class TTSRequest(BaseModel):
    text: str

@app.post("/generate-audio")
async def generate_audio(req: TTSRequest):
    # TODO: Implement ElevenLabs TTS
    return {"audio_url": "https://example.com/voiceover.mp3"}
""",
    "services/subtitles/subtitles.py": """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Subtitles Service")

class SubtitlesRequest(BaseModel):
    audio_url: str

@app.post("/generate-subtitles")
async def generate_subtitles(req: SubtitlesRequest):
    return {"subtitles_url": "https://example.com/subs.srt"}
""",
    "services/renderer/render.py": """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Renderer Service")

class RenderRequest(BaseModel):
    job_id: str
    assets: dict

@app.post("/render")
async def render(req: RenderRequest):
    # TODO: Implement FFmpeg / Remotion rendering
    return {"job_id": req.job_id, "status": "rendering"}

@app.get("/render-status/{job_id}")
async def render_status(job_id: str):
    return {"status": "done", "videoUrl": "https://example.com/final.mp4", "thumbnailUrl": "https://example.com/thumb.jpg"}
""",
    "services/publisher/youtube.py": """
from fastapi import APIRouter

router = APIRouter()

@router.post("/youtube")
async def publish_youtube():
    # TODO: Implement YouTube Data API v3
    return {"status": "published"}
""",
    "services/publisher/instagram.py": """
from fastapi import APIRouter

router = APIRouter()

@router.post("/instagram")
async def publish_instagram():
    # TODO: Implement Meta Graph API
    return {"status": "published"}
""",
    "services/publisher/tiktok.py": """
from fastapi import APIRouter

router = APIRouter()

@router.post("/tiktok")
async def publish_tiktok():
    # TODO: Implement TikTok API
    return {"status": "published"}
""",
    "services/scheduler/scheduler.py": """
from fastapi import FastAPI

app = FastAPI(title="Scheduler Service")

@app.post("/schedule")
async def schedule():
    return {"status": "scheduled"}
""",
    "services/storage/storage.py": """
from fastapi import FastAPI

app = FastAPI(title="Storage Service")

@app.post("/upload")
async def upload():
    # TODO: Implement S3/Supabase storage
    return {"url": "https://example.com/file"}
""",
    "services/logging/logger.py": """
from loguru import logger
import sys

logger.configure(handlers=[{"sink": sys.stdout, "format": "{time} - {level} - {message}"}])
""",
    "apps/telegram-bot/bot.py": """
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
    welcome_text = "Welcome to Content Creation Automation Bot!\\nUse /create <prompt> to generate content."
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
                    message = f"**{result.get('title', 'Title')}**\\n\\n{result.get('script', '')}\\n\\n{' '.join(result.get('hashtags', []))}"
                    await update.message.reply_text(message, parse_mode='Markdown')
                    break
                elif status == "failed":
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
    main()
""",
    "apps/telegram-bot/commands/__init__.py": "",
    "apps/telegram-bot/handlers/__init__.py": "",
    "apps/telegram-bot/conversations/__init__.py": "",
    "apps/telegram-bot/notifications/__init__.py": "",
    "services/renderer/timeline/__init__.py": "",
    "services/renderer/ffmpeg/__init__.py": "",
    "services/renderer/templates/__init__.py": "",
    "Dockerfile": """
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
""",
    "requirements.txt": """
fastapi==0.104.1
uvicorn==0.24.0.post1
python-telegram-bot==20.6
pydantic==2.4.2
pydantic-settings==2.0.3
httpx==0.25.1
loguru==0.7.2
""",
    "docker-compose.yml": """
version: '3.8'

x-base-service: &base-service
  build:
    context: .
    dockerfile: Dockerfile
  env_file: .env
  volumes:
    - .:/app
  environment:
    - PYTHONPATH=/app

services:
  telegram-bot:
    <<: *base-service
    command: python apps/telegram-bot/bot.py
    environment:
      - PYTHONPATH=/app
      - API_SERVER_URL=http://api-server:8000
    depends_on:
      - api-server
    restart: always

  api-server:
    <<: *base-service
    command: uvicorn apps.api_server.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - CLASSIFIER_URL=http://classifier:8000
      - SCRIPT_GENERATOR_URL=http://script-generator:8000
    depends_on:
      - classifier
      - script-generator

  classifier:
    <<: *base-service
    command: uvicorn services.classifier.classifier:app --host 0.0.0.0 --port 8000

  script-generator:
    <<: *base-service
    command: uvicorn services.script_generator.script_generator:app --host 0.0.0.0 --port 8000

  web-search:
    <<: *base-service
    command: uvicorn services.web_search.search:app --host 0.0.0.0 --port 8000

  asset-generator:
    <<: *base-service
    command: uvicorn services.asset_generator.image_gen:app --host 0.0.0.0 --port 8000

  tts:
    <<: *base-service
    command: uvicorn services.tts.tts:app --host 0.0.0.0 --port 8000

  subtitles:
    <<: *base-service
    command: uvicorn services.subtitles.subtitles:app --host 0.0.0.0 --port 8000

  renderer:
    <<: *base-service
    command: uvicorn services.renderer.render:app --host 0.0.0.0 --port 8000

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: content_db
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"
""",
    ".env.example": """
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
TAVILY_API_KEY=
YOUTUBE_API_KEY=
META_ACCESS_TOKEN=
TIKTOK_API_KEY=
DATABASE_URL=postgresql://user:pass@postgres:5432/content_db
REDIS_URL=redis://redis:6379
S3_BUCKET=
SUPABASE_URL=
SUPABASE_KEY=
""",
    "README.md": """
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
- **Databases:** PostgreSQL, Redis
"""
}

def scaffold():
    for filepath, content in files.items():
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Avoid writing to an existing file if it's the backend/.env which was active but spec says create .env.example
        # We will write relative to current directory.
        with open(path, "w") as f:
            f.write(content.strip() + "\\n")
            
if __name__ == "__main__":
    scaffold()
    print("Scaffolding complete.")
