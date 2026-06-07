#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "checklist": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_EXECUTION_CHECKLIST_V1.md",
    "operator_runbook": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_OPERATOR_RUNBOOK.csv",
    "post_check": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_POST_CHECK_TEMPLATE.csv",
    "rollback_decision": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_ROLLBACK_DECISION_TEMPLATE.csv",
    "feature_flag_window": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_FEATURE_FLAG_WINDOW_TEMPLATE.csv",
    "api_curl": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_API_CURL_TEMPLATE.md",
}
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require(path: Path, needles: tuple[str, ...], label: str) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    checks = [
        (
            FILES["checklist"],
            (
                "EMR real import pilot_0 execution checklist V1",
                "pilot_0",
                "exactly 1 ready_for_import receipt",
                "ENABLE_EMR_REAL_IMPORT=false by default",
                "ENABLE_EMR_REAL_IMPORT=true",
                "quality_gate.passed=true",
                "would_create_count=1",
                "summary.created_count=1",
                "feature flag returned to disabled",
            ),
            "pilot0 checklist",
        ),
        (
            FILES["operator_runbook"],
            (
                "step_number,phase,owner,action",
                "Enable real import flag",
                "Execute pilot_0",
                "Disable real import flag",
                "Clinical spot-check created case",
            ),
            "pilot0 operator runbook",
        ),
        (
            FILES["post_check"],
            (
                "batch_id,execution_id,receipt_id,created_case_id",
                "no_update_performed",
                "no_attachment_downloaded",
                "feature_flag_disabled_after",
            ),
            "pilot0 post-check template",
        ),
        (
            FILES["rollback_decision"],
            (
                "decision_id,batch_id,execution_id",
                "rollback_snapshot_id",
                "rollback_required",
                "clinical_spot_check_result",
            ),
            "pilot0 rollback decision template",
        ),
        (
            FILES["feature_flag_window"],
            (
                "window_id,batch_id,execution_id",
                "ENABLE_EMR_REAL_IMPORT_before",
                "ENABLE_EMR_REAL_IMPORT_during",
                "ENABLE_EMR_REAL_IMPORT_after",
            ),
            "pilot0 feature flag window template",
        ),
        (
            FILES["api_curl"],
            (
                "EMR real import pilot_0 API cURL template",
                "I_UNDERSTAND_THIS_WILL_CREATE_CASES",
                "create_only_ack",
                "max_items",
                "summary.created_count=1",
            ),
            "pilot0 API curl template",
        ),
        (
            SMOKE,
            (
                "validate_emr_import_pilot0_checklist.py",
                "emr real import pilot0 checklist validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_emr_import_pilot0_checklist.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK EMR real import pilot_0 checklist: runbook, templates and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
