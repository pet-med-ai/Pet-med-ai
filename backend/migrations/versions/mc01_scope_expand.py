"""Add explicit organization/clinic ownership; no inferred memberships or rollout.

Revision ID: mc01_scope_expand
Revises: 0009_diag_data
"""

from alembic import op
import sqlalchemy as sa

revision = "mc01_scope_expand"
down_revision = "0009_diag_data"
branch_labels = None
depends_on = None


def uid(name, **kw):
    return sa.Column(name, sa.Uuid(as_uuid=False), **kw)


def upgrade():
    op.add_column(
        "users",
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
    )
    op.add_column(
        "users",
        sa.Column(
            "principal_kind", sa.String(16), nullable=False, server_default="human"
        ),
    )
    op.add_column(
        "users",
        sa.Column("token_version", sa.BigInteger(), nullable=False, server_default="1"),
    )
    with op.batch_alter_table("users") as batch:
        batch.create_check_constraint(
            "ck_user_active_status", "status IN ('active','suspended','revoked')"
        )
        batch.create_check_constraint(
            "ck_user_principal_kind", "principal_kind IN ('human','service')"
        )
        batch.create_check_constraint("ck_user_token_version", "token_version >= 1")
    op.create_table(
        "organizations",
        uid("id", primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("authz_epoch", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("status IN ('active','suspended')", name="ck_org_status"),
    )
    op.create_table(
        "clinics",
        uid("id", primary_key=True),
        uid("org_id", nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "timezone", sa.String(60), nullable=False, server_default="Asia/Shanghai"
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("org_id", "id", name="uq_clinic_org_id"),
        sa.UniqueConstraint("org_id", "code", name="uq_clinic_org_code"),
        sa.CheckConstraint("status IN ('active','suspended')", name="ck_clinic_status"),
    )
    op.create_table(
        "org_memberships",
        uid("id", primary_key=True),
        uid("org_id", nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("authz_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_member_org_user"),
        sa.UniqueConstraint("org_id", "id", name="uq_member_org_id"),
        sa.CheckConstraint(
            "status IN ('active','suspended','revoked')", name="ck_member_status"
        ),
    )
    op.create_table(
        "role_bindings",
        uid("id", primary_key=True),
        uid("org_id", nullable=False),
        uid("membership_id", nullable=False),
        uid("clinic_id", nullable=True),
        sa.Column("scope_kind", sa.String(16), nullable=False),
        sa.Column("role_code", sa.String(32), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "granted_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "membership_id"],
            ["org_memberships.org_id", "org_memberships.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "clinic_id"],
            ["clinics.org_id", "clinics.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(scope_kind='org' AND clinic_id IS NULL AND role_code='org_admin') OR "
            "(scope_kind='clinic' AND clinic_id IS NOT NULL AND role_code IN "
            "('clinic_admin','veterinarian','clinical_assistant','frontdesk','cashier','pharmacist','clinical_auditor'))",
            name="ck_role_scope",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from", name="ck_role_period"
        ),
    )
    op.create_index(
        "ix_role_member_scope",
        "role_bindings",
        ["org_id", "membership_id", "clinic_id"],
    )
    op.create_table(
        "patients",
        uid("id", primary_key=True),
        uid("org_id", nullable=False),
        sa.Column("patient_no", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("species", sa.String(50), nullable=False),
        sa.Column("demographics", sa.JSON()),
        sa.Column("row_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("org_id", "id", name="uq_patient_org_id"),
        sa.UniqueConstraint("org_id", "patient_no", name="uq_patient_org_no"),
    )
    # Nullable expansion permits an audited, separate backfill. No account -> staff guess.
    for column in (
        uid("org_id"),
        uid("clinic_id"),
        uid("patient_id"),
        sa.Column(
            "visibility", sa.String(20), nullable=False, server_default="owner_private"
        ),
        sa.Column("row_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column(
            "clinical_epoch", sa.BigInteger(), nullable=False, server_default="1"
        ),
    ):
        op.add_column("cases", column)
    owner_fk = next(
        fk
        for fk in sa.inspect(op.get_bind()).get_foreign_keys("cases")
        if fk["constrained_columns"] == ["owner_id"]
    )
    with op.batch_alter_table(
        "cases",
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        },
    ) as batch:
        batch.drop_constraint(
            owner_fk["name"] or "fk_cases_owner_id_users", type_="foreignkey"
        )
        batch.create_foreign_key(
            "fk_cases_owner_id_users",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_case_clinic_scope",
            "clinics",
            ["org_id", "clinic_id"],
            ["org_id", "id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_case_patient_scope",
            "patients",
            ["org_id", "patient_id"],
            ["org_id", "id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint("uq_case_scope", ["org_id", "clinic_id", "id"])
        batch.create_check_constraint(
            "ck_case_scope_pair",
            "(org_id IS NULL AND clinic_id IS NULL AND patient_id IS NULL) OR (org_id IS NOT NULL AND clinic_id IS NOT NULL)",
        )
        batch.create_check_constraint(
            "ck_case_visibility", "visibility IN ('owner_private','clinic')"
        )
    op.create_index("ix_cases_scope_id", "cases", ["org_id", "clinic_id", "id"])
    op.create_table(
        "case_access_grants",
        uid("id", primary_key=True),
        uid("org_id", nullable=False),
        uid("clinic_id", nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        uid("grantee_membership_id", nullable=False),
        sa.Column(
            "permission", sa.String(32), nullable=False, server_default="clinical.read"
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "granted_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "clinic_id", "case_id"],
            ["cases.org_id", "cases.clinic_id", "cases.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "grantee_membership_id"],
            ["org_memberships.org_id", "org_memberships.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "permission='clinical.read' AND length(trim(reason)) > 0",
            name="ck_case_grant_read_only",
        ),
    )
    op.create_index(
        "ix_grant_member_case",
        "case_access_grants",
        ["org_id", "grantee_membership_id", "case_id"],
    )
    op.create_table(
        "auth_sessions",
        uid("id", primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("token_version", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "access_audit_events",
        uid("id", primary_key=True),
        uid("org_id", nullable=False),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("request_key", sa.String(64), nullable=False),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("target_type", sa.String(60), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("before_permissions", sa.JSON()),
        sa.Column("after_permissions", sa.JSON()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("org_id", "request_key", name="uq_access_audit_request"),
    )
    op.create_table(
        "migration_batches",
        uid("id", primary_key=True),
        sa.Column("migration_key", sa.String(80), nullable=False),
        sa.Column("batch_no", sa.Integer(), nullable=False),
        sa.Column("last_entity_id", sa.Integer()),
        sa.Column("mapping_sha256", sa.String(64), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.Column("content_checksums", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "committed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("migration_key", "batch_no", name="uq_migration_batch"),
    )


def downgrade():
    raise RuntimeError(
        "Forward-only scope expansion: restore a verified pre-write backup or roll forward; never discard permissions or audit history."
    )
