#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VERSIONS = BACKEND / "migrations" / "versions"

MIGRATIONS = [
    "0001_baseline_current_schema.py",
    "0002_kpi_data_models.py",
    "0003_audit_log.py",
    "0004_webhook_inbox_receipts.py",
    "0005_emr_import_batches.py",
    "0006_emr_import_execution_results.py",
]

REQUIRED_FILES = [
    BACKEND / "alembic.ini",
    BACKEND / "migrations" / "env.py",
    BACKEND / "migrations" / "script.py.mako",
    BACKEND / "migrations" / "README",
] + [VERSIONS / name for name in MIGRATIONS]

EXPECTED_METADATA_TABLES = {
    "users",
    "cases",
    "consult_sessions",
    "imaging_studies",
    "imaging_billing",
    "followups",
    "qa_audit",
    "audit_log",
    "webhook_inbox",
    "emr_import_batches",
    "emr_import_batch_receipts",
    "emr_import_execution_runs",
    "emr_import_execution_item_results",
}


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        return fail("missing Alembic files: " + ", ".join(missing))

    for path in REQUIRED_FILES:
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    ini_text = (BACKEND / "alembic.ini").read_text(encoding="utf-8")
    if "script_location = migrations" not in ini_text:
        return fail("backend/alembic.ini must set script_location = migrations")

    checks = [
        ("0001_baseline_current_schema.py", ('revision = "0001_baseline"', 'op.create_table(', '"users"', '"cases"', '"consult_sessions"')),
        ("0002_kpi_data_models.py", ('revision = "0002_kpi_data_models"', 'down_revision = "0001_baseline"', '"imaging_studies"', '"imaging_billing"', '"followups"', '"qa_audit"')),
        ("0003_audit_log.py", ('revision = "0003_audit_log"', 'down_revision = "0002_kpi_data_models"', '"audit_log"')),
        ("0004_webhook_inbox_receipts.py", ('revision = "0004_webhook_inbox_receipts"', 'down_revision = "0003_audit_log"', '"webhook_inbox"')),
        ("0005_emr_import_batches.py", ('revision = "0005_emr_import_batches"', 'down_revision = "0004_webhook_inbox_receipts"', '"emr_import_batches"', '"emr_import_batch_receipts"')),
        ("0006_emr_import_execution_results.py", ('revision = "0006_emr_import_execution_results"', 'down_revision = "0005_emr_import_batches"', '"emr_import_execution_runs"', '"emr_import_execution_item_results"')),
    ]
    for filename, needles in checks:
        rc = require_text(VERSIONS / filename, needles, filename)
        if rc:
            return rc

    sys.path.insert(0, str(BACKEND))
    from db import Base  # noqa: WPS433
    import models  # noqa: F401,WPS433

    tables = set(Base.metadata.tables.keys())
    if tables != EXPECTED_METADATA_TABLES:
        return fail(
            "SQLAlchemy metadata tables mismatch: "
            f"actual={sorted(tables)}, expected={sorted(EXPECTED_METADATA_TABLES)}"
        )

    print("OK Alembic setup: baseline, KPI, audit log, webhook inbox, EMR batch and execution result migrations are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
