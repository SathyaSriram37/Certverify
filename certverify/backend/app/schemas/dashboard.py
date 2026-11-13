import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.verification import JobStatus, FinalVerdict


class DailyUploadStat(BaseModel):
    date: str
    count: int


class RecentUploadItem(BaseModel):
    certificate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    filename: str
    file_type: str
    status: JobStatus
    risk_score: Optional[int] = None
    final_verdict: Optional[FinalVerdict] = None
    created_at: datetime


class DashboardStats(BaseModel):
    total_uploads: int
    verified_count: int
    suspicious_count: int
    unable_count: int
    processing_count: int
    avg_risk_score: float
    uploads_by_day: List[DailyUploadStat]
    recent_uploads: List[RecentUploadItem]

