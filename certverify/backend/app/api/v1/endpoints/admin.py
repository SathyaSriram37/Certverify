from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin, require_staff
from app.models.audit_log import AuditLog
from app.models.certificates import Certificate
from app.models.users import User, UserRole
from app.models.verification import FinalVerdict, JobStatus, RiskAssessment, VerificationJob
from app.schemas.admin import (
    AdminCertificateItem,
    AdminStats,
    AdminUserItem,
    AdminUserUpdateRequest,
    AuditLogResponse,
)
from app.schemas.auth import UserResponse
from app.schemas.certificates import PaginatedResponse
from app.schemas.dashboard import DailyUploadStat
from app.services.audit_service import log_action

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    # Total users
    users_q = select(func.count(User.id))
    users_res = await db.execute(users_q)
    total_users = users_res.scalar() or 0

    # Total certificates
    certs_q = select(func.count(Certificate.id)).where(Certificate.is_deleted == False)
    certs_res = await db.execute(certs_q)
    total_certificates = certs_res.scalar() or 0

    # Verdicts
    v_q = select(RiskAssessment.final_verdict, func.count(RiskAssessment.id)).group_by(RiskAssessment.final_verdict)
    v_res = await db.execute(v_q)
    v_rows = v_res.all()
    verdicts = {v.value: 0 for v in FinalVerdict}
    for row in v_rows:
        verdicts[row[0].value] = row[1]

    # Suspicious this week
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    susp_q = select(func.count(RiskAssessment.id)).where(
        RiskAssessment.final_verdict == FinalVerdict.SUSPICIOUS,
        RiskAssessment.created_at >= one_week_ago,
    )
    susp_res = await db.execute(susp_q)
    suspicious_this_week = susp_res.scalar() or 0

    # Average processing seconds
    avg_sec = 0.0
    jobs_q = select(VerificationJob.started_at, VerificationJob.completed_at).where(
        VerificationJob.status == JobStatus.COMPLETED,
        VerificationJob.started_at.isnot(None),
        VerificationJob.completed_at.isnot(None),
    )
    jobs_res = await db.execute(jobs_q)
    completed_jobs = jobs_res.all()
    if completed_jobs:
        durations = [(j[1] - j[0]).total_seconds() for j in completed_jobs if j[1] and j[0]]
        if durations:
            avg_sec = round(sum(durations) / len(durations), 1)

    # 30 days daily uploads in 1 single grouped query
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=29)
    start_dt = datetime.combine(thirty_days_ago, datetime.min.time())

    day_col = func.date(Certificate.created_at)
    cq = (
        select(day_col, func.count(Certificate.id))
        .where(
            Certificate.is_deleted == False,
            Certificate.created_at >= start_dt,
        )
        .group_by(day_col)
    )
    c_res = await db.execute(cq)
    counts_map = {row[0].strftime("%Y-%m-%d") if hasattr(row[0], 'strftime') else str(row[0]): row[1] for row in c_res.all()}

    daily_stats: list[DailyUploadStat] = []
    for i in range(30):
        d = thirty_days_ago + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        daily_stats.append(DailyUploadStat(date=d.strftime("%m/%d"), count=counts_map.get(d_str, 0)))

    return AdminStats(
        total_users=total_users,
        total_certificates=total_certificates,
        verdicts=verdicts,
        suspicious_this_week=suspicious_this_week,
        avg_processing_seconds=avg_sec,
        daily_uploads_30d=daily_stats,
    )


