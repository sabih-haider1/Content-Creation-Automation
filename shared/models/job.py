from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    prompt: str
    niche: Optional[str] = None
    content_type: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)\n