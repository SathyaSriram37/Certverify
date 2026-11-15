import uuid
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.certificates import Certificate
from app.models.users import User
from app.models.verification import JobStatus, RiskAssessment, VerificationJob, VerificationResult
from app.schemas.certificates import CertificateDetailResponse, JobStatusResponse
from app.schemas.verification import (
    JobDetailResponse,
    ReportResponse,
    ResultsResponse,
    RiskAssessmentResponse,
    VerificationResultResponse,
)
from app.services.audit_service import log_action
from app.services.report.report_generator import generate_report

router = APIRouter()


async def _get_authorized_job(
    job_id: str,
    current_user: User,
    db: AsyncSession,
) -> tuple[VerificationJob, Certificate]:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    job_stmt = select(VerificationJob).where(VerificationJob.id == job_uuid)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification job not found",
        )

    cert_stmt = select(Certificate).where(Certificate.id == job.certificate_id)
    cert_res = await db.execute(cert_stmt)
    cert = cert_res.scalar_one_or_none()

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated certificate not found",
        )

    # Ownership check
    if cert.user_id != current_user.id and current_user.role.value not in ["ADMIN", "HR_VERIFIER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to verification job",
        )

    return job, cert


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job, _ = await _get_authorized_job(job_id, current_user, db)
    return JobStatusResponse(
        id=job.id,
        job_id=job.id,
        status=job.status,
        progress_percentage=job.progress_percentage,
        current_step=job.current_step,
        error_message=job.error_message,
    )


@router.post("/{job_id}/retry", response_model=JobStatusResponse)
async def retry_verification_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job, cert = await _get_authorized_job(job_id, current_user, db)

    # Reset job status
    job.status = JobStatus.PENDING
    job.progress_percentage = 0
    job.current_step = "Queued for re-analysis"
    job.error_message = None
    await db.commit()
    await db.refresh(job)

    # Dispatch verification task: Celery or BackgroundTasks
    try:
        from app.tasks.verification_task import run_verification
        run_verification.delay(str(job.id), str(cert.id))
    except Exception:
        from app.tasks.verification_task import execute_verification_pipeline
        background_tasks.add_task(execute_verification_pipeline, str(job.id), str(cert.id))

    await log_action(
        db=db,
        user_id=current_user.id,
        action="RETRY_VERIFICATION",
        resource_type="VERIFICATION_JOB",
        resource_id=str(job.id),
        request=request,
    )

    return JobStatusResponse(
        id=job.id,
        job_id=job.id,
        status=job.status,
        progress_percentage=job.progress_percentage,
        current_step=job.current_step,
        error_message=job.error_message,
    )


@router.get("/{job_id}/results", response_model=ResultsResponse)
async def get_job_results(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job, cert = await _get_authorized_job(job_id, current_user, db)

    # Results
    res_stmt = (
        select(VerificationResult)
        .where(VerificationResult.job_id == job.id)
        .order_by(VerificationResult.created_at)
    )
    res_exec = await db.execute(res_stmt)
    results = res_exec.scalars().all()

    # Risk Assessment
    ra_stmt = select(RiskAssessment).where(RiskAssessment.job_id == job.id)
    ra_exec = await db.execute(ra_stmt)
    risk_assessment = ra_exec.scalar_one_or_none()

    return ResultsResponse(
        job=JobDetailResponse.model_validate(job),
        results=[VerificationResultResponse.model_validate(r) for r in results],
        risk_assessment=RiskAssessmentResponse.model_validate(risk_assessment) if risk_assessment else None,
        certificate=CertificateDetailResponse.model_validate(cert),
    )


@router.get("/{job_id}/report", response_model=ReportResponse)
async def get_job_report(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job, _ = await _get_authorized_job(job_id, current_user, db)

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification is not yet complete. Please wait until status is COMPLETED.",
        )

    # Ensure local PDF is generated
    import os
    reports_dir = settings.REPORTS_DIR
    os.makedirs(reports_dir, exist_ok=True)
    local_pdf = os.path.join(reports_dir, f"report_{job_id}.pdf")
    if not os.path.exists(local_pdf):
        await generate_report(job_id, db)

    report_url = f"/api/v1/verify/{job_id}/report/download"

    await log_action(
        db=db,
        user_id=current_user.id,
        action="DOWNLOAD_REPORT",
        resource_type="REPORT",
        resource_id=job_id,
        request=request,
    )

    return ReportResponse(report_url=report_url)


@router.get("/{job_id}/report/download")
async def download_report_pdf(
    job_id: str,
    request: Request,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    import os
    from fastapi.responses import Response

    auth_header = request.headers.get("Authorization")
    raw_token = None
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header.replace("Bearer ", "").strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required to download report",
        )

    from app.core.security import decode_token
    payload = decode_token(raw_token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    user = await db.get(User, uuid.UUID(user_id_str))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    job, _ = await _get_authorized_job(job_id, user, db)

    reports_dir = settings.REPORTS_DIR
    os.makedirs(reports_dir, exist_ok=True)
    local_pdf = os.path.join(reports_dir, f"report_{job_id}.pdf")
    if not os.path.exists(local_pdf):
        await generate_report(job_id, db)

    with open(local_pdf, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="CertVerify_Audit_Report_{str(job_id)[:8]}.pdf"',
            "Content-Type": "application/pdf",
        },
    )

