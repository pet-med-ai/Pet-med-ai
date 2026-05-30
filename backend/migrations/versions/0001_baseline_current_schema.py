"""baseline current schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-29 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("patient_name", sa.String(length=255), nullable=False),
        sa.Column("species", sa.String(length=50), nullable=False),
        sa.Column("sex", sa.String(length=10), nullable=True),
        sa.Column("age_info", sa.String(length=50), nullable=True),
        sa.Column("breed", sa.String(length=100), nullable=True),
        sa.Column("weight", sa.String(length=50), nullable=True),
        sa.Column("coat_color", sa.String(length=100), nullable=True),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("owner_phone", sa.String(length=50), nullable=True),
        sa.Column("chief_complaint", sa.Text(), nullable=False),
        sa.Column("history", sa.Text(), nullable=True),
        sa.Column("exam_findings", sa.Text(), nullable=True),
        sa.Column("analysis", sa.Text(), nullable=True),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("prognosis", sa.Text(), nullable=True),
        sa.Column("attachments", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cases_id", "cases", ["id"], unique=False)
    op.create_index("ix_cases_owner_id", "cases", ["owner_id"], unique=False)
    op.create_index("ix_cases_patient_name", "cases", ["patient_name"], unique=False)
    op.create_index("ix_cases_deleted_at", "cases", ["deleted_at"], unique=False)
    op.create_index("ix_cases_patient_species", "cases", ["patient_name", "species"], unique=False)

    op.create_table(
        "consult_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_uid", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consult_sessions_id", "consult_sessions", ["id"], unique=False)
    op.create_index("ix_consult_sessions_session_uid", "consult_sessions", ["session_uid"], unique=True)
    op.create_index("ix_consult_sessions_owner_id", "consult_sessions", ["owner_id"], unique=False)
    op.create_index("ix_consult_sessions_case_id", "consult_sessions", ["case_id"], unique=False)
    op.create_index("ix_consult_sessions_created_at", "consult_sessions", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_consult_sessions_created_at", table_name="consult_sessions")
    op.drop_index("ix_consult_sessions_case_id", table_name="consult_sessions")
    op.drop_index("ix_consult_sessions_owner_id", table_name="consult_sessions")
    op.drop_index("ix_consult_sessions_session_uid", table_name="consult_sessions")
    op.drop_index("ix_consult_sessions_id", table_name="consult_sessions")
    op.drop_table("consult_sessions")

    op.drop_index("ix_cases_patient_species", table_name="cases")
    op.drop_index("ix_cases_deleted_at", table_name="cases")
    op.drop_index("ix_cases_patient_name", table_name="cases")
    op.drop_index("ix_cases_owner_id", table_name="cases")
    op.drop_index("ix_cases_id", table_name="cases")
    op.drop_table("cases")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
