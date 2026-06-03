"""add webhook inbox receipt model

Revision ID: 0004_webhook_inbox_receipts
Revises: 0003_audit_log
Create Date: 2026-06-03 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_webhook_inbox_receipts"
down_revision = "0003_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_inbox",
        sa.Column("receipt_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("signature_hash", sa.String(length=128), nullable=True),
        sa.Column("external_case_id", sa.String(length=100), nullable=True),
        sa.Column("external_encounter_id", sa.String(length=100), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("validation_warnings", sa.JSON(), nullable=True),
        sa.Column("mapped_case_preview", sa.JSON(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("receipt_id"),
    )
    op.create_index("ix_webhook_inbox_source", "webhook_inbox", ["source"], unique=False)
    op.create_index("ix_webhook_inbox_event_type", "webhook_inbox", ["event_type"], unique=False)
    op.create_index("ux_webhook_inbox_idempotency_key", "webhook_inbox", ["idempotency_key"], unique=True)
    op.create_index("ix_webhook_inbox_payload_hash", "webhook_inbox", ["payload_hash"], unique=False)
    op.create_index("ix_webhook_inbox_external_case_id", "webhook_inbox", ["external_case_id"], unique=False)
    op.create_index("ix_webhook_inbox_external_encounter_id", "webhook_inbox", ["external_encounter_id"], unique=False)
    op.create_index("ix_webhook_inbox_case_id", "webhook_inbox", ["case_id"], unique=False)
    op.create_index("ix_webhook_inbox_status", "webhook_inbox", ["status"], unique=False)
    op.create_index("ix_webhook_inbox_dry_run", "webhook_inbox", ["dry_run"], unique=False)
    op.create_index("ix_webhook_inbox_error_code", "webhook_inbox", ["error_code"], unique=False)
    op.create_index("ix_webhook_inbox_received_at", "webhook_inbox", ["received_at"], unique=False)
    op.create_index("ix_webhook_inbox_processed_at", "webhook_inbox", ["processed_at"], unique=False)
    op.create_index("ix_webhook_inbox_source_received", "webhook_inbox", ["source", "received_at"], unique=False)
    op.create_index("ix_webhook_inbox_status_received", "webhook_inbox", ["status", "received_at"], unique=False)
    op.create_index("ix_webhook_inbox_external_case", "webhook_inbox", ["external_case_id", "external_encounter_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_webhook_inbox_external_case", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_status_received", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_source_received", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_processed_at", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_received_at", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_error_code", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_dry_run", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_status", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_case_id", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_external_encounter_id", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_external_case_id", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_payload_hash", table_name="webhook_inbox")
    op.drop_index("ux_webhook_inbox_idempotency_key", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_event_type", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_source", table_name="webhook_inbox")
    op.drop_table("webhook_inbox")
