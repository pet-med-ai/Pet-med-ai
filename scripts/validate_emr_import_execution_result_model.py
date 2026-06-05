#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MIGRATION = BACKEND / "migrations" / "versions" / "0006_emr_import_results.py"
MODELS = BACKEND / "models.py"


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
    for path in (MODELS, MIGRATION):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    rc = require_text(
        MODELS,
        (
            "class EmrImportExecutionRun(Base):",
            "__tablename__ = \"emr_import_execution_runs\"",
            "class EmrImportExecutionItemResult(Base):",
            "__tablename__ = \"emr_import_execution_item_results\"",
            "created_case_id",
            "failure_code",
            "rollback_status",
        ),
        "backend/models.py",
    )
    if rc:
        return rc

    rc = require_text(
        MIGRATION,
        (
            'revision = "0006_emr_import_results"',
            'down_revision = "0005_emr_import_batches"',
            'op.create_table(',
            '"emr_import_execution_runs"',
            '"emr_import_execution_item_results"',
            '"created_case_id"',
            '"failure_code"',
            '"rollback_status"',
        ),
        "0006 migration",
    )
    if rc:
        return rc

    sys.path.insert(0, str(BACKEND))
    from db import Base  # noqa: WPS433
    import models  # noqa: F401,WPS433

    tables = set(Base.metadata.tables.keys())
    expected = {"emr_import_execution_runs", "emr_import_execution_item_results"}
    missing = sorted(expected - tables)
    if missing:
        return fail(f"SQLAlchemy metadata missing tables: {missing}")

    print("OK EMR import execution result model: ORM metadata and Alembic 0006 migration are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
