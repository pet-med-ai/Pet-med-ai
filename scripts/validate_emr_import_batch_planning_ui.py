#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
PAGE = FRONTEND / "src" / "pages" / "EmrImportBatchPlanningPage.jsx"
APP = FRONTEND / "src" / "App.jsx"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"


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
    for path in (PAGE, APP, SMOKE):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")

    rc = require_text(
        PAGE,
        (
            "EMR Real Import Batch Planning",
            "/api/webhooks/emr/inbox",
            "/api/emr/import-batches",
            "/api/emr/import-batches/plan",
            "ready_for_import",
            "selectedReceiptIds",
            "clinical_signoff_id",
            "rollback_snapshot_id",
            "writes_emr_import_batches=true",
            "writes_emr_import_batch_receipts=true",
            "writes_audit_log=true",
            "writes_case_database=false",
            "creates_case=false",
            "updates_case=false",
            "downloads_attachments=false",
            "executes_real_import=false",
            "can_execute_import=false",
            "emr_import_batch_planning_ui_v1",
        ),
        "frontend/src/pages/EmrImportBatchPlanningPage.jsx",
    )
    if rc:
        return rc

    rc = require_text(
        APP,
        (
            'import EmrImportBatchPlanningPage from "./pages/EmrImportBatchPlanningPage";',
            '<Route path="/emr/import-batches" element={<EmrImportBatchPlanningPage />} />',
        ),
        "frontend/src/App.jsx",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_emr_import_batch_planning_ui.py",
            "emr import batch planning UI validation",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK EMR real import batch planning UI: route, page and planning API binding are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
