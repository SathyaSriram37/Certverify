import uuid
from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    ip_address = "unknown"
    user_agent = ""
    if request:
        if request.client:
            ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "")

    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    return log_entry

