from fastapi import FastAPI

app = FastAPI()

@app.post("/get-music")
async def get_music():
    return {"audio_url": "https://example.com/music.mp3"}\n