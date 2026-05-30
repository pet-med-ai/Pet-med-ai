"""add KPI data models

Revision ID: 0002_kpi_data_models
Revises: 0001_baseline
Create Date: 2026-05-30 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_kpi_data_models"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imaging_studies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("modality", sa.String(length=50), nullable=False),
        sa.Column("body_part", sa.String(length=100), nullable=True),
        sa.Column("taken_at", sa.DateTime(), nullable=False),
        sa.Column("is_planned_review", sa.Boolean(), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=True),
        sa.Column("report_url", sa.String(length=500), nullable=True),
        sa.Column("viewer_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_imaging_studies_id", "imaging_studies", ["id"], unique=False)
    op.create_index("ix_imaging_studies_case_id", "imaging_studies", ["case_id"], unique=False)
    op.create_index("ix_imaging_studies_modality", "imaging_studies", ["modality"], unique=False)
    op.create_index("ix_imaging_studies_body_part", "imaging_studies", ["body_part"], unique=False)
    op.create_index("ix_imaging_studies_taken_at", "imaging_studies", ["taken_at"], unique=False)
    op.create_index("ix_imaging_studies_tag", "imaging_studies", ["tag"], unique=False)
    op.create_index(
        "ix_imaging_studies_case_modality_part_time",
        "imaging_studies",
        ["case_id", "modality", "body_part", "taken_at"],
        unique=False,
    )

    op.create_table(
        "imaging_billing",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("imaging_id", sa.Integer(), nullable=True),
        sa.Column("fee", sa.Float(), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=True),
        sa.Column("bill_date", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["imaging_id"], ["imaging_studies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_imaging_billing_id", "imaging_billing", ["id"], unique=False)
    op.create_index("ix_imaging_billing_case_id", "imaging_billing", ["case_id"], unique=False)
    op.create_index("ix_imaging_billing_imaging_id", "imaging_billing", ["imaging_id"], unique=False)
    op.create_index("ix_imaging_billing_tag", "imaging_billing", ["tag"], unique=False)
    op.create_index("ix_imaging_billing_bill_date", "imaging_billing", ["bill_date"], unique=False)
    op.create_index("ix_imaging_billing_case_bill_date", "imaging_billing", ["case_id", "bill_date"], unique=False)

    op.create_table(
        "followups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("done_at", sa.DateTime(), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("owner", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_followups_id", "followups", ["id"], unique=False)
    op.create_index("ix_followups_case_id", "followups", ["case_id"], unique=False)
    op.create_index("ix_followups_due_date", "followups", ["due_date"], unique=False)
    op.create_index("ix_followups_done_at", "followups", ["done_at"], unique=False)
    op.create_index("ix_followups_status", "followups", ["status"], unique=False)
    op.create_index("ix_followups_case_due_date", "followups", ["case_id", "due_date"], unique=False)
    op.create_index("ix_followups_status_due_date", "followups", ["status", "due_date"], unique=False)

    op.create_table(
        "qa_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("auditor", sa.String(length=100), nullable=True),
        sa.Column("audit_type", sa.String(length=50), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qa_audit_id", "qa_audit", ["id"], unique=False)
    op.create_index("ix_qa_audit_case_id", "qa_audit", ["case_id"], unique=False)
    op.create_index("ix_qa_audit_audit_type", "qa_audit", ["audit_type"], unique=False)
    op.create_index("ix_qa_audit_severity", "qa_audit", ["severity"], unique=False)
    op.create_index("ix_qa_audit_status", "qa_audit", ["status"], unique=False)
    op.create_index("ix_qa_audit_created_at", "qa_audit", ["created_at"], unique=False)
    op.create_index("ix_qa_audit_case_created_at", "qa_audit", ["case_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_qa_audit_case_created_at", table_name="qa_audit")
    op.drop_index("ix_qa_audit_created_at", table_name="qa_audit")
    op.drop_index("ix_qa_audit_status", table_name="qa_audit")
    op.drop_index("ix_qa_audit_severity", table_name="qa_audit")
    op.drop_index("ix_qa_audit_audit_type", table_name="qa_audit")
    op.drop_index("ix_qa_audit_case_id", table_name="qa_audit")
    op.drop_index("ix_qa_audit_id", table_name="qa_audit")
    op.drop_table("qa_audit")

    op.drop_index("ix_followups_status_due_date", table_name="followups")
    op.drop_index("ix_followups_case_due_date", table_name="followups")
    op.drop_index("ix_followups_status", table_name="followups")
    op.drop_index("ix_followups_done_at", table_name="followups")
    op.drop_index("ix_followups_due_date", table_name="followups")
    op.drop_index("ix_followups_case_id", table_name="followups")
    op.drop_index("ix_followups_id", table_name="followups")
    op.drop_table("followups")

    op.drop_index("ix_imaging_billing_case_bill_date", table_name="imaging_billing")
    op.drop_index("ix_imaging_billing_bill_date", table_name="imaging_billing")
    op.drop_index("ix_imaging_billing_tag", table_name="imaging_billing")
    op.drop_index("ix_imaging_billing_imaging_id", table_name="imaging_billing")
    op.drop_index("ix_imaging_billing_case_id", table_name="imaging_billing")
    op.drop_index("ix_imaging_billing_id", table_name="imaging_billing")
    op.drop_table("imaging_billing")

    op.drop_index("ix_imaging_studies_case_modality_part_time", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_tag", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_taken_at", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_body_part", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_modality", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_case_id", table_name="imaging_studies")
    op.drop_index("ix_imaging_studies_id", table_name="imaging_studies")
    op.drop_table("imaging_studies")
