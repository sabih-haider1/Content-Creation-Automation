from fastapi import FastAPI

app = FastAPI()

@app.post("/generate-metadata")
async def generate_metadata():
    return {"description": "Auto generated description", "tags": ["video"]}\n