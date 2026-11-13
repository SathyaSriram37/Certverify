import os
import cv2
import numpy as np
from PIL import Image
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.services.storage_service import storage_service


def analyze_fft_frequency(image_path: str, cert_id: str) -> Dict[str, Any]:
    """
    Analyzes 2D Fast Fourier Transform (FFT) frequency spectrum of the certificate.
    Synthetic AI generators (Diffusion / GAN models) leave characteristic periodic frequency
    peaks and unnatural high-frequency energy distributions.
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {
                "fft_analyzed": False,
                "synthetic_ai_score": 0.0,
                "ai_generated_suspected": False,
                "spectral_energy_ratio": 0.0,
                "fft_spectrum_url": None,
            }

        # Downsample if image is extremely large to optimize FFT calculation
        h, w = img.shape
        target_size = (1024, 1024)
        resized = cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)

        # 2D Fast Fourier Transform
        f = np.fft.fft2(resized)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-9)

        # Radial distribution analysis: High frequency vs Low frequency ratio
        center_y, center_x = 512, 512
        y, x = np.ogrid[:1024, :1024]
        dist_from_center = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)

        # Mask radii: low freq (< 100 px), mid freq (100-300 px), high freq (> 300 px)
        low_freq_mask = dist_from_center < 100
        high_freq_mask = dist_from_center > 350

        low_energy = np.mean(magnitude_spectrum[low_freq_mask])
        high_energy = np.mean(magnitude_spectrum[high_freq_mask])

        # Authentic scanned/rasterized documents have high continuous energy roll-off (low / high ratio > 1.8)
        # Synthetic AI generators exhibit unnatural high-frequency residual noise or sharp periodic spikes
        spectral_ratio = float(low_energy / max(high_energy, 1.0))
        
        # Check standard deviation of high-frequency band for periodic spikes
        high_freq_std = float(np.std(magnitude_spectrum[high_freq_mask]))
        
        # Calculate synthetic AI likelihood score (0.0 = authentic document, 1.0 = AI generated)
        synthetic_score = 0.0
        if high_freq_std > 28.0:
            synthetic_score += 0.45
        if spectral_ratio < 1.15:
            synthetic_score += 0.40

        synthetic_score = round(min(1.0, max(0.0, synthetic_score)), 2)
        ai_suspected = synthetic_score >= 0.70

        # Generate Normalized Spectrum Heatmap Image for UI
        norm_mag = cv2.normalize(magnitude_spectrum, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        color_heatmap = cv2.applyColorMap(norm_mag, cv2.COLORMAP_JET)

        fft_filename = f"fft_{cert_id[:12]}.png"
        fft_dest_path = os.path.join(storage_service.upload_dir, fft_filename)
        cv2.imwrite(fft_dest_path, color_heatmap)

        fft_url = f"/static/uploads/{fft_filename}"

        return {
            "fft_analyzed": True,
            "synthetic_ai_score": synthetic_score,
            "ai_generated_suspected": ai_suspected,
            "spectral_energy_ratio": round(spectral_ratio, 2),
            "high_freq_dispersion": round(high_freq_std, 2),
            "fft_spectrum_url": fft_url,
        }
    except Exception as exc:
        return {
            "fft_analyzed": False,
            "error": str(exc),
            "synthetic_ai_score": 0.0,
            "ai_generated_suspected": False,
            "fft_spectrum_url": None,
        }


def extract_visual_signatures(image_path: str, cert_id: str) -> Dict[str, Any]:
    """
    Extracts physical ink signatures from the document's signature regions.
    Saves isolated signature crops so HR and auditors can visually inspect authenticity.
    """
    extracted_urls: List[str] = []
    signatures_found = 0

    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"signatures_detected": 0, "signature_crops": []}

        h, w, _ = img.shape
        # Focus on bottom 45% of the certificate layout
        bottom_offset = int(h * 0.55)
        bottom = img[bottom_offset:h, :]

        gray = cv2.cvtColor(bottom, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 15
        )

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        sig_regions = []

        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            # Filter contours matching signature proportions (wide, non-trivial area, separated from border)
            if 90 < cw < (w * 0.35) and 35 < ch < (h * 0.22) and 600 < area < 45000:
                sig_regions.append((x, y, cw, ch))

        # Sort left-to-right
        sig_regions = sorted(sig_regions, key=lambda b: b[0])[:3]

        for idx, (x, y, cw, ch) in enumerate(sig_regions):
            # Add padding
            pad_x = max(0, int(cw * 0.1))
            pad_y = max(0, int(ch * 0.1))
            crop_x0 = max(0, x - pad_x)
            crop_y0 = max(0, y - pad_y)
            crop_x1 = min(w, x + cw + pad_x)
            crop_y1 = min(bottom.shape[0], y + ch + pad_y)

            crop = bottom[crop_y0:crop_y1, crop_x0:crop_x1]
            if crop.size > 0:
                sig_name = f"sig_{cert_id[:8]}_{idx}.png"
                sig_dest = os.path.join(storage_service.upload_dir, sig_name)
                cv2.imwrite(sig_dest, crop)
                extracted_urls.append(f"/static/uploads/{sig_name}")
                signatures_found += 1

        return {
            "signatures_detected": signatures_found,
            "signature_crops": extracted_urls,
            "has_physical_signature": signatures_found > 0,
        }
    except Exception:
        return {"signatures_detected": 0, "signature_crops": []}


def analyze_font_alignment(image_path: str) -> Dict[str, Any]:
    """
    Detects baseline shifts and font tampering where text has been digitally modified or superimposed.
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {"baseline_anomaly": False, "confidence": 0.95}

        # Otsu thresholding
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Horizontal projection profile to detect baseline shifts
        horizontal_proj = np.sum(binary, axis=1)
        peaks = np.where(horizontal_proj > (np.max(horizontal_proj) * 0.15))[0]
        
        # Compute line spacing consistency
        if len(peaks) > 5:
            diffs = np.diff(peaks)
            std_diff = float(np.std(diffs))
            # Standard typed certificates have relatively uniform line spacing
            is_anomaly = std_diff > 45.0
            return {
                "baseline_anomaly": is_anomaly,
                "spacing_variance": round(std_diff, 2),
                "line_profile_checked": True,
            }
        return {"baseline_anomaly": False, "spacing_variance": 0.0, "line_profile_checked": True}
    except Exception:
        return {"baseline_anomaly": False, "line_profile_checked": False}


def run_deepfake_and_manipulation_audit(
    image_path: str, cert_id: str
) -> Dict[str, Any]:
    """
    Unified enterprise forensic runner combining FFT frequency analysis,
    font baseline integrity, and signature stroke extraction.
    """
    fft_res = analyze_fft_frequency(image_path, cert_id)
    sig_res = extract_visual_signatures(image_path, cert_id)
    font_res = analyze_font_alignment(image_path)

    flags = []
    if fft_res.get("ai_generated_suspected"):
        flags.append("FFT spectrum detected synthetic AI generation artifacts")
    if font_res.get("baseline_anomaly"):
        flags.append("Typography baseline variance suggests potential text overlay")

    return {
        "fft_data": fft_res,
        "signature_data": sig_res,
        "font_data": font_res,
        "deepfake_flags": flags,
        "is_ai_generated": fft_res.get("ai_generated_suspected", False),
    }

