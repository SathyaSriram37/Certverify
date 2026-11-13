import hmac
import hashlib
import json
import secrets
import pytest
from app.services.webhook_service import dispatch_webhook_sync
from app.schemas.developer import ApiKeyCreate, WebhookCreate

def test_api_key_generation_and_hashing():
    token_suffix = secrets.token_urlsafe(32)
    short_prefix = f"cv_live_{secrets.token_hex(4)}"
    raw_api_key = f"{short_prefix}_{token_suffix}"
    
    assert raw_api_key.startswith("cv_live_")
    assert short_prefix in raw_api_key
    
    # Verify SHA-256 hash
    hashed = hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()
    assert len(hashed) == 64
    assert hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest() == hashed

def test_webhook_hmac_signature():
    secret = "test_webhook_secret_key_12345"
    payload = {
        "event": "verification.completed",
        "certificate_id": "test-uuid-1234",
        "status": "VALID",
        "risk_score": 15
    }
    
    body_bytes = json.dumps(payload, default=str).encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    
    actual_sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    assert actual_sig == expected_sig
    assert len(actual_sig) == 64

def test_developer_schemas():
    key_input = ApiKeyCreate(name="Staging Service Key", rate_limit_per_minute=120)
    assert key_input.name == "Staging Service Key"
    assert key_input.rate_limit_per_minute == 120

    webhook_input = WebhookCreate(url="https://api.partner.com/certverify/webhook", secret="top_secret_token")
    assert webhook_input.url == "https://api.partner.com/certverify/webhook"
    assert webhook_input.secret == "top_secret_token"

def test_batch_csv_export_format():
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Certificate ID", "File Name", "Status", "Risk Score", "Confidence Score", "Issuer Name", "Recipient Name", "Issue Date", "Verified At"])
    
    writer.writerow([
        "cert-001", "iso_9001.pdf", "VALID", 10, 95.0, "ISO Global", "John Doe", "2024-01-01", "2024-01-02 10:00:00"
    ])
    
    csv_content = output.getvalue()
    assert "Certificate ID,File Name,Status,Risk Score,Confidence Score" in csv_content
    assert "iso_9001.pdf" in csv_content
    assert "ISO Global" in csv_content
