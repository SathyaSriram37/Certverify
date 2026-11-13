import uuid
from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel
from app.models.verification import JobStatus, FinalVerdict

T = TypeVar("T")


class UploadResponse(BaseModel):
    certificate_id: uuid.UUID
    job_id: uuid.UUID
    filename: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    job_id: uuid.UUID
    status: JobStatus
    progress_percentage: int
    current_step: Optional[str] = None
    error_message: Optional[str] = None


class CertificateListItem(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_url: str
    file_type: str
    file_size_bytes: int
    created_at: datetime
    job_id: Optional[uuid.UUID] = None
    job_status: Optional[JobStatus] = None
    risk_score: Optional[int] = None
    final_verdict: Optional[FinalVerdict] = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class CertificateDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    file_url: str
    cloudinary_public_id: str
    file_type: str
    file_size_bytes: int
    mime_type: str
    created_at: datetime

    class Config:
        from_attributes = True

