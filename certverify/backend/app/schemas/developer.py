from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field, HttpUrl


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Friendly label for this API key")
    rate_limit_per_minute: int = Field(60, ge=10, le=1000)


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    rate_limit_per_minute: int
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreatedResponse(BaseModel):
    id: uuid.UUID
    name: str
    raw_key: str
    key_prefix: str
    rate_limit_per_minute: int
    created_at: datetime
    message: str = "Please copy and store your API key safely. You will not be able to see it again!"


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=1024, description="HTTPS endpoint to receive verification results")
    secret: Optional[str] = Field(None, max_length=255, description="Shared secret for HMAC-SHA256 signature verification")


class WebhookResponse(BaseModel):
    id: uuid.UUID
    url: str
    secret: str
    is_active: bool
    last_delivered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    success: bool
    http_status: Optional[int] = None
    message: str
    delivered_at: datetime

