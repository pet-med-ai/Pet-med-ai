from alembic import op
import sqlalchemy as sa

# revision 保持 Alembic 自动生成的，不要改
revision = "0e708f4e65f5"
down_revision = "0001_create_cases"   # 对应第一条迁移
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1) users 表
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    # 2) cases 表新增 owner_id
    op.add_column("cases", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index("ix_cases_owner_id", "cases", ["owner_id"])
    op.create_foreign_key(
        "fk_cases_owner_id_users", "cases", "users",
        ["owner_id"], ["id"], ondelete="CASCADE"
    )

def downgrade() -> None:
    # 删除外键/列
    op.drop_constraint("fk_cases_owner_id_users", "cases", type_="foreignkey")
    op.drop_index("ix_cases_owner_id", table_name="cases")
    op.drop_column("cases", "owner_id")

    # 删除 users
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
