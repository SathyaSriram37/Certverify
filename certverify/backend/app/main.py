import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from starlette.middleware.gzip import GZipMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.startup import validate_startup
from app.middleware.security_headers import SecurityHeadersMiddleware

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    await validate_startup()
    yield
    # Shutdown logic if any


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise AI-Powered Universal Certificate Verification & Forgery Detection SaaS Platform",
    lifespan=lifespan,
)

# Attach SlowAPI limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# GZip Compression (compress JSON & API responses > 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for storage uploads
from app.services.storage_service import storage_service
app.mount("/static/uploads", StaticFiles(directory=storage_service.upload_dir), name="uploads")

# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "database": "supabase_postgresql_async",
    }

