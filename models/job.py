from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
class BatchJob(SQLModel, table=True):
    __tablename__ = "batch_jobs"
    job_id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True)
    username: str
    filename: str
    status: JobStatus = Field(default=JobStatus.QUEUED, index=True)
    priority: JobPriority = Field(default=JobPriority.NORMAL)
    total_rows: int = 0
    completed_rows: int = 0
    failed_rows: int = 0
    error_message: Optional[str] = None
    result_url: Optional[str] = None 
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None