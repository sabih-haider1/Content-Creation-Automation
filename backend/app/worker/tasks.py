from celery import Celery
from app.services.gemini import generate_script
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Redis
celery_app = Celery("content_worker", broker="redis://localhost:6379/0")

@celery_app.task
def generate_content_pipeline(prompt: str, chat_id: int):
    print(f"[{chat_id}] Starting pipeline for prompt: {prompt}")

    # Step 1: AI Scripting
    blueprint = generate_script(prompt)
    print(f"[{chat_id}] Blueprint Generated: \n{blueprint}")

    return "Pipeline Completed"
