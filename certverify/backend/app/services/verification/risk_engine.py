from dataclasses import dataclass
from typing import Dict, List, Optional
from app.models.verification import FinalVerdict, ModuleStatus, RiskLevel, VerificationResult

MODULE_WEIGHTS: Dict[str, int] = {
    "OCR_EXTRACTION": 5,
    "CLASSIFICATION": 5,
    "ENTITY_EXTRACTION": 10,
    "COMPANY_INTELLIGENCE": 20,
    "LOGO_SIMILARITY": 10,
    "ISO_VERIFICATION": 10,
    "PDF_FORENSICS": 25,
    "IMAGE_FORENSICS": 25,
    "QR_CODE": 15,
    "DIGITAL_SIGNATURE": 15,
    "DUPLICATE_DETECTION": 20,
}


@dataclass
class RiskCalc:
    risk_score: int
    risk_level: RiskLevel
    final_verdict: FinalVerdict
    module_summary: Dict[str, str]


def calculate_risk(results: List[VerificationResult]) -> RiskCalc:
    """
    Enterprise Calibrated Risk Engine.
    Differentiates between severe forensic forgery (FAIL) and
    routine advisory warnings (WARNING) while rewarding verified authenticity signals.
    """
    base_risk = 0.0
    critical_penalties = 0.0
    positive_trust = 0.0

    has_hard_fail = False
    hard_fail_reasons: List[str] = []

    for r in results:
        mod = r.module_name
        status = r.status
        details = r.details or {}

        # 1. CRITICAL FORGERY SIGNALS (Hard Fails)
        if status == ModuleStatus.FAIL:
            has_hard_fail = True
            if mod in ["PDF_FORENSICS", "IMAGE_FORENSICS"]:
                critical_penalties += 45.0
                hard_fail_reasons.append("Forensic manipulation detected")
            elif mod == "QR_CODE":
                critical_penalties += 35.0
                hard_fail_reasons.append("Fraudulent QR redirect")
            elif mod == "DUPLICATE_DETECTION":
                critical_penalties += 30.0
                hard_fail_reasons.append("Duplicate or plagiarized certificate")
            else:
                critical_penalties += 20.0

        # 2. ADVISORY WARNINGS (Calibrated per module)
        elif status == ModuleStatus.WARNING:
            if mod == "PDF_FORENSICS":
                # Check if it was just font variety vs modification
                if details.get("modification_suspected"):
                    base_risk += 12.0
                elif details.get("whiteout_data", {}).get("whiteout_detected"):
                    critical_penalties += 40.0
                else:
                    base_risk += 3.0  # Mild styling note
            elif mod == "IMAGE_FORENSICS":
                if details.get("deepfake_audit", {}).get("is_ai_generated"):
                    critical_penalties += 40.0
                elif details.get("editing_software_detected"):
                    base_risk += 15.0
                else:
                    base_risk += 4.0
            elif mod == "COMPANY_INTELLIGENCE":
                # Unverified online is advisory, not proof of fraud
                base_risk += 6.0
            elif mod == "ISO_VERIFICATION":
                # Claimed unverified standard
                base_risk += 4.0
            elif mod == "DUPLICATE_DETECTION":
                base_risk += 10.0
            else:
                base_risk += 2.0

        # 3. POSITIVE TRUST CREDITS (Evidence of Genuine Authenticity)
        elif status == ModuleStatus.PASS:
            if mod == "IMAGE_FORENSICS":
                positive_trust += 8.0  # Clean FFT spectrum and ELA
            elif mod == "PDF_FORENSICS":
                positive_trust += 8.0  # Clean metadata, no revisions
            elif mod == "COMPANY_INTELLIGENCE":
                positive_trust += 10.0  # Issuer verified in live public web / registry
            elif mod == "ISO_VERIFICATION":
                positive_trust += 10.0  # Real ISO standards verified
            elif mod == "DIGITAL_SIGNATURE":
                positive_trust += 15.0  # Cryptographic signature present and valid
            elif mod == "QR_CODE":
                positive_trust += 8.0  # Valid QR destination matches issuer
            elif mod == "ENTITY_EXTRACTION":
                positive_trust += 5.0  # All essential credential fields resolved

    # Calculate final score
    if has_hard_fail:
        # Forgeries scale between 65 and 100
        score = int(min(100, max(65, 50.0 + critical_penalties + base_risk - positive_trust)))
    else:
        # Legitimate documents: net penalty minus trust credits
        raw_net = base_risk - (positive_trust * 0.4)
        score = int(max(0, min(55, raw_net)))

    # Determine Risk Level
    if score <= 20:
        level = RiskLevel.LOW
    elif score <= 50:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.HIGH

    # Determine Final Verdict
    mostly_skipped = (
        sum(1 for r in results if r.status == ModuleStatus.SKIPPED)
        > (len(results) * 0.65)
        if results
        else True
    )

    if mostly_skipped:
        verdict = FinalVerdict.UNABLE_TO_VERIFY
    elif has_hard_fail or score > 50:
        verdict = FinalVerdict.SUSPICIOUS
    else:
        verdict = FinalVerdict.VERIFIED

    module_summary = {r.module_name: r.status.value for r in results}

    return RiskCalc(
        risk_score=score,
        risk_level=level,
        final_verdict=verdict,
        module_summary=module_summary,
    )


def generate_reasoning(results: List[VerificationResult], calc: RiskCalc) -> str:
    passed = [r for r in results if r.status == ModuleStatus.PASS]
    warnings = [r for r in results if r.status == ModuleStatus.WARNING]
    failures = [r for r in results if r.status == ModuleStatus.FAIL]

    parts: List[str] = []
    
    if calc.final_verdict == FinalVerdict.VERIFIED:
        parts.append(f"CertVerify AI successfully verified this credential with high authenticity confidence (Risk Score: {calc.risk_score}/100).")
        if passed:
            parts.append(f"Passed verification checks: {', '.join(r.module_name.replace('_', ' ').title() for r in passed[:5])}.")
    elif calc.final_verdict == FinalVerdict.SUSPICIOUS:
        parts.append(f"CertVerify AI flagged this document as suspicious (Risk Score: {calc.risk_score}/100).")
        if failures:
            parts.append(f"Critical violations detected: {'; '.join(r.finding_summary for r in failures)}.")
        if warnings:
            parts.append(f"Advisory anomalies: {'; '.join(r.finding_summary for r in warnings[:3])}.")
    else:
        parts.append(f"Verification was inconclusive due to insufficient data or unresolvable document channels.")

    parts.append("All assessments are driven by automated neural pattern matching, digital metadata forensics, and live public registers.")
    return " ".join(parts)
