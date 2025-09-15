"""bootstrap users & cases tables (idempotent create)"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# === Alembic identifiers（按你的实际值替换）===
revision = "9ee4c9534807"       # ← 这里填这条迁移的 revision（一般与文件名开头一致）
down_revision = "664a5f32576b"  # ← 这里填上一条迁移的 revision
branch_labels = None
depends_on = None


# --------- 工具：存在性检测，避免重复创建 ----------
def _has_table(bind, name: str) -> bool:
    return inspect(bind).has_table(name)

def _has_index(bind, table: str, index_name: str) -> bool:
    insp = inspect(bind)
    try:
        idxs = [ix["name"] for ix in insp.get_indexes(table)]
    except Exception:
        return False
    return index_name in idxs


# ===================== 迁移：升级 =====================
def upgrade() -> None:
    bind = op.get_bind()

    # 1) users 表（若不存在则创建）
    if not _has_table(bind, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False,
                      server_default=sa.text("(CURRENT_TIMESTAMP)")),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )
        if not _has_index(bind, "users", "ix_users_id"):
            op.create_index("ix_users_id", "users", ["id"])
        if not _has_index(bind, "users", "ix_users_email"):
            op.create_index("ix_users_email", "users", ["email"])

    # 2) cases 表（若不存在则创建）
    if not _has_table(bind, "cases"):
        op.create_table(
            "cases",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),

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

            sa.Column("attachments", sa.JSON(), nullable=True),

            sa.Column("created_at", sa.DateTime(), nullable=False,
                      server_default=sa.text("(CURRENT_TIMESTAMP)")),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),

            sa.ForeignKeyConstraint(
                ["owner_id"], ["users.id"],
                name="fk_cases_owner_id_users", ondelete="CASCADE"
            ),
        )

        # 索引（若不存在则创建）
        if not _has_index(bind, "cases", "ix_cases_id"):
            op.create_index("ix_cases_id", "cases", ["id"])
        if not _has_index(bind, "cases", "ix_cases_owner_id"):
            op.create_index("ix_cases_owner_id", "cases", ["owner_id"])
        if not _has_index(bind, "cases", "ix_cases_patient_name"):
            op.create_index("ix_cases_patient_name", "cases", ["patient_name"])
        if not _has_index(bind, "cases", "ix_cases_deleted_at"):
            op.create_index("ix_cases_deleted_at", "cases", ["deleted_at"])


# ===================== 迁移：回退 =====================
def downgrade() -> None:
    bind = op.get_bind()

    # 先删 cases（先索引、再外键、再表）
    if _has_table(bind, "cases"):
        for ix in ("ix_cases_deleted_at", "ix_cases_patient_name", "ix_cases_owner_id", "ix_cases_id"):
            if _has_index(bind, "cases", ix):
                op.drop_index(ix, table_name="cases")
        try:
            op.drop_constraint("fk_cases_owner_id_users", "cases", type_="foreignkey")
        except Exception:
            pass
        op.drop_table("cases")

    # 再删 users（先索引、再唯一约束、再表）
    if _has_table(bind, "users"):
        for ix in ("ix_users_email", "ix_users_id"):
            if _has_index(bind, "users", ix):
                op.drop_index(ix, table_name="users")
        try:
            op.drop_constraint("uq_users_email", "users", type_="unique")
        except Exception:
            pass
        op.drop_table("users")
