#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

API = ROOT / "backend" / "preventive_care_notification_api.py"
MAIN = ROOT / "backend" / "main.py"
DOC = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_NOTIFICATION_QUEUE_V1.md"
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
            'router = APIRouter(prefix="/api/preventive-care/notification-queue"',
            "@router.get",
            '@router.post("/draft"',
            '@router.post("/{notification_id}/review"',
            '@router.post("/{notification_id}/mark-contacted"',
            '@router.post("/{notification_id}/cancel"',
            "PreventiveCareNotificationQueue",
            "PreventiveCareReminder",
            "PreventiveCareClientPreference",
            "manual_review_required",
            "client_opt_out_snapshot",
            '"sends_external_message": False',
            '"auto_send": False',
            '"creates_case": False',
            '"updates_case": False',
            '"executes_real_import": False',
        ),
        "backend/preventive_care_notification_api.py",
    )
    if rc:
        return rc

    forbidden = (
        "smtplib",
        "twilio",
        "send_sms",
        "send_wechat",
        "send_email",
        "requests.post(",
        "httpx.post(",
        "BackgroundTasks",
        "ENABLE_EMR_REAL_IMPORT=true",
    )
    api_text = API.read_text(encoding="utf-8")
    for needle in forbidden:
        if needle in api_text:
            return fail(f"notification queue V1 must stay manual/no external send: {needle}")

    rc = require_text(
        MAIN,
        (
            "preventive_care_notification_api_router",
            "app.include_router(preventive_care_notification_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Preventive Care Reminder Notification Queue V1",
            "manual_review_required=true",
            "sends_external_message=false",
            "auto_send=false",
            "blocked_opt_out",
        ),
        "notification queue doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_preventive_care_notification_queue.py",
            "preventive care notification queue validation",
            "/api/preventive-care/notification-queue/draft",
            "preventive care notification queue draft",
            "preventive care notification queue mark contacted",
            "preventive care notification queue user B cannot review user A item",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_preventive_care_notification_queue.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK preventive care notification queue: manual queue endpoints and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
