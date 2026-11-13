import uuid
from datetime import datetime
import enum
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ModuleStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FinalVerdict(str, enum.Enum):
    VERIFIED = "VERIFIED"
    SUSPICIOUS = "SUSPICIOUS"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"


class VerificationJob(Base):
    __tablename__ = "verification_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"), default=JobStatus.PENDING, nullable=False, index=True
    )
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    certificate = relationship("Certificate", back_populates="verification_jobs")
    results = relationship(
        "VerificationResult", back_populates="job", cascade="all, delete-orphan", order_by="VerificationResult.created_at"
    )
    risk_assessment = relationship(
        "RiskAssessment", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[ModuleStatus] = mapped_column(
        Enum(ModuleStatus, name="module_status_enum"), nullable=False
    )
    finding_summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    job = relationship("VerificationJob", back_populates="results")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_jobs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum"), nullable=False
    )
    final_verdict: Mapped[FinalVerdict] = mapped_column(
        Enum(FinalVerdict, name="final_verdict_enum"), nullable=False, index=True
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    report_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    job = relationship("VerificationJob", back_populates="risk_assessment")


class CertificateFingerprint(Base):
    __tablename__ = "certificate_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificates.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    phash: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    dhash: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    certificate = relationship("Certificate", back_populates="fingerprint")

