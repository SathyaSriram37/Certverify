import logging
import os
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.certificates import Certificate
from app.models.users import User
from app.models.verification import JobStatus, RiskAssessment, VerificationJob
from app.schemas.certificates import (
    CertificateListItem,
    PaginatedResponse,
    UploadResponse,
)
from app.services.audit_service import log_action
from app.services.storage_service import storage_service
from app.tasks.verification_task import execute_verification_pipeline, run_verification

logger = logging.getLogger(__name__)

try:
    import magic  # type: ignore
    MAGIC_AVAILABLE = True
except Exception:
    MAGIC_AVAILABLE = False

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_certificate(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid certificate file is required",
        )

    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Detect MIME type
    detected_mime = None
    if MAGIC_AVAILABLE:
        try:
            detected_mime = magic.from_buffer(content, mime=True)
        except Exception as mime_err:
            logger.debug("magic MIME detection failed: %s", mime_err)

    if not detected_mime:
        detected_mime = file.content_type or "application/octet-stream"

    allowed_mimes = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    # Check mime or file extension
    ext = os.path.splitext(file.filename)[1].lower()
    is_valid_ext = ext in [".pdf", ".jpg", ".jpeg", ".png"]
    if detected_mime not in allowed_mimes and not is_valid_ext:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, JPG, and PNG certificate documents are supported",
        )

    file_type = ext.lstrip(".").upper() if ext else "UNKNOWN"

    # Upload to storage
    stored = await storage_service.upload_certificate(
        file_bytes=content,
        filename=file.filename,
        user_id=str(current_user.id),
    )

    # Create Certificate row
    cert = Certificate(
        user_id=current_user.id,
        original_filename=file.filename,
        file_url=stored.url,
        cloudinary_public_id=stored.public_id,
        file_type=file_type,
        file_size_bytes=len(content),
        mime_type=detected_mime,
        is_deleted=False,
    )
    db.add(cert)
    await db.flush()

    # Guarantee local file availability by certificate ID for instant Celery pipeline processing
    try:
        cert_local_name = f"{cert.id}{ext}"
        cert_local_file = os.path.join(storage_service.upload_dir, cert_local_name)
        with open(cert_local_file, "wb") as f:
            f.write(content)
        # Also ensure original filename exists in upload_dir for fallback
        orig_file_path = os.path.join(storage_service.upload_dir, file.filename)
        with open(orig_file_path, "wb") as f:
            f.write(content)
    except Exception as file_err:
        logger.warning("Could not persist local certificate copies for %s: %s", cert.id, file_err)

    # Create VerificationJob row
    job = VerificationJob(
        certificate_id=cert.id,
        status=JobStatus.PENDING,
        progress_percentage=0,
        current_step="Queued for analysis",
    )
    db.add(job)
    await db.commit()
    await db.refresh(cert)
    await db.refresh(job)

    # Trigger async verification task: Celery worker (Primary) or FastAPI BackgroundTasks (Resilient Fallback)
    try:
        run_verification.delay(str(job.id), str(cert.id))
    except Exception as exc:
        logger.warning(
            "Celery broker unavailable (%s). Executing verification via in-process background task.",
            exc,
        )
        background_tasks.add_task(execute_verification_pipeline, str(job.id), str(cert.id))

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        action="UPLOAD",
        resource_type="CERTIFICATE",
        resource_id=str(cert.id),
        request=request,
    )

    return UploadResponse(
        certificate_id=cert.id,
        job_id=job.id,
        filename=cert.original_filename,
        status=job.status,
    )


@router.get("/", response_model=PaginatedResponse[CertificateListItem])
async def list_certificates(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status_filter: JobStatus | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * size

    # Base query for certificates of user
    base_query = (
        select(Certificate)
        .where(Certificate.user_id == current_user.id, Certificate.is_deleted == False)
    )

    if status_filter:
        base_query = base_query.where(
            Certificate.id.in_(
                select(VerificationJob.certificate_id).where(VerificationJob.status == status_filter)
            )
        )

    total_query = select(func.count()).select_from(base_query.subquery())
    total_res = await db.execute(total_query)
    total = total_res.scalar() or 0

    certs_query = (
        base_query
        .order_by(desc(Certificate.created_at))
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(certs_query)
    certs = result.scalars().all()

    items: list[CertificateListItem] = []
    if certs:
        cert_ids = [c.id for c in certs]
        # Batch fetch all verification jobs for these certificates
        job_stmt = (
            select(VerificationJob)
            .where(VerificationJob.certificate_id.in_(cert_ids))
            .order_by(desc(VerificationJob.created_at))
        )
        job_res = await db.execute(job_stmt)
        all_jobs = job_res.scalars().all()

        # Map certificate_id -> latest job
        latest_jobs: dict = {}
        for j in all_jobs:
            if j.certificate_id not in latest_jobs:
                latest_jobs[j.certificate_id] = j

        # Batch fetch risk assessments for these jobs
        job_ids = [j.id for j in latest_jobs.values()]
        risk_map: dict = {}
        if job_ids:
            ra_stmt = select(RiskAssessment).where(RiskAssessment.job_id.in_(job_ids))
            ra_res = await db.execute(ra_stmt)
            for ra in ra_res.scalars().all():
                risk_map[ra.job_id] = ra

        for cert in certs:
            latest_job = latest_jobs.get(cert.id)
            ra = risk_map.get(latest_job.id) if latest_job else None

            items.append(
                CertificateListItem(
                    id=cert.id,
                    original_filename=cert.original_filename,
                    file_url=cert.file_url,
                    file_type=cert.file_type,
                    file_size_bytes=cert.file_size_bytes,
                    created_at=cert.created_at,
                    job_id=latest_job.id if latest_job else None,
                    job_status=latest_job.status if latest_job else None,
                    risk_score=ra.risk_score if ra else None,
                    final_verdict=ra.final_verdict if ra else None,
                )
            )

    pages = (total + size - 1) // size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.delete("/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certificate(
    certificate_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cert_uuid = uuid.UUID(certificate_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid certificate ID format",
        )

    stmt = select(Certificate).where(
        Certificate.id == cert_uuid,
        Certificate.is_deleted == False,
    )
    result = await db.execute(stmt)
    cert = result.scalar_one_or_none()

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )

    # Verify ownership or staff privileges
    if cert.user_id != current_user.id and current_user.role.value not in ["ADMIN", "HR_VERIFIER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to delete this certificate",
        )

    if cert.cloudinary_public_id:
        try:
            await storage_service.delete_file(cert.cloudinary_public_id)
        except Exception as storage_err:
            logger.warning("Failed to delete storage file %s: %s", cert.cloudinary_public_id, storage_err)

    cert.is_deleted = True
    await db.commit()

    await log_action(
        db=db,
        user_id=current_user.id,
        action="DELETE",
        resource_type="CERTIFICATE",
        resource_id=str(cert.id),
        request=request,
    )

