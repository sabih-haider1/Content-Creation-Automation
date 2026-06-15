from pydantic import BaseModel
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    prompt: str

class AnalyzeResponse(BaseModel):
    niche: str
    content_type: str
    confidence: float

class GenerateScriptRequest(BaseModel):
    job_id: str
    prompt: str
    niche: str
    content_type: str

class GenerateScriptResponse(BaseModel):
    title: str
    script: str
    hashtags: List[str]

class JobCreateRequest(BaseModel):
    user_id: str
    prompt: str

class JobResponse(BaseModel):
    job_id: str
    status: str\n