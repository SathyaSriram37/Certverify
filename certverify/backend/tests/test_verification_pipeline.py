import uuid
import pytest
from app.models.verification import JobStatus, VerificationJob
from app.tasks.verification_task import execute_verification_pipeline, run_verification


def test_pipeline_missing_job_graceful_exit():
    # If a non-existent job ID is passed, execute_verification_pipeline should exit safely without crashing
    non_existent_id = str(uuid.uuid4())
    dummy_cert_id = str(uuid.uuid4())
    # Should not raise exception
    execute_verification_pipeline(non_existent_id, dummy_cert_id)


def test_celery_task_registration():
    # Confirm run_verification task is registered with celery
    assert run_verification.name == "run_verification"
    assert hasattr(run_verification, "delay")
    assert hasattr(run_verification, "apply_async")
