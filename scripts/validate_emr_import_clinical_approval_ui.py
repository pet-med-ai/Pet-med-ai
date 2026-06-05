#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "src" / "pages" / "EmrImportBatchPlanningPage.jsx"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
DOC = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_CLINICAL_APPROVAL_UI_V1.md"


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
    rc = require_text(
        PAGE,
        (
            "EMR Real Import Clinical Approval",
            "/api/emr/import-batches/${encodeURIComponent(batchId)}/clinical-approval",
            "handleClinicalApproval",
            "approvalAction",
            "clinical_signed",
            "needs_fix",
            "approval_rejected",
            "audit_log_id",
            "status_after",
            "writes_emr_import_batches=true",
            "writes_audit_log=true",
            "writes_case_database=false",
            "creates_case=false",
            "updates_case=false",
            "downloads_attachments=false",
            "executes_real_import=false",
            "can_execute_import=false",
        ),
        "frontend/src/pages/EmrImportBatchPlanningPage.jsx",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_emr_import_clinical_approval_ui.py",
            "emr real import clinical approval UI validation",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "EMR real import clinical approval UI V1",
            "writes_emr_import_batches=true",
            "writes_audit_log=true",
            "writes_case_database=false",
            "executes_real_import=false",
        ),
        "docs/integrations/EMR_REAL_IMPORT_CLINICAL_APPROVAL_UI_V1.md",
    )
    if rc:
        return rc

    print("OK EMR real import clinical approval UI: approval panel and safety markers are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
