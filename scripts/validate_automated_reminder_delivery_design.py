#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DESIGN = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_DESIGN_V1.md"
FLAGS = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_FEATURE_FLAGS_V1.md"
STATE_MACHINE = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_STATE_MACHINE.csv"
CONSENT = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_CONSENT_OPT_OUT_DESIGN_V1.md"
TEMPLATE_POLICY = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_TEMPLATE_POLICY_V1.md"
LOG_MODEL = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_LOG_MODEL_DESIGN.csv"
PILOT = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_PILOT_PLAN_V1.md"
TEST_MATRIX = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_DRY_RUN_TEST_MATRIX.csv"
ADDENDUM = ROOT / "docs" / "ops" / "AUTOMATED_REMINDER_DELIVERY_DESIGN_RELEASE_ADDENDUM.md"
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
            DESIGN,
            (
                "Automated Reminder Delivery Design V1",
                "NO-GO for real delivery",
                "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
                "DeliveryEligibilityCheck",
                "ProviderAdapter",
                "auto_send=false",
                "sends_external_message=false",
                "manual_review_required=true",
            ),
            "automated delivery design",
        ),
        (
            FLAGS,
            (
                "Automated Reminder Delivery Feature Flags V1",
                "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
                "ENABLE_PREVENTIVE_SMS_DELIVERY=false",
                "ENABLE_PREVENTIVE_DELIVERY_DRY_RUN=true",
            ),
            "feature flag design",
        ),
        (
            STATE_MACHINE,
            (
                "state,description,may_send_external_message",
                "blocked_opt_out",
                "blocked_kill_switch",
                "manual_review_required",
            ),
            "state machine",
        ),
        (
            CONSENT,
            (
                "Automated Reminder Delivery Consent / Opt-out Design V1",
                "opt_out_all=true",
                "immediately before provider send",
                "sends_external_message=false",
            ),
            "consent design",
        ),
        (
            TEMPLATE_POLICY,
            (
                "Automated Reminder Delivery Template Policy V1",
                "not a diagnosis or prescription",
                "Forbidden wording",
                "no template is approved for automated delivery",
            ),
            "template policy",
        ),
        (
            LOG_MODEL,
            (
                "delivery_id,string,yes",
                "opt_out_snapshot,json,yes",
                "message_hash,string,yes",
                "provider_message_id,string,no",
            ),
            "delivery log model design",
        ),
        (
            PILOT,
            (
                "Automated Reminder Delivery Pilot Plan V1",
                "NO-GO until design",
                "single channel",
                "max owners: 5",
                "Stop conditions",
            ),
            "pilot plan",
        ),
        (
            TEST_MATRIX,
            (
                "test_id,category,test",
                "ARD-T001",
                "opt_out_all true blocks send",
                "delivery never creates Case",
            ),
            "dry-run test matrix",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Automated Reminder Delivery Design",
                "This stage did not send SMS",
                "Automated Reminder Delivery Data Model V1",
            ),
            "release addendum",
        ),
        (
            SMOKE,
            (
                "validate_automated_reminder_delivery_design.py",
                "automated reminder delivery design validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_automated_reminder_delivery_design.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK automated reminder delivery design: design docs, gates and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
