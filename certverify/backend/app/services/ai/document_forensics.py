import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageChops, ImageDraw
from app.services.storage_service import storage_service


def parse_pdf_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses PDF format D:YYYYMMDDHHmmSS."""
    if not date_str:
        return None
    try:
        clean = re.sub(r"^D:", "", date_str)
        # Take first 14 chars YYYYMMDDHHMMSS
        clean = re.sub(r"[Z'+-].*$", "", clean)[:14]
        return datetime.strptime(clean, "%Y%m%d%H%M%S")
    except Exception:
        return None


def detect_whiteout_tampering(page: fitz.Page) -> Dict[str, Any]:
    """
    Forensic check: Detects covert white rectangular overlays placed over existing text
    (a hallmark technique of forged certificates where names or numbers are covered up).
    """
    whiteout_boxes = []
    try:
        drawings = page.get_drawings()
        for d in drawings:
            fill = d.get("fill")
            rect = d.get("rect")
            if fill and rect:
                # Check for white or near-white fills
                is_white = all(c >= 0.98 for c in fill) if isinstance(fill, (list, tuple)) else (fill == (1, 1, 1))
                # Check if dimension is typical for text covering (width > 30, height between 8 and 60)
                w = rect.x1 - rect.x0
                h = rect.y1 - rect.y0
                if is_white and w > 35 and 8 <= h <= 80:
                    # Exclude the full page background rectangle
                    if w < page.rect.width * 0.9 and h < page.rect.height * 0.9:
                        whiteout_boxes.append([round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1)])
    except Exception:
        pass

    return {
        "whiteout_detected": len(whiteout_boxes) > 0,
        "suspicious_box_count": len(whiteout_boxes),
        "boxes": whiteout_boxes[:5],
    }


def detect_incremental_updates(file_path: str) -> Dict[str, Any]:
    """Checks if PDF has multiple revision saves (incremental updates)."""
    eof_count = 0
    try:
        with open(file_path, "rb") as f:
            content = f.read()
            eof_count = len(re.findall(rb"%%EOF", content))
    except Exception:
        pass

    return {
        "revision_count": max(1, eof_count),
        "has_incremental_updates": eof_count > 2,
    }


def analyze_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Enterprise PDF Forensic Analysis.
    Detects tampering, modification drift, covert white-out rectangles,
    unusual font anomalies, and revision count.
    """
    flags: List[str] = []
    unique_families = 0
    image_count = 0
    ann_count = 0
    mod_suspected = False
    creation_dt = None
    mod_dt = None
    whiteout_data = {"whiteout_detected": False, "suspicious_box_count": 0, "boxes": []}
    revision_data = {"revision_count": 1, "has_incremental_updates": False}

    try:
        doc = fitz.open(file_path)
        meta = doc.metadata or {}

        # 1. Timestamp Drift Analysis
        creation_dt = parse_pdf_date(meta.get("creationDate"))
        mod_dt = parse_pdf_date(meta.get("modDate"))

        if creation_dt and mod_dt:
            delta_seconds = (mod_dt - creation_dt).total_seconds()
            # If modified significantly later (> 48 hours), flag as post-issuance modification
            if delta_seconds > 172800:
                flags.append(f"Document modified {int(delta_seconds // 86400)} days after original creation")
                mod_suspected = True

        # Producer / Creator Inspection
        producer = (meta.get("producer") or "").lower()
        creator = (meta.get("creator") or "").lower()
        tamper_tools = ["ilovepdf", "sejda", "pdfescape", "foxit phantom", "nitro pdf", "photoshop"]
        for tool in tamper_tools:
            if tool in producer or tool in creator:
                flags.append(f"Known consumer PDF manipulation tool detected ({tool})")
                mod_suspected = True

        if len(doc) > 0:
            page = doc[0]
            fonts = page.get_fonts(full=True)
            unique_families = len(set(f[3] for f in fonts if len(f) > 3 and f[3]))
            # Professional certificates legitimately use up to 7 font variants
            if unique_families > 8:
                flags.append(f"Highly unusual font variety ({unique_families} font families)")

            images = page.get_images()
            image_count = len(images)

            annots = list(page.annots()) if hasattr(page, "annots") and page.annots() else []
            ann_count = len(annots)
            if ann_count > 0:
                flags.append(f"{ann_count} post-issuance annotation layer(s) found")

            # Covert White-Out Overlay Detection
            whiteout_data = detect_whiteout_tampering(page)
            if whiteout_data["whiteout_detected"]:
                flags.append(f"Covert white-out overlay detected ({whiteout_data['suspicious_box_count']} masking patch(es))")

        # Incremental Updates
        revision_data = detect_incremental_updates(file_path)
        if revision_data["has_incremental_updates"]:
            flags.append(f"Multiple incremental PDF revisions detected ({revision_data['revision_count']} %%EOF markers)")

    except Exception as exc:
        flags.append(f"Metadata read error: {exc}")

    # Confidence score is based on severity of flags
    confidence = 0.0
    if whiteout_data["whiteout_detected"]:
        confidence += 0.60
    if mod_suspected:
        confidence += 0.35
    if unique_families > 8:
        confidence += 0.20
    if revision_data["has_incremental_updates"]:
        confidence += 0.25

    confidence = round(min(1.0, confidence), 2)

    return {
        "modification_suspected": mod_suspected,
        "font_family_count": unique_families,
        "font_inconsistency": unique_families > 8,
        "image_count": image_count,
        "annotation_count": ann_count,
        "suspicious_flags": flags,
        "confidence_score": confidence,
        "whiteout_data": whiteout_data,
        "revision_data": revision_data,
        "creation_date": str(creation_dt) if creation_dt else None,
        "mod_date": str(mod_dt) if mod_dt else None,
    }


