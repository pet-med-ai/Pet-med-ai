#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "src" / "App.jsx"
PAGE = ROOT / "frontend" / "src" / "pages" / "WebhookInboxPage.jsx"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
DOC = ROOT / "docs" / "integrations" / "WEBHOOK_INBOX_DETAIL_UI_V1.md"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require(path: Path, needles: tuple[str, ...], label: str) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    checks = [
        (APP, ("WebhookInboxPage", 'path="/webhooks/emr/inbox"'), "frontend/src/App.jsx"),
        (PAGE, (
            "EMR Webhook Inbox",
            "/api/webhooks/emr/inbox",
            "include_payload",
            "mapped_case_preview",
            "validation_errors",
            "validation_warnings",
            "writes_case_database",
            "不创建病例",
        ), "frontend/src/pages/WebhookInboxPage.jsx"),
        (SMOKE, ("validate_webhook_inbox_ui.py", "webhook inbox detail UI validation"), "scripts/smoke_petmed.sh"),
        (DOC, ("EMR Webhook inbox detail UI V1", "只读", "include_payload", "mapped_case_preview"), "docs/integrations/WEBHOOK_INBOX_DETAIL_UI_V1.md"),
    ]
    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    page_text = PAGE.read_text(encoding="utf-8")
    forbidden = (
        "api.post(\"/api/webhooks/emr/inbox",
        "api.put(",
        "api.patch(",
        "api.delete(\"/api/webhooks/emr/inbox",
        "creates_case: true",
    )
    for needle in forbidden:
        if needle in page_text:
            return fail(f"webhook inbox UI must remain read-only; found forbidden text: {needle}")

    print("OK webhook inbox detail UI: route, page and read-only API binding are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
