#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_RISK_REVIEW_V1.md"
RISK_REGISTER = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_RISK_REGISTER.csv"
GO_NO_GO = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_GO_NO_GO_CHECKLIST.csv"
CHANNEL_MATRIX = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_CHANNEL_MATRIX.csv"
PROVIDER = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_PROVIDER_CHECKLIST.csv"
INCIDENT = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_INCIDENT_PLAYBOOK_V1.md"
ADDENDUM = ROOT / "docs" / "ops" / "AUTOMATED_REMINDER_DELIVERY_RISK_REVIEW_RELEASE_ADDENDUM.md"
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
                "Automated Reminder Delivery Risk Review V1",
                "Default state",
                "NO-GO",
                "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
                "sends_external_message=false",
                "auto_send=false",
                "manual_review_required=true",
                "Automated Reminder Delivery Design V1",
                "Hard No-Go",
            ),
            "risk review runbook",
        ),
        (
            RISK_REGISTER,
            (
                "risk_id,severity,category",
                "ARD-R001",
                "client receives message after opt-out",
                "provider credential leak",
                "delivery code mutates Case",
            ),
            "risk register",
        ),
        (
            GO_NO_GO,
            (
                "gate_id,gate,owner",
                "Monthly review completed",
                "No opt-out incident",
                "Kill switch design",
                "Final risk decision",
            ),
            "go no-go checklist",
        ),
        (
            CHANNEL_MATRIX,
            (
                "channel,allowed_in_current_v1",
                "sms_automated,false",
                "wechat_automated,false",
                "email_automated,false",
            ),
            "channel matrix",
        ),
        (
            PROVIDER,
            (
                "Provider selected",
                "Credentials stored in Render env",
                "No credentials in repo",
                "Kill switch tested",
            ),
            "provider checklist",
        ),
        (
            INCIDENT,
            (
                "Automated Reminder Delivery Incident Playbook V1",
                "message sent after client opt-out",
                "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
                "auto_send=false",
            ),
            "incident playbook",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Automated Reminder Delivery Risk Review",
                "This stage did not send SMS",
                "Automated Reminder Delivery Design V1",
            ),
            "release addendum",
        ),
        (
            SMOKE,
            (
                "validate_automated_reminder_delivery_risk_review.py",
                "automated reminder delivery risk review validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_automated_reminder_delivery_risk_review.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK automated reminder delivery risk review: risk register, gates and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
