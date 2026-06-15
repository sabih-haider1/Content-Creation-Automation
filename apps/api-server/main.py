from fastapi import FastAPI, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
import httpx
from loguru import logger
from shared.schemas.api_schemas import JobCreateRequest, JobResponse, AnalyzeRequest, GenerateScriptRequest
from shared.models.job import Job
from apps.api_server.routes import jobs, auth, schedule

app = FastAPI(title="API Gateway")

app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(schedule.router, prefix="/schedule", tags=["schedule"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}\n