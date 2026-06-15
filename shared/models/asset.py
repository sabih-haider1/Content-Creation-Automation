from pydantic import BaseModel
from typing import List

class Asset(BaseModel):
    job_id: str
    images: List[str] = []
    videos: List[str] = []
    audio: str = ""\n