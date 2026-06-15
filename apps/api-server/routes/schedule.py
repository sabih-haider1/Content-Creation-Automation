from fastapi import APIRouter

router = APIRouter()

@router.post("")
async def schedule_job():
    return {"status": "scheduled"}\n