from typing import List, Union
import json
import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CertVerify AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database & Supabase
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/certverify"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/certverify"
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    REDIS_PASSWORD: str = ""

    # Security
    SECRET_KEY: str = "change-this-to-a-32-char-minimum-secret-production-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = "demo-cloud"
    CLOUDINARY_API_KEY: str = "demo-api-key"
    CLOUDINARY_API_SECRET: str = "demo-api-secret"

    # Limits & CORS
    MAX_FILE_SIZE_MB: int = 10
    STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage"))
    REPORTS_DIR: str = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "reports"))
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://localhost:80",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

