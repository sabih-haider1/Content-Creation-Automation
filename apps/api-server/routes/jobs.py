from fastapi import APIRouter, BackgroundTasks, HTTPException
import httpx
from loguru import logger
from shared.schemas.api_schemas import JobCreateRequest, JobResponse, GenerateScriptRequest
from shared.models.job import Job
from urllib.parse import urlparse
from bs4 import BeautifulSoup

router = APIRouter()
jobs_db = {}

CLASSIFIER_URL = "http://classifier:8000"
SCRIPT_GENERATOR_URL = "http://script-generator:8000"

async def process_job(job: Job):
    try:
        async with httpx.AsyncClient() as client:
            # Check if prompt is a URL
            parsed_url = urlparse(job.prompt)
            if parsed_url.scheme in ["http", "https"]:
                logger.info(f"URL detected for job {job.id}: {job.prompt}")
                try:
                    resp = await client.get(job.prompt, timeout=10.0, follow_redirects=True)
                    if resp.status_code != 200:
                        logger.warning(f"URL not accessible: {job.prompt} (Status: {resp.status_code})")
                        job.status = "failed"
                        job.error_message = "not accessible"
                        return
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Remove script and style elements
                    for script_or_style in soup(["script", "style"]):
                        script_or_style.decompose()
                    
                    text = soup.get_text(separator=' ', strip=True)
                    # Limit text length to avoid overloading LLMs
                    job.prompt = text[:2000]
                    logger.info(f"Extracted {len(text)} characters from {job.prompt[:50]}...")
                except Exception as e:
                    logger.error(f"Error fetching URL {job.prompt}: {e}")
                    job.status = "failed"
                    job.error_message = "not accessible"
                    return

            # 1. Analyze
            logger.info(f"Analyzing job {job.id}")
            jobs_db[job.id].status = "analyzing"
            analyze_resp = await client.post(f"{CLASSIFIER_URL}/analyze", json={"prompt": job.prompt}, timeout=30.0)
            analyze_resp.raise_for_status()
            analysis = analyze_resp.json()
            
            job.niche = analysis["niche"]
            job.content_type = analysis["content_type"]
            
            # 2. Generate Script
            logger.info(f"Generating script for job {job.id}")
            jobs_db[job.id].status = "generating_script"
            script_req = GenerateScriptRequest(
                job_id=job.id,
                prompt=job.prompt,
                niche=job.niche,
                content_type=job.content_type
            )
            script_resp = await client.post(f"{SCRIPT_GENERATOR_URL}/generate-script", json=script_req.model_dump(), timeout=30.0)
            script_resp.raise_for_status()
            script_data = script_resp.json()
            
            jobs_db[job.id].status = "done"
            jobs_db[job.id].result = script_data
            logger.info(f"Job {job.id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job.id} failed: {e}")
        jobs_db[job.id].status = "failed"


@router.post("", response_model=JobResponse)
async def create_job(req: JobCreateRequest, background_tasks: BackgroundTasks):
    job = Job(user_id=req.user_id, prompt=req.prompt)
    jobs_db[job.id] = job
    background_tasks.add_task(process_job, job)
    return JobResponse(job_id=job.id, status=job.status)

@router.get("/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs_db[job_id]
    response = {"id": job.id, "status": job.status}
    if hasattr(job, "result") and job.result:
        response["result"] = job.result
    if job.niche:
        response["niche"] = job.niche
    if job.content_type:
        response["content_type"] = job.content_type
    if job.error_message:
        response["error_message"] = job.error_message
    return response

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    jobs_db[job_id].status = "cancelled"
    return {"status": "cancelled"}\n