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
    main_py = BACKEND / "main.py"

    for path in (emr, main_py):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    rc = require_text(
        emr,
        (
            'router = APIRouter(prefix="/api/webhooks"',
            '@router.post("/emr/dry-run"',
            "X-PMAI-Timestamp",
            "X-PMAI-Signature",
            "Idempotency-Key",
            "HMAC-SHA256",
            "writes_database",
            "writes_webhook_inbox",
            "writes_case_database",
            "creates_case",
            "downloads_attachments",
            "mapped_case_preview",
            "DEFAULT_DRY_RUN_SECRET",
            "WebhookInbox",
        ),
        "backend/emr_webhook.py",
    )
    if rc:
        return rc

    emr_text = emr.read_text(encoding="utf-8")
    forbidden = (
        "Case(",
        "ConsultSession(",
        "AuditLog(",
        '@router.post("/emr"',
    )
    for needle in forbidden:
        if needle in emr_text:
            return fail(f"dry-run receiver must not perform real ingestion or expose real endpoint: {needle}")

    rc = require_text(
        main_py,
        (
            "emr_webhook_router",
            "app.include_router(emr_webhook_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    print("OK EMR webhook dry-run receiver: signed dry-run endpoint and main.py include are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
