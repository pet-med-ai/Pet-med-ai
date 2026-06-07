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


def section_between(text: str, start_marker: str, end_markers: tuple[str, ...], label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"missing section start for {label}: {start_marker}")

    candidates = []
    for marker in end_markers:
        idx = text.find(marker, start + len(start_marker))
        if idx >= 0:
            candidates.append(idx)

    end = min(candidates) if candidates else len(text)
    return text[start:end]


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
            # The review action can live in the same router file, but it must
            # not be treated as part of the read-only review API section.
            '@router.post("/inbox/{receipt_id}/review-action"',
            "webhook_inbox_review_action",
        ),
        "backend/webhook_inbox_api.py",
    )
    if rc:
        return rc

    text = api_file.read_text(encoding="utf-8")

    try:
        list_section = section_between(
            text,
            '@router.get("/inbox"',
            (
                '\n\n@router.post("/inbox/{receipt_id}/review-action"',
                '\n\n@router.get("/inbox/{receipt_id}"',
            ),
            "webhook inbox list endpoint",
        )
        detail_section = section_between(
            text,
            '@router.get("/inbox/{receipt_id}"',
            (
                "\n\n@router.",
                "\n\nclass ",
                "\n\ndef ",
            ),
            "webhook inbox detail endpoint",
        )
    except ValueError as exc:
        return fail(str(exc))

    read_only_scope = list_section + "\n" + detail_section

    forbidden = (
        "@router.post(",
        "@router.put(",
        "@router.patch(",
        "@router.delete(",
        "db.add(",
        "db.commit(",
        "Case(",
        "ConsultSession(",
        "AuditLog(",
    )
    for needle in forbidden:
        if needle in read_only_scope:
            return fail(f"webhook inbox review API read-only sections must remain read-only: {needle}")

    for needle in (
        '"review_only": True',
        '"writes_database": False',
        '"creates_case": False',
        '"downloads_attachments": False',
    ):
        if needle not in list_section:
            return fail(f"webhook inbox list section missing read-only marker: {needle}")

    for needle in (
        '"review_only": True',
        '"writes_database": False',
        '"creates_case": False',
        '"downloads_attachments": False',
        "include_payload",
        "payload_omitted",
    ):
        if needle not in detail_section and needle not in text:
            return fail(f"webhook inbox detail section missing expected marker: {needle}")

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
