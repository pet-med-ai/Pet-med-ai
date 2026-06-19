#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "clinical_data"

REQUIRED_FILES = [
    DOCS / "DIAGNOSTIC_DATA_MODEL_GAP_REVIEW_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_GAP_CHECKLIST.csv",
    DOCS / "DIAGNOSTIC_REPORT_FIELD_CANDIDATES_V1.csv",
    DOCS / "OBSERVATION_FIELD_CANDIDATES_V1.csv",
    DOCS / "IMAGING_STUDY_FIELD_CANDIDATES_V1.csv",
    DOCS / "DIAGNOSTIC_DATA_MODEL_RISK_REGISTER_V1.csv",
    DOCS / "DIAGNOSTIC_DATA_MODEL_NEXT_STAGE_RECOMMENDATION_V1.csv",
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

def require_phrases(path: Path, phrases: tuple[str, ...]) -> None:
    text = require_file(path)
    for phrase in phrases:
        if phrase not in text:
            fail(f"{path.relative_to(ROOT)} missing phrase: {phrase}")

def main() -> int:
    for path in REQUIRED_FILES:
        require_file(path)

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_GAP_REVIEW_V1.md",
        (
            "Diagnostic Data Model Gap Review V1",
            "DiagnosticReport",
            "Observation",
            "ImagingStudy",
            "Case",
            "AI abnormal summary",
            "no Alembic migration",
            "no real device ingest",
            "GO_TO_DIAGNOSTIC_REPORT_OBSERVATION_IMAGINGSTUDY_DESIGN_V1",
        ),
    )

    checklist = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_GAP_CHECKLIST.csv",
        ("check_id", "area", "item", "required_state", "actual_state", "evidence", "owner", "go_no_go", "status", "notes"),
    )
    required_checks = {f"DDM-GAP-{i:03d}" for i in range(1, 13)}
    found_checks = {row.get("check_id", "") for row in checklist}
    missing = sorted(required_checks - found_checks)
    if missing:
        fail(f"gap checklist missing checks: {missing}")
    for row in checklist:
        if row.get("go_no_go") == "GO_REQUIRED" and row.get("status") != "PASS":
            fail(f"required checklist row not PASS: {row.get('check_id')}")

    field_columns = ("field_name", "type_candidate", "required_candidate", "purpose", "notes")
    report_rows = require_columns(DOCS / "DIAGNOSTIC_REPORT_FIELD_CANDIDATES_V1.csv", field_columns)
    observation_rows = require_columns(DOCS / "OBSERVATION_FIELD_CANDIDATES_V1.csv", field_columns)
    imaging_rows = require_columns(DOCS / "IMAGING_STUDY_FIELD_CANDIDATES_V1.csv", field_columns)

    for label, rows, required_fields in (
        ("DiagnosticReport", report_rows, {"case_id", "report_type", "source_type", "status", "report_text", "ai_summary_status"}),
        ("Observation", observation_rows, {"case_id", "diagnostic_report_id", "display_name", "value_type", "unit", "abnormal_flag"}),
        ("ImagingStudy", imaging_rows, {"case_id", "modality", "source_type", "report_text", "ai_summary_status", "review_status"}),
    ):
        found = {row.get("field_name", "") for row in rows}
        missing_fields = sorted(required_fields - found)
        if missing_fields:
            fail(f"{label} missing candidate fields: {missing_fields}")

    risks = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_RISK_REGISTER_V1.csv",
        ("risk_id", "area", "severity", "risk", "mitigation", "owner", "status", "notes"),
    )
    if len(risks) < 8:
        fail("risk register should include at least 8 risks")
    risk_text = "\\n".join(row.get("risk", "") + " " + row.get("mitigation", "") for row in risks)
    for phrase in ("AI abnormal summary", "PHI", "real ingest", "Cross-user"):
        if phrase not in risk_text:
            fail(f"risk register missing coverage: {phrase}")

    recs = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_NEXT_STAGE_RECOMMENDATION_V1.csv",
        ("recommendation_id", "current_stage", "decision", "next_stage", "allowed_next_outputs", "blocked_next_outputs", "owner", "notes"),
    )
    rec = recs[0]
    if rec.get("decision") != "GO_TO_DIAGNOSTIC_REPORT_OBSERVATION_IMAGINGSTUDY_DESIGN_V1":
        fail("next-stage decision is not locked")
    if "no migration" not in rec.get("blocked_next_outputs", ""):
        fail("next-stage recommendation must block migration")

    print("PASS: Diagnostic Data Model Gap Review V1 files are present and structurally valid")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
