#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASE_DETAIL = ROOT / "frontend" / "src" / "pages" / "CaseDetail.jsx"
DOC = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_UI_V1.md"
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
            CASE_DETAIL,
            (
                "Preventive Care Reminder UI V1",
                "fetchPreventiveCareReminders",
                "runPreventiveCareDryRun",
                "createPreventiveCareReminderFromPreview",
                "completePreventiveCareReminder",
                "snoozePreventiveCareReminder",
                "dismissPreventiveCareReminder",
                "disablePreventiveCareReminder",
                "/api/preventive-care/dry-run",
                "/api/preventive-care/reminders",
                "预防保健提醒 / Preventive Care",
                "生成疫苗/驱虫提醒预览",
                "创建站内提醒",
                "延后14天",
                "禁用提醒",
                "sends_external_message=false",
            ),
            "frontend/src/pages/CaseDetail.jsx",
        ),
        (
            DOC,
            (
                "Preventive Care Reminder UI V1",
                "GET /api/preventive-care/reminders",
                "POST /api/preventive-care/dry-run",
                "sends_external_message=false",
                "creates_case=false",
                "生成疫苗/驱虫提醒预览",
            ),
            "preventive care UI doc",
        ),
        (
            SMOKE,
            (
                "validate_preventive_care_reminder_ui.py",
                "preventive care reminder UI validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_preventive_care_reminder_ui.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK preventive care reminder UI: Case detail in-app reminder panel and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
