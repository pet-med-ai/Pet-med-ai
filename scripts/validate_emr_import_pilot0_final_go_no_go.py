#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_FINAL_GO_NO_GO_V1.md"
CHECKLIST = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_FINAL_GO_NO_GO_CHECKLIST.csv"
EVIDENCE = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_FINAL_EVIDENCE_PACKET.csv"
SIGNOFF = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_FINAL_APPROVER_SIGNOFF_TEMPLATE.csv"
DECISION = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_FINAL_DECISION_RECORD_TEMPLATE.csv"
HANDOFF = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_CONTROLLED_EXECUTION_WINDOW_HANDOFF_TEMPLATE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "EMR_PILOT0_FINAL_GO_NO_GO_RELEASE_RECORD_ADDENDUM.md"
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
                "EMR real import pilot_0 final Go / No-Go V1",
                "Default decision",
                "NO-GO",
                "Render / GitHub Security Hardening V1",
                "ENABLE_EMR_REAL_IMPORT=false",
                "ENABLE_EMR_REAL_IMPORT=true",
                "batch.receipt_count == 1",
                "would_update_count > 0",
                "GO: all evidence complete",
            ),
            "final go no-go runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "GitHub Actions latest run",
                "Security hardening completed",
                "Render DB backup verified",
                "feature flag close procedure",
                "final Go No-Go decision",
            ),
            "final go no-go checklist",
        ),
        (
            EVIDENCE,
            (
                "field,value,required",
                "security_hardening_complete",
                "rollback_snapshot_id",
                "batch_receipt_count",
                "would_update_count",
                "final_decision",
            ),
            "final evidence packet",
        ),
        (
            SIGNOFF,
            (
                "signoff_id,final_review_id,batch_id",
                "clinical_decision",
                "security_decision",
                "rollback_decision",
                "release_decision",
            ),
            "approver signoff",
        ),
        (
            DECISION,
            (
                "decision_id,final_review_id,batch_id",
                "hard_no_go_present",
                "next_stage_allowed",
                "NO-GO",
            ),
            "decision record",
        ),
        (
            HANDOFF,
            (
                "handoff_id,decision_id,batch_id",
                "ENABLE_EMR_REAL_IMPORT=false",
                "ENABLE_EMR_REAL_IMPORT=true",
                "max_cases_to_create",
                "updates_allowed",
            ),
            "execution window handoff",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "EMR pilot_0 final Go / No-Go",
                "Feature flag before",
                "Max cases to create: 1",
            ),
            "release record addendum",
        ),
        (
            SMOKE,
            (
                "validate_emr_import_pilot0_final_go_no_go.py",
                "emr real import pilot0 final go no-go validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_emr_import_pilot0_final_go_no_go.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK EMR real import pilot_0 final Go/No-Go: decision package and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
