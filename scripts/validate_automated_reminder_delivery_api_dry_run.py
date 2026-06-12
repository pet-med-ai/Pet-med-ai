#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

API = ROOT / "backend" / "automated_reminder_delivery_api.py"
MAIN = ROOT / "backend" / "main.py"
DOC = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_API_DRY_RUN_V1.md"
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
            'router = APIRouter(prefix="/api/automated-reminder-delivery"',
            '@router.post("/dry-run"',
            '@router.get("/attempts"',
            '@router.get("/attempts/{delivery_id}"',
            '@router.post("/attempts/{delivery_id}/cancel"',
            "AutomatedReminderDeliveryAttempt",
            "AutomatedReminderDeliveryTemplate",
            "PreventiveCareNotificationQueue",
            "evaluate_delivery_eligibility",
            '"sends_external_message": False',
            '"auto_send": False',
            '"creates_case": False',
            '"updates_case": False',
            '"executes_real_import": False',
        ),
        "automated reminder delivery API",
    )
    if rc:
        return rc

    forbidden = (
        "requests.post(",
        "httpx.post(",
        "smtplib",
        "twilio",
        "send_sms",
        "send_wechat",
        "send_email",
        "ProviderAdapter",
        "provider.send",
        "ENABLE_EMR_REAL_IMPORT=true",
    )
    api_text = API.read_text(encoding="utf-8")
    for needle in forbidden:
        if needle in api_text:
            return fail(f"dry-run API must not send external messages or call providers: {needle}")

    rc = require_text(
        MAIN,
        (
            "automated_reminder_delivery_api_router",
            "app.include_router(automated_reminder_delivery_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Automated Reminder Delivery API Dry-run V1",
            "POST /api/automated-reminder-delivery/dry-run",
            "GET /api/automated-reminder-delivery/attempts",
            "sends_external_message=false",
            "auto_send=false",
            "creates_case=false",
        ),
        "API dry-run doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_automated_reminder_delivery_api_dry_run.py",
            "automated reminder delivery API dry-run validation",
            "/api/automated-reminder-delivery/dry-run",
            "automated reminder delivery dry-run create",
            "automated reminder delivery attempt cancel",
            "automated reminder delivery user B cannot see user A attempt",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_automated_reminder_delivery_api_dry_run.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK automated reminder delivery API dry-run: dry-run attempt endpoints and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
