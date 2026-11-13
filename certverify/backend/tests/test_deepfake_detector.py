import os
import cv2
import numpy as np
import pytest
from app.services.ai.deepfake_detector import (
    analyze_fft_frequency,
    analyze_font_alignment,
    extract_visual_signatures,
    run_deepfake_and_manipulation_audit,
)


@pytest.fixture
def sample_test_image(tmp_path):
    img_path = str(tmp_path / "test_certificate.png")
    # Create synthetic test canvas with text and lines
    canvas = np.full((1000, 1400, 3), 255, dtype=np.uint8)
    cv2.putText(canvas, "CERTIFICATE OF ACHIEVEMENT", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    cv2.putText(canvas, "Presented to John Doe", (300, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    # Add simulated signature contour in bottom half
    cv2.ellipse(canvas, (900, 800), (120, 40), 15, 0, 360, (0, 0, 150), 3)
    cv2.imwrite(img_path, canvas)
    return img_path


def test_fft_frequency_analysis(sample_test_image):
    res = analyze_fft_frequency(sample_test_image, "test_cert_123")
    assert res["fft_analyzed"] is True
    assert "synthetic_ai_score" in res
    assert 0.0 <= res["synthetic_ai_score"] <= 1.0
    assert "spectral_energy_ratio" in res
    assert res["ai_generated_suspected"] is False


def test_font_alignment(sample_test_image):
    res = analyze_font_alignment(sample_test_image)
    assert "baseline_anomaly" in res
    assert res["line_profile_checked"] is True


def test_signature_extraction(sample_test_image):
    res = extract_visual_signatures(sample_test_image, "test_cert_123")
    assert "signatures_detected" in res
    assert "signature_crops" in res
    assert isinstance(res["signature_crops"], list)


def test_full_deepfake_audit(sample_test_image):
    res = run_deepfake_and_manipulation_audit(sample_test_image, "test_cert_123")
    assert "fft_data" in res
    assert "signature_data" in res
    assert "font_data" in res
    assert res["is_ai_generated"] is False

