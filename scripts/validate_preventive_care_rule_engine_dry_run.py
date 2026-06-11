#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

RULES_MODULE = BACKEND / "preventive_care_rules.py"
CLI = ROOT / "scripts" / "preventive_care_rule_dry_run.py"
SAMPLE = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_RULE_DRY_RUN_SAMPLE_INPUT.json"
RULES_CSV = ROOT / "docs" / "preventive_care" / "VACCINE_DEWORMING_RULES_V1.csv"
DOC = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_RULE_ENGINE_DRY_RUN_V1.md"
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


def validate_runtime() -> int:
    sys.path.insert(0, str(BACKEND))
    from preventive_care_rules import compute_preventive_care_reminders, load_preventive_care_rules  # noqa: WPS433

    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    rules = load_preventive_care_rules(RULES_CSV)
    report = compute_preventive_care_reminders(sample["pet"], as_of=sample["as_of_date"], rules=rules)

    if report.get("message") != "preventive_care_rule_engine_dry_run":
        return fail("dry-run report message mismatch")
    if report.get("writes_database") is not False:
        return fail("dry-run must not write database")
    if report.get("sends_external_message") is not False:
        return fail("dry-run must not send external message")

    items = report.get("items") or []
    if len(items) < 5:
        return fail(f"expected at least 5 reminder previews, got {len(items)}")

    by_rule = {item.get("rule_id"): item for item in items}
    for rule_id in ("canine_core_vaccine_review_adult", "adult_deworming_quarterly_if_no_broad_control", "annual_wellness_exam"):
        if rule_id not in by_rule:
            return fail(f"expected dry-run item missing: {rule_id}")

    for item in items:
        if item.get("allow_auto_send") is not False:
            return fail(f"allow_auto_send must be false for {item.get('rule_id')}")
        if item.get("requires_clinician_confirmation") is not True:
            return fail(f"requires_clinician_confirmation must be true for {item.get('rule_id')}")
        if item.get("writes_database") is not False:
            return fail(f"item writes_database must be false for {item.get('rule_id')}")

    cmd = [
        sys.executable,
        str(CLI),
        "--input",
        str(SAMPLE),
        "--rules",
        str(RULES_CSV),
        "--as-of",
        "2026-06-11",
    ]
    result = subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        return fail("CLI dry-run failed: " + result.stderr[:500])
    cli_report = json.loads(result.stdout)
    if cli_report.get("message") != "preventive_care_rule_engine_dry_run":
        return fail("CLI output message mismatch")
    if cli_report.get("summary", {}).get("total", 0) < 5:
        return fail("CLI output does not contain expected reminders")

    return 0


def main() -> int:
    for path in (RULES_MODULE, CLI, SAMPLE, RULES_CSV, DOC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        RULES_MODULE,
        (
            "compute_preventive_care_reminders",
            "reminder_preview_for_rule",
            "load_preventive_care_rules",
            '"writes_database": False',
            '"sends_external_message": False',
            '"allow_auto_send": False',
        ),
        "backend/preventive_care_rules.py",
    )
    if rc:
        return rc

    forbidden = ("SessionLocal", "db.add(", "db.commit(", "requests.post(", "smtplib", "ENABLE_EMR_REAL_IMPORT=true")
    module_text = RULES_MODULE.read_text(encoding="utf-8")
    for needle in forbidden:
        if needle in module_text:
            return fail(f"dry-run rule engine must stay offline/read-only; forbidden marker found: {needle}")

    rc = require_text(
        CLI,
        (
            "Preventive Care Reminder Rule Engine dry-run V1",
            "compute_preventive_care_reminders",
            "--only-actionable",
        ),
        "scripts/preventive_care_rule_dry_run.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Preventive Care Reminder Rule Engine Dry-run V1",
            "writes_database=false",
            "sends_external_message=false",
            "reason=missing_trigger_date",
        ),
        "dry-run doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_preventive_care_rule_engine_dry_run.py",
            "preventive care reminder rule engine dry-run validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_preventive_care_rule_engine_dry_run.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    rc = validate_runtime()
    if rc:
        return rc

    print("OK preventive care reminder rule engine dry-run: offline rule calculation and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
