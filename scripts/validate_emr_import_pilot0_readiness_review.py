#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_CONTROLLED_EXECUTION_READINESS_REVIEW_V1.md"
CHECKLIST = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_CONTROLLED_EXECUTION_READINESS_CHECKLIST.csv"
FLAG_APPROVAL = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_FEATURE_FLAG_WINDOW_APPROVAL_TEMPLATE.csv"
OPERATOR_SIGNOFF = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_OPERATOR_SIGNOFF_TEMPLATE.csv"
GO_NO_GO = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_CONTROLLED_EXECUTION_GO_NO_GO_TEMPLATE.csv"
EVIDENCE = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_CONTROLLED_EXECUTION_EVIDENCE_PACKET.csv"
ADDENDUM = ROOT / "docs" / "ops" / "EMR_PILOT0_CONTROLLED_EXECUTION_READINESS_RELEASE_RECORD_ADDENDUM.md"
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
                "EMR real import pilot_0 controlled execution readiness review V1",
                "NO-GO",
                "ENABLE_EMR_REAL_IMPORT=false",
                "ENABLE_EMR_REAL_IMPORT=true",
                "exactly one create-only EMR import pilot",
                "batch.receipt_count == 1",
                "would_update_count=0",
                "blocked_count=0",
                "Hard No-Go",
            ),
            "readiness review runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "GitHub Actions CI Gate",
                "Database revision alignment",
                "Feature flags before window",
                "would update count",
                "final decision",
            ),
            "readiness checklist",
        ),
        (
            FLAG_APPROVAL,
            (
                "approval_id,batch_id,receipt_id",
                "ENABLE_EMR_REAL_IMPORT_before",
                "ENABLE_EMR_REAL_IMPORT_during",
                "ENABLE_EMR_REAL_IMPORT_after",
                "other_dangerous_flags_remain_false",
            ),
            "feature flag window approval",
        ),
        (
            OPERATOR_SIGNOFF,
            (
                "signoff_id,batch_id,receipt_id",
                "operator_understands_creates_one_case",
                "operator_understands_no_updates",
                "operator_understands_disable_flag_after",
            ),
            "operator signoff",
        ),
        (
            GO_NO_GO,
            (
                "decision_id,batch_id,receipt_id",
                "ci_green",
                "backup_verified",
                "dry_run_passed",
                "feature_flags_safe",
                "rollback_owner_ready",
            ),
            "go no-go decision",
        ),
        (
            EVIDENCE,
            (
                "field,value,required",
                "github_actions_run_url",
                "database_revision",
                "rollback_snapshot_id",
                "would_create_count",
                "blocked_count",
                "final_decision",
            ),
            "evidence packet",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "pilot_0 controlled execution readiness review",
                "Only ENABLE_EMR_REAL_IMPORT may be temporarily enabled",
                "Case updates remain disabled",
            ),
            "release addendum",
        ),
        (
            SMOKE,
            (
                "validate_emr_import_pilot0_readiness_review.py",
                "emr real import pilot0 readiness review validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_emr_import_pilot0_readiness_review.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK EMR real import pilot_0 controlled execution readiness review: runbook, templates and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
