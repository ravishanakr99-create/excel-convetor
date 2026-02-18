"""Job models."""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobCreate(BaseModel):
    name: Optional[str] = None


class Job(BaseModel):
    id: str
    user_id: int
    name: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    total_files: int = 0
    processed_files: int = 0
    progress_percent: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    file_names: List[str] = []

    class Config:
        from_attributes = True
