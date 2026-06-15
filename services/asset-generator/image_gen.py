from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Image Gen Service")

class AssetRequest(BaseModel):
    prompt: str

@app.post("/generate-assets")
async def generate_assets(req: AssetRequest):
    # TODO: Implement Runway/Kling/Midjourney API
    return {"images": ["https://via.placeholder.com/1080x1920.png"]}\n