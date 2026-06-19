#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "clinical_data"

REQUIRED_FILES = [
    DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_READINESS_REVIEW_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_READINESS_CHECKLIST_V1.csv",
    DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_RISK_REGISTER_V1.csv",
    DOCS / "DIAGNOSTIC_DATA_MODEL_ALEMBIC_PLAN_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_ROLLBACK_PLAN_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_SMOKE_COVERAGE_PLAN_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_GO_NO_GO_V1.csv",
]

def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)

def require_file(path: Path) -> str:
    if not path.exists():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    if path.stat().st_size <= 0:
        fail(f"empty required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")

def require_phrases(path: Path, phrases: tuple[str, ...]) -> None:
    text = require_file(path)
    for phrase in phrases:
        if phrase not in text:
            fail(f"{path.relative_to(ROOT)} missing phrase: {phrase}")

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def require_columns(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    rows = read_csv(path)
    if not rows:
        fail(f"{path.relative_to(ROOT)} has no rows")
    missing = [c for c in columns if c not in rows[0]]
    if missing:
        fail(f"{path.relative_to(ROOT)} missing columns: {missing}")
    return rows

def main() -> int:
    for path in REQUIRED_FILES:
        require_file(path)

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_READINESS_REVIEW_V1.md",
        (
            "Diagnostic Data Model Migration Readiness Review V1",
            "不新增 Alembic migration",
            "DiagnosticReport",
            "Observation",
            "ImagingStudy",
            "GO_TO_DIAGNOSTIC_DATA_MODEL_MIGRATION_V1",
            "NO_GO_REWORK_DESIGN_OR_READINESS",
        ),
    )

    checklist = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_READINESS_CHECKLIST_V1.csv",
        ("check_id", "area", "item", "required_state", "actual_state", "evidence", "owner", "go_no_go", "status", "notes"),
    )
    required = {f"DMR-{i:03d}" for i in range(1, 21)}
    found = {row.get("check_id", "") for row in checklist}
    missing = sorted(required - found)
    if missing:
        fail(f"readiness checklist missing checks: {missing}")
    for row in checklist:
        if row.get("go_no_go") == "GO_REQUIRED" and row.get("status") != "PASS":
            fail(f"readiness checklist required row not PASS: {row.get('check_id')}")

    risks = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_RISK_REGISTER_V1.csv",
        ("risk_id", "area", "severity", "risk", "mitigation", "owner", "status", "notes"),
    )
    if len(risks) < 10:
        fail("risk register must include at least 10 risks")
    risk_text = "\\n".join(row.get("risk", "") + " " + row.get("mitigation", "") for row in risks)
    for phrase in ("revision id too long", "identifier name exceeds 63", "Cross-user", "AI summary", "real ingest"):
        if phrase not in risk_text:
            fail(f"risk register missing phrase: {phrase}")

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_ALEMBIC_PLAN_V1.md",
        (
            "0009_diag_data",
            "0008_auto_delivery",
            "diagnostic_reports",
            "observations",
            "imaging_studies",
            "ix_diag_reports_case_id",
            "ix_observations_report_id",
            "ix_imaging_studies_case_id",
            "63",
        ),
    )

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_ROLLBACK_PLAN_V1.md",
        (
            "alembic downgrade 0008_auto_delivery",
            "database_revision=0008_auto_delivery",
            "schema_ok=true",
            "No PHI",
        ),
    )

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_SMOKE_COVERAGE_PLAN_V1.md",
        (
            "system version",
            "schema_ok=true",
            "feature flags remain disabled",
            "user B cannot read user A diagnostic data",
            "AI summary remains draft",
        ),
    )

    decisions = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_GO_NO_GO_V1.csv",
        ("decision_id", "stage", "decision", "next_stage", "required_state", "actual_state", "owner", "signoff_status", "notes"),
    )
    decision = decisions[0]
    if decision.get("decision") != "GO_TO_DIAGNOSTIC_DATA_MODEL_MIGRATION_V1":
        fail("go/no-go decision must be GO_TO_DIAGNOSTIC_DATA_MODEL_MIGRATION_V1")
    if decision.get("signoff_status") != "signed":
        fail("go/no-go signoff_status must be signed")
    if "real ingest remains blocked" not in decision.get("notes", ""):
        fail("go/no-go notes must keep real ingest blocked")

    print("PASS: Diagnostic Data Model Migration Readiness Review V1 files are present and structurally valid")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
