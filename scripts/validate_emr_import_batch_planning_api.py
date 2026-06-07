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
    api = BACKEND / "emr_import_batch_api.py"
    main_py = BACKEND / "main.py"

    for path in (api, main_py):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    rc = require_text(
        api,
        (
            'router = APIRouter(prefix="/api/emr/import-batches"',
            '@router.post("/plan"',
            '@router.get(""',
            '@router.get("/{batch_id}"',
            "EmrImportBatch",
            "EmrImportBatchReceipt",
            "WebhookInbox",
            "AuditLog",
            "ready_for_import",
            "writes_emr_import_batches",
            "writes_emr_import_batch_receipts",
            "writes_audit_log",
            "writes_case_database",
            "creates_case",
            "updates_case",
            "downloads_attachments",
            "executes_real_import",
            "can_execute_import",
        ),
        "backend/emr_import_batch_api.py",
    )
    if rc:
        return rc

    api_text = api.read_text(encoding="utf-8")

    try:
        plan_section = section_between(
            api_text,
            '@router.post("/plan"',
            (
                '\n\n@router.post("/{batch_id}/clinical-approval"',
                '\n\nCREATE_ONLY_PILOT_MAX_RECEIPTS',
                '\n\n@router.post("/{batch_id}/execute"',
                '\n\n@router.post("/{batch_id}/execution-dry-run"',
                '\n\n@router.get("", response_model=dict)',
            ),
            "plan endpoint",
        )
        list_section = section_between(
            api_text,
            '@router.get("", response_model=dict)',
            (
                '\n\n@router.get("/{batch_id}"',
            ),
            "list batches endpoint",
        )
        detail_section = section_between(
            api_text,
            '@router.get("/{batch_id}"',
            (
                "\n\n#",
                "\n\nclass ",
                "\n\ndef ",
                '\n\n@router.post(',
            ),
            "batch detail endpoint",
        )
    except ValueError as exc:
        return fail(str(exc))

    planning_scope = plan_section + "\n" + list_section + "\n" + detail_section

    # These are forbidden in planning endpoints only. They are valid in the
    # feature-flag protected /execute create-only endpoint.
    forbidden = (
        "Case(",
        "ConsultSession(",
        "save-case",
        "download_attachments",
        "EmrImportExecutionRun(",
        "EmrImportExecutionItemResult(",
    )
    for needle in forbidden:
        if needle in planning_scope:
            return fail(f"planning API must not create cases or download attachments inside planning scope: {needle}")

    # Planning may write planning batch tables and audit, but must not claim Case writes.
    for needle in (
        '"writes_emr_import_batches": True',
        '"writes_emr_import_batch_receipts": True',
        '"writes_audit_log": True',
        '"writes_case_database": False',
        '"creates_case": False',
        '"updates_case": False',
        '"downloads_attachments": False',
        '"executes_real_import": False',
        '"can_execute_import": False',
    ):
        if needle not in plan_section:
            return fail(f"planning endpoint missing safety marker: {needle}")

    for needle in (
        '"writes_database": False',
        '"creates_case": False',
    ):
        if needle not in list_section:
            return fail(f"planning list endpoint missing read-only marker: {needle}")

    for needle in (
        '"writes_case_database": False',
        '"creates_case": False',
        '"updates_case": False',
        '"downloads_attachments": False',
        '"executes_real_import": False',
    ):
        if needle not in detail_section:
            return fail(f"planning detail endpoint missing safety marker: {needle}")

    rc = require_text(
        main_py,
        (
            "emr_import_batch_api_router",
            "app.include_router(emr_import_batch_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    print("OK EMR real import batch planning API: batch planning endpoints and safety gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
