#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_WEEKLY_OPS_RUNBOOK_V1.md"
CHECKLIST = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_WEEKLY_OPS_CHECKLIST.csv"
LOG_TEMPLATE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_WEEKLY_OPS_LOG_TEMPLATE.csv"
THRESHOLDS = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_WEEKLY_OPS_KPI_THRESHOLDS.csv"
TRIAGE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_WEEKLY_OPS_TRIAGE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "PREVENTIVE_CARE_WEEKLY_OPS_RELEASE_ADDENDUM.md"
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
                "Preventive Care Reminder Weekly Ops Runbook V1",
                "Every Monday morning",
                "https://pet-med-ai-frontend-static.onrender.com/ops",
                "auto_send=false",
                "sends_external_message=false",
                "manual_review_required=true",
                "database_revision == 0007_preventive_care",
                "Hard Stop",
            ),
            "weekly ops runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "Open Ops Dashboard",
                "Record preventive attention",
                "Review draft items",
                "Respect opt-out",
                "Complete weekly log",
            ),
            "weekly ops checklist",
        ),
        (
            LOG_TEMPLATE,
            (
                "week_id,week_start,week_end",
                "preventive_attention",
                "queue_needs_review",
                "external_message_sent",
                "final_status",
            ),
            "weekly ops log template",
        ),
        (
            THRESHOLDS,
            (
                "metric,green,amber,red",
                "preventive_attention",
                "queue_needs_review",
                "auto_send",
                "sends_external_message",
            ),
            "weekly ops KPI thresholds",
        ),
        (
            TRIAGE,
            (
                "issue_id,severity,area",
                "PC-WEEK-SMOKE",
                "PC-WEEK-EXTMSG",
                "PC-WEEK-OPTOUT",
                "PC-WEEK-SECRET",
            ),
            "weekly ops triage",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Preventive Care Reminder Weekly Ops Runbook",
                "auto_send=false",
                "opt-out items not contacted",
            ),
            "weekly ops release addendum",
        ),
        (
            SMOKE,
            (
                "validate_preventive_care_weekly_ops_runbook.py",
                "preventive care weekly ops runbook validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_preventive_care_weekly_ops_runbook.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK preventive care weekly ops runbook: weekly SOP, checklist, log and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
