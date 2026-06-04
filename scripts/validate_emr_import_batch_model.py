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
MIGRATION_FILE = VERSIONS / "0005_emr_import_batches.py"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        return fail(f"{label} missing expected content: {missing[0]}")
    return 0


def main() -> int:
    for path in (MODEL_FILE, MIGRATION_FILE):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    rc = require_text(
        MODEL_FILE,
        (
            "class EmrImportBatch(Base):",
            '__tablename__ = "emr_import_batches"',
            "class EmrImportBatchReceipt(Base):",
            '__tablename__ = "emr_import_batch_receipts"',
            "batch_id",
            "source_system",
            "clinical_signoff_id",
            "rollback_snapshot_id",
            "frozen_at",
        ),
        "backend/models.py",
    )
    if rc:
        return rc

    rc = require_text(
        MIGRATION_FILE,
        (
            'revision = "0005_emr_import_batches"',
            'down_revision = "0004_webhook_inbox_receipts"',
            'op.create_table(',
            '"emr_import_batches"',
            '"emr_import_batch_receipts"',
            '"batch_id"',
            '"receipt_id"',
            '"rollback_snapshot_id"',
        ),
        "0005 EMR import batch migration",
    )
    if rc:
        return rc

    sys.path.insert(0, str(BACKEND))
    from db import Base  # noqa: WPS433
    import models  # noqa: F401,WPS433

    tables = set(Base.metadata.tables.keys())
    expected = {"emr_import_batches", "emr_import_batch_receipts"}
    missing_tables = sorted(expected - tables)
    if missing_tables:
        return fail(f"SQLAlchemy metadata missing EMR import batch tables: {missing_tables}")

    print("OK EMR real import batch model: ORM metadata and Alembic 0005 migration are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
