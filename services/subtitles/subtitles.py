from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Subtitles Service")

class SubtitlesRequest(BaseModel):
    audio_url: str

@app.post("/generate-subtitles")
async def generate_subtitles(req: SubtitlesRequest):
    return {"subtitles_url": "https://example.com/subs.srt"}\n