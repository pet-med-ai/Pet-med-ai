"""add diagnostic data models

Revision ID: 0009_diag_data
Revises: 0008_auto_delivery
Create Date: 2026-06-19 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009_diag_data"
down_revision = "0008_auto_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_system", sa.String(length=100), nullable=True),
        sa.Column("source_report_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("report_text", sa.Text(), nullable=True),
        sa.Column("abnormal_summary", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_summary_status", sa.String(length=50), nullable=False),
        sa.Column("ordering_clinician", sa.String(length=120), nullable=True),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("attachment_ref", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diag_reports_case_id", "diagnostic_reports", ["case_id"], unique=False)
    op.create_index("ix_diag_reports_status", "diagnostic_reports", ["status"], unique=False)
    op.create_index("ix_diag_reports_source", "diagnostic_reports", ["source_type"], unique=False)
    op.create_index("ix_diag_reports_ai_status", "diagnostic_reports", ["ai_summary_status"], unique=False)

    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("diagnostic_report_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("value_text", sa.String(length=255), nullable=True),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_type", sa.String(length=50), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("reference_low", sa.Float(), nullable=True),
        sa.Column("reference_high", sa.Float(), nullable=True),
        sa.Column("reference_text", sa.String(length=255), nullable=True),
        sa.Column("abnormal_flag", sa.String(length=50), nullable=True),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("specimen_type", sa.String(length=100), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("review_status", sa.String(length=50), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["diagnostic_report_id"], ["diagnostic_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_observations_case_id", "observations", ["case_id"], unique=False)
    op.create_index("ix_observations_report_id", "observations", ["diagnostic_report_id"], unique=False)
    op.create_index("ix_observations_code", "observations", ["code"], unique=False)
    op.create_index("ix_observations_abnormal", "observations", ["abnormal_flag"], unique=False)
    op.create_index("ix_observations_review", "observations", ["review_status"], unique=False)

    op.add_column("imaging_studies", sa.Column("study_uid", sa.String(length=255), nullable=True))
    op.add_column("imaging_studies", sa.Column("accession_number", sa.String(length=120), nullable=True))
    op.add_column("imaging_studies", sa.Column("source_type", sa.String(length=50), nullable=True))
    op.add_column("imaging_studies", sa.Column("source_system", sa.String(length=100), nullable=True))
    op.add_column("imaging_studies", sa.Column("report_text", sa.Text(), nullable=True))
    op.add_column("imaging_studies", sa.Column("abnormal_flag", sa.String(length=50), nullable=True))
    op.add_column("imaging_studies", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.add_column("imaging_studies", sa.Column("ai_summary_status", sa.String(length=50), nullable=True))
    op.add_column("imaging_studies", sa.Column("review_status", sa.String(length=50), nullable=True))
    op.add_column("imaging_studies", sa.Column("reviewed_by", sa.String(length=120), nullable=True))
    op.add_column("imaging_studies", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("imaging_studies", sa.Column("attachment_ref", sa.String(length=500), nullable=True))
    op.add_column("imaging_studies", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.create_index("ix_img_studies_source", "imaging_studies", ["source_type"], unique=False)
    op.create_index("ix_img_studies_review", "imaging_studies", ["review_status"], unique=False)
    op.create_index("ix_img_studies_abnormal", "imaging_studies", ["abnormal_flag"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_img_studies_abnormal", table_name="imaging_studies")
    op.drop_index("ix_img_studies_review", table_name="imaging_studies")
    op.drop_index("ix_img_studies_source", table_name="imaging_studies")

    with op.batch_alter_table("imaging_studies") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("attachment_ref")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by")
        batch_op.drop_column("review_status")
        batch_op.drop_column("ai_summary_status")
        batch_op.drop_column("ai_summary")
        batch_op.drop_column("abnormal_flag")
        batch_op.drop_column("report_text")
        batch_op.drop_column("source_system")
        batch_op.drop_column("source_type")
        batch_op.drop_column("accession_number")
        batch_op.drop_column("study_uid")

    op.drop_index("ix_observations_review", table_name="observations")
    op.drop_index("ix_observations_abnormal", table_name="observations")
    op.drop_index("ix_observations_code", table_name="observations")
    op.drop_index("ix_observations_report_id", table_name="observations")
    op.drop_index("ix_observations_case_id", table_name="observations")
    op.drop_table("observations")

    op.drop_index("ix_diag_reports_ai_status", table_name="diagnostic_reports")
    op.drop_index("ix_diag_reports_source", table_name="diagnostic_reports")
    op.drop_index("ix_diag_reports_status", table_name="diagnostic_reports")
    op.drop_index("ix_diag_reports_case_id", table_name="diagnostic_reports")
    op.drop_table("diagnostic_reports")
