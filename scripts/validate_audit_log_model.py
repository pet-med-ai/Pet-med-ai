#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VERSIONS = BACKEND / "migrations" / "versions"
MODEL_FILE = BACKEND / "models.py"
MIGRATION_FILE = VERSIONS / "0003_audit_log.py"

EXPECTED_COLUMNS = {
    "id",
    "log_id",
    "request_id",
    "patient_token",
    "clinician_id",
    "model_version",
    "confidence",
    "suggested_action",
    "action_taken",
    "override_reason",
    "note",
    "case_id",
    "session_uid",
    "event_type",
    "source",
    "metadata",
    "created_at",
}


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_file(path: Path) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    return 0


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    for path in (MODEL_FILE, MIGRATION_FILE):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        MODEL_FILE,
        (
            "class AuditLog(Base):",
            "__tablename__ = \"audit_log\"",
            "log_id",
            "request_id",
            "clinician_id",
            "confidence",
            "suggested_action",
            "action_taken",
            "override_reason",
        ),
        "AuditLog ORM model",
    )
    if rc:
        return rc

    rc = require_text(
        MIGRATION_FILE,
        (
            "revision = \"0003_audit_log\"",
            "down_revision = \"0002_kpi_data_models\"",
            "op.create_table(",
            "audit_log",
            "log_id",
            "request_id",
            "clinician_id",
            "confidence",
            "suggested_action",
            "action_taken",
            "override_reason",
        ),
        "audit log migration",
    )
    if rc:
        return rc

    sys.path.insert(0, str(BACKEND))
    from db import Base  # noqa: WPS433
    import models  # noqa: F401,WPS433

    tables = set(Base.metadata.tables.keys())
    if "audit_log" not in tables:
        return fail(f"SQLAlchemy metadata missing audit_log table: actual={sorted(tables)}")

    columns = set(Base.metadata.tables["audit_log"].columns.keys())
    missing = sorted(EXPECTED_COLUMNS - columns)
    if missing:
        return fail(f"audit_log table missing columns: {missing}; actual={sorted(columns)}")

    print("OK audit log model: ORM metadata and Alembic 0003 migration are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
