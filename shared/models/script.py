from pydantic import BaseModel
from typing import List

class Script(BaseModel):
    job_id: str
    title: str
    script: str
    hashtags: List[str]\n