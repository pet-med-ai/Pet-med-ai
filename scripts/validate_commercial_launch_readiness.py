#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REVIEW = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_READINESS_REVIEW_V1.md"
CHECKLIST = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_READINESS_CHECKLIST.csv"
RISKS = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_RISK_REGISTER.csv"
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


def require_csv(path: Path, required_columns: tuple[str, ...], needles: tuple[str, ...], label: str) -> int:
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

    if len(rows) < 5:
        return fail(f"{label} should contain meaningful launch rows")
    return 0


def main() -> int:
    py_compile.compile(str(Path(__file__)), doraise=True)

    rc = require_text(
        REVIEW,
        (
            "Commercial Launch Readiness Review V1",
            "database_revision == alembic_head",
            "database_revision == 0008_auto_delivery",
            "schema_ok=true",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
            "ENABLE_EMR_REAL_IMPORT=false",
            "NO-GO",
            "Commercial Launch Feature Scope Lock V1",
            "does not",
            "send external messages",
        ),
        "readiness review doc",
    )
    if rc:
        return rc

    rc = require_csv(
        CHECKLIST,
        (
            "area",
            "item",
            "required_state",
            "evidence_command",
            "go_no_go",
            "owner",
            "status",
            "notes",
        ),
        (
            "database_revision expected value",
            "0008_auto_delivery",
            "schema_ok",
            "Online smoke",
            "Automated reminder real sending disabled",
            "EMR real import disabled",
            "Cross-user case isolation",
            "Backup rollback evidence",
            "Consent and AI notice reviewed",
        ),
        "readiness checklist",
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
            "CLR-R001",
            "database_revision mismatch",
            "automated reminder live sending enabled",
            "EMR real import enabled",
            "cross-user data access",
            "secret leak",
            "legal consent missing",
        ),
        "risk register",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_launch_readiness.py",
            "commercial launch readiness validation",
            "database_revision",
            "0008_auto_delivery",
            "alembic_head",
            "FRONTEND_URL",
            "frontend live",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_launch_readiness.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial launch readiness review: docs, checklist, risk register and CI/smoke hooks are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
