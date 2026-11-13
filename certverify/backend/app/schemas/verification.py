import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from app.models.verification import JobStatus, ModuleStatus, RiskLevel, FinalVerdict
from app.schemas.certificates import CertificateDetailResponse


class VerificationResultResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    module_name: str
    status: ModuleStatus
    finding_summary: str
    details: Dict[str, Any]
    confidence_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RiskAssessmentResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    risk_score: int
    risk_level: RiskLevel
    final_verdict: FinalVerdict
    reasoning: str
    report_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobDetailResponse(BaseModel):
    id: uuid.UUID
    certificate_id: uuid.UUID
    status: JobStatus
    progress_percentage: int
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResultsResponse(BaseModel):
    job: JobDetailResponse
    results: List[VerificationResultResponse]
    risk_assessment: Optional[RiskAssessmentResponse] = None
    certificate: Optional[CertificateDetailResponse] = None


class ReportResponse(BaseModel):
    report_url: str

