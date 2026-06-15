from fastapi import APIRouter

router = APIRouter()

@router.post("/token")
async def validate_token():
    return {"status": "valid"}\n