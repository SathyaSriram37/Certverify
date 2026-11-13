from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel
from app.models.verification import FinalVerdict, JobStatus, RiskLevel


class BatchCertificateItem(BaseModel):
    certificate_id: uuid.UUID
    filename: str
    job_id: Optional[uuid.UUID] = None
    status: JobStatus = JobStatus.PENDING
    progress_percentage: int = 0
    risk_score: Optional[int] = None
    risk_level: Optional[RiskLevel] = None
    final_verdict: Optional[FinalVerdict] = None
    candidate_name: Optional[str] = None
    organization_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BatchDetailResponse(BaseModel):
    batch_id: uuid.UUID
    batch_name: str
    total_count: int
    completed_count: int
    processing_count: int
    failed_count: int
    average_risk_score: Optional[float] = None
    status: str
    created_at: datetime
    certificates: List[BatchCertificateItem] = []


class BatchSummaryItem(BaseModel):
    batch_id: uuid.UUID
    batch_name: str
    total_count: int
    completed_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class BatchUploadResponse(BaseModel):
    batch_id: uuid.UUID
    batch_name: str
    total_count: int
    message: str
    certificates: List[BatchCertificateItem] = []

