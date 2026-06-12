from fastapi import FastAPI
from app.api.webhook import router as webhook_router

app = FastAPI(title="Content OS API")

app.include_router(webhook_router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "System Online", "service": "Content Generation OS"}
