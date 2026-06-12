#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MODEL_FILE = BACKEND / "models.py"
MIGRATION_FILE = BACKEND / "migrations" / "versions" / "0007_preventive_care.py"
DOC = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_REMINDER_DATA_MODEL_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"

EXPECTED_TABLES = {
    "preventive_care_rule_sets",
    "preventive_care_reminders",
    "preventive_care_events",
    "preventive_care_client_preferences",
    "preventive_care_notification_queue",
}

EXPECTED_COLUMNS = {
    "preventive_care_rule_sets": {
        "rule_id", "species", "life_stage", "category", "trigger_basis",
        "interval_days", "due_window_days", "lead_days",
        "requires_clinician_confirmation", "requires_client_consent", "allow_auto_send",
        "recommended_stage", "source_note", "note", "metadata", "created_at", "updated_at",
    },
    "preventive_care_reminders": {
        "reminder_id", "owner_id", "case_id", "pet_id", "pet_name", "species", "category",
        "rule_id", "source_rule_id", "status", "due_date", "due_window_start", "due_window_end",
        "reminder_lead_days", "last_completed_at", "next_due_date",
        "clinician_override", "override_reason", "client_opt_out", "channel_preference",
        "note", "metadata", "created_at", "updated_at",
    },
    "preventive_care_events": {
        "event_id", "reminder_id", "owner_id", "case_id", "pet_id", "event_type", "category",
        "event_date", "product_name", "lot_number", "next_due_date", "clinician_id",
        "note", "metadata", "created_at",
    },
    "preventive_care_client_preferences": {
        "id", "owner_id", "allow_in_app", "allow_sms", "allow_wechat", "allow_email",
        "opt_out_all", "preferred_channel", "updated_by", "note", "metadata", "created_at", "updated_at",
    },
    "preventive_care_notification_queue": {
        "notification_id", "reminder_id", "owner_id", "case_id", "channel", "status",
        "scheduled_for", "sent_at", "manual_review_required", "reviewed_by",
        "client_opt_out_snapshot", "message_preview", "failure_code", "failure_reason",
        "metadata", "created_at", "updated_at",
    },
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


def main() -> int:
    for path in (MODEL_FILE, MIGRATION_FILE, DOC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        MODEL_FILE,
        (
            "class PreventiveCareRuleSet(Base):",
            "class PreventiveCareReminder(Base):",
            "class PreventiveCareEvent(Base):",
            "class PreventiveCareClientPreference(Base):",
            "class PreventiveCareNotificationQueue(Base):",
            "__tablename__ = \"preventive_care_reminders\"",
            "allow_auto_send",
            "manual_review_required",
            "client_opt_out",
        ),
        "backend/models.py",
    )
    if rc:
        return rc

    rc = require_text(
        MIGRATION_FILE,
        (
            'revision = "0007_preventive_care"',
            'down_revision = "0006_emr_import_results"',
            "op.create_table(",
            "preventive_care_rule_sets",
            "preventive_care_reminders",
            "preventive_care_events",
            "preventive_care_client_preferences",
            "preventive_care_notification_queue",
            "allow_auto_send",
            "manual_review_required",
        ),
        "preventive care migration",
    )
    if rc:
        return rc

    if len("0007_preventive_care") > 32:
        return fail("preventive care Alembic revision id exceeds 32 chars")

    sys.path.insert(0, str(BACKEND))
    from db import Base  # noqa: WPS433
    import models  # noqa: F401,WPS433

    tables = Base.metadata.tables
    missing_tables = sorted(EXPECTED_TABLES - set(tables.keys()))
    if missing_tables:
        return fail(f"SQLAlchemy metadata missing preventive care tables: {missing_tables}")

    for table_name, expected in EXPECTED_COLUMNS.items():
        actual = set(tables[table_name].columns.keys())
        missing = sorted(expected - actual)
        if missing:
            return fail(f"{table_name} missing columns: {missing}; actual={sorted(actual)}")

    rc = require_text(
        DOC,
        (
            "Preventive Care Reminder Data Model V1",
            "PreventiveCareReminder",
            "preventive_care_notification_queue",
            "allow_auto_send=false",
            "manual_review_required=true",
            "executes_real_import=false",
        ),
        "preventive care data model doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_preventive_care_reminder_model.py",
            "preventive care reminder data model validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_preventive_care_reminder_model.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK preventive care reminder data model: ORM metadata and Alembic 0007 migration are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
