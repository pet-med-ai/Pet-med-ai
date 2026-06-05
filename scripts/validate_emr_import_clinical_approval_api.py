#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "backend" / "emr_import_batch_api.py"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
DOC = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_CLINICAL_APPROVAL_API_V1.md"


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
    for path in (API, SMOKE, DOC):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
    py_compile.compile(str(API), doraise=True)

    rc = require_text(
        API,
        (
            "EmrImportClinicalApprovalIn",
            '@router.post("/{batch_id}/clinical-approval"',
            "emr_import_clinical_approval",
            "clinical_approval_api",
            "build_execution_dry_run_report",
            "quality_gate",
            "writes_emr_import_batches",
            "writes_audit_log",
            "writes_case_database",
            "creates_case",
            "updates_case",
            "downloads_attachments",
            "executes_real_import",
            "can_execute_import",
            "audit_log_id",
        ),
        "backend/emr_import_batch_api.py",
    )
    if rc:
        return rc

    text = API.read_text(encoding="utf-8")
    clinical_section = text.split('@router.post("/{batch_id}/clinical-approval"', 1)[-1].split('@router.post("/{batch_id}/execution-dry-run"', 1)[0]
    forbidden = ("Case(", "db.delete(", 'downloads_attachments": True', 'creates_case": True', 'updates_case": True')
    for needle in forbidden:
        if needle in clinical_section:
            return fail(f"clinical approval API must not perform real import or Case writes: {needle}")

    rc = require_text(
        SMOKE,
        (
            "emr real import clinical approval",
            "/clinical-approval",
            "emr_import_clinical_approval",
            "writes_emr_import_batches",
            "writes_audit_log",
            "writes_case_database",
            "can_execute_import",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK EMR real import clinical approval API: approval gate and safety checks are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