def perform_ela(image_path: str, is_vector_pdf: bool = True) -> Dict[str, Any]:
    """
    Adaptive Error Level Analysis (ELA).
    Dynamically adjusts threshold between native digital vector documents and scanned bitmaps.
    """
    ela_mean = 0.0
    ela_suspicious = False
    # Vector documents have sharp geometric edges that naturally register higher ELA
    threshold = 36.0 if is_vector_pdf else 24.0

    try:
        original = Image.open(image_path).convert("RGB")
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        # Save with standard 75% JPEG compression
        original.save(tmp_path, "JPEG", quality=75)
        resaved = Image.open(tmp_path).convert("RGB")

        # Compute pixel difference
        diff = ImageChops.difference(original, resaved)
        diff_arr = np.array(diff, dtype=np.float32)
        ela_mean = float(np.mean(diff_arr))
        ela_suspicious = ela_mean > threshold

        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except Exception:
        pass

    return {
        "ela_mean": round(ela_mean, 2),
        "ela_suspicious": ela_suspicious,
        "threshold": threshold,
    }


def analyze_exif(image_path: str) -> Dict[str, Any]:
    """Inspects EXIF metadata for image manipulation software signatures."""
    edit_sw_keywords = [
        "photoshop", "gimp", "lightroom", "pixelmator",
        "affinity", "paint.net", "coreldraw"
    ]
    detected_software: Optional[str] = None

    try:
        img = Image.open(image_path)
        exif = img.getexif()
        if exif:
            for tag_id, val in exif.items():
                val_str = str(val).lower()
                for sw in edit_sw_keywords:
                    if sw in val_str:
                        detected_software = sw.title()
                        break
                if detected_software:
                    break
    except Exception:
        pass

    return {
        "has_exif": detected_software is not None,
        "editing_software_detected": detected_software,
    }


def create_annotated_image(image_path: str, ela_data: Dict[str, Any], cert_id: str) -> Optional[str]:
    """Saves a forensic heat overlay thumbnail if suspicious artifacts are found."""
    try:
        from app.core.config import settings
        original = Image.open(image_path).convert("RGB")
        w, h = original.size

        # Create overlay canvas
        overlay = original.copy()
        draw = ImageDraw.Draw(overlay)

        if ela_data.get("ela_suspicious"):
            # Mark high discrepancy areas
            draw.rectangle([10, 10, w - 10, 40], fill=(239, 68, 68, 180))
            draw.text((20, 15), "FORENSIC WARNING: High Compression Anomaly Detected", fill=(255, 255, 255))

        out_name = f"ela_{cert_id}.png"
        out_dir = os.path.join(settings.STORAGE_DIR, "uploads")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, out_name)
        overlay.save(out_path, "PNG")

        return f"/static/uploads/{out_name}"
    except Exception:
        return None
