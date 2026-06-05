"""add EMR import execution result models

Revision ID: 0006_emr_import_results
Revises: 0005_emr_import_batches
Create Date: 2026-06-05 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006_emr_import_results"
down_revision = "0005_emr_import_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emr_import_execution_runs",
        sa.Column("execution_id", sa.String(length=64), nullable=False),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("mode", sa.String(length=100), nullable=False),
        sa.Column("operator_id", sa.String(length=100), nullable=True),
        sa.Column("clinical_signoff_id", sa.String(length=100), nullable=True),
        sa.Column("rollback_snapshot_id", sa.String(length=100), nullable=True),
        sa.Column("approval_audit_log_id", sa.String(length=64), nullable=True),
        sa.Column("receipt_count", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("rolled_back_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["approval_audit_log_id"], ["audit_log.log_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["batch_id"], ["emr_import_batches.batch_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("execution_id"),
    )
    op.create_index("ix_emr_import_execution_runs_batch_id", "emr_import_execution_runs", ["batch_id"], unique=False)
    op.create_index("ix_emr_import_execution_runs_status", "emr_import_execution_runs", ["status"], unique=False)
    op.create_index("ix_emr_import_execution_runs_source_system", "emr_import_execution_runs", ["source_system"], unique=False)
    op.create_index("ix_emr_import_execution_runs_operator_id", "emr_import_execution_runs", ["operator_id"], unique=False)
    op.create_index("ix_emr_import_execution_runs_clinical_signoff_id", "emr_import_execution_runs", ["clinical_signoff_id"], unique=False)
    op.create_index("ix_emr_import_execution_runs_rollback_snapshot_id", "emr_import_execution_runs", ["rollback_snapshot_id"], unique=False)
    op.create_index("ix_emr_import_execution_runs_approval_audit_log_id", "emr_import_execution_runs", ["approval_audit_log_id"], unique=False)
    op.create_index("ix_emr_import_execution_runs_started_at", "emr_import_execution_runs", ["started_at"], unique=False)
    op.create_index("ix_emr_import_execution_runs_completed_at", "emr_import_execution_runs", ["completed_at"], unique=False)
    op.create_index("ix_emr_import_execution_runs_rolled_back_at", "emr_import_execution_runs", ["rolled_back_at"], unique=False)
    op.create_index("ix_emr_import_execution_runs_created_by", "emr_import_execution_runs", ["created_by"], unique=False)
    op.create_index("ix_emr_import_execution_runs_created_at", "emr_import_execution_runs", ["created_at"], unique=False)
    op.create_index("ix_emr_import_execution_runs_batch_status", "emr_import_execution_runs", ["batch_id", "status"], unique=False)
    op.create_index("ix_emr_import_execution_runs_source_created", "emr_import_execution_runs", ["source_system", "created_at"], unique=False)

    op.create_table(
        "emr_import_execution_item_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.String(length=64), nullable=False),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_id", sa.String(length=64), nullable=True),
        sa.Column("external_case_id", sa.String(length=100), nullable=True),
        sa.Column("external_encounter_id", sa.String(length=100), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_case_id", sa.Integer(), nullable=True),
        sa.Column("target_case_id", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("rollback_status", sa.String(length=50), nullable=True),
        sa.Column("rollback_note", sa.Text(), nullable=True),
        sa.Column("case_diff", sa.JSON(), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["emr_import_batches.batch_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["execution_id"], ["emr_import_execution_runs.execution_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receipt_id"], ["webhook_inbox.receipt_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emr_import_execution_item_results_id", "emr_import_execution_item_results", ["id"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_execution_id", "emr_import_execution_item_results", ["execution_id"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_batch_id", "emr_import_execution_item_results", ["batch_id"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_receipt_id", "emr_import_execution_item_results", ["receipt_id"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_external_case_id", "emr_import_execution_item_results", ["external_case_id"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_external_encounter_id", "emr_import_execution_item_results", ["external_encounter_id"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_idempotency_key", "emr_import_execution_item_results", ["idempotency_key"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_payload_hash", "emr_import_execution_item_results", ["payload_hash"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_operation", "emr_import_execution_item_results", ["operation"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_status", "emr_import_execution_item_results", ["status"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_created_case_id", "emr_import_execution_item_results", ["created_case_id"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_target_case_id", "emr_import_execution_item_results", ["target_case_id"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_failure_code", "emr_import_execution_item_results", ["failure_code"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_rollback_status", "emr_import_execution_item_results", ["rollback_status"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_started_at", "emr_import_execution_item_results", ["started_at"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_completed_at", "emr_import_execution_item_results", ["completed_at"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_rolled_back_at", "emr_import_execution_item_results", ["rolled_back_at"], unique=False)
    op.create_index("ix_emr_import_execution_item_results_created_at", "emr_import_execution_item_results", ["created_at"], unique=False)
    op.create_index("ux_emr_import_execution_item_receipt", "emr_import_execution_item_results", ["execution_id", "receipt_id"], unique=True)
    op.create_index("ix_emr_import_execution_items_batch_status", "emr_import_execution_item_results", ["batch_id", "status"], unique=False)
    op.create_index("ix_emr_import_execution_items_failure", "emr_import_execution_item_results", ["failure_code", "status"], unique=False)
    op.create_index("ix_emr_import_execution_items_created_case", "emr_import_execution_item_results", ["created_case_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_emr_import_execution_items_created_case", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_items_failure", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_items_batch_status", table_name="emr_import_execution_item_results")
    op.drop_index("ux_emr_import_execution_item_receipt", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_created_at", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_rolled_back_at", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_completed_at", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_started_at", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_rollback_status", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_failure_code", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_target_case_id", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_created_case_id", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_status", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_operation", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_payload_hash", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_idempotency_key", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_external_encounter_id", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_external_case_id", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_receipt_id", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_batch_id", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_execution_id", table_name="emr_import_execution_item_results")
    op.drop_index("ix_emr_import_execution_item_results_id", table_name="emr_import_execution_item_results")
    op.drop_table("emr_import_execution_item_results")

    op.drop_index("ix_emr_import_execution_runs_source_created", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_batch_status", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_created_at", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_created_by", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_rolled_back_at", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_completed_at", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_started_at", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_approval_audit_log_id", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_rollback_snapshot_id", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_clinical_signoff_id", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_operator_id", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_source_system", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_status", table_name="emr_import_execution_runs")
    op.drop_index("ix_emr_import_execution_runs_batch_id", table_name="emr_import_execution_runs")
    op.drop_table("emr_import_execution_runs")
