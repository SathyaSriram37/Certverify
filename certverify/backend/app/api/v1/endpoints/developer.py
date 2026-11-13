import hashlib
import os
import secrets
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_or_api_key
from app.models.certificates import Certificate
from app.models.developer import ApiKey, WebhookConfig
from app.models.users import User
from app.models.verification import JobStatus, VerificationJob
from app.schemas.certificates import UploadResponse
from app.schemas.developer import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    WebhookCreate,
    WebhookResponse,
    WebhookTestResponse,
)
from app.services.audit_service import log_action
from app.services.storage_service import storage_service
from app.services.webhook_service import dispatch_webhook_sync
from app.tasks.verification_task import run_verification

router = APIRouter()


# --- API KEY MANAGEMENT ---

@router.post("/keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token_suffix = secrets.token_urlsafe(32)
    short_prefix = f"cv_live_{secrets.token_hex(4)}"
    raw_api_key = f"{short_prefix}_{token_suffix}"

    # Hash using SHA-256
    hashed = hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()

    key_record = ApiKey(
        user_id=current_user.id,
        name=data.name.strip(),
        key_prefix=short_prefix,
        hashed_key=hashed,
        rate_limit_per_minute=data.rate_limit_per_minute,
        is_active=True,
    )
    db.add(key_record)
    await db.commit()
    await db.refresh(key_record)

    return ApiKeyCreatedResponse(
        id=key_record.id,
        name=key_record.name,
        raw_key=raw_api_key,
        key_prefix=short_prefix,
        rate_limit_per_minute=key_record.rate_limit_per_minute,
        created_at=key_record.created_at,
    )


@router.get("/keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .order_by(desc(ApiKey.created_at))
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    res = await db.execute(stmt)
    key_record = res.scalar_one_or_none()
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found",
        )
    key_record.is_active = False
    await db.commit()
    return None


# --- WEBHOOK CONFIGURATION ---

@router.get("/webhook", response_model=Optional[WebhookResponse])
async def get_webhook_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WebhookConfig).where(WebhookConfig.user_id == current_user.id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


@router.post("/webhook", response_model=WebhookResponse)
async def update_webhook_config(
    data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WebhookConfig).where(WebhookConfig.user_id == current_user.id)
    res = await db.execute(stmt)
    webhook = res.scalar_one_or_none()

    secret = data.secret or secrets.token_hex(20)

    if not webhook:
        webhook = WebhookConfig(
            user_id=current_user.id,
            url=data.url.strip(),
            secret=secret,
            is_active=True,
        )
        db.add(webhook)
    else:
        webhook.url = data.url.strip()
        if data.secret:
            webhook.secret = data.secret
        webhook.is_active = True

    await db.commit()
    await db.refresh(webhook)
    return webhook


@router.post("/webhook/test", response_model=WebhookTestResponse)
async def test_webhook(
    current_user: User = Depends(get_current_user),
):
    success = dispatch_webhook_sync(
        user_id=str(current_user.id),
        event_type="test.ping",
        payload={
            "message": "CertVerify AI Webhook Ping Test Successful!",
            "company": "CertVerify Production Suite",
        },
    )
    return WebhookTestResponse(
        success=success,
        http_status=200 if success else 400,
        message="Ping event successfully dispatched to your endpoint" if success else "Failed to deliver webhook. Check your endpoint URL.",
        delivered_at=datetime.utcnow(),
    )


# --- PROGRAMMATIC B2B VERIFICATION ENDPOINT ---

@router.post("/verify", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def headless_api_verify(
    request: Request,
    file: UploadFile = File(...),
    auth_user: User = Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    High-performance B2B headless API endpoint for programmatic certificate verification.
    Accepts X-API-Key: cv_live_... header or Bearer JWT token.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is required")

    content = await file.read()
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported formats: PDF, JPG, PNG",
        )

    stored = await storage_service.upload_certificate(
        file_bytes=content,
        filename=file.filename,
        user_id=str(auth_user.id),
    )

    cert = Certificate(
        user_id=auth_user.id,
        original_filename=file.filename,
        file_url=stored.url,
        cloudinary_public_id=stored.public_id,
        file_type=ext.lstrip(".").upper(),
        file_size_bytes=len(content),
        mime_type="application/pdf" if ext == ".pdf" else f"image/{ext.lstrip('.')}",
        is_deleted=False,
    )
    db.add(cert)
    await db.flush()

    # Save local master
    try:
        cert_local_name = f"{cert.id}{ext}"
        cert_local_file = os.path.join(storage_service.upload_dir, cert_local_name)
        with open(cert_local_file, "wb") as f_out:
            f_out.write(content)
    except Exception:
        pass

    job = VerificationJob(
        certificate_id=cert.id,
        status=JobStatus.PENDING,
        progress_percentage=0,
        current_step="API Queued",
    )
    db.add(job)
    await db.commit()

    try:
        run_verification.delay(str(job.id), str(cert.id))
    except Exception:
        pass

    return UploadResponse(
        certificate_id=cert.id,
        job_id=job.id,
        filename=cert.original_filename,
        status=job.status,
    )

