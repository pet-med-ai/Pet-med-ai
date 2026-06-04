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
    forbidden = (
        "Case(",
        "ConsultSession(",
        "save-case",
        "download_attachments",
    )
    for needle in forbidden:
        if needle in api_text:
            return fail(f"planning API must not create cases or download attachments: {needle}")

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
