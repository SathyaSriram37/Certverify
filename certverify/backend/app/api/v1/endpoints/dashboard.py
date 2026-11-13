from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.certificates import Certificate
from app.models.users import User
from app.models.verification import FinalVerdict, JobStatus, RiskAssessment, VerificationJob
from app.schemas.dashboard import DailyUploadStat, DashboardStats, RecentUploadItem

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Total uploads
    total_query = select(func.count(Certificate.id)).where(
        Certificate.user_id == current_user.id,
        Certificate.is_deleted == False,
    )
    total_res = await db.execute(total_query)
    total_uploads = total_res.scalar() or 0

    # Verdict counts & average risk score
    risk_query = (
        select(
            RiskAssessment.final_verdict,
            func.count(RiskAssessment.id),
        )
        .join(VerificationJob, RiskAssessment.job_id == VerificationJob.id)
        .join(Certificate, VerificationJob.certificate_id == Certificate.id)
        .where(
            Certificate.user_id == current_user.id,
            Certificate.is_deleted == False,
        )
        .group_by(RiskAssessment.final_verdict)
    )
    risk_res = await db.execute(risk_query)
    verdict_rows = risk_res.all()
    verdict_counts = {row[0]: row[1] for row in verdict_rows}

    verified_count = verdict_counts.get(FinalVerdict.VERIFIED, 0)
    suspicious_count = verdict_counts.get(FinalVerdict.SUSPICIOUS, 0)
    unable_count = verdict_counts.get(FinalVerdict.UNABLE_TO_VERIFY, 0)

    # In progress jobs
    proc_query = (
        select(func.count(VerificationJob.id))
        .join(Certificate, VerificationJob.certificate_id == Certificate.id)
        .where(
            Certificate.user_id == current_user.id,
            Certificate.is_deleted == False,
            VerificationJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),
        )
    )
    proc_res = await db.execute(proc_query)
    processing_count = proc_res.scalar() or 0

    # Average risk score
    avg_query = (
        select(func.avg(RiskAssessment.risk_score))
        .join(VerificationJob, RiskAssessment.job_id == VerificationJob.id)
        .join(Certificate, VerificationJob.certificate_id == Certificate.id)
        .where(
            Certificate.user_id == current_user.id,
            Certificate.is_deleted == False,
        )
    )
    avg_res = await db.execute(avg_query)
    avg_risk_score = round(float(avg_res.scalar() or 0.0), 1)

    # Last 7 days upload stats (1 single aggregated query instead of 7 queries)
    today = datetime.utcnow().date()
    seven_days_ago = today - timedelta(days=6)
    start_dt = datetime.combine(seven_days_ago, datetime.min.time())

    day_col = func.date(Certificate.created_at)
    grouped_counts_q = (
        select(day_col, func.count(Certificate.id))
        .where(
            Certificate.user_id == current_user.id,
            Certificate.is_deleted == False,
            Certificate.created_at >= start_dt,
        )
        .group_by(day_col)
    )
    grouped_res = await db.execute(grouped_counts_q)
    counts_by_date = {row[0].strftime("%Y-%m-%d") if hasattr(row[0], 'strftime') else str(row[0]): row[1] for row in grouped_res.all()}

    daily_stats: list[DailyUploadStat] = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        daily_stats.append(DailyUploadStat(date=day.strftime("%b %d"), count=counts_by_date.get(day_str, 0)))

    # Recent 5 uploads with joined job & risk assessment in 1 single query
    recent_q = (
        select(
            Certificate,
            VerificationJob,
            RiskAssessment,
        )
        .outerjoin(VerificationJob, VerificationJob.certificate_id == Certificate.id)
        .outerjoin(RiskAssessment, RiskAssessment.job_id == VerificationJob.id)
        .where(
            Certificate.user_id == current_user.id,
            Certificate.is_deleted == False,
        )
        .order_by(desc(Certificate.created_at))
        .limit(5)
    )
    recent_res = await db.execute(recent_q)
    recent_rows = recent_res.all()

    seen_cert_ids = set()
    recent_items: list[RecentUploadItem] = []
    for cert, job, ra in recent_rows:
        if cert.id in seen_cert_ids:
            continue
        seen_cert_ids.add(cert.id)
        recent_items.append(
            RecentUploadItem(
                certificate_id=cert.id,
                job_id=job.id if job else None,
                filename=cert.original_filename,
                file_type=cert.file_type,
                status=job.status if job else JobStatus.PENDING,
                risk_score=ra.risk_score if ra else None,
                final_verdict=ra.final_verdict if ra else None,
                created_at=cert.created_at,
            )
        )

    return DashboardStats(
        total_uploads=total_uploads,
        verified_count=verified_count,
        suspicious_count=suspicious_count,
        unable_count=unable_count,
        processing_count=processing_count,
        avg_risk_score=avg_risk_score,
        uploads_by_day=daily_stats,
        recent_uploads=recent_items,
    )
