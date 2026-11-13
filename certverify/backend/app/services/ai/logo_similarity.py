from dataclasses import dataclass
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse
import httpx
import imagehash
from PIL import Image


@dataclass
class LogoSimilarityResult:
    attempted: bool
    favicon_found: bool
    similarity_score: float


async def compare_logo(
    image_path: str, website_url: Optional[str]
) -> LogoSimilarityResult:
    if not website_url:
        return LogoSimilarityResult(
            attempted=False, favicon_found=False, similarity_score=0.0
        )

    domain = urlparse(website_url).netloc
    if not domain:
        domain = website_url.replace("https://", "").replace("http://", "").split("/")[0]

    if not domain:
        return LogoSimilarityResult(
            attempted=False, favicon_found=False, similarity_score=0.0
        )

    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
        try:
            r = await client.get(f"https://{domain}/favicon.ico")
            if r.status_code != 200 or len(r.content) < 32:
                # Try google favicon fallback
                r = await client.get(f"https://www.google.com/s2/favicons?domain={domain}&sz=64")

            if r.status_code != 200 or len(r.content) < 32:
                return LogoSimilarityResult(
                    attempted=True, favicon_found=False, similarity_score=0.0
                )

            site_img = Image.open(BytesIO(r.content)).resize((64, 64)).convert("RGB")
            cert_img = Image.open(image_path).convert("RGB")
            w, h = cert_img.size
            # Top-left quadrant where organization logo typically resides
            logo = cert_img.crop((0, 0, max(w // 4, 32), max(h // 4, 32))).resize((64, 64))

            ham = imagehash.phash(logo) - imagehash.phash(site_img)
            score = max(0.0, min(1.0, round(1.0 - (ham / 64.0), 2)))
            return LogoSimilarityResult(
                attempted=True, favicon_found=True, similarity_score=score
            )
        except Exception:
            return LogoSimilarityResult(
                attempted=True, favicon_found=False, similarity_score=0.0
            )

