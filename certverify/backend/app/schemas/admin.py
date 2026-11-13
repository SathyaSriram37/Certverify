import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models.users import UserRole
from app.models.verification import JobStatus, FinalVerdict
from app.schemas.dashboard import DailyUploadStat


class AdminStats(BaseModel):
    total_users: int
    total_certificates: int
    verdicts: Dict[str, int]
    suspicious_this_week: int
    avg_processing_seconds: float
    daily_uploads_30d: List[DailyUploadStat]


class AdminUserItem(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    upload_count: int


class AdminUserUpdateRequest(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class AdminCertificateItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    created_at: datetime
    job_id: Optional[uuid.UUID] = None
    status: Optional[JobStatus] = None
    risk_score: Optional[int] = None
    final_verdict: Optional[FinalVerdict] = None
    is_suspicious: bool = False


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: str
    user_agent: str
    created_at: datetime

