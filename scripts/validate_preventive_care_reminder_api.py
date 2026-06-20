#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

API = ROOT / "backend" / "preventive_care_api.py"
MAIN = ROOT / "backend" / "main.py"
DOC = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_API_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_file(path: Path) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    return 0


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    rc = require_file(path)
    if rc:
        return rc
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    for path in (API, MAIN, DOC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        API,
        (
            'router = APIRouter(prefix="/api/preventive-care"',
            '@router.get("/rules"',
            '@router.post("/dry-run"',
            '@router.get("/reminders"',
            '@router.post("/reminders"',
            '@router.post("/reminders/{reminder_id}/complete"',
            '@router.post("/reminders/{reminder_id}/snooze"',
            '@router.post("/reminders/{reminder_id}/dismiss"',
            '@router.post("/reminders/{reminder_id}/disable"',
            '@router.get("/client-preferences"',
            '@router.put("/client-preferences"',
            "get_current_user",
            "PreventiveCareReminder",
            "PreventiveCareEvent",
            "PreventiveCareClientPreference",
            "PreventiveCareRuleSet",
            "source_rule_id = data.source_rule_id or data.rule_id",
            "db.get(PreventiveCareRuleSet, data.rule_id)",
            "rule_id=linked_rule_id",
            "compute_preventive_care_reminders",
            '"sends_external_message": False',
            '"creates_case": False',
            '"updates_case": False',
            '"executes_real_import": False',
        ),
        "backend/preventive_care_api.py",
    )
    if rc:
        return rc

    forbidden = (
        "smtplib",
        "twilio",
        "send_sms",
        "send_wechat",
        "requests.post(",
        "httpx.post(",
        "ENABLE_EMR_REAL_IMPORT=true",
    )
    api_text = API.read_text(encoding="utf-8")
    for needle in forbidden:
        if needle in api_text:
            return fail(f"preventive care API V1 must not send external messages or open real import: {needle}")

    rc = require_text(
        MAIN,
        (
            "preventive_care_api_router",
            "app.include_router(preventive_care_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Preventive Care Reminder API V1",
            "POST /api/preventive-care/dry-run",
            "POST /api/preventive-care/reminders",
            "sends_external_message=false",
            "creates_case=false",
        ),
        "preventive care API doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_preventive_care_reminder_api.py",
            "preventive care reminder API validation",
            "/api/preventive-care/dry-run",
            "/api/preventive-care/reminders",
            "preventive care reminder complete",
            "preventive care client preferences save",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_preventive_care_reminder_api.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK preventive care reminder API: authenticated in-app reminder endpoints and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
