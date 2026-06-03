#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


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
    emr = BACKEND / "emr_webhook.py"
    models = BACKEND / "models.py"
    for path in (emr, models):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    rc = require_text(
        models,
        (
            "class WebhookInbox(Base):",
            '__tablename__ = "webhook_inbox"',
            "idempotency_key",
            "payload_hash",
            "validation_errors",
            "mapped_case_preview",
        ),
        "backend/models.py",
    )
    if rc:
        return rc

    rc = require_text(
        emr,
        (
            "WebhookInbox",
            "db: Session = Depends(get_db)",
            "_save_webhook_inbox_record",
            "_duplicate_response",
            "writes_webhook_inbox",
            "receipt_persisted",
            "mapped_case_preview",
            "writes_case_database",
        ),
        "backend/emr_webhook.py",
    )
    if rc:
        return rc

    text = emr.read_text(encoding="utf-8")
    forbidden = ("Case(", "ConsultSession(", "AuditLog(")
    for needle in forbidden:
        if needle in text:
            return fail(f"receipt persistence must not create clinical records or audit rows yet: {needle}")

    print("OK EMR webhook receipt persistence: dry-run receipts persist to webhook_inbox only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