@router.get("/users", response_model=PaginatedResponse[AdminUserItem])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * size
    base_q = select(User)

    if search:
        search_filter = f"%{search.strip().lower()}%"
        base_q = base_q.where(
            (func.lower(User.email).ilike(search_filter))
            | (func.lower(User.full_name).ilike(search_filter))
        )

    if role:
        base_q = base_q.where(User.role == role)

    total_res = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = total_res.scalar() or 0

    users_res = await db.execute(
        base_q.order_by(desc(User.created_at)).offset(offset).limit(size)
    )
    users = users_res.scalars().all()

    items: list[AdminUserItem] = []
    if users:
        u_ids = [u.id for u in users]
        up_count_q = (
            select(Certificate.user_id, func.count(Certificate.id))
            .where(Certificate.user_id.in_(u_ids), Certificate.is_deleted == False)
            .group_by(Certificate.user_id)
        )
        up_res = await db.execute(up_count_q)
        counts_by_uid = {row[0]: row[1] for row in up_res.all()}

        for u in users:
            items.append(
                AdminUserItem(
                    id=u.id,
                    email=u.email,
                    full_name=u.full_name,
                    role=u.role,
                    is_active=u.is_active,
                    created_at=u.created_at,
                    upload_count=counts_by_uid.get(u.id, 0),
                )
            )

    pages = (total + size - 1) // size if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    req: AdminUserUpdateRequest,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    target_user = res.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if req.role is not None:
        target_user.role = req.role

    if req.is_active is not None:
        target_user.is_active = req.is_active

    await db.commit()
    await db.refresh(target_user)

    await log_action(
        db=db,
        user_id=admin_user.id,
        action="ADMIN_UPDATE_USER",
        resource_type="USER",
        resource_id=str(target_user.id),
        request=request,
    )

    return UserResponse.model_validate(target_user)


@router.get("/certificates", response_model=PaginatedResponse[AdminCertificateItem])
async def list_admin_certificates(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    verdict: Optional[FinalVerdict] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * size
    base_q = (
        select(Certificate, User.email)
        .join(User, Certificate.user_id == User.id)
        .where(Certificate.is_deleted == False)
    )

    if date_from:
        base_q = base_q.where(Certificate.created_at >= date_from)
    if date_to:
        base_q = base_q.where(Certificate.created_at <= date_to)

    total_res = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = total_res.scalar() or 0

    certs_res = await db.execute(
        base_q.order_by(desc(Certificate.created_at)).offset(offset).limit(size)
    )
    rows = certs_res.all()

    items: list[AdminCertificateItem] = []
    if rows:
        cert_ids = [c[0].id for c in rows]
        job_stmt = (
            select(VerificationJob)
            .where(VerificationJob.certificate_id.in_(cert_ids))
            .order_by(desc(VerificationJob.created_at))
        )
        job_res = await db.execute(job_stmt)
        all_jobs = job_res.scalars().all()
        latest_jobs: dict = {}
        for j in all_jobs:
            if j.certificate_id not in latest_jobs:
                latest_jobs[j.certificate_id] = j

        job_ids = [j.id for j in latest_jobs.values()]
        risk_map: dict = {}
        if job_ids:
            ra_stmt = select(RiskAssessment).where(RiskAssessment.job_id.in_(job_ids))
            ra_res = await db.execute(ra_stmt)
            for ra in ra_res.scalars().all():
                risk_map[ra.job_id] = ra

        for cert, user_email in rows:
            job = latest_jobs.get(cert.id)
            ra = risk_map.get(job.id) if job else None
            risk_val = ra.risk_score if ra else None
            verdict_val = ra.final_verdict if ra else None

            if verdict and verdict_val != verdict:
                continue

            items.append(
                AdminCertificateItem(
                    id=cert.id,
                    user_id=cert.user_id,
                    user_email=user_email,
                    original_filename=cert.original_filename,
                    file_type=cert.file_type,
                    file_size_bytes=cert.file_size_bytes,
                    created_at=cert.created_at,
                    job_id=job.id if job else None,
                    status=job.status if job else None,
                    risk_score=risk_val,
                    final_verdict=verdict_val,
                    is_suspicious=(verdict_val == FinalVerdict.SUSPICIOUS),
                )
            )

    pages = (total + size - 1) // size if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * size
    base_q = select(AuditLog, User.email).outerjoin(User, AuditLog.user_id == User.id)

    if user_id:
        base_q = base_q.where(AuditLog.user_id == user_id)

    total_res = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = total_res.scalar() or 0

    logs_res = await db.execute(
        base_q.order_by(desc(AuditLog.created_at)).offset(offset).limit(size)
    )
    rows = logs_res.all()

    items = [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user_email,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
        for log, user_email in rows
    ]

    pages = (total + size - 1) // size if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)

