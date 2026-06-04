"""add EMR real import batch models

Revision ID: 0005_emr_import_batches
Revises: 0004_webhook_inbox_receipts
Create Date: 2026-06-04 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_emr_import_batches"
down_revision = "0004_webhook_inbox_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emr_import_batches",
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("receipt_count", sa.Integer(), nullable=False),
        sa.Column("ready_for_import_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("review_action_count", sa.Integer(), nullable=False),
        sa.Column("clinical_signoff_id", sa.String(length=100), nullable=True),
        sa.Column("rollback_snapshot_id", sa.String(length=100), nullable=True),
        sa.Column("frozen_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("batch_id"),
    )
    op.create_index("ix_emr_import_batches_source_system", "emr_import_batches", ["source_system"], unique=False)
    op.create_index("ix_emr_import_batches_status", "emr_import_batches", ["status"], unique=False)
    op.create_index("ix_emr_import_batches_clinical_signoff_id", "emr_import_batches", ["clinical_signoff_id"], unique=False)
    op.create_index("ix_emr_import_batches_rollback_snapshot_id", "emr_import_batches", ["rollback_snapshot_id"], unique=False)
    op.create_index("ix_emr_import_batches_frozen_at", "emr_import_batches", ["frozen_at"], unique=False)
    op.create_index("ix_emr_import_batches_approved_at", "emr_import_batches", ["approved_at"], unique=False)
    op.create_index("ix_emr_import_batches_started_at", "emr_import_batches", ["started_at"], unique=False)
    op.create_index("ix_emr_import_batches_completed_at", "emr_import_batches", ["completed_at"], unique=False)
    op.create_index("ix_emr_import_batches_created_by", "emr_import_batches", ["created_by"], unique=False)
    op.create_index("ix_emr_import_batches_approved_by", "emr_import_batches", ["approved_by"], unique=False)
    op.create_index("ix_emr_import_batches_created_at", "emr_import_batches", ["created_at"], unique=False)
    op.create_index("ix_emr_import_batches_status_created", "emr_import_batches", ["status", "created_at"], unique=False)
    op.create_index("ix_emr_import_batches_source_status", "emr_import_batches", ["source_system", "status"], unique=False)

    op.create_table(
        "emr_import_batch_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_id", sa.String(length=64), nullable=False),
        sa.Column("review_status", sa.String(length=50), nullable=True),
        sa.Column("ready_for_import", sa.Boolean(), nullable=False),
        sa.Column("external_case_id", sa.String(length=100), nullable=True),
        sa.Column("external_encounter_id", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["emr_import_batches.batch_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_id"], ["webhook_inbox.receipt_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emr_import_batch_receipts_id", "emr_import_batch_receipts", ["id"], unique=False)
    op.create_index("ix_emr_import_batch_receipts_batch_id", "emr_import_batch_receipts", ["batch_id"], unique=False)
    op.create_index("ix_emr_import_batch_receipts_receipt_id", "emr_import_batch_receipts", ["receipt_id"], unique=False)
    op.create_index("ix_emr_import_batch_receipts_review_status", "emr_import_batch_receipts", ["review_status"], unique=False)
    op.create_index("ix_emr_import_batch_receipts_ready_for_import", "emr_import_batch_receipts", ["ready_for_import"], unique=False)
    op.create_index("ix_emr_import_batch_receipts_external_case_id", "emr_import_batch_receipts", ["external_case_id"], unique=False)
    op.create_index("ix_emr_import_batch_receipts_external_encounter_id", "emr_import_batch_receipts", ["external_encounter_id"], unique=False)
    op.create_index("ix_emr_import_batch_receipts_created_at", "emr_import_batch_receipts", ["created_at"], unique=False)
    op.create_index("ux_emr_import_batch_receipt", "emr_import_batch_receipts", ["batch_id", "receipt_id"], unique=True)
    op.create_index("ix_emr_import_batch_receipts_ready", "emr_import_batch_receipts", ["batch_id", "ready_for_import"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_emr_import_batch_receipts_ready", table_name="emr_import_batch_receipts")
    op.drop_index("ux_emr_import_batch_receipt", table_name="emr_import_batch_receipts")
    op.drop_index("ix_emr_import_batch_receipts_created_at", table_name="emr_import_batch_receipts")
    op.drop_index("ix_emr_import_batch_receipts_external_encounter_id", table_name="emr_import_batch_receipts")
    op.drop_index("ix_emr_import_batch_receipts_external_case_id", table_name="emr_import_batch_receipts")
    op.drop_index("ix_emr_import_batch_receipts_ready_for_import", table_name="emr_import_batch_receipts")
    op.drop_index("ix_emr_import_batch_receipts_review_status", table_name="emr_import_batch_receipts")
    op.drop_index("ix_emr_import_batch_receipts_receipt_id", table_name="emr_import_batch_receipts")
    op.drop_index("ix_emr_import_batch_receipts_batch_id", table_name="emr_import_batch_receipts")
    op.drop_index("ix_emr_import_batch_receipts_id", table_name="emr_import_batch_receipts")
    op.drop_table("emr_import_batch_receipts")

    op.drop_index("ix_emr_import_batches_source_status", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_status_created", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_created_at", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_approved_by", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_created_by", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_completed_at", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_started_at", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_approved_at", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_frozen_at", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_rollback_snapshot_id", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_clinical_signoff_id", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_status", table_name="emr_import_batches")
    op.drop_index("ix_emr_import_batches_source_system", table_name="emr_import_batches")
    op.drop_table("emr_import_batches")
