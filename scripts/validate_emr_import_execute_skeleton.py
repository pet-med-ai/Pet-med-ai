#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "backend" / "emr_import_batch_api.py"
DOC = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_EXECUTE_API_DRY_RUN_PROTECTED_SKELETON_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    for path in (API, Path(__file__)):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    rc = require_text(
        API,
        (
            "class EmrImportExecuteIn",
            '@router.post("/{batch_id}/execute"',
            "emr_real_import_execute_blocked",
            "execute_api_skeleton",
            "dry_run_ack",
            "I_UNDERSTAND_THIS_ENDPOINT_IS_DISABLED",
            "blocked_by_design",
            "execution_enabled",
            "writes_database",
            "writes_case_database",
            "writes_audit_log",
            "creates_case",
            "updates_case",
            "downloads_attachments",
            "executes_real_import",
            "can_execute_import",
            "execution_block_reason",
        ),
        "backend/emr_import_batch_api.py",
    )
    if rc:
        return rc

    text = API.read_text(encoding="utf-8")
    start = text.index('@router.post("/{batch_id}/execute"')
    end = text.index('@router.post("/{batch_id}/execution-dry-run"', start)
    section = text[start:end]

    forbidden = (
        "db.add(",
        "db.commit(",
        "Case(",
        "AuditLog(",
        "EmrImportExecutionRun(",
        "EmrImportExecutionItemResult(",
        "status_after",
    )
    for needle in forbidden:
        if needle in section:
            return fail(f"execute skeleton must not mutate database or write records: {needle}")

    rc = require_text(
        DOC,
        (
            "EMR real import execute API dry-run-protected skeleton V1",
            "POST /api/emr/import-batches/{batch_id}/execute",
            "HTTP 409",
            "blocked_by_design=true",
            "writes_case_database=false",
            "creates_case=false",
            "executes_real_import=false",
            "can_execute_import=false",
        ),
        "execution skeleton doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_emr_import_execute_skeleton.py",
            "emr real import execute skeleton blocked",
            "/api/emr/import-batches/${emr_batch_id}/execute",
            "emr_real_import_execute_blocked",
            "blocked_by_design",
            "execution_enabled",
            "executes_real_import",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK EMR real import execute API dry-run-protected skeleton: disabled execute endpoint and safety checks are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
