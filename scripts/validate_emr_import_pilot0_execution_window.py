#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_CONTROLLED_EXECUTION_WINDOW_V1.md"
CHECKLIST = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_CONTROLLED_EXECUTION_WINDOW_CHECKLIST.csv"
RESULT = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_EXECUTION_RESULT_RECORD_TEMPLATE.csv"
CLOSEOUT = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_FEATURE_FLAG_CLOSEOUT_TEMPLATE.csv"
POST = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_POST_EXECUTION_CHECKLIST.csv"
ADDENDUM = ROOT / "docs" / "ops" / "EMR_PILOT0_CONTROLLED_EXECUTION_WINDOW_RELEASE_RECORD_ADDENDUM.md"
SCRIPT = ROOT / "scripts" / "emr_pilot0_execute_guarded.sh"
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
            RUNBOOK,
            (
                "EMR real import pilot_0 controlled execution window V1",
                "exactly one ready_for_import receipt",
                "ENABLE_EMR_REAL_IMPORT=true",
                "ENABLE_EMR_REAL_IMPORT=false",
                "scripts/emr_pilot0_execute_guarded.sh",
                "Hard stop after execution",
            ),
            "controlled execution window runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "Enable real import flag",
                "Run guarded execution",
                "Disable real import flag",
                "Online smoke after window",
            ),
            "window checklist",
        ),
        (
            RESULT,
            (
                "execution_record_id,window_id,batch_id",
                "created_case_id",
                "created_count",
                "updated_count",
                "downloads_attachments",
            ),
            "execution result template",
        ),
        (
            CLOSEOUT,
            (
                "closeout_id,window_id,batch_id",
                "feature_flags_after",
                "online_smoke_after",
                "closeout_decision",
            ),
            "feature flag closeout template",
        ),
        (
            POST,
            (
                "check_id,category,item",
                "created_count",
                "updated_count",
                "real import disabled after window",
            ),
            "post execution checklist",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "EMR pilot_0 controlled execution window",
                "At most one Case was created",
                "ENABLE_EMR_REAL_IMPORT was disabled after execution",
            ),
            "release addendum",
        ),
        (
            SCRIPT,
            (
                "I_UNDERSTAND_THIS_WILL_CREATE_EXACTLY_ONE_CASE",
                "I_UNDERSTAND_THIS_WILL_CREATE_CASES",
                "ENABLE_EMR_REAL_IMPORT",
                "summary.receipt_count must be 1",
                "summary.created_count must be 1",
                "summary.updated_count must be 0",
                "Do not run a second execution",
            ),
            "guarded execute script",
        ),
        (
            SMOKE,
            (
                "validate_emr_import_pilot0_execution_window.py",
                "emr real import pilot0 execution window validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_emr_import_pilot0_execution_window.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK EMR real import pilot_0 controlled execution window: guarded script, runbook and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
