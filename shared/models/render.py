from pydantic import BaseModel

class Render(BaseModel):
    job_id: str
    video_url: str
    thumbnail_url: str\n