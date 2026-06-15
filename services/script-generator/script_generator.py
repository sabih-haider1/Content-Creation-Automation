from fastapi import FastAPI
from loguru import logger
from shared.schemas.api_schemas import GenerateScriptRequest, GenerateScriptResponse
import asyncio

app = FastAPI(title="Script Generator Service")

@app.post("/generate-script", response_model=GenerateScriptResponse)
async def generate_script(req: GenerateScriptRequest):
    logger.info(f"Generating script for job {req.job_id}")
    # TODO: Replace with real LLM call
    await asyncio.sleep(2)
    
    title = f"The Truth About {req.prompt}"
    script = f"Hook: Have you ever wondered about {req.prompt}?\nBody: It's a fascinating topic in the {req.niche} space.\nCall to Action: Like and subscribe for more {req.content_type} content!"
    hashtags = [f"#{req.niche.replace(' ', '')}", f"#{req.content_type.replace(' ', '')}", "#shorts"]
    
    return GenerateScriptResponse(
        title=title,
        script=script,
        hashtags=hashtags
    )\n