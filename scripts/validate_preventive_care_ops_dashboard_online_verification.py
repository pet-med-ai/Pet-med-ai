#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_OPS_DASHBOARD_ONLINE_VERIFICATION_V1.md"
CHECKLIST = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_OPS_DASHBOARD_ONLINE_VERIFICATION_CHECKLIST.csv"
EVIDENCE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_OPS_DASHBOARD_ONLINE_VERIFICATION_EVIDENCE.csv"
TRIAGE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_OPS_DASHBOARD_ONLINE_VERIFICATION_TRIAGE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "PREVENTIVE_CARE_OPS_DASHBOARD_ONLINE_VERIFICATION_RELEASE_ADDENDUM.md"
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
                "Preventive Care Reminder Ops Dashboard Online Verification V1",
                "https://pet-med-ai-frontend-static.onrender.com/ops",
                "GET /api/preventive-care/ops/summary",
                "Preventive Care Reminder Ops Dashboard V1",
                "read_only=true",
                "writes_database=false",
                "auto_send=false",
                "sends_external_message=false",
                "manual_review_required=true",
                "Hard No-Go",
            ),
            "ops dashboard online verification runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "Preventive Ops section visible",
                "Summary endpoint status",
                "Read-only gate",
                "No external send gate",
                "Manual review gate",
            ),
            "ops dashboard online verification checklist",
        ),
        (
            EVIDENCE,
            (
                "verification_id,date,operator_id",
                "summary_endpoint_status",
                "read_only_true",
                "writes_database_false",
                "auto_send_false",
                "sends_external_message_false",
                "manual_review_required_true",
            ),
            "ops dashboard online verification evidence",
        ),
        (
            TRIAGE,
            (
                "issue_id,date,severity",
                "PCOPS-500",
                "PCOPS-WRITE",
                "PCOPS-EXTMSG",
                "PCOPS-SECRET",
            ),
            "ops dashboard online verification triage",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Preventive Care Reminder Ops Dashboard Online Verification",
                "Preventive Care Reminder Ops Dashboard V1 is read-only",
                "It does not send SMS / WeChat / email",
            ),
            "release addendum",
        ),
        (
            SMOKE,
            (
                "validate_preventive_care_ops_dashboard_online_verification.py",
                "preventive care ops dashboard online verification validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_preventive_care_ops_dashboard_online_verification.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK preventive care ops dashboard online verification: runbook, checklist and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
