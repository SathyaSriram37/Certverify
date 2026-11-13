import csv
import io
import os
import uuid
import zipfile
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.batch import BatchVerification
from app.models.certificates import Certificate
from app.models.users import User
from app.models.verification import JobStatus, RiskAssessment, VerificationJob, VerificationResult
from app.schemas.batch import BatchCertificateItem, BatchDetailResponse, BatchSummaryItem, BatchUploadResponse
from app.services.audit_service import log_action
from app.services.storage_service import storage_service
from app.tasks.verification_task import run_verification

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


@router.post("/upload", response_model=BatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_batch(
    request: Request,
    batch_name: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one certificate or ZIP archive is required",
        )

    extracted_items = []

    # Check if single ZIP file was provided
    if len(files) == 1 and files[0].filename and files[0].filename.lower().endswith(".zip"):
        zip_file = files[0]
        zip_bytes = await zip_file.read()
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    # Security: ZipSlip prevention
                    filename = os.path.basename(member.filename)
                    if not filename or filename.startswith(".") or ".." in member.filename:
                        continue
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        content = zf.read(member.filename)
                        if len(content) <= settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                            extracted_items.append((filename, content, ext))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or corrupted ZIP archive: {exc}",
            )
    else:
        # Standard multi-file upload
        for f in files:
            if not f.filename:
                continue
            ext = os.path.splitext(f.filename)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                content = await f.read()
                if len(content) <= settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                    extracted_items.append((f.filename, content, ext))

    if not extracted_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid PDF or image certificates found in upload (allowed: .pdf, .jpg, .png)",
        )

    # Create Batch record
    resolved_batch_name = batch_name.strip() if batch_name and batch_name.strip() else f"Batch Verification ({len(extracted_items)} files) - {datetime.utcnow().strftime('%d %b %Y %H:%M')}"
    batch = BatchVerification(
        user_id=current_user.id,
        batch_name=resolved_batch_name,
        total_count=len(extracted_items),
        status="PROCESSING",
    )
    db.add(batch)
    await db.flush()

    response_items: List[BatchCertificateItem] = []

    # Process and queue each certificate
    for fname, content, ext in extracted_items:
        stored = await storage_service.upload_certificate(
            file_bytes=content,
            filename=fname,
            user_id=str(current_user.id),
        )

        mime = "application/pdf" if ext == ".pdf" else f"image/{ext.lstrip('.')}"
        cert = Certificate(
            user_id=current_user.id,
            batch_id=batch.id,
            original_filename=fname,
            file_url=stored.url,
            cloudinary_public_id=stored.public_id,
            file_type=ext.lstrip(".").upper(),
            file_size_bytes=len(content),
            mime_type=mime,
            is_deleted=False,
        )
        db.add(cert)
        await db.flush()

        # Cache persistent copy by cert.id for instant Celery access
        try:
            cert_local_name = f"{cert.id}{ext}"
            cert_local_file = os.path.join(storage_service.upload_dir, cert_local_name)
            with open(cert_local_file, "wb") as f_out:
                f_out.write(content)
        except Exception:
            pass

        # Create VerificationJob
        job = VerificationJob(
            certificate_id=cert.id,
            status=JobStatus.PENDING,
            progress_percentage=0,
            current_step="Queued in Batch",
        )
        db.add(job)
        await db.flush()

        # Enqueue async Celery worker
        try:
            run_verification.delay(str(job.id), str(cert.id))
        except Exception:
            pass

        response_items.append(
            BatchCertificateItem(
                certificate_id=cert.id,
                filename=cert.original_filename,
                job_id=job.id,
                status=job.status,
                progress_percentage=0,
                created_at=cert.created_at,
            )
        )

    await db.commit()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        action="BATCH_UPLOAD",
        resource_type="BATCH",
        resource_id=str(batch.id),
        details={"total_count": len(extracted_items), "batch_name": resolved_batch_name},
        request=request,
    )

    return BatchUploadResponse(
        batch_id=batch.id,
        batch_name=resolved_batch_name,
        total_count=len(extracted_items),
        message=f"Successfully queued {len(extracted_items)} certificates for automated verification",
        certificates=response_items,
    )


