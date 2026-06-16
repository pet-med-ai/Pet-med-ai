#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "ops" / "COMMERCIAL_V1_POST_GO_STABILIZATION_RUNBOOK_V1.md"
PILOT = ROOT / "docs" / "ops" / "COMMERCIAL_V1_FIRST_CLINIC_PILOT_OPERATIONS_V1.md"
DAILY = ROOT / "docs" / "ops" / "COMMERCIAL_V1_FIRST_WEEK_DAILY_CHECKLIST.csv"
CHECKLIST = ROOT / "docs" / "ops" / "COMMERCIAL_V1_PILOT_OPERATIONS_CHECKLIST.csv"
INCIDENT = ROOT / "docs" / "ops" / "COMMERCIAL_V1_POST_GO_INCIDENT_LOG_TEMPLATE.csv"
METRICS = ROOT / "docs" / "ops" / "COMMERCIAL_V1_PILOT_METRICS_REVIEW_TEMPLATE.csv"
FINAL = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_FINAL_DECISION_RECORD.csv"
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


def validate_final_go_record() -> int:
    if not FINAL.exists():
        return fail("missing Commercial Launch Final decision record")
    text = FINAL.read_text(encoding="utf-8")
    if "GO_PRODUCTION_COMMERCIAL_LAUNCH" not in text:
        return fail("post-go stabilization requires Final Go decision to be GO_PRODUCTION_COMMERCIAL_LAUNCH")
    return 0


def main() -> int:
    py_compile.compile(str(Path(__file__)), doraise=True)

    rc = validate_final_go_record()
    if rc:
        return rc

    rc = require_text(
        RUNBOOK,
        (
            "Commercial V1 Post-Go Stabilization Runbook V1",
            "D0 through D7",
            "online smoke ALL PASS",
            "schema_ok=true",
            "database_revision == 0008_auto_delivery",
            "all_dangerous_features_disabled=true",
            "automated SMS sending",
            "EMR real import",
            "Stabilization exit criteria",
            "Do not jump directly into live automated messaging or EMR real writes",
        ),
        "post-go stabilization runbook",
    )
    if rc:
        return rc

    rc = require_text(
        PILOT,
        (
            "Commercial V1 First Clinic Pilot Operations V1",
            "one clinic",
            "named pilot users",
            "manual contact",
            "AI is assistive only",
            "Day 0 launch day flow",
            "Days 1-7 operating flow",
            "Pilot success criteria",
            "Pilot failure criteria",
        ),
        "first clinic pilot operations",
    )
    if rc:
        return rc

    rc = require_csv(
        DAILY,
        (
            "day",
            "date",
            "reviewer",
            "backend_healthz",
            "frontend_live",
            "system_version_ok",
            "schema_ok",
            "database_revision",
            "alembic_head",
            "dangerous_flags_disabled",
            "online_smoke",
            "ai_consult_ok",
            "dynamic_consult_ok",
            "case_save_ok",
            "case_detail_ok",
            "case_edit_ok",
            "word_export_ok",
            "preventive_reminder_ok",
            "manual_queue_ok",
            "opt_out_ok",
            "open_p0_count",
            "open_p1_count",
            "decision",
            "notes",
        ),
        (
            "D0",
            "D7",
            "0008_auto_delivery",
            "Launch day supervised workflow",
            "Exit review day",
        ),
        "first week daily checklist",
        min_rows=8,
    )
    if rc:
        return rc

    rc = require_csv(
        CHECKLIST,
        (
            "check_id",
            "phase",
            "item",
            "required_state",
            "owner",
            "status",
            "notes",
        ),
        (
            "PV1-001",
            "Commercial V1 final GO recorded",
            "Staff briefing completed",
            "Manual contact only confirmed",
            "Daily smoke recorded",
            "Expansion decision recorded",
        ),
        "pilot operations checklist",
        min_rows=12,
    )
    if rc:
        return rc

    rc = require_csv(
        INCIDENT,
        (
            "incident_id",
            "date",
            "severity",
            "area",
            "summary",
            "detected_by",
            "affected_workflow",
            "immediate_action",
            "owner",
            "status",
            "resolution",
            "notes",
        ),
        (
            "PV1-INCIDENT-TEMPLATE",
        ),
        "post-go incident log template",
        min_rows=1,
    )
    if rc:
        return rc

    rc = require_csv(
        METRICS,
        (
            "review_id",
            "period_start",
            "period_end",
            "clinic_name",
            "reviewer",
            "ai_consults_count",
            "dynamic_followups_count",
            "cases_created_count",
            "cases_updated_count",
            "word_exports_count",
            "preventive_reminders_reviewed",
            "manual_queue_items_reviewed",
            "opt_out_events_count",
            "p0_count",
            "p1_count",
            "p2_count",
            "staff_feedback_summary",
            "client_feedback_summary",
            "decision",
            "next_actions",
        ),
        (
            "PV1-METRICS-TEMPLATE",
        ),
        "pilot metrics review template",
        min_rows=1,
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_v1_post_go_stabilization.py",
            "commercial v1 post-go stabilization validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_v1_post_go_stabilization.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial v1 post-go stabilization: first clinic pilot runbook, daily checklist, incident log and metrics templates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
