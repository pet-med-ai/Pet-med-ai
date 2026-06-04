#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend" / "src" / "pages" / "WebhookInboxPage.jsx"


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
    api = BACKEND / "webhook_inbox_api.py"
    main_py = BACKEND / "main.py"
    for path in (api, main_py):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    if not FRONTEND.exists():
        return fail("missing frontend/src/pages/WebhookInboxPage.jsx")

    rc = require_text(
        api,
        (
            '@router.post("/inbox/{receipt_id}/review-action"',
            "WebhookInboxReviewActionIn",
            "ready_for_import",
            "needs_fix",
            "rejected_by_reviewer",
            "AuditLog(",
            "webhook_inbox_review",
            "writes_webhook_inbox",
            "writes_audit_log",
            "writes_case_database",
            "creates_case",
            "downloads_attachments",
        ),
        "backend/webhook_inbox_api.py",
    )
    if rc:
        return rc

    api_text = api.read_text(encoding="utf-8")
    forbidden = ('Case(', '@router.put(', '@router.patch(', '@router.delete(')
    for needle in forbidden:
        if needle in api_text:
            return fail(f"review action API must not create cases or expose mutating non-review routes: {needle}")

    rc = require_text(
        FRONTEND,
        (
            "人工复核动作",
            "/review-action",
            "ready_for_import",
            "needs_fix",
            "rejected",
            "audit_log_id",
            "writes_webhook_inbox=true",
            "writes_audit_log=true",
            "writes_case_database=false",
            "creates_case=false",
        ),
        "frontend/src/pages/WebhookInboxPage.jsx",
    )
    if rc:
        return rc

    print("OK webhook inbox review action: backend API and frontend action panel are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
