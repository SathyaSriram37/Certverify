import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import sync_engine
from app.models.developer import WebhookConfig


def dispatch_webhook_sync(user_id: str, event_type: str, payload: Dict[str, Any]) -> bool:
    """
    Delivers a real-time HTTP POST notification to the user's registered webhook endpoint.
    Signs the payload with HMAC-SHA256 using the webhook secret.
    """
    try:
        with Session(sync_engine) as db:
            stmt = select(WebhookConfig).where(
                WebhookConfig.user_id == user_id,
                WebhookConfig.is_active == True,
            )
            webhook = db.execute(stmt).scalar_one_or_none()
            if not webhook or not webhook.url:
                return False

            body = {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload,
            }
            body_bytes = json.dumps(body).encode("utf-8")

            # HMAC-SHA256 signature
            signature = hmac.new(
                webhook.secret.encode("utf-8"),
                body_bytes,
                hashlib.sha256,
            ).hexdigest()

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "CertVerify-Webhook/1.0",
                "X-CertVerify-Signature": signature,
                "X-CertVerify-Event": event_type,
            }

            with httpx.Client(timeout=8.0) as client:
                resp = client.post(webhook.url, content=body_bytes, headers=headers)
                webhook.last_delivered_at = datetime.utcnow()
                db.commit()
                return resp.status_code < 400
    except Exception:
        return False

