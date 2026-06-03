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
    api_file = BACKEND / "webhook_inbox_api.py"
    main_py = BACKEND / "main.py"

    for path in (api_file, main_py):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    rc = require_text(
        api_file,
        (
            'router = APIRouter(prefix="/api/webhooks/emr"',
            '@router.get("/inbox"',
            '@router.get("/inbox/{receipt_id}"',
            "WebhookInbox",
            "include_payload",
            "payload_omitted",
            "review_only",
            "writes_database",
            "creates_case",
            "downloads_attachments",
            "get_current_user",
        ),
        "backend/webhook_inbox_api.py",
    )
    if rc:
        return rc

    text = api_file.read_text(encoding="utf-8")
    forbidden = (
        "@router.post(",
        "@router.put(",
        "@router.patch(",
        "@router.delete(",
        "db.add(",
        "db.commit(",
        "Case(",
        "ConsultSession(",
    )
    for needle in forbidden:
        if needle in text:
            return fail(f"webhook inbox review API must remain read-only: {needle}")

    rc = require_text(
        main_py,
        (
            "webhook_inbox_api_router",
            "app.include_router(webhook_inbox_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    print("OK webhook inbox review API: authenticated read-only receipt review endpoints are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
