"""Treatment drafts, immutable revisions, account attestations and command receipts.

Explicit PostgreSQL-only expansion. Does not provision clinicians, import legacy
text, install runtime grants, enable a service, or activate historical 0010.
"""

from pathlib import Path
from alembic import op

revision = "mc02_treatment_store"
down_revision = "mc01_scope_expand"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("mc02 requires an explicitly selected PostgreSQL target")
    op.get_bind().exec_driver_sql(
        (Path(__file__).parents[2] / "treatment_store/schema.sql")
        .read_text()
        .replace("%", "%%")
    )


def downgrade():
    raise RuntimeError(
        "Signed history is forward-only; restore a verified backup instead"
    )
