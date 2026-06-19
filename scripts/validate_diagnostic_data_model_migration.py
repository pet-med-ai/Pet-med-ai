#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

MIGRATION = ROOT / "backend" / "migrations" / "versions" / "0009_diag_data.py"
MODELS = ROOT / "backend" / "models.py"
DOC = ROOT / "docs" / "clinical_data" / "DIAGNOSTIC_DATA_MODEL_MIGRATION_V1.md"

EXPECTED_TABLE_COLUMNS = {
    "diagnostic_reports": {
        "id", "case_id", "report_type", "source_type", "source_system", "source_report_id",
        "status", "title", "report_text", "abnormal_summary", "ai_summary",
        "ai_summary_status", "ordering_clinician", "reviewed_by", "reviewed_at",
        "attachment_ref", "metadata_json", "created_at", "updated_at",
    },
    "observations": {
        "id", "case_id", "diagnostic_report_id", "code", "display_name",
        "value_text", "value_numeric", "value_type", "unit", "reference_low",
        "reference_high", "reference_text", "abnormal_flag", "interpretation",
        "specimen_type", "collected_at", "observed_at", "source_type",
        "review_status", "metadata_json", "created_at", "updated_at",
    },
    "imaging_studies": {
        "id", "case_id", "modality", "body_part", "taken_at", "is_planned_review",
        "tag", "report_url", "viewer_url", "thumbnail_url", "metadata", "created_at",
        "study_uid", "accession_number", "source_type", "source_system", "report_text",
        "abnormal_flag", "ai_summary", "ai_summary_status", "review_status",
        "reviewed_by", "reviewed_at", "attachment_ref", "updated_at",
    },
}

EXPECTED_INDEXES = {
    "ix_diag_reports_case_id",
    "ix_diag_reports_status",
    "ix_diag_reports_source",
    "ix_diag_reports_ai_status",
    "ix_observations_case_id",
    "ix_observations_report_id",
    "ix_observations_code",
    "ix_observations_abnormal",
    "ix_observations_review",
    "ix_img_studies_source",
    "ix_img_studies_review",
    "ix_img_studies_abnormal",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> int:
    if not MIGRATION.exists():
        fail("missing migration: backend/migrations/versions/0009_diag_data.py")
    if not MODELS.exists():
        fail("missing backend/models.py")
    if not DOC.exists():
        fail("missing diagnostic data model migration doc")

    migration_text = MIGRATION.read_text(encoding="utf-8")
    models_text = MODELS.read_text(encoding="utf-8")
    doc_text = DOC.read_text(encoding="utf-8")

    if 'revision = "0009_diag_data"' not in migration_text:
        fail("0009 migration revision id mismatch")
    if 'down_revision = "0008_auto_delivery"' not in migration_text:
        fail("0009 migration must chain from 0008_auto_delivery")
    if len("0009_diag_data") > 32:
        fail("revision id too long")
    if 'op.create_table(\n        "imaging_studies"' in migration_text:
        fail("0009 must not create imaging_studies; it already exists from 0002")

    for required in ('"diagnostic_reports"', '"observations"', '"imaging_studies"'):
        if required not in migration_text:
            fail(f"0009 migration missing marker: {required}")

    for idx in EXPECTED_INDEXES:
        if idx not in migration_text and idx not in models_text:
            fail(f"missing expected short index: {idx}")
        if len(idx) > 63:
            fail(f"index name too long: {idx}")

    for class_name in ("DiagnosticReport", "Observation", "ImagingStudy"):
        if not re.search(rf"class\s+{class_name}\s*\(Base\)", models_text):
            fail(f"models.py missing class {class_name}")

    try:
        from db import Base  # type: ignore
        import models  # noqa: F401
    except Exception as exc:
        fail(f"failed to import backend models: {exc}")

    for table_name, expected_columns in EXPECTED_TABLE_COLUMNS.items():
        table = Base.metadata.tables.get(table_name)
        if table is None:
            fail(f"missing table on metadata: {table_name}")
        columns = set(table.columns.keys())
        missing = sorted(expected_columns - columns)
        if missing:
            fail(f"{table_name} missing columns: {missing}")

    try:
        tree = ast.parse(migration_text)
    except SyntaxError as exc:
        fail(f"migration syntax error: {exc}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if value.startswith(("ix_", "uq_", "fk_", "ck_")) and len(value) > 63:
                fail(f"identifier exceeds PostgreSQL 63 char limit: {value}")

    for phrase in (
        "ImagingStudy already exists",
        "revision=0009_diag_data",
        "down_revision=0008_auto_delivery",
        "real lab equipment ingest",
        "real DICOM / PACS ingest",
    ):
        if phrase not in doc_text:
            fail(f"migration doc missing phrase: {phrase}")

    print("PASS: Diagnostic data model migration V1 ORM, Alembic migration and validation markers are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
