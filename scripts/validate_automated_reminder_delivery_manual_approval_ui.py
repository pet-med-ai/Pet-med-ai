#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

API = ROOT / "backend" / "automated_reminder_delivery_api.py"
PAGE = ROOT / "frontend" / "src" / "pages" / "AutomatedReminderDeliveryManualApprovalPage.jsx"
APP = ROOT / "frontend" / "src" / "App.jsx"
DOC = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_MANUAL_APPROVAL_UI_V1.md"
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
    for path in (API, PAGE, APP, DOC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        API,
        (
            "AutomatedReminderDeliveryManualReviewIn",
            '@router.post("/attempts/{delivery_id}/manual-review"',
            "manual_review_automated_reminder_delivery_attempt",
            "manual_reviewed_dry_run",
            '"sends_external_message": False',
            '"auto_send": False',
            '"creates_case": False',
            '"updates_case": False',
            '"executes_real_import": False',
        ),
        "automated reminder delivery API manual-review endpoint",
    )
    if rc:
        return rc

    api_text = API.read_text(encoding="utf-8")
    for needle in ("requests.post(", "httpx.post(", "smtplib", "twilio", "send_sms", "send_wechat", "send_email", "ProviderAdapter", "provider.send", "ENABLE_EMR_REAL_IMPORT=true"):
        if needle in api_text:
            return fail(f"manual approval stage must not send external messages or call providers: {needle}")

    rc = require_text(
        PAGE,
        (
            "Automated Reminder Delivery Manual Approval UI V1",
            "/api/automated-reminder-delivery/attempts",
            "/manual-review",
            "自动提醒发送人工审批（Dry-run）",
            "审核通过 dry-run",
            "要求修改",
            "auto_send=false",
            "sends_external_message=false",
        ),
        "manual approval UI page",
    )
    if rc:
        return rc

    rc = require_text(
        APP,
        (
            "AutomatedReminderDeliveryManualApprovalPage",
            "/automated-reminder-delivery/manual-approval",
            "自动提醒审批",
        ),
        "frontend App route",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Automated Reminder Delivery Manual Approval UI V1",
            "POST /api/automated-reminder-delivery/attempts/{delivery_id}/manual-review",
            "dry_run=true",
            "sends_external_message=false",
            "approved for dry-run review evidence only",
        ),
        "manual approval UI doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_automated_reminder_delivery_manual_approval_ui.py",
            "automated reminder delivery manual approval UI validation",
            "/api/automated-reminder-delivery/attempts/${manual_approval_delivery_id}/manual-review",
            "automated reminder delivery manual review",
            "automated reminder delivery user B cannot review user A attempt",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_automated_reminder_delivery_manual_approval_ui.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK automated reminder delivery manual approval UI: dry-run approval route, page and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
