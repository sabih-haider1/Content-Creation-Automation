from fastapi import APIRouter, Request
from app.worker.tasks import generate_content_pipeline

router = APIRouter()

@router.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    try:
        message = data["message"]["text"]
        chat_id = data["message"]["chat"]["id"]
    except KeyError:
        return {"status": "ignored", "reason": "Not a text message"}

    # Trigger background job
    generate_content_pipeline.delay(prompt=message, chat_id=chat_id)

    return {"status": "Task queued successfully"}
