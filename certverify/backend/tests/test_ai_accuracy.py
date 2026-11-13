from datetime import datetime, timedelta
import pytest
from app.models.verification import FinalVerdict, ModuleStatus, RiskLevel, VerificationResult
from app.services.ai import classifier_service, document_forensics, entity_extractor, ocr_service
from app.services.verification import risk_engine


def test_classifier_accuracy_iso_and_degrees():
    iso_text = """
    CERTIFICATE OF REGISTRATION
    This is to certify that the Quality Management System of
    Apex Global Solutions Pvt Ltd
    conforms to the requirements of
    ISO 9001:2015
    Scope of certification: Software Design and Cloud Infrastructure.
    Accredited by IAF and NABCB.
    Certificate No: ISO-9001-88492
    """
    res = classifier_service.classify(iso_text)
    assert res.cert_type == "ISO_COMPLIANCE"
    assert res.confidence >= 0.70
    assert "ISO_COMPLIANCE" in res.all_scores

    degree_text = """
    UNIVERSITY OF CAMBRIDGE
    This is to certify that Johnathan Doe
    has been admitted to the Degree of Bachelor of Engineering
    with First Class Honours.
    Cumulative Grade Point Average (CGPA): 8.92
    Controller of Examinations
    """
    res_deg = classifier_service.classify(degree_text)
    assert res_deg.cert_type == "ACADEMIC_DEGREE"
    assert res_deg.confidence >= 0.70


def test_entity_extractor_iso_certificate():
    iso_text = """
    TUV NORD CERT GmbH
    Certificate of Registration
    This is to certify that the Management System of
    TechNova Robotics Private Limited
    has been assessed and found to conform to the requirements of
    ISO 27001:2022
    for the scope of Artificial Intelligence and Data Security.
    Accreditation Body: IAF
    Certificate No: ISO/IEC-27001-9921
    Date of Issue: 15 January 2024
    Valid Until: 14 January 2027
    Official Website: https://www.technovarobotics.com
    Email: audit@tuvnord.com
    Authorized Signatory
    Dr. Marcus Vance
    Managing Director
    """
    entities = entity_extractor.extract(iso_text)
    assert entities["candidate_name"] == "TechNova Robotics Private Limited"
    assert entities["standard_code"] == "ISO 27001:2022"
    assert entities["accreditation_body"] == "IAF"
    assert entities["cert_number"] == "ISO/IEC-27001-9921"
    assert entities["issue_date"] == "15 January 2024"
    assert entities["expiry_date"] == "14 January 2027"
    assert entities["is_expired"] is False
    assert entities["website"] == "https://www.technovarobotics.com"
    assert entities["signatory"] is not None


def test_entity_extractor_expired_certificate():
    past_date = "10 January 2020"
    text = f"""
    GLOBAL CERTIFICATIONS
    Awarded to Ramesh Kumar
    ISO 9001:2015
    Date of Issue: 10 January 2017
    Expiry Date: {past_date}
    """
    entities = entity_extractor.extract(text)
    assert entities["candidate_name"] == "Ramesh Kumar"
    assert entities["is_expired"] is True


def test_risk_engine_authentic_certificate_zero_risk():
    import uuid
    dummy_job_id = uuid.uuid4()
    
    # Simulate a 100% authentic certificate with clean forensic checks
    results = [
        VerificationResult(
            job_id=dummy_job_id,
            module_name="OCR_EXTRACTION",
            status=ModuleStatus.PASS,
            finding_summary="Clean text extracted",
            confidence_score=0.99,
            details={"block_count": 25, "avg_confidence": 0.99},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="CLASSIFICATION",
            status=ModuleStatus.PASS,
            finding_summary="ISO COMPLIANCE (95% confidence)",
            confidence_score=0.95,
            details={"cert_type": "ISO_COMPLIANCE"},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="ENTITY_EXTRACTION",
            status=ModuleStatus.PASS,
            finding_summary="All key entities extracted",
            confidence_score=0.95,
            details={"candidate_name": "Apex Ltd", "standard_code": "ISO 9001:2015"},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="COMPANY_INTELLIGENCE",
            status=ModuleStatus.PASS,
            finding_summary="Verified online on corporate records",
            confidence_score=0.90,
            details={"online_presence_found": True},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="ISO_VERIFICATION",
            status=ModuleStatus.PASS,
            finding_summary="ISO standards verified in IAF register",
            confidence_score=0.95,
            details={"claimed": True, "evidence_found": True},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="PDF_FORENSICS",
            status=ModuleStatus.PASS,
            finding_summary="Pristine PDF document structure (Zero metadata tampering)",
            confidence_score=0.0,
            details={"suspicious_flags": [], "whiteout_data": {"whiteout_detected": False}},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="IMAGE_FORENSICS",
            status=ModuleStatus.PASS,
            finding_summary="FFT Spectral & Physical Integrity Verified",
            confidence_score=0.95,
            details={"ela_suspicious": False, "editing_software_detected": None},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="DUPLICATE_DETECTION",
            status=ModuleStatus.PASS,
            finding_summary="No duplicate matches",
            confidence_score=1.0,
            details={"matches": []},
        ),
    ]

    calc = risk_engine.calculate_risk(results)
    # A pristine authentic certificate must have risk score 0 and VERIFIED verdict
    assert calc.risk_score <= 5
    assert calc.risk_level == RiskLevel.LOW
    assert calc.final_verdict == FinalVerdict.VERIFIED


def test_risk_engine_forged_tampered_certificate():
    import uuid
    dummy_job_id = uuid.uuid4()
    
    # Simulate a forged certificate with Photoshop editing and whiteout
    results = [
        VerificationResult(
            job_id=dummy_job_id,
            module_name="OCR_EXTRACTION",
            status=ModuleStatus.PASS,
            finding_summary="Text extracted",
            confidence_score=0.85,
            details={},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="PDF_FORENSICS",
            status=ModuleStatus.FAIL,
            finding_summary="Covert white-out overlay detected (2 masking patches)",
            confidence_score=0.85,
            details={"whiteout_data": {"whiteout_detected": True}},
        ),
        VerificationResult(
            job_id=dummy_job_id,
            module_name="IMAGE_FORENSICS",
            status=ModuleStatus.FAIL,
            finding_summary="Editing software signature found: Adobe Photoshop",
            confidence_score=0.30,
            details={"editing_software_detected": "Photoshop"},
        ),
    ]

    calc = risk_engine.calculate_risk(results)
    assert calc.risk_score >= 65
    assert calc.risk_level == RiskLevel.HIGH
    assert calc.final_verdict == FinalVerdict.SUSPICIOUS

