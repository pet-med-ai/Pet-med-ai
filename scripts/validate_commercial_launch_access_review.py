#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REVIEW = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_ACCESS_REVIEW_V1.md"
ACCESS_MATRIX = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_ACCESS_MATRIX.csv"
ROUTE_MATRIX = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_ROUTE_ACCESS_MATRIX.csv"
IDOR_TESTS = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_IDOR_TEST_PLAN.csv"
EVIDENCE = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_ACCESS_REVIEW_EVIDENCE_TEMPLATE.csv"
MAIN = ROOT / "backend" / "main.py"
PREVENTIVE = ROOT / "backend" / "preventive_care_api.py"
AUTOMATED = ROOT / "backend" / "automated_reminder_delivery_api.py"
APP = ROOT / "frontend" / "src" / "App.jsx"
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


def validate_existing_owner_scopes() -> int:
    rc = require_text(
        MAIN,
        (
            "def get_owned_case_or_404",
            "Case.owner_id == user.id",
            "query = db.query(Case).filter(Case.owner_id == user.id)",
            "get_current_user",
            "assert_consult_session_access",
            "owner_id",
            "raise HTTPException(status_code=404",
        ),
        "backend/main.py owner-scoped case/session access",
    )
    if rc:
        return rc

    rc = require_text(
        PREVENTIVE,
        (
            "def _case_or_404",
            "def _reminder_or_404",
            "owner_id",
            "_user_id(user)",
            "raise HTTPException(status_code=404",
            '"sends_external_message": False',
        ),
        "backend/preventive_care_api.py owner-scoped preventive care access",
    )
    if rc:
        return rc

    rc = require_text(
        AUTOMATED,
        (
            "def _reminder_or_404",
            "def _notification_or_404",
            "def _attempt_or_404",
            "owner_id",
            "_user_id(user)",
            '"auto_send": False',
            '"sends_external_message": False',
            '"executes_real_import": False',
        ),
        "backend/automated_reminder_delivery_api.py owner-scoped automated delivery access",
    )
    if rc:
        return rc

    return 0


def validate_route_scope_notes() -> int:
    if not APP.exists():
        return fail(f"missing file: {APP.relative_to(ROOT)}")
    text = APP.read_text(encoding="utf-8")

    if 'path="/automated-reminder-delivery/manual-approval"' not in text:
        return fail("manual approval route should remain visible to access review until proper route guard is implemented")

    if 'to="/automated-reminder-delivery/manual-approval"' in text:
        return fail("manual approval must not be visible in default clinic navigation after Feature Scope Lock V1")

    return 0


def main() -> int:
    py_compile.compile(str(Path(__file__)), doraise=True)

    rc = require_text(
        REVIEW,
        (
            "Commercial Launch User Roles / Access Review V1",
            "authenticated owner-scoped user model",
            "User B must not be able",
            "IDOR",
            "UI hiding is not an authorization boundary",
            "full RBAC is not yet implemented",
            "Final commercial launch is approved",
            "EMR real import",
            "Automated Reminder Delivery manual approval",
        ),
        "access review doc",
    )
    if rc:
        return rc

    rc = require_csv(
        ACCESS_MATRIX,
        (
            "role",
            "description",
            "allowed_commercial_v1",
            "forbidden_commercial_v1",
            "notes",
        ),
        (
            "anonymous",
            "clinic_user",
            "clinician",
            "front_desk",
            "clinic_admin",
            "internal_admin",
            "release_owner",
            "security_owner",
        ),
        "access matrix",
        min_rows=8,
    )
    if rc:
        return rc

    rc = require_csv(
        ROUTE_MATRIX,
        (
            "route",
            "component",
            "commercial_v1_class",
            "target_roles",
            "current_action",
            "final_go_requirement",
            "risk",
        ),
        (
            "/cases/:id",
            "/preventive-care/notification-queue",
            "/ops",
            "/webhooks/emr/inbox",
            "/emr/import-batches",
            "/automated-reminder-delivery/manual-approval",
            "/api/system/feature-flags",
        ),
        "route access matrix",
        min_rows=10,
    )
    if rc:
        return rc

    rc = require_csv(
        IDOR_TESTS,
        (
            "test_id",
            "area",
            "setup",
            "attacker_action",
            "expected_result",
            "owner",
            "status",
            "notes",
        ),
        (
            "IDOR-CASE-001",
            "IDOR-CONSULT-001",
            "IDOR-PREV-001",
            "IDOR-ARD-001",
            "IDOR-EMR-001",
            "IDOR-OPS-001",
        ),
        "IDOR test plan",
        min_rows=15,
    )
    if rc:
        return rc

    rc = require_csv(
        EVIDENCE,
        (
            "review_id",
            "date",
            "reviewer",
            "base_url",
            "frontend_url",
            "git_commit",
            "ci_static_pass",
            "online_smoke_pass",
            "schema_ok",
            "database_revision",
            "alembic_head",
            "case_idor_pass",
            "consult_session_idor_pass",
            "preventive_care_idor_pass",
            "automated_delivery_idor_pass",
            "admin_route_review_pass",
            "open_p0_count",
            "open_p1_count",
            "decision",
            "notes",
        ),
        (
            "ACCESS-REVIEW-V1",
            "NO-GO by default",
        ),
        "access review evidence template",
        min_rows=1,
    )
    if rc:
        return rc

    rc = validate_existing_owner_scopes()
    if rc:
        return rc

    rc = validate_route_scope_notes()
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_launch_access_review.py",
            "commercial launch access review validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_launch_access_review.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial launch access review: role matrix, route matrix, IDOR plan and owner-scoped controls are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
