"""initial_tables

Revision ID: 001_initial_tables
Revises: 
Create Date: 2026-11-04 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Safe Enum Creation
    op.execute("DO $$ BEGIN CREATE TYPE user_role_enum AS ENUM ('USER', 'ADMIN', 'HR_VERIFIER'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE job_status_enum AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE module_status_enum AS ENUM ('PASS', 'FAIL', 'WARNING', 'SKIPPED', 'ERROR'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE risk_level_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE final_verdict_enum AS ENUM ('VERIFIED', 'SUSPICIOUS', 'UNABLE_TO_VERIFY'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # 2. Users Table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", postgresql.ENUM("USER", "ADMIN", "HR_VERIFIER", name="user_role_enum", create_type=False), nullable=False, server_default="USER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        if_not_exists=True,
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);")

    # 3. Certificates Table
    op.create_table(
        "certificates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(1024), nullable=False),
        sa.Column("cloudinary_public_id", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        if_not_exists=True,
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_certificates_user_id ON certificates (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_certificates_is_deleted ON certificates (is_deleted);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_certificates_created_at ON certificates (created_at);")

    # 4. Verification Jobs Table
    op.create_table(
        "verification_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("certificate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("certificates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", postgresql.ENUM("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="job_status_enum", create_type=False), nullable=False, server_default="PENDING"),
        sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        if_not_exists=True,
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_jobs_certificate_id ON verification_jobs (certificate_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_jobs_status ON verification_jobs (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_jobs_created_at ON verification_jobs (created_at);")

    # 5. Verification Results Table
    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("verification_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_name", sa.String(50), nullable=False),
        sa.Column("status", postgresql.ENUM("PASS", "FAIL", "WARNING", "SKIPPED", "ERROR", name="module_status_enum", create_type=False), nullable=False),
        sa.Column("finding_summary", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        if_not_exists=True,
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_results_job_id ON verification_results (job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_results_module_name ON verification_results (module_name);")

    # 6. Risk Assessments Table
    op.create_table(
        "risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("verification_jobs.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="risk_level_enum", create_type=False), nullable=False),
        sa.Column("final_verdict", postgresql.ENUM("VERIFIED", "SUSPICIOUS", "UNABLE_TO_VERIFY", name="final_verdict_enum", create_type=False), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("report_url", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        if_not_exists=True,
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_risk_assessments_final_verdict ON risk_assessments (final_verdict);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_risk_assessments_created_at ON risk_assessments (created_at);")

    # 7. Certificate Fingerprints Table
    op.create_table(
        "certificate_fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("certificate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("certificates.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("phash", sa.String(16), nullable=False),
        sa.Column("dhash", sa.String(16), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        if_not_exists=True,
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_certificate_fingerprints_phash ON certificate_fingerprints (phash);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_certificate_fingerprints_dhash ON certificate_fingerprints (dhash);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_certificate_fingerprints_text_hash ON certificate_fingerprints (text_hash);")

    # 8. Audit Logs Table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("user_agent", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        if_not_exists=True,
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_type ON audit_logs (resource_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at);")


def downgrade() -> None:
    op.drop_table("audit_logs", if_exists=True)
    op.drop_table("certificate_fingerprints", if_exists=True)
    op.drop_table("risk_assessments", if_exists=True)
    op.drop_table("verification_results", if_exists=True)
    op.drop_table("verification_jobs", if_exists=True)
    op.drop_table("certificates", if_exists=True)
    op.drop_table("users", if_exists=True)

    op.execute("DROP TYPE IF EXISTS final_verdict_enum")
    op.execute("DROP TYPE IF EXISTS risk_level_enum")
    op.execute("DROP TYPE IF EXISTS module_status_enum")
    op.execute("DROP TYPE IF EXISTS job_status_enum")
    op.execute("DROP TYPE IF EXISTS user_role_enum")
