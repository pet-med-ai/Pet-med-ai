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

ENGINE = BACKEND / "automated_reminder_delivery_eligibility.py"
CLI = ROOT / "scripts" / "automated_reminder_delivery_eligibility_dry_run.py"
SAMPLE = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_ELIGIBILITY_SAMPLE_INPUT.json"
DOC = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_ELIGIBILITY_DRY_RUN_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"

EXPECTED_SCENARIOS = {
    "dry_run_with_live_flags_off": "blocked_kill_switch",
    "blocked_opt_out": "blocked_opt_out",
    "blocked_missing_consent": "blocked_missing_consent",
    "blocked_manual_review": "manual_review_required",
    "blocked_unapproved_template": "blocked_unapproved_template",
    "blocked_quiet_hours": "blocked_quiet_hours",
    "blocked_rate_limit": "blocked_rate_limit",
    "live_eligible_if_flags_on": None,
}


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
    from automated_reminder_delivery_eligibility import evaluate_delivery_scenarios  # noqa: WPS433

    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    report = evaluate_delivery_scenarios(payload)

    if report.get("message") != "automated_reminder_delivery_eligibility_scenarios":
        return fail("scenario report message mismatch")
    if report.get("sends_external_message") is not False:
        return fail("dry-run scenario report must not send external messages")
    if report.get("writes_database") is not False:
        return fail("dry-run scenario report must not write database")

    results = {item.get("scenario_id"): item for item in report.get("results", [])}
    for scenario_id, expected_first_reason in EXPECTED_SCENARIOS.items():
        item = results.get(scenario_id)
        if not item:
            return fail(f"missing scenario result: {scenario_id}")
        if item.get("sends_external_message") is not False:
            return fail(f"scenario must not send external message: {scenario_id}")
        if item.get("auto_send") is not False:
            return fail(f"scenario must not auto_send: {scenario_id}")
        if item.get("dry_run") is not True:
            return fail(f"scenario must be dry_run: {scenario_id}")
        if expected_first_reason is None:
            if item.get("eligible_for_live_send") is not True:
                return fail(f"scenario should be live eligible when flags are on: {scenario_id}")
        else:
            reasons = [r.get("reason") for r in item.get("blocked_reasons", [])]
            if expected_first_reason not in reasons:
                return fail(f"{scenario_id} missing expected blocker {expected_first_reason}; got {reasons}")

    cmd = [
        sys.executable,
        str(CLI),
        "--input",
        str(SAMPLE),
    ]
    result = subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        return fail("CLI dry-run failed: " + result.stderr[:500])
    cli_report = json.loads(result.stdout)
    if cli_report.get("total", 0) < len(EXPECTED_SCENARIOS):
        return fail("CLI did not return expected scenario count")

    return 0


def main() -> int:
    for path in (ENGINE, CLI, SAMPLE, DOC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        ENGINE,
        (
            "evaluate_delivery_eligibility",
            "evaluate_delivery_scenarios",
            "blocked_opt_out",
            "blocked_kill_switch",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY",
            '"sends_external_message": False',
            '"auto_send": False',
            '"writes_database": False',
            '"creates_case": False',
            '"executes_real_import": False',
        ),
        "backend/automated_reminder_delivery_eligibility.py",
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
        "db.commit(",
        "SessionLocal",
        "ENABLE_EMR_REAL_IMPORT=true",
    )
    engine_text = ENGINE.read_text(encoding="utf-8")
    for needle in forbidden:
        if needle in engine_text:
            return fail(f"eligibility dry-run engine must stay offline/read-only; forbidden marker found: {needle}")

    rc = require_text(
        CLI,
        (
            "Automated Reminder Delivery Eligibility Engine dry-run V1",
            "evaluate_delivery_eligibility",
            "evaluate_delivery_scenarios",
            "--single",
        ),
        "scripts/automated_reminder_delivery_eligibility_dry_run.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Automated Reminder Delivery Eligibility Engine Dry-run V1",
            "blocked_opt_out",
            "blocked_kill_switch",
            "sends_external_message=false",
            "writes_database=false",
        ),
        "eligibility dry-run doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_automated_reminder_delivery_eligibility_dry_run.py",
            "automated reminder delivery eligibility dry-run validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_automated_reminder_delivery_eligibility_dry_run.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    rc = validate_runtime()
    if rc:
        return rc

    print("OK automated reminder delivery eligibility dry-run: offline safety gate evaluation is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
