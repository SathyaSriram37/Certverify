from dataclasses import dataclass
import hashlib
from typing import List, Optional
import imagehash
from PIL import Image
from sqlalchemy.orm import Session
from app.models.certificates import Certificate
from app.models.verification import CertificateFingerprint, VerificationJob, VerificationResult

_st_model = None


def get_model():
    global _st_model
    if _st_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _st_model = False
    return _st_model


@dataclass
class FingerprintData:
    phash: str
    dhash: str
    text_hash: str


@dataclass
class DuplicateMatch:
    certificate_id: str
    filename: str
    upload_date: str
    img_similarity: float
    text_similarity: float
    match_type: str  # "EXACT" | "NEAR_DUPLICATE" | "SIMILAR_TEMPLATE"


def compute_fingerprint(image_path: str, text: str) -> FingerprintData:
    try:
        img = Image.open(image_path).convert("RGB")
        ph = str(imagehash.phash(img))
        dh = str(imagehash.dhash(img))
    except Exception:
        ph = "0000000000000000"
        dh = "0000000000000000"

    norm_text = " ".join(text.lower().split())
    th = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
    return FingerprintData(phash=ph, dhash=dh, text_hash=th)


def find_duplicates(
    cert_id: str,
    fp: FingerprintData,
    cur_text: str,
    db: Session,
) -> List[DuplicateMatch]:
    all_fps = (
        db.query(CertificateFingerprint)
        .filter(CertificateFingerprint.certificate_id != cert_id)
        .all()
    )
    matches: List[DuplicateMatch] = []

    try:
        cur_hash = imagehash.hex_to_hash(fp.phash)
    except Exception:
        return []

    model = get_model()

    for stored in all_fps:
        try:
            stored_hash = imagehash.hex_to_hash(stored.phash)
            hamming = cur_hash - stored_hash
            img_sim = round(1.0 - (hamming / 64.0), 3)

            if img_sim < 0.70:
                continue

            text_sim = 0.0
            stored_ocr = (
                db.query(VerificationResult)
                .filter(VerificationResult.module_name == "OCR_EXTRACTION")
                .join(VerificationJob, VerificationResult.job_id == VerificationJob.id)
                .filter(VerificationJob.certificate_id == stored.certificate_id)
                .first()
            )

            if stored_ocr and cur_text and model:
                try:
                    stored_text = stored_ocr.details.get("full_text", "")[:500]
                    if stored_text.strip():
                        embs = model.encode([cur_text[:500], stored_text])
                        from sklearn.metrics.pairwise import cosine_similarity
                        text_sim = float(cosine_similarity([embs[0]], [embs[1]])[0][0])
                except Exception:
                    text_sim = 0.0

            match_type = (
                "EXACT"
                if hamming == 0
                else "NEAR_DUPLICATE"
                if hamming < 10
                else "SIMILAR_TEMPLATE"
            )

            cert = db.query(Certificate).get(stored.certificate_id)
            if cert:
                matches.append(
                    DuplicateMatch(
                        certificate_id=str(cert.id),
                        filename=cert.original_filename,
                        upload_date=cert.created_at.strftime("%Y-%m-%d %H:%M"),
                        img_similarity=img_sim,
                        text_similarity=round(max(0.0, text_sim), 3),
                        match_type=match_type,
                    )
                )
        except Exception:
            continue

    return sorted(matches, key=lambda m: m.img_similarity, reverse=True)[:5]

