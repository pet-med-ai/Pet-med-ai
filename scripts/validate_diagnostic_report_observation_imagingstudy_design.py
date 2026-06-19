#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "clinical_data"

REQUIRED_FILES = [
    DOCS / "DIAGNOSTIC_REPORT_OBSERVATION_IMAGINGSTUDY_DESIGN_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_ENTITY_RELATIONSHIP_V1.md",
    DOCS / "DIAGNOSTIC_REPORT_SCHEMA_DESIGN_V1.csv",
    DOCS / "OBSERVATION_SCHEMA_DESIGN_V1.csv",
    DOCS / "IMAGING_STUDY_SCHEMA_DESIGN_V1.csv",
    DOCS / "DIAGNOSTIC_DATA_MODEL_STATUS_WORKFLOW_V1.csv",
    DOCS / "DIAGNOSTIC_DATA_MODEL_SOURCE_TYPE_POLICY_V1.csv",
    DOCS / "DIAGNOSTIC_DATA_MODEL_AI_SUMMARY_BOUNDARY_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_READONLY_API_PLAN_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_DRY_RUN_FIXTURES_PLAN_V1.md",
    DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_READINESS_CHECKLIST.csv",
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

def require_fields(path: Path, fields: set[str]) -> None:
    rows = require_columns(path, ("field_name", "type_candidate", "required", "unique", "indexed", "purpose", "notes"))
    found = {row.get("field_name", "") for row in rows}
    missing = sorted(fields - found)
    if missing:
        fail(f"{path.relative_to(ROOT)} missing schema fields: {missing}")

def main() -> int:
    for path in REQUIRED_FILES:
        require_file(path)

    require_phrases(
        DOCS / "DIAGNOSTIC_REPORT_OBSERVATION_IMAGINGSTUDY_DESIGN_V1.md",
        (
            "DiagnosticReport",
            "Observation",
            "ImagingStudy",
            "不新增 Alembic migration",
            "GO_TO_DIAGNOSTIC_DATA_MODEL_MIGRATION_READINESS_REVIEW_V1",
        ),
    )

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_ENTITY_RELATIONSHIP_V1.md",
        (
            "Case",
            "DiagnosticReport",
            "Observation",
            "ImagingStudy",
            "owner-scope",
        ),
    )

    require_fields(
        DOCS / "DIAGNOSTIC_REPORT_SCHEMA_DESIGN_V1.csv",
        {"case_id", "report_type", "source_type", "status", "report_text", "ai_summary", "ai_summary_status", "attachment_ref"},
    )
    require_fields(
        DOCS / "OBSERVATION_SCHEMA_DESIGN_V1.csv",
        {"case_id", "diagnostic_report_id", "display_name", "value_numeric", "unit", "reference_low", "reference_high", "abnormal_flag", "review_status"},
    )
    require_fields(
        DOCS / "IMAGING_STUDY_SCHEMA_DESIGN_V1.csv",
        {"case_id", "modality", "body_region", "study_uid", "report_text", "ai_summary", "ai_summary_status", "review_status", "attachment_ref"},
    )

    status_rows = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_STATUS_WORKFLOW_V1.csv",
        ("entity", "status", "meaning", "allowed_next", "clinical_gate", "notes"),
    )
    status_text = "\\n".join(row.get("status", "") for row in status_rows)
    for status in ("draft", "review_pending", "reviewed", "final", "amended", "voided"):
        if status not in status_text:
            fail(f"status workflow missing status: {status}")

    source_rows = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_SOURCE_TYPE_POLICY_V1.csv",
        ("source_type", "allowed_in_design_v1", "real_ingest", "requires_risk_review", "purpose", "notes"),
    )
    source_text = "\\n".join(row.get("source_type", "") + row.get("notes", "") for row in source_rows)
    for source in ("manual", "emr_dry_run", "lab_device_dry_run", "imaging_gateway_dry_run", "dicom_dry_run"):
        if source not in source_text:
            fail(f"source policy missing source: {source}")

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_AI_SUMMARY_BOUNDARY_V1.md",
        (
            "AI 可以生成异常摘要草稿",
            "不能替代医生最终诊断",
            "not_generated",
            "draft",
            "reviewed",
            "rejected",
        ),
    )

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_READONLY_API_PLAN_V1.md",
        (
            "read-only",
            "dry-run",
            "user B cannot read user A",
            "must not write database",
        ),
    )

    require_phrases(
        DOCS / "DIAGNOSTIC_DATA_MODEL_DRY_RUN_FIXTURES_PLAN_V1.md",
        (
            "CBC panel",
            "Biochemistry panel",
            "X-ray report metadata",
            "真实客户姓名",
        ),
    )

    checklist = require_columns(
        DOCS / "DIAGNOSTIC_DATA_MODEL_MIGRATION_READINESS_CHECKLIST.csv",
        ("check_id", "area", "item", "required_state", "actual_state", "owner", "status", "notes"),
    )
    if len(checklist) < 10:
        fail("migration readiness checklist should include at least 10 rows")
    if not any(row.get("check_id") == "DMR-001" for row in checklist):
        fail("migration readiness checklist missing DMR-001")

    print("PASS: DiagnosticReport / Observation / ImagingStudy Design V1 files are present and structurally valid")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
