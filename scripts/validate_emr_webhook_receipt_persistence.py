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
            "signature_hash",
            "validation_errors",
            "validation_warnings",
            "mapped_case_preview",
            "payload",
            "dry_run",
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
            "_persist_receipt",
            "_existing_receipt_response",
            "_handle_emr_dry_run",
            "IntegrityError",
            "writes_webhook_inbox",
            "receipt_persisted",
            "mapped_case_preview",
            "writes_case_database",
            "downloads_attachments",
            '@router.post("/emr/dry-run"',
            '@router.post("/emr/case-mapping/dry-run"',
        ),
        "backend/emr_webhook.py",
    )
    if rc:
        return rc

    text = emr.read_text(encoding="utf-8")

    # The persistence function was originally named _save_webhook_inbox_record.
    # Current code uses _persist_receipt. Validate behavior, not a stale helper name.
    try:
        persist_section = section_between(
            text,
            "def _persist_receipt(",
            (
                "\n\nasync def _handle_emr_dry_run(",
                "\n\ndef _existing_receipt_response(",
                "\n\n@router.",
            ),
            "_persist_receipt",
        )
        handler_section = section_between(
            text,
            "async def _handle_emr_dry_run(",
            (
                '\n\n@router.post("/emr/dry-run"',
            ),
            "_handle_emr_dry_run",
        )
        dry_run_route_section = section_between(
            text,
            '@router.post("/emr/dry-run"',
            (
                '\n\n@router.post("/emr/case-mapping/dry-run"',
            ),
            "emr dry-run route",
        )
        mapping_route_section = section_between(
            text,
            '@router.post("/emr/case-mapping/dry-run"',
            (
                "\n\n@router.",
                "\n\nclass ",
                "\n\ndef ",
            ),
            "emr case mapping dry-run route",
        )
    except ValueError as exc:
        return fail(str(exc))

    receipt_scope = persist_section + "\n" + handler_section + "\n" + dry_run_route_section + "\n" + mapping_route_section

    for needle in (
        "WebhookInbox(",
        "db.add(obj)",
        "db.commit()",
        "db.rollback()",
        "db.refresh(obj)",
        "validation_errors=errors",
        "validation_warnings=warnings",
        "mapped_case_preview=case_preview",
        "payload=_safe_payload_for_storage(payload)",
        "dry_run=True",
    ):
        if needle not in persist_section:
            return fail(f"_persist_receipt missing persistence marker: {needle}")

    for needle in (
        "_persist_receipt(",
        "_existing_receipt_response(",
        "receipt_persisted=True",
        '"writes_webhook_inbox": True',
        '"writes_case_database": False',
        '"creates_case": False',
        '"updates_case": False',
        '"downloads_attachments": False',
    ):
        if needle not in receipt_scope and needle not in text:
            return fail(f"receipt persistence flow missing safety marker: {needle}")

    # Receipt persistence may write only webhook_inbox. It must not create clinical records or audit rows.
    forbidden = (
        "Case(",
        "ConsultSession(",
        "AuditLog(",
        "EmrImportBatch(",
        "EmrImportExecutionRun(",
        "EmrImportExecutionItemResult(",
        "requests.get(",
        "urllib",
        "download(",
    )
    for needle in forbidden:
        if needle in receipt_scope:
            return fail(f"receipt persistence must not create clinical records, audit rows, batches, or download attachments: {needle}")

    print("OK EMR webhook receipt persistence: dry-run receipts persist to webhook_inbox only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
