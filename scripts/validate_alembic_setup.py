#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VERSIONS = BACKEND / "migrations" / "versions"

REQUIRED_FILES = [
    BACKEND / "alembic.ini",
    BACKEND / "migrations" / "env.py",
    BACKEND / "migrations" / "script.py.mako",
    BACKEND / "migrations" / "README",
    VERSIONS / "0001_baseline_current_schema.py",
    VERSIONS / "0002_kpi_data_models.py",
    VERSIONS / "0003_audit_log.py",
    VERSIONS / "0004_webhook_inbox_receipts.py",
]

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
        (
            VERSIONS / "0001_baseline_current_schema.py",
            (
                'revision = "0001_baseline"',
                'op.create_table(\n        "users"',
                'op.create_table(\n        "cases"',
                'op.create_table(\n        "consult_sessions"',
            ),
            "baseline migration",
        ),
        (
            VERSIONS / "0002_kpi_data_models.py",
            (
                'revision = "0002_kpi_data_models"',
                'down_revision = "0001_baseline"',
                'op.create_table(\n        "imaging_studies"',
                'op.create_table(\n        "imaging_billing"',
                'op.create_table(\n        "followups"',
                'op.create_table(\n        "qa_audit"',
            ),
            "KPI data model migration",
        ),
        (
            VERSIONS / "0003_audit_log.py",
            (
                'revision = "0003_audit_log"',
                'down_revision = "0002_kpi_data_models"',
                'op.create_table(\n        "audit_log"',
            ),
            "audit log migration",
        ),
        (
            VERSIONS / "0004_webhook_inbox_receipts.py",
            (
                'revision = "0004_webhook_inbox_receipts"',
                'down_revision = "0003_audit_log"',
                'op.create_table(\n        "webhook_inbox"',
            ),
            "webhook inbox migration",
        ),
    ]

    for path, needles, label in checks:
        rc = require_text(path, needles, label)
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

    print("OK Alembic setup: baseline, KPI, audit log, webhook inbox migrations and SQLAlchemy metadata are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
