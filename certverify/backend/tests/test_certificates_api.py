import uuid
import pytest
from fastapi import HTTPException
from app.api.v1.endpoints.certificates import router
from app.models.verification import JobStatus


def test_certificates_router_routes():
    # Verify certificate router endpoints are defined
    route_paths = [r.path for r in router.routes]
    assert "/upload" in route_paths
    assert "/" in route_paths
    assert "/{certificate_id}" in route_paths


def test_invalid_uuid_handling():
    # Verify that a non-UUID string fails validation properly
    invalid_id = "not-a-valid-uuid-1234"
    with pytest.raises(ValueError):
        uuid.UUID(invalid_id)


def test_valid_uuid_parsing():
    test_id = str(uuid.uuid4())
    parsed = uuid.UUID(test_id)
    assert str(parsed) == test_id
