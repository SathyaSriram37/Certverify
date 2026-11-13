import sys
import unittest
import os

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.services.verification.risk_engine import calculate_risk, generate_reasoning
from app.models.verification import VerificationResult, ModuleStatus, RiskLevel, FinalVerdict
from app.services.ai.classifier_service import classify
from app.services.ai.entity_extractor import extract
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
import uuid


class TestRiskEngine(unittest.TestCase):
    def test_calculate_risk_verified(self):
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
        self.assertLessEqual(calc.risk_score, 30)
        self.assertEqual(calc.risk_level, RiskLevel.LOW)
        self.assertEqual(calc.final_verdict, FinalVerdict.VERIFIED)

        reasoning = generate_reasoning(results, calc)
        self.assertIn("Passed checks:", reasoning)
        self.assertIn("VERIFIED", reasoning)

    def test_calculate_risk_suspicious(self):
        job_id = uuid.uuid4()
        results = [
            VerificationResult(
                job_id=job_id,
                module_name="IMAGE_FORENSICS",
                status=ModuleStatus.FAIL,
                finding_summary="Tampered image",
                details={},
            ),
            VerificationResult(
                job_id=job_id,
                module_name="COMPANY_INTELLIGENCE",
                status=ModuleStatus.PASS,
                finding_summary="Online presence",
                details={},
            ),
        ]
        calc = calculate_risk(results)
        self.assertEqual(calc.final_verdict, FinalVerdict.SUSPICIOUS)

    def test_calculate_risk_unable_to_verify(self):
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
        ]
        calc = calculate_risk(results)
        self.assertEqual(calc.final_verdict, FinalVerdict.UNABLE_TO_VERIFY)


class TestClassifierAndEntities(unittest.TestCase):
    def test_classification_educational(self):
        text = "Stanford University confers upon John Doe Bachelor of Science with honours."
        res = classify(text)
        self.assertEqual(res.cert_type, "EDUCATIONAL")
        self.assertGreater(res.confidence, 0.0)

    def test_classification_employment(self):
        text = "Experience certificate: Jane worked with us during the service period as senior developer."
        res = classify(text)
        self.assertEqual(res.cert_type, "EMPLOYMENT")
        self.assertGreater(res.confidence, 0.0)

    def test_entity_extraction(self):
        text = """
        Acme Technologies Ltd
        This is to certify that Jane Smith has successfully completed
        Certificate No: ACM-98765-ENG
        Issue Date: October 24, 2025
        https://acmetech.com
        contact@acmetech.com
        Authorized by Director Robert Vance
        """
        entities = extract(text)
        self.assertEqual(entities["candidate_name"], "Jane Smith")
        self.assertIn("Acme", entities["organization_name"] or "")
        self.assertEqual(entities["cert_number"], "ACM-98765-ENG")
        self.assertIsNotNone(entities["issue_date"])
        self.assertEqual(entities["website"], "https://acmetech.com")
        self.assertEqual(entities["email"], "contact@acmetech.com")
        self.assertIsNotNone(entities["signatory"])


if __name__ == "__main__":
    unittest.main()

