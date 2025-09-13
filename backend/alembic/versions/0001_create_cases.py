from alembic import op
import sqlalchemy as sa

# 保持 alembic 自动生成的 revision
revision = "664a5f32576b"
down_revision = "0e708f4e65f5"   # ← 这里写上一步文件的 revision
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("cases", sa.Column("attachments", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column("cases", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_cases_deleted_at", "cases", ["deleted_at"])

def downgrade() -> None:
    op.drop_index("ix_cases_deleted_at", table_name="cases")
    op.drop_column("cases", "deleted_at")
    op.drop_column("cases", "updated_at")
    op.drop_column("cases", "attachments")
