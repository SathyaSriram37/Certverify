from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse
import cv2
import httpx

try:
    import pyzbar.pyzbar as pyzbar
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False


@dataclass
class QRData:
    type: str
    data: str


@dataclass
class QRURLResult:
    raw_data: str
    is_url: bool
    domain: Optional[str]
    active: bool
    ssl_ok: bool
    domain_type: str  # "OFFICIAL" | "THIRD_PARTY" | "SUSPICIOUS" | "TEXT_DATA"
    is_suspicious: bool


SUSPICIOUS_HOSTS = {
    "bit.ly",
    "tinyurl.com",
    "goo.gl",
    "t.co",
    "wix.com",
    "weebly.com",
    "wordpress.com",
    "blogspot.com",
    "is.gd",
    "buff.ly",
    "ow.ly",
}


def scan_qr(image_path: str) -> List[QRData]:
    if not PYZBAR_AVAILABLE:
        # Fallback using OpenCV QRCodeDetector
        try:
            detector = cv2.QRCodeDetector()
            img = cv2.imread(image_path)
            if img is not None:
                val, points, _ = detector.detectAndDecode(img)
                if val:
                    return [QRData(type="QRCODE", data=val)]
        except Exception:
            pass
        return []

    try:
        img = cv2.imread(image_path)
        if img is None:
            return []
        decoded = pyzbar.decode(img)
        return [QRData(type=d.type, data=d.data.decode("utf-8", errors="ignore")) for d in decoded]
    except Exception:
        return []


async def verify_qr_url(qr_data: str, org_domain: Optional[str]) -> QRURLResult:
    if not qr_data.startswith("http://") and not qr_data.startswith("https://"):
        return QRURLResult(
            raw_data=qr_data,
            is_url=False,
            domain=None,
            active=False,
            ssl_ok=False,
            domain_type="TEXT_DATA",
            is_suspicious=False,
        )

    parsed = urlparse(qr_data)
    domain = parsed.netloc.lower()
    is_suspicious = any(susp in domain for susp in SUSPICIOUS_HOSTS)
    matches_org = bool(org_domain and org_domain.lower() in domain)

    active = False
    ssl_ok = qr_data.startswith("https://")

    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
        try:
            r = await client.get(qr_data)
            active = r.status_code < 400
        except Exception:
            active = False

    domain_type = (
        "OFFICIAL"
        if matches_org
        else "SUSPICIOUS"
        if is_suspicious
        else "THIRD_PARTY"
    )

    return QRURLResult(
        raw_data=qr_data,
        is_url=True,
        domain=domain,
        active=active,
        ssl_ok=ssl_ok,
        domain_type=domain_type,
        is_suspicious=is_suspicious,
    )