@router.get("/{batch_id}", response_model=BatchDetailResponse)
async def get_batch_details(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(BatchVerification)
        .where(BatchVerification.id == batch_id, BatchVerification.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch verification not found",
        )

    # Fetch certificates with jobs and risk assessment
    cert_stmt = (
        select(Certificate)
        .where(Certificate.batch_id == batch_id, Certificate.is_deleted == False)
        .options(
            selectinload(Certificate.verification_jobs).selectinload(VerificationJob.risk_assessment),
            selectinload(Certificate.verification_jobs).selectinload(VerificationJob.results),
        )
        .order_by(desc(Certificate.created_at))
    )
    cert_res = await db.execute(cert_stmt)
    certs = cert_res.scalars().all()

    items: List[BatchCertificateItem] = []
    completed_cnt = 0
    processing_cnt = 0
    failed_cnt = 0
    risk_scores = []

    for c in certs:
        job = c.verification_jobs[0] if c.verification_jobs else None
        ra = job.risk_assessment if job else None

        cand_name = None
        org_name = None
        if job and job.results:
            for r in job.results:
                if r.module_name == "ENTITY_EXTRACTION" and r.details:
                    cand_name = r.details.get("candidate_name")
                    org_name = r.details.get("organization_name")

        if job:
            if job.status == JobStatus.COMPLETED:
                completed_cnt += 1
            elif job.status == JobStatus.FAILED:
                failed_cnt += 1
            else:
                processing_cnt += 1

            if ra and ra.risk_score is not None:
                risk_scores.append(ra.risk_score)

        items.append(
            BatchCertificateItem(
                certificate_id=c.id,
                filename=c.original_filename,
                job_id=job.id if job else None,
                status=job.status if job else JobStatus.PENDING,
                progress_percentage=job.progress_percentage if job else 0,
                risk_score=ra.risk_score if ra else None,
                risk_level=ra.risk_level if ra else None,
                final_verdict=ra.final_verdict if ra else None,
                candidate_name=cand_name,
                organization_name=org_name,
                created_at=c.created_at,
            )
        )

    avg_score = round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else None

    # Update batch status if all finished
    if len(certs) > 0 and (completed_cnt + failed_cnt) == len(certs):
        if batch.status != "COMPLETED":
            batch.status = "COMPLETED"
            batch.completed_at = datetime.utcnow()
            await db.commit()

    return BatchDetailResponse(
        batch_id=batch.id,
        batch_name=batch.batch_name,
        total_count=len(certs),
        completed_count=completed_cnt,
        processing_count=processing_cnt,
        failed_count=failed_cnt,
        average_risk_score=avg_score,
        status=batch.status,
        created_at=batch.created_at,
        certificates=items,
    )


@router.get("/{batch_id}/export")
async def export_batch_csv(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(BatchVerification)
        .where(BatchVerification.id == batch_id, BatchVerification.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )

    cert_stmt = (
        select(Certificate)
        .where(Certificate.batch_id == batch_id, Certificate.is_deleted == False)
        .options(
            selectinload(Certificate.verification_jobs).selectinload(VerificationJob.risk_assessment),
            selectinload(Certificate.verification_jobs).selectinload(VerificationJob.results),
        )
        .order_by(desc(Certificate.created_at))
    )
    cert_res = await db.execute(cert_stmt)
    certs = cert_res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Certificate ID",
        "Original Filename",
        "Candidate Name",
        "Issuing Organization",
        "Credential ID",
        "Status",
        "Risk Score (0-100)",
        "Risk Level",
        "Final Verdict",
        "OCR Confidence",
        "Company Verified",
        "ISO Status",
        "Forensics Status",
        "Verification Date",
    ])

    for c in certs:
        job = c.verification_jobs[0] if c.verification_jobs else None
        ra = job.risk_assessment if job else None

        cand_name = "N/A"
        org_name = "N/A"
        cred_id = "N/A"
        ocr_conf = "N/A"
        comp_ver = "N/A"
        iso_stat = "N/A"
        foren_stat = "N/A"

        if job and job.results:
            for r in job.results:
                if r.module_name == "ENTITY_EXTRACTION" and r.details:
                    cand_name = r.details.get("candidate_name") or "N/A"
                    org_name = r.details.get("organization_name") or "N/A"
                    cred_id = r.details.get("cert_number") or "N/A"
                elif r.module_name == "OCR_EXTRACTION":
                    ocr_conf = f"{r.confidence_score:.0%}" if r.confidence_score else "N/A"
                elif r.module_name == "COMPANY_INTELLIGENCE":
                    comp_ver = r.status.value
                elif r.module_name == "ISO_VERIFICATION":
                    iso_stat = r.finding_summary
                elif r.module_name == "IMAGE_FORENSICS":
                    foren_stat = r.status.value

        writer.writerow([
            str(c.id),
            c.original_filename,
            cand_name,
            org_name,
            cred_id,
            job.status.value if job else "PENDING",
            ra.risk_score if (ra and ra.risk_score is not None) else "N/A",
            ra.risk_level.value if (ra and ra.risk_level) else "N/A",
            ra.final_verdict.value if (ra and ra.final_verdict) else "N/A",
            ocr_conf,
            comp_ver,
            iso_stat,
            foren_stat,
            c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    csv_data = output.getvalue()
    filename = f"CertVerify_Audit_Batch_{str(batch_id)[:8]}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/", response_model=List[BatchSummaryItem])
async def list_batches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(BatchVerification)
        .where(BatchVerification.user_id == current_user.id)
        .order_by(desc(BatchVerification.created_at))
        .limit(50)
    )
    res = await db.execute(stmt)
    batches = res.scalars().all()

    items = []
    for b in batches:
        # Count completed certificates
        c_stmt = (
            select(func.count(Certificate.id))
            .join(VerificationJob, VerificationJob.certificate_id == Certificate.id)
            .where(Certificate.batch_id == b.id, VerificationJob.status == JobStatus.COMPLETED)
        )
        c_res = await db.execute(c_stmt)
        completed_cnt = c_res.scalar() or 0

        items.append(
            BatchSummaryItem(
                batch_id=b.id,
                batch_name=b.batch_name,
                total_count=b.total_count,
                completed_count=completed_cnt,
                status=b.status,
                created_at=b.created_at,
            )
        )

    return items

