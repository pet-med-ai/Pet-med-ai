#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPORT = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_REHEARSAL_EXECUTION_REPORT_V1.md"
EVIDENCE = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_REHEARSAL_EVIDENCE_SUMMARY.csv"
API_EVIDENCE = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_REHEARSAL_API_EVIDENCE_TEMPLATE.csv"
DECISION = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_REHEARSAL_GO_NO_GO_REPORT_TEMPLATE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "EMR_PILOT0_REHEARSAL_RELEASE_RECORD_ADDENDUM.md"
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
            REPORT,
            (
                "EMR real import pilot_0 rehearsal execution report V1",
                "ENABLE_EMR_REAL_IMPORT remained false throughout",
                "HTTP 403",
                "feature flag disabled",
                "quality_gate.passed=true",
                "would_create_count=1",
                "would_update_count=0",
                "No-Go findings",
                "GO: rehearsal passed",
            ),
            "pilot0 rehearsal execution report",
        ),
        (
            EVIDENCE,
            (
                "field,value,required,notes",
                "receipt_id",
                "batch_id",
                "clinical_signoff_id",
                "rollback_snapshot_id",
                "execute_blocked_status",
                "final_decision",
            ),
            "evidence summary",
        ),
        (
            API_EVIDENCE,
            (
                "step,endpoint,method",
                "execution_dry_run",
                "clinical_approval",
                "execute_blocked",
                "online_smoke_after",
            ),
            "api evidence template",
        ),
        (
            DECISION,
            (
                "decision_id,rehearsal_id,batch_id",
                "NO-GO",
                "next_allowed_stage",
            ),
            "go no-go report template",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "EMR pilot_0 dry-run rehearsal evidence",
                "No Case was created",
                "ENABLE_EMR_REAL_IMPORT remained false",
            ),
            "release record addendum",
        ),
        (
            SMOKE,
            (
                "validate_emr_import_pilot0_rehearsal_report.py",
                "emr real import pilot0 rehearsal report validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_emr_import_pilot0_rehearsal_report.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK EMR real import pilot_0 rehearsal report: report templates and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
