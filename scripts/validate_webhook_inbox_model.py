#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MIGRATION = BACKEND / "migrations" / "versions" / "0004_webhook_inbox_receipts.py"


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
    required_files = [
        BACKEND / "models.py",
        MIGRATION,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.exists()]
    if missing:
        return fail("missing webhook inbox model files: " + ", ".join(missing))

    py_compile.compile(str(BACKEND / "models.py"), doraise=True)
    py_compile.compile(str(MIGRATION), doraise=True)

    rc = require_text(
        BACKEND / "models.py",
        (
            "class WebhookInbox(Base):",
            '__tablename__ = "webhook_inbox"',
            "receipt_id",
            "idempotency_key",
            "payload_hash",
            "mapped_case_preview",
            "validation_errors",
            "ux_webhook_inbox_idempotency_key",
        ),
        "WebhookInbox ORM model",
    )
    if rc:
        return rc

    rc = require_text(
        MIGRATION,
        (
            'revision = "0004_webhook_inbox_receipts"',
            'down_revision = "0003_audit_log"',
            'op.create_table(\n        "webhook_inbox"',
            'op.create_index("ux_webhook_inbox_idempotency_key"',
        ),
        "webhook inbox Alembic migration",
    )
    if rc:
        return rc

    sys.path.insert(0, str(BACKEND))
    from db import Base  # noqa: WPS433
    import models  # noqa: F401,WPS433

    table = Base.metadata.tables.get("webhook_inbox")
    if table is None:
        return fail("SQLAlchemy metadata missing table: webhook_inbox")

    columns = set(table.columns.keys())
    expected_columns = {
        "receipt_id",
        "source",
        "event_type",
        "idempotency_key",
        "payload_hash",
        "signature_hash",
        "external_case_id",
        "external_encounter_id",
        "case_id",
        "status",
        "dry_run",
        "validation_errors",
        "validation_warnings",
        "mapped_case_preview",
        "payload",
        "error_code",
        "error_message",
        "received_at",
        "processed_at",
        "created_at",
        "updated_at",
    }
    missing_columns = sorted(expected_columns - columns)
    if missing_columns:
        return fail("webhook_inbox missing columns: " + ", ".join(missing_columns))

    print("OK webhook inbox model: ORM metadata and Alembic 0004 migration are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
