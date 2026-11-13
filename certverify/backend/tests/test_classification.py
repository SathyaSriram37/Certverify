from app.services.ai.classifier_service import classify
from app.services.ai.entity_extractor import extract


def test_classify_educational():
    text = "Stanford University certifies that John Doe completed Bachelor of Science in Computer Science with top CGPA."
    res = classify(text)
    assert res.cert_type == "EDUCATIONAL"
    assert res.confidence > 0.0


def test_classify_employment():
    text = "Experience certificate: This is to certify that Alice worked with us as full time software engineer for the service period."
    res = classify(text)
    assert res.cert_type == "EMPLOYMENT"
    assert res.confidence > 0.0


def test_entity_extractor():
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
    assert entities["candidate_name"] == "Jane Smith"
    assert "Acme" in (entities["organization_name"] or "")
    assert entities["cert_number"] == "ACM-98765-ENG"
    assert entities["issue_date"] is not None
    assert entities["website"] == "https://acmetech.com"
    assert entities["email"] == "contact@acmetech.com"
    assert entities["signatory"] is not None

