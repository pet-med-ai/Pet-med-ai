from alembic import op
import sqlalchemy as sa

# 修订标识
revision = "0001_create_cases"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("patient_name", sa.String(length=255), nullable=False),
        sa.Column("species", sa.String(length=50), nullable=False, server_default="dog"),
        sa.Column("sex", sa.String(length=10), nullable=True),
        sa.Column("age_info", sa.String(length=50), nullable=True),
        sa.Column("chief_complaint", sa.Text(), nullable=False),
        sa.Column("history", sa.Text(), nullable=True),
        sa.Column("exam_findings", sa.Text(), nullable=True),
        sa.Column("analysis", sa.Text(), nullable=True),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("prognosis", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_cases_id", "cases", ["id"])
    op.create_index("ix_cases_patient_name", "cases", ["patient_name"])

def downgrade():
    op.drop_index("ix_cases_patient_name", table_name="cases")
    op.drop_index("ix_cases_id", table_name="cases")
    op.drop_table("cases")
