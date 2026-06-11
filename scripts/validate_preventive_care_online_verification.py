#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_ONLINE_VERIFICATION_V1.md"
CHECKLIST = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_ONLINE_VERIFICATION_CHECKLIST.csv"
EVIDENCE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_ONLINE_VERIFICATION_EVIDENCE.csv"
TRIAGE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_ONLINE_VERIFICATION_TRIAGE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "PREVENTIVE_CARE_REMINDER_ONLINE_VERIFICATION_RELEASE_ADDENDUM.md"
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
                "Preventive Care Reminder Online Verification V1",
                "https://pet-med-ai-frontend-static.onrender.com",
                "https://pet-med-ai-backend.onrender.com",
                "预防保健提醒 / Preventive Care",
                "生成疫苗/驱虫提醒预览",
                "预防保健前台待联系队列",
                "auto_send=false",
                "sends_external_message=false",
                "Hard No-Go",
            ),
            "online verification runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "Preventive panel visible",
                "Create in-app reminder",
                "Create queue draft",
                "Mark manually contacted",
                "No external message sent",
            ),
            "online verification checklist",
        ),
        (
            EVIDENCE,
            (
                "verification_id,date,operator_id",
                "reminder_id",
                "notification_id",
                "auto_send_false",
                "sends_external_message_false",
                "console_secret_leak_absent",
            ),
            "online verification evidence",
        ),
        (
            TRIAGE,
            (
                "issue_id,date,severity",
                "PCV-401",
                "PCV-EXTERNAL-SENT",
                "PCV-OPTOUT-IGNORED",
                "PCV-SECRET",
            ),
            "online verification triage",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Preventive Care Reminder Online Verification",
                "No automatic external message was sent",
                "No EMR import was executed",
            ),
            "release addendum",
        ),
        (
            SMOKE,
            (
                "validate_preventive_care_online_verification.py",
                "preventive care reminder online verification validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_preventive_care_online_verification.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK preventive care online verification: runbook, checklist and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
