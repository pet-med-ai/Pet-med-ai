#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SPEC = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_SPEC_V1.md"
RULES = ROOT / "docs" / "preventive_care" / "VACCINE_DEWORMING_RULES_V1.csv"
FIELD_MODEL = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_FIELD_MODEL_V1.json"
SOP = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_SAFETY_SOP_V1.md"
COMM = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_CLIENT_COMMUNICATION_TEMPLATES_V1.md"
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


def validate_rules() -> int:
    if not RULES.exists():
        return fail(f"missing file: {RULES.relative_to(ROOT)}")
    rows = list(csv.DictReader(RULES.read_text(encoding="utf-8").splitlines()))
    if len(rows) < 10:
        return fail(f"expected at least 10 preventive care seed rules, got {len(rows)}")

    required_categories = {
        "canine_core_vaccine",
        "feline_core_vaccine",
        "internal_deworming",
        "external_parasite_prevention",
        "fecal_exam",
        "annual_preventive_exam",
    }
    categories = {row.get("category") for row in rows}
    missing = sorted(required_categories - categories)
    if missing:
        return fail("preventive care rules missing categories: " + ", ".join(missing))

    for row in rows:
        if row.get("allow_auto_send") != "no":
            return fail(f"rule {row.get('rule_id')} must have allow_auto_send=no in spec V1")
        if row.get("requires_clinician_confirmation") != "yes":
            return fail(f"rule {row.get('rule_id')} must require clinician confirmation")
    return 0


def validate_field_model() -> int:
    if not FIELD_MODEL.exists():
        return fail(f"missing file: {FIELD_MODEL.relative_to(ROOT)}")
    try:
        data = json.loads(FIELD_MODEL.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid field model JSON: {exc}")

    if data.get("version") != "preventive-care-reminder-spec-v1":
        return fail("unexpected preventive care field model version")

    safety = data.get("safety") or {}
    for key in ("writes_database", "creates_case", "updates_case", "sends_external_message", "executes_real_import"):
        if safety.get(key) is not False:
            return fail(f"field model safety marker must be false: {key}")

    entities = data.get("future_entities") or {}
    for name in ("preventive_care_reminders", "preventive_care_events", "preventive_care_client_preferences"):
        if name not in entities:
            return fail(f"field model missing future entity: {name}")

    return 0


def main() -> int:
    checks = [
        (
            SPEC,
            (
                "Preventive Care Reminder Spec V1",
                "vaccine reminders",
                "deworming reminders",
                "not as automatic medical orders",
                "client opt-out",
                "sends_external_message=false",
                "writes_database=false",
            ),
            "preventive care spec",
        ),
        (
            SOP,
            (
                "Preventive Care Reminder Safety SOP V1",
                "not a diagnosis or prescription",
                "No automatic external messaging in V1",
                "client consent",
                "opt-out registry",
                "sends_external_message=false",
            ),
            "preventive care safety SOP",
        ),
        (
            COMM,
            (
                "Preventive Care Client Communication Templates V1",
                "not sent automatically in V1",
                "预防保健提醒",
                "Opt-out acknowledgement",
            ),
            "client communication templates",
        ),
        (
            SMOKE,
            (
                "validate_preventive_care_reminder_spec.py",
                "preventive care reminder spec validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_preventive_care_reminder_spec.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    rc = validate_rules()
    if rc:
        return rc

    rc = validate_field_model()
    if rc:
        return rc

    print("OK preventive care reminder spec: rules, field model, SOP and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
