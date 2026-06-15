from fastapi import FastAPI
from loguru import logger
from shared.schemas.api_schemas import AnalyzeRequest, AnalyzeResponse
import asyncio

app = FastAPI(title="Classifier Service")

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    logger.info(f"Analyzing prompt: {req.prompt}")
    # TODO: Replace with real LLM call
    await asyncio.sleep(1)
    
    niche = "educational" if "explain" in req.prompt.lower() else "entertainment"
    content_type = "informative"
    
    return AnalyzeResponse(
        niche=niche,
        content_type=content_type,
        confidence=0.95
    )\n