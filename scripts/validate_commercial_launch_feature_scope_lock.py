#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCOPE_DOC = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_FEATURE_SCOPE_LOCK_V1.md"
FEATURE_MATRIX = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_FEATURE_MATRIX.csv"
ROUTE_MATRIX = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_ROUTE_VISIBILITY_MATRIX.csv"
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


def validate_app_scope_lock() -> int:
    if not APP.exists():
        return fail(f"missing file: {APP.relative_to(ROOT)}")

    text = APP.read_text(encoding="utf-8")

    if 'path="/automated-reminder-delivery/manual-approval"' not in text:
        return fail("App route for automated reminder manual approval should remain documented until Access Review handles route authorization")

    if 'to="/automated-reminder-delivery/manual-approval"' in text:
        return fail("Automated Reminder Delivery manual approval must not be exposed in default clinic navigation")

    if "Commercial Launch Feature Scope Lock V1" not in text:
        return fail("App.jsx should include a scope-lock comment explaining why the manual approval nav link is hidden")

    return 0


def main() -> int:
    py_compile.compile(str(Path(__file__)), doraise=True)

    rc = require_text(
        SCOPE_DOC,
        (
            "Commercial Launch Feature Scope Lock V1",
            "public_clinic",
            "clinic_staff",
            "clinic_admin",
            "internal_admin",
            "internal_dry_run",
            "hidden_paused",
            "future_not_in_v1",
            "AI consultation",
            "Clinical Docs Word export",
            "preventive care in-app reminders",
            "Automated Reminder Delivery manual approval",
            "EMR real import execution",
            "true SMS provider",
            "Do not treat UI hiding as a security boundary",
            "Commercial Launch User Roles / Access Review V1",
        ),
        "feature scope lock doc",
    )
    if rc:
        return rc

    rc = require_csv(
        FEATURE_MATRIX,
        (
            "feature_id",
            "area",
            "feature_name",
            "commercial_v1_status",
            "visible_to",
            "frontend_surface",
            "backend_surface",
            "data_writes",
            "external_effect",
            "launch_decision",
            "notes",
        ),
        (
            "FS-AI-001",
            "AI consultation",
            "FS-CASE-001",
            "Case create/list/detail/edit",
            "FS-PREV-002",
            "Front-desk manual contact queue",
            "FS-EMR-004",
            "EMR real import execution",
            "FS-ARD-002",
            "Automated delivery manual approval UI",
            "hidden_paused",
            "future_not_in_v1",
        ),
        "feature matrix",
        min_rows=20,
    )
    if rc:
        return rc

    rc = require_csv(
        ROUTE_MATRIX,
        (
            "route",
            "component",
            "current_surface",
            "commercial_v1_status",
            "visible_to",
            "required_action_v1",
            "next_access_review_action",
            "notes",
        ),
        (
            "/",
            "/cases/:id",
            "/preventive-care/notification-queue",
            "/automated-reminder-delivery/manual-approval",
            "internal_dry_run",
            "remove from default clinic navigation",
            "add internal/admin guard",
        ),
        "route visibility matrix",
        min_rows=8,
    )
    if rc:
        return rc

    rc = validate_app_scope_lock()
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_launch_feature_scope_lock.py",
            "commercial launch feature scope lock validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_launch_feature_scope_lock.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial launch feature scope lock: feature matrix, route visibility matrix, and navigation hiding are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
