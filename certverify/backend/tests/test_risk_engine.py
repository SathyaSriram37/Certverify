import uuid
from app.models.verification import FinalVerdict, ModuleStatus, RiskLevel, VerificationResult
from app.services.verification.risk_engine import calculate_risk, generate_reasoning


def test_calculate_risk_verified():
    job_id = uuid.uuid4()
    results = [
        VerificationResult(
            job_id=job_id,
            module_name="COMPANY_INTELLIGENCE",
            status=ModuleStatus.PASS,
            finding_summary="Found online",
            details={},
        ),
        VerificationResult(
            job_id=job_id,
            module_name="IMAGE_FORENSICS",
            status=ModuleStatus.PASS,
            finding_summary="No manipulation",
            details={},
        ),
        VerificationResult(
            job_id=job_id,
            module_name="OCR_EXTRACTION",
            status=ModuleStatus.PASS,
            finding_summary="High confidence",
            details={},
        ),
    ]

    calc = calculate_risk(results)
    assert calc.risk_score <= 30
    assert calc.risk_level == RiskLevel.LOW
    assert calc.final_verdict == FinalVerdict.VERIFIED

    reasoning = generate_reasoning(results, calc)
    assert "Passed verification checks:" in reasoning or "Passed checks:" in reasoning
    assert "verified" in reasoning.lower()


def test_calculate_risk_suspicious_forensics():
    job_id = uuid.uuid4()
    results = [
        VerificationResult(
            job_id=job_id,
            module_name="IMAGE_FORENSICS",
            status=ModuleStatus.FAIL,
            finding_summary="ELA detected tampering",
            details={},
        ),
        VerificationResult(
            job_id=job_id,
            module_name="COMPANY_INTELLIGENCE",
            status=ModuleStatus.PASS,
            finding_summary="Found online",
            details={},
        ),
    ]

    calc = calculate_risk(results)
    assert calc.final_verdict == FinalVerdict.SUSPICIOUS


def test_calculate_risk_unable_to_verify():
    job_id = uuid.uuid4()
    results = [
        VerificationResult(
            job_id=job_id,
            module_name="OCR_EXTRACTION",
            status=ModuleStatus.SKIPPED,
            finding_summary="Skipped",
            details={},
        ),
        VerificationResult(
            job_id=job_id,
            module_name="COMPANY_INTELLIGENCE",
            status=ModuleStatus.SKIPPED,
            finding_summary="Skipped",
            details={},
        ),
        VerificationResult(
            job_id=job_id,
            module_name="IMAGE_FORENSICS",
            status=ModuleStatus.SKIPPED,
            finding_summary="Skipped",
            details={},
        ),
        VerificationResult(
            job_id=job_id,
            module_name="QR_CODE",
            status=ModuleStatus.SKIPPED,
            finding_summary="Skipped",
            details={},
        ),
    ]

    calc = calculate_risk(results)
    assert calc.final_verdict == FinalVerdict.UNABLE_TO_VERIFY

