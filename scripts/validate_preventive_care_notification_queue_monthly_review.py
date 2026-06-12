#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_NOTIFICATION_QUEUE_MONTHLY_REVIEW_V1.md"
CHECKLIST = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_NOTIFICATION_QUEUE_MONTHLY_REVIEW_CHECKLIST.csv"
REPORT = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_NOTIFICATION_QUEUE_MONTHLY_REPORT_TEMPLATE.csv"
SCORECARD = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_NOTIFICATION_QUEUE_MONTHLY_KPI_SCORECARD.csv"
TRIAGE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_NOTIFICATION_QUEUE_MONTHLY_TRIAGE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "PREVENTIVE_CARE_NOTIFICATION_QUEUE_MONTHLY_REVIEW_RELEASE_ADDENDUM.md"
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
                "Preventive Care Reminder Notification Queue Monthly Review V1",
                "First business day of each month",
                "last 4 weekly logs",
                "auto_send=false",
                "sends_external_message=false",
                "manual_review_required=true",
                "Automated Reminder Delivery Risk Review V1",
                "Hard Stop",
            ),
            "monthly review runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "Review last 4 weekly logs",
                "Aggregate weekly metrics",
                "Review blocked opt-out",
                "Confirm no external send",
                "Monthly decision",
            ),
            "monthly review checklist",
        ),
        (
            REPORT,
            (
                "month_id,month_start,month_end",
                "online_smoke_pass_rate",
                "external_message_sent_count",
                "opt_out_incident_count",
                "monthly_decision",
            ),
            "monthly report template",
        ),
        (
            SCORECARD,
            (
                "metric,green,amber,red",
                "online_smoke_pass_rate",
                "external_message_sent_count",
                "opt_out_incident_count",
                "queue_backlog_trend",
            ),
            "monthly KPI scorecard",
        ),
        (
            TRIAGE,
            (
                "issue_id,severity,area",
                "PC-MONTH-EXTMSG",
                "PC-MONTH-OPTOUT",
                "PC-MONTH-SECRET",
                "PC-MONTH-SCHEMA",
            ),
            "monthly triage",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Preventive Care Notification Queue Monthly Review",
                "No automatic SMS was sent",
                "Client opt-out items were not contacted",
            ),
            "monthly release addendum",
        ),
        (
            SMOKE,
            (
                "validate_preventive_care_notification_queue_monthly_review.py",
                "preventive care notification queue monthly review validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_preventive_care_notification_queue_monthly_review.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK preventive care notification queue monthly review: monthly review package and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
