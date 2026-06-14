#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PLAN = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_MONITORING_ALERTING_PLAN_V1.md"
CHECKS = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_MONITORING_CHECKS.csv"
ALERTS = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_ALERT_MATRIX.csv"
ESCALATION = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_ALERT_ESCALATION_MATRIX.csv"
EVIDENCE = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_ALERT_EVIDENCE_TEMPLATE.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def require_csv(path: Path, required_columns: tuple[str, ...], needles: tuple[str, ...], label: str, min_rows: int = 1) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")

    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return fail(f"{label} has no header")
            missing = [col for col in required_columns if col not in reader.fieldnames]
            if missing:
                return fail(f"{label} missing columns: {', '.join(missing)}")
            rows = list(reader)
    except Exception as exc:
        return fail(f"{label} is not valid CSV: {exc}")

    if len(rows) < min_rows:
        return fail(f"{label} should contain at least {min_rows} rows")
    return 0


def main() -> int:
    py_compile.compile(str(Path(__file__)), doraise=True)

    rc = require_text(
        PLAN,
        (
            "Commercial Launch Monitoring / Alerting Plan V1",
            "schema_ok=false",
            "database_revision != alembic_head",
            "database_revision != 0008_auto_delivery",
            "all_dangerous_features_disabled=false",
            "ENABLE_EMR_REAL_IMPORT=true",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY=true",
            "cross-user data access suspected",
            "secret appears in logs/UI",
            "P0",
            "P1",
            "P2",
            "P3",
            "This V1 plan does not create these integrations",
            "Commercial Launch Backup / Restore Drill V2",
        ),
        "monitoring alerting plan",
    )
    if rc:
        return rc

    rc = require_csv(
        CHECKS,
        (
            "check_id",
            "mode",
            "area",
            "signal",
            "source",
            "frequency",
            "expected_state",
            "severity_if_fail",
            "owner",
            "action",
        ),
        (
            "MON-001",
            "Backend healthz",
            "schema_ok",
            "database_revision == 0008_auto_delivery",
            "all_dangerous_features_disabled",
            "Automated reminder live delivery disabled",
            "Online smoke",
            "GitHub Actions latest main run",
        ),
        "monitoring checks",
        min_rows=15,
    )
    if rc:
        return rc

    rc = require_csv(
        ALERTS,
        (
            "alert_id",
            "severity",
            "area",
            "trigger",
            "detect_by",
            "notify",
            "first_response_sla",
            "stop_clinic_use",
            "required_evidence",
            "resume_condition",
        ),
        (
            "ALERT-P0-SCHEMA",
            "ALERT-P0-REVISION-MISMATCH",
            "ALERT-P0-DANGEROUS-FLAG",
            "ALERT-P0-AUTO-DELIVERY",
            "ALERT-P0-CROSS-USER",
            "ALERT-P0-SECRET",
            "ALERT-P1-SMOKE-FAIL",
            "ALERT-P2-SCOPE-DRIFT",
        ),
        "alert matrix",
        min_rows=15,
    )
    if rc:
        return rc

    rc = require_csv(
        ESCALATION,
        (
            "severity",
            "response_time",
            "notify_roles",
            "required_action",
            "decision_owner",
            "resume_approval",
        ),
        (
            "P0",
            "P1",
            "P2",
            "P3",
            "release_owner",
            "security_owner",
            "clinical_ops_owner",
        ),
        "alert escalation matrix",
        min_rows=4,
    )
    if rc:
        return rc

    rc = require_csv(
        EVIDENCE,
        (
            "alert_id",
            "date",
            "detected_by",
            "environment",
            "base_url",
            "frontend_url",
            "git_commit",
            "healthz_status",
            "frontend_status",
            "schema_ok",
            "database_revision",
            "alembic_head",
            "dangerous_flags_disabled",
            "smoke_result",
            "ci_static_result",
            "render_reference",
            "github_actions_reference",
            "owner",
            "severity",
            "decision",
            "next_action",
            "notes",
        ),
        (
            "ALERT-EVIDENCE-TEMPLATE",
        ),
        "alert evidence template",
        min_rows=1,
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_launch_monitoring_alerting_plan.py",
            "commercial launch monitoring alerting plan validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_launch_monitoring_alerting_plan.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial launch monitoring alerting plan: checks, alert matrix, escalation and evidence template are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
