#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MODEL_FILE = BACKEND / "models.py"
MIGRATION_FILE = BACKEND / "migrations" / "versions" / "0008_automated_delivery.py"
DOC = ROOT / "docs" / "preventive_care" / "AUTOMATED_REMINDER_DELIVERY_DATA_MODEL_V1.md"
ALEMBIC_VALIDATOR = ROOT / "scripts" / "validate_alembic_setup.py"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"

EXPECTED_TABLES = {
    "automated_reminder_delivery_templates",
    "automated_reminder_delivery_attempts",
    "automated_reminder_delivery_receipts",
    "automated_reminder_delivery_suppression_rules",
}

EXPECTED_COLUMNS = {
    "automated_reminder_delivery_templates": {
        "id", "template_key", "template_version", "channel", "language", "category",
        "subject", "body", "clinical_safety_text", "opt_out_text", "review_status",
        "approved_by", "approved_at", "metadata", "created_at", "updated_at",
    },
    "automated_reminder_delivery_attempts": {
        "delivery_id", "owner_id", "reminder_id", "notification_id", "channel",
        "template_key", "template_version", "eligibility_result", "blocked_reason", "status",
        "manual_review_required", "approved_by", "approved_at", "dry_run", "auto_send",
        "sends_external_message", "consent_snapshot", "opt_out_snapshot",
        "contact_destination_hash", "message_hash", "provider_name", "provider_message_id",
        "attempt_count", "last_error", "queued_at", "sent_at", "delivered_at", "failed_at",
        "canceled_at", "metadata", "created_at", "updated_at",
    },
    "automated_reminder_delivery_receipts": {
        "receipt_id", "delivery_id", "provider_name", "provider_message_id", "event_type",
        "status", "received_at", "signature_verified", "idempotency_key", "raw_payload_hash",
        "failure_code", "failure_reason", "metadata", "created_at",
    },
    "automated_reminder_delivery_suppression_rules": {
        "id", "owner_id", "reminder_id", "notification_id", "pet_id", "category", "channel",
        "reason", "active", "starts_at", "ends_at", "created_by", "note",
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
    for path in (MODEL_FILE, MIGRATION_FILE, DOC, ALEMBIC_VALIDATOR):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        MODEL_FILE,
        (
            "class AutomatedReminderDeliveryTemplate(Base):",
            "class AutomatedReminderDeliveryAttempt(Base):",
            "class AutomatedReminderDeliveryReceipt(Base):",
            "class AutomatedReminderDeliverySuppressionRule(Base):",
            "__tablename__ = \"automated_reminder_delivery_attempts\"",
            "manual_review_required",
            "auto_send",
            "sends_external_message",
            "dry_run",
            "provider_message_id",
        ),
        "backend/models.py",
    )
    if rc:
        return rc

    rc = require_text(
        MIGRATION_FILE,
        (
            'revision = "0008_auto_delivery"',
            'down_revision = "0007_preventive_care"',
            "op.create_table(",
            "automated_reminder_delivery_templates",
            "automated_reminder_delivery_attempts",
            "automated_reminder_delivery_receipts",
            "automated_reminder_delivery_suppression_rules",
            "manual_review_required",
            "sends_external_message",
        ),
        "automated delivery migration",
    )
    if rc:
        return rc

    if len("0008_auto_delivery") > 32:
        return fail("automated delivery Alembic revision id exceeds 32 chars")

    rc = require_text(
        ALEMBIC_VALIDATOR,
        (
            "0008_automated_delivery.py",
            "automated_reminder_delivery_templates",
            "automated_reminder_delivery_attempts",
            "automated_reminder_delivery_receipts",
            "automated_reminder_delivery_suppression_rules",
        ),
        "validate_alembic_setup.py",
    )
    if rc:
        return rc

    sys.path.insert(0, str(BACKEND))
    from db import Base  # noqa: WPS433
    import models  # noqa: F401,WPS433

    tables = Base.metadata.tables
    missing_tables = sorted(EXPECTED_TABLES - set(tables.keys()))
    if missing_tables:
        return fail(f"SQLAlchemy metadata missing automated delivery tables: {missing_tables}")

    for table_name, expected in EXPECTED_COLUMNS.items():
        actual = set(tables[table_name].columns.keys())
        missing = sorted(expected - actual)
        if missing:
            return fail(f"{table_name} missing columns: {missing}; actual={sorted(actual)}")

    rc = require_text(
        DOC,
        (
            "Automated Reminder Delivery Data Model V1",
            "AutomatedReminderDeliveryAttempt",
            "0008_auto_delivery",
            "auto_send=false",
            "sends_external_message=false",
            "manual_review_required=true",
            "executes_real_import=false",
        ),
        "automated delivery data model doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_automated_reminder_delivery_model.py",
            "automated reminder delivery data model validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_automated_reminder_delivery_model.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK automated reminder delivery data model: ORM metadata and Alembic 0008 migration are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
