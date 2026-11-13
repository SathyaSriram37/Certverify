import os
import uuid
from dataclasses import dataclass
from typing import Optional
import cloudinary
import cloudinary.uploader
from app.core.config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


@dataclass
class StorageResult:
    url: str
    public_id: str
    bytes: int
    format: str
    local_path: Optional[str] = None


class StorageService:
    def __init__(self) -> None:
        self.upload_dir = os.path.abspath(os.path.join(settings.STORAGE_DIR, "uploads"))
        os.makedirs(self.upload_dir, exist_ok=True)

    def is_cloudinary_configured(self) -> bool:
        return bool(
            settings.CLOUDINARY_CLOUD_NAME
            and settings.CLOUDINARY_CLOUD_NAME != "demo-cloud"
            and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_KEY != "demo-api-key"
        )

    async def upload_certificate(
        self, file_bytes: bytes, filename: str, user_id: str
    ) -> StorageResult:
        file_ext = os.path.splitext(filename)[1].lstrip(".").lower() or "bin"
        unique_name = f"{uuid.uuid4().hex[:12]}_{filename}"

        # 1. ALWAYS persist a local master copy for zero-latency, reliable pipeline verification
        local_dest_path = os.path.join(self.upload_dir, unique_name)
        with open(local_dest_path, "wb") as f:
            f.write(file_bytes)

        # 2. Upload to Cloudinary if configured
        if self.is_cloudinary_configured():
            try:
                folder = f"certverify/certificates/{user_id}"
                result = cloudinary.uploader.upload(
                    file_bytes,
                    folder=folder,
                    public_id=f"cert_{uuid.uuid4().hex[:12]}",
                    resource_type="auto",
                )
                return StorageResult(
                    url=result.get("secure_url", result.get("url")),
                    public_id=result.get("public_id"),
                    bytes=len(file_bytes),
                    format=result.get("format", file_ext),
                    local_path=local_dest_path,
                )
            except Exception:
                pass

        return StorageResult(
            url=f"/static/uploads/{unique_name}",
            public_id=f"local_{unique_name}",
            bytes=len(file_bytes),
            format=file_ext,
            local_path=local_dest_path,
        )

    async def delete_file(self, public_id: str) -> bool:
        if public_id.startswith("local_"):
            local_filename = public_id.replace("local_", "")
            path = os.path.join(self.upload_dir, local_filename)
            if os.path.exists(path):
                os.remove(path)
            return True

        if self.is_cloudinary_configured():
            try:
                cloudinary.uploader.destroy(public_id, resource_type="image")
                cloudinary.uploader.destroy(public_id, resource_type="raw")
                return True
            except Exception:
                return False
        return True


storage_service = StorageService()

