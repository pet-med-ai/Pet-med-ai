#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_PILOT_RUNBOOK_V1.md"
CANDIDATE = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_PILOT_CANDIDATE_CHECKLIST.csv"
WINDOW = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_PILOT_CONTROLLED_WINDOW_CHECKLIST.csv"
EVIDENCE = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_PILOT_EVIDENCE_TEMPLATE.csv"
INCIDENT = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_PILOT_INCIDENT_MATRIX.csv"
POST_REVIEW = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_POST_PILOT_REVIEW_TEMPLATE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "AUTOMATED_REMINDER_DELIVERY_PILOT_RUNBOOK_RELEASE_ADDENDUM.md"
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
                "Automated Reminder Delivery Pilot Runbook V1",
                "NO-GO",
                "max_owners=5",
                "database_revision == 0008_auto_delivery",
                "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
                "Stop conditions",
                "Hard No-Go",
            ),
            "pilot runbook",
        ),
        (
            CANDIDATE,
            (
                "candidate_id,owner_id,reminder_id",
                "client_consent_verified",
                "template_approved",
                "manual_approval_recorded",
                "clinical_ops_approved",
            ),
            "candidate checklist",
        ),
        (
            WINDOW,
            (
                "phase,item,owner",
                "Kill switch test",
                "Final dry-run",
                "Disable live flag",
                "Complete pilot report",
            ),
            "controlled window checklist",
        ),
        (
            EVIDENCE,
            (
                "pilot_id,date,operator_id",
                "online_smoke_before",
                "database_revision",
                "kill_switch_tested",
                "wrong_recipient_count",
                "final_decision",
            ),
            "pilot evidence",
        ),
        (
            INCIDENT,
            (
                "incident_id,severity,area",
                "ARD-PILOT-WRONG-RECIPIENT",
                "ARD-PILOT-OPTOUT",
                "ARD-PILOT-SECRET",
                "ARD-PILOT-CASE",
            ),
            "incident matrix",
        ),
        (
            POST_REVIEW,
            (
                "pilot_id,review_date,review_owner",
                "success_count",
                "opt_out_incident_count",
                "decision",
            ),
            "post-pilot review",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Automated Reminder Delivery Pilot Runbook",
                "This stage did not send SMS",
                "Automated Reminder Delivery Provider Adapter Sandbox V1",
            ),
            "release addendum",
        ),
        (
            SMOKE,
            (
                "validate_automated_reminder_delivery_pilot_runbook.py",
                "automated reminder delivery pilot runbook validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_automated_reminder_delivery_pilot_runbook.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK automated reminder delivery pilot runbook: controlled pilot SOP, evidence and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
