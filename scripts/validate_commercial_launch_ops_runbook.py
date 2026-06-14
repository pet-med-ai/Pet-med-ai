#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_OPS_RUNBOOK_V1.md"
DAILY = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_DAILY_HEALTH_CHECK.csv"
WEEKLY = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_WEEKLY_OPS_CHECKLIST.csv"
MONTHLY = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_MONTHLY_OPS_REVIEW.csv"
INCIDENT = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_INCIDENT_RESPONSE_MATRIX.csv"
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


def require_csv(path: Path, required_columns: tuple[str, ...], needles: tuple[str, ...], label: str, min_rows: int = 5) -> int:
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
        RUNBOOK,
        (
            "Commercial Launch Ops Runbook V1",
            "Daily health check",
            "Weekly operations review",
            "Monthly operations review",
            "P0 incident response",
            "Render incident handling",
            "GitHub Actions failure handling",
            "Database / Alembic incident handling",
            "Feature flag incident handling",
            "Secrets incident handling",
            "database_revision == 0008_auto_delivery",
            "database_revision == alembic_head",
            "schema_ok=true",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
            "ENABLE_EMR_REAL_IMPORT=false",
            "No SMS / WeChat / email provider send is allowed",
            "Commercial Launch User Roles / Access Review V1",
        ),
        "ops runbook",
    )
    if rc:
        return rc

    rc = require_csv(
        DAILY,
        (
            "check_id",
            "frequency",
            "area",
            "item",
            "command_or_evidence",
            "expected_result",
            "owner",
            "go_no_go",
            "status",
            "notes",
        ),
        (
            "DAILY-001",
            "Backend healthz",
            "schema_ok",
            "database_revision == 0008_auto_delivery",
            "Automated reminder live send disabled",
            "Online smoke",
            "Open incident review",
        ),
        "daily health check",
        min_rows=12,
    )
    if rc:
        return rc

    rc = require_csv(
        WEEKLY,
        (
            "check_id",
            "frequency",
            "area",
            "item",
            "evidence",
            "expected_result",
            "owner",
            "status",
            "notes",
        ),
        (
            "WEEKLY-001",
            "Review preventive care notification queue",
            "Review GitHub Actions latest main status",
            "Review Render deploy history",
            "Review high-risk flags",
            "Create weekly ops summary",
        ),
        "weekly ops checklist",
        min_rows=10,
    )
    if rc:
        return rc

    rc = require_csv(
        MONTHLY,
        (
            "review_id",
            "frequency",
            "area",
            "item",
            "evidence",
            "expected_result",
            "owner",
            "status",
            "notes",
        ),
        (
            "MONTHLY-001",
            "Review release records",
            "Review backup rollback evidence",
            "Review feature scope drift",
            "Review long-term clinical roadmap",
            "Monthly operating decision",
        ),
        "monthly ops review",
        min_rows=8,
    )
    if rc:
        return rc

    rc = require_csv(
        INCIDENT,
        (
            "incident_id",
            "severity",
            "area",
            "trigger",
            "immediate_action",
            "owner",
            "resume_criteria",
            "status",
            "notes",
        ),
        (
            "OPS-P0-DATA-CROSS-USER",
            "OPS-P0-SCHEMA",
            "OPS-P0-AUTO-SEND",
            "OPS-P0-EMR-IMPORT",
            "OPS-P0-SECRET",
            "OPS-P1-BACKEND-DOWN",
            "OPS-P1-CI-RED",
            "OPS-P2-SCOPE-DRIFT",
        ),
        "incident response matrix",
        min_rows=10,
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_launch_ops_runbook.py",
            "commercial launch ops runbook validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_launch_ops_runbook.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial launch ops runbook: daily/weekly/monthly operations and incident response validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
