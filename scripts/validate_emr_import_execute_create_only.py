#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "backend" / "emr_import_batch_api.py"
DOC = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_EXECUTE_CREATE_ONLY_IMPLEMENTATION_V1.md"
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
            '@router.post("/{batch_id}/execute"',
            "execute_emr_real_import_create_only_pilot",
            "assert_feature_enabled",
            'assert_feature_enabled("ENABLE_EMR_REAL_IMPORT")',
            'is_feature_enabled("ENABLE_EMR_IMPORT_CASE_UPDATE")',
            'is_feature_enabled("ENABLE_EMR_ATTACHMENT_DOWNLOAD")',
            'is_feature_enabled("ENABLE_PRESCRIPTION_STRUCTURED_WRITE")',
            "CREATE_ONLY_PILOT_MAX_RECEIPTS",
            "REAL_IMPORT_CONFIRMATION",
            "I_UNDERSTAND_THIS_WILL_CREATE_CASES",
            "create_only_ack",
            "EmrImportExecutionRun",
            "EmrImportExecutionItemResult",
            "Case(owner_id",
            "case_update_blocked",
            "duplicate_blocked",
            "emr_real_import_execute_create_only_pilot",
            "writes_case_database",
            "writes_execution_results",
            "updates_case",
            "downloads_attachments",
            "executes_real_import",
            "create_only",
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
        "db.delete(",
        ".delete(",
        "requests.get(",
        "urllib",
        "download(",
        "Prescription(",
        "Billing(",
        "Invoice(",
        ".chief_complaint =",
        ".history =",
        ".exam_findings =",
    )
    for needle in forbidden:
        if needle in section:
            return fail(f"create-only execute implementation contains forbidden marker: {needle}")

    rc = require_text(
        DOC,
        (
            "EMR real import execute API implementation V1 - create-only pilot",
            "ENABLE_EMR_REAL_IMPORT=true",
            "create-only",
            "updates_case=false",
            "downloads_attachments=false",
            "pilot limit",
        ),
        "create-only implementation doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_emr_import_execute_create_only.py",
            "emr real import execute feature flag blocked",
            "/api/emr/import-batches/${emr_batch_id}/execute",
            "feature flag disabled",
            "ENABLE_EMR_REAL_IMPORT",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK EMR real import execute create-only implementation: feature-flag protected Case creation path is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
