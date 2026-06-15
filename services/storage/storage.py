from fastapi import FastAPI

app = FastAPI(title="Storage Service")

@app.post("/upload")
async def upload():
    # TODO: Implement S3/Supabase storage
    return {"url": "https://example.com/file"}\n