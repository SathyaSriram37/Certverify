from fastapi import APIRouter
from app.api.v1.endpoints import admin, auth, batch, certificates, dashboard, developer, verify

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(certificates.router, prefix="/certificates", tags=["Certificates"])
api_router.include_router(batch.router, prefix="/batch", tags=["Batch Verification"])
api_router.include_router(developer.router, prefix="/developer", tags=["Developer & B2B API"])
api_router.include_router(verify.router, prefix="/verify", tags=["Verification"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
