#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_BACKUP_RESTORE_DRILL_V2.md"
CHECKLIST = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_BACKUP_RESTORE_DRILL_CHECKLIST.csv"
EVIDENCE = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_BACKUP_RESTORE_EVIDENCE_TEMPLATE.csv"
COMMANDS = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_BACKUP_RESTORE_COMMAND_TEMPLATE.md"
RISKS = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_BACKUP_RESTORE_RISK_REGISTER.csv"
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
        RUNBOOK,
        (
            "Commercial Launch Backup / Restore Drill V2",
            "Never restore directly into production",
            "database_revision == alembic_head",
            "database_revision == 0008_auto_delivery",
            "schema_ok=true",
            "all_dangerous_features_disabled=true",
            "backup exists",
            "restore path tested",
            "restore duration recorded",
            "NO-GO until evidence is filled",
            "does not mean the real restore drill has been performed",
        ),
        "backup restore drill runbook",
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
            "evidence",
            "owner",
            "go_no_go",
            "status",
            "notes",
        ),
        (
            "BRD2-001",
            "Backend healthz",
            "Expected revision",
            "Recent Render backup exists",
            "Non-production restore target identified",
            "Restore duration recorded",
            "Restored revision expected",
            "No secrets in evidence",
            "Release owner signoff",
        ),
        "backup restore checklist",
        min_rows=20,
    )
    if rc:
        return rc

    rc = require_csv(
        EVIDENCE,
        (
            "drill_id",
            "date",
            "environment",
            "source_db",
            "backup_source",
            "backup_reference",
            "backup_timestamp",
            "backup_age_minutes",
            "restore_target",
            "restore_started_at",
            "restore_finished_at",
            "restore_duration_minutes",
            "rto_observed_minutes",
            "rpo_observed_minutes",
            "preflight_schema_ok",
            "preflight_database_revision",
            "preflight_alembic_head",
            "restored_alembic_version",
            "restored_schema_ok",
            "restored_database_revision",
            "restored_alembic_head",
            "restored_core_tables_ok",
            "restored_smoke_result",
            "dangerous_flags_disabled",
            "secrets_exposed",
            "phi_exposed",
            "temp_target_cleanup_status",
            "release_owner",
            "security_owner",
            "backend_owner",
            "clinical_ops_owner",
            "decision",
            "notes",
        ),
        (
            "BRD2-TEMPLATE",
            "NO-GO until real restore evidence is filled",
        ),
        "backup restore evidence template",
        min_rows=1,
    )
    if rc:
        return rc

    rc = require_text(
        COMMANDS,
        (
            "Commercial Launch Backup / Restore Command Template V2",
            "Do not commit real DATABASE_URL",
            "pg_dump",
            "pg_restore",
            "RESTORE_DATABASE_URL",
            "SELECT version_num FROM alembic_version",
            "0008_auto_delivery",
            "Do not commit the dump file",
        ),
        "backup restore command template",
    )
    if rc:
        return rc

    rc = require_csv(
        RISKS,
        (
            "risk_id",
            "risk",
            "severity",
            "trigger",
            "mitigation",
            "go_no_go",
            "owner",
            "status",
        ),
        (
            "BRD2-R001",
            "no recent backup exists",
            "restore performed against production",
            "restored revision mismatch",
            "secrets in evidence",
            "PHI in evidence",
            "restore duration not recorded",
        ),
        "backup restore risk register",
        min_rows=10,
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_launch_backup_restore_drill_v2.py",
            "commercial launch backup restore drill v2 validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_launch_backup_restore_drill_v2.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial launch backup restore drill v2: runbook, checklist, evidence, commands and risk register are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
