#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RELEASE_RECORD = ROOT / "docs" / "ops" / "PREVENTIVE_CARE_REMINDER_RELEASE_RECORD_V1.md"
CHECKLIST = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_RELEASE_CHECKLIST.csv"
EVIDENCE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_RELEASE_EVIDENCE.csv"
ROLLBACK = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_ROLLBACK_NOTES_V1.md"
TRIAGE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_RELEASE_TRIAGE.csv"
RELEASE_TEMPLATE = ROOT / "docs" / "ops" / "releases" / "preventive-care-reminder-v1.md"
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
            RELEASE_RECORD,
            (
                "Preventive Care Reminder Release Record V1",
                "preventive-care-reminder-v1",
                "sends_external_message=false",
                "auto_send=false",
                "manual_review_required=true",
                "database_revision=0007_preventive_care",
                "GO",
                "NO-GO",
            ),
            "release record",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "Online smoke",
                "Preventive migration",
                "No external message",
                "Client opt-out respected",
                "Final decision",
            ),
            "release checklist",
        ),
        (
            EVIDENCE,
            (
                "field,value,required",
                "github_actions_run_url",
                "online_smoke_result",
                "preventive_care_migration",
                "sends_external_message_false_verified",
                "final_decision",
            ),
            "release evidence",
        ),
        (
            ROLLBACK,
            (
                "Preventive Care Reminder Rollback Notes V1",
                "system sends external SMS / WeChat / email unexpectedly",
                "client opt-out ignored",
                "sends_external_message=false",
            ),
            "rollback notes",
        ),
        (
            TRIAGE,
            (
                "issue_id,severity,area",
                "PCR-REL-EXTMSG",
                "PCR-REL-OPTOUT",
                "PCR-REL-SECRET",
            ),
            "release triage",
        ),
        (
            RELEASE_TEMPLATE,
            (
                "Release: preventive-care-reminder-v1",
                "No automatic SMS was sent",
                "No Case was created",
                "No EMR import was executed",
            ),
            "release template",
        ),
        (
            SMOKE,
            (
                "validate_preventive_care_release_record.py",
                "preventive care reminder release record validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_preventive_care_release_record.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK preventive care release record: release evidence, rollback notes and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
