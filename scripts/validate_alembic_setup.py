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

    rc = require_text(
        VERSIONS / "0001_baseline_current_schema.py",
        (
            "revision = \"0001_baseline\"",
            "op.create_table(",
            "users",
            "cases",
            "consult_sessions",
        ),
        "baseline migration",
    )
    if rc:
        return rc

    rc = require_text(
        VERSIONS / "0002_kpi_data_models.py",
        (
            "revision = \"0002_kpi_data_models\"",
            "down_revision = \"0001_baseline\"",
            "op.create_table(",
            "imaging_studies",
            "imaging_billing",
            "followups",
            "qa_audit",
        ),
        "KPI data model migration",
    )
    if rc:
        return rc

    rc = require_text(
        VERSIONS / "0003_audit_log.py",
        (
            "revision = \"0003_audit_log\"",
            "down_revision = \"0002_kpi_data_models\"",
            "op.create_table(",
            "audit_log",
            "log_id",
            "request_id",
            "clinician_id",
        ),
        "audit log migration",
    )
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

    print("OK Alembic setup: baseline, KPI, audit log migrations and SQLAlchemy metadata are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
