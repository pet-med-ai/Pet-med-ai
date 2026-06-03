"""add audit log model

Revision ID: 0003_audit_log
Revises: 0002_kpi_data_models
Create Date: 2026-06-01 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_audit_log"
down_revision = "0002_kpi_data_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("log_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("patient_token", sa.String(length=255), nullable=True),
        sa.Column("clinician_id", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.String(length=100), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("session_uid", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_audit_log_confidence_range"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index("ix_audit_log_request_id", "audit_log", ["request_id"], unique=False)
    op.create_index("ix_audit_log_patient_token", "audit_log", ["patient_token"], unique=False)
    op.create_index("ix_audit_log_clinician_id", "audit_log", ["clinician_id"], unique=False)
    op.create_index("ix_audit_log_action_taken", "audit_log", ["action_taken"], unique=False)
    op.create_index("ix_audit_log_case_id", "audit_log", ["case_id"], unique=False)
    op.create_index("ix_audit_log_session_uid", "audit_log", ["session_uid"], unique=False)
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"], unique=False)
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"], unique=False)
    op.create_index("ix_audit_log_request_created_at", "audit_log", ["request_id", "created_at"], unique=False)
    op.create_index("ix_audit_log_clinician_created_at", "audit_log", ["clinician_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_log_clinician_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_request_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_event_type", table_name="audit_log")
    op.drop_index("ix_audit_log_session_uid", table_name="audit_log")
    op.drop_index("ix_audit_log_case_id", table_name="audit_log")
    op.drop_index("ix_audit_log_action_taken", table_name="audit_log")
    op.drop_index("ix_audit_log_clinician_id", table_name="audit_log")
    op.drop_index("ix_audit_log_patient_token", table_name="audit_log")
    op.drop_index("ix_audit_log_request_id", table_name="audit_log")
    op.drop_table("audit_log")
