#!/usr/bin/env python3
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "clinical_data"

DOC = DOC_DIR / "DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_VERIFICATION_V1.md"
CHECKLIST = DOC_DIR / "DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_CHECKLIST_V1.csv"
SCHEMA_EVIDENCE = DOC_DIR / "DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_SCHEMA_EVIDENCE_V1.csv"
SMOKE_EVIDENCE = DOC_DIR / "DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_SMOKE_EVIDENCE_V1.csv"
GO_NO_GO = DOC_DIR / "DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_GO_NO_GO_V1.csv"

MIGRATION = ROOT / "backend" / "migrations" / "versions" / "0009_diag_data.py"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"

EXPECTED_FILES = (
    DOC,
    CHECKLIST,
    SCHEMA_EVIDENCE,
    SMOKE_EVIDENCE,
    GO_NO_GO,
    MIGRATION,
    SMOKE,
    CI_STATIC,
)

DANGEROUS_TRUE_MARKERS = (
    "ENABLE_EMR_REAL_IMPORT=true",
    "ENABLE_EMR_IMPORT_CASE_UPDATE=true",
    "ENABLE_EMR_ATTACHMENT_DOWNLOAD=true",
    "ENABLE_PREVENTIVE_AUTO_DELIVERY=true",
    "ENABLE_PREVENTIVE_SMS_DELIVERY=true",
    "ENABLE_PREVENTIVE_WECHAT_DELIVERY=true",
    "ENABLE_PREVENTIVE_EMAIL_DELIVERY=true",
    "ENABLE_PRESCRIPTION_STRUCTURED_WRITE=true",
    "ENABLE_DEVICE_REAL_INGEST=true",
    "ENABLE_BILLING_REAL_WRITE=true",
)

REQUIRED_DOC_PHRASES = (
    "Diagnostic Data Model Post-Migration Verification V1",
    "database_revision=0009_diag_data",
    "alembic_head=0009_diag_data",
    "schema_ok=true",
    "imaging_studies already existed from 0002_kpi_data_models",
    "0009 must not recreate imaging_studies",
    "diagnostic_reports",
    "observations",
    "imaging_studies additive columns",
    "dangerous feature flags remain disabled",
    "online smoke test still passes",
    "cross-user isolation still passes",
    "no real outbound messaging is enabled",
    "no real EMR write is enabled",
    "no real lab / DICOM / device ingest is enabled",
    "GO_TO_DIAGNOSTIC_DATA_READONLY_API_DRY_RUN_V1",
)

REQUIRED_CHECKLIST_IDS = {
    "PMV-001",
    "PMV-002",
    "PMV-003",
    "PMV-004",
    "PMV-005",
    "PMV-006",
    "PMV-007",
    "PMV-008",
    "PMV-009",
    "PMV-010",
    "PMV-011",
    "PMV-012",
    "PMV-013",
    "PMV-014",
    "PMV-015",
}

REQUIRED_SCHEMA_IDS = {
    "SCHEMA-001",
    "SCHEMA-002",
    "SCHEMA-003",
    "SCHEMA-004",
    "SCHEMA-005",
    "SCHEMA-006",
    "SCHEMA-007",
    "SCHEMA-008",
    "SCHEMA-009",
    "SCHEMA-010",
    "SCHEMA-011",
    "SCHEMA-012",
    "SCHEMA-013",
    "SCHEMA-014",
    "SCHEMA-015",
    "SCHEMA-016",
    "SCHEMA-017",
    "SCHEMA-018",
    "SCHEMA-019",
}

REQUIRED_SMOKE_IDS = {
    "SMOKE-001",
    "SMOKE-002",
    "SMOKE-003",
    "SMOKE-004",
    "SMOKE-005",
    "SMOKE-006",
    "SMOKE-007",
    "SMOKE-008",
    "SMOKE-009",
    "SMOKE-010",
    "SMOKE-011",
    "SMOKE-012",
}

REQUIRED_DECISION_IDS = {
    "GO-001",
    "GO-002",
    "GO-003",
    "GO-004",
    "GO-FINAL",
}

IMAGING_ADDITIVE_COLUMNS = {
    "study_uid",
    "accession_number",
    "source_type",
    "source_system",
    "report_text",
    "abnormal_flag",
    "ai_summary",
    "ai_summary_status",
    "review_status",
    "reviewed_by",
    "reviewed_at",
    "attachment_ref",
    "updated_at",
}


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_file(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"missing file: {rel(path)}")


def require_text(path: Path, phrases: tuple[str, ...]) -> None:
    text = read_text(path)
    for phrase in phrases:
        if phrase not in text:
            raise AssertionError(f"{rel(path)} missing required phrase: {phrase}")


def require_no_dangerous_true_markers(path: Path) -> None:
    text = read_text(path)
    for marker in DANGEROUS_TRUE_MARKERS:
        if marker in text:
            raise AssertionError(f"{rel(path)} must not contain dangerous enabled marker: {marker}")


def read_csv_rows(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    require_file(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(required_columns - columns)
        if missing:
            raise AssertionError(f"{rel(path)} missing columns: {missing}")
        rows = list(reader)
    if not rows:
        raise AssertionError(f"{rel(path)} must not be empty")
    return rows


def require_csv_ids(path: Path, id_column: str, required_ids: set[str], required_columns: set[str]) -> None:
    rows = read_csv_rows(path, required_columns)
    ids = {row.get(id_column, "").strip() for row in rows}
    missing = sorted(required_ids - ids)
    if missing:
        raise AssertionError(f"{rel(path)} missing ids in {id_column}: {missing}")


def main() -> int:
    try:
        for path in EXPECTED_FILES:
            require_file(path)

        py_compile.compile(str(Path(__file__)), doraise=True)

        for path in (DOC, CHECKLIST, SCHEMA_EVIDENCE, SMOKE_EVIDENCE, GO_NO_GO):
            require_no_dangerous_true_markers(path)

        require_text(DOC, REQUIRED_DOC_PHRASES)

        require_csv_ids(
            CHECKLIST,
            "gate_id",
            REQUIRED_CHECKLIST_IDS,
            {"gate_id", "category", "requirement", "evidence_source", "expected_result", "blocking", "go_no_go"},
        )
        require_csv_ids(
            SCHEMA_EVIDENCE,
            "evidence_id",
            REQUIRED_SCHEMA_IDS,
            {"evidence_id", "object_type", "object_name", "expected_state", "evidence_command", "required_result", "notes"},
        )
        require_csv_ids(
            SMOKE_EVIDENCE,
            "smoke_id",
            REQUIRED_SMOKE_IDS,
            {"smoke_id", "area", "command", "expected_result", "pass_condition", "notes"},
        )
        require_csv_ids(
            GO_NO_GO,
            "decision_id",
            REQUIRED_DECISION_IDS,
            {"decision_id", "criterion", "required_state", "decision_if_pass", "decision_if_fail", "next_action"},
        )

        migration_text = read_text(MIGRATION)
        if 'revision = "0009_diag_data"' not in migration_text:
            raise AssertionError("0009 migration revision id mismatch")
        if 'down_revision = "0008_auto_delivery"' not in migration_text:
            raise AssertionError("0009 migration must chain from 0008_auto_delivery")
        if 'op.create_table(\n        "imaging_studies"' in migration_text:
            raise AssertionError("0009 must not recreate imaging_studies; it already exists from 0002")
        for marker in ('"diagnostic_reports"', '"observations"', '"imaging_studies"'):
            if marker not in migration_text:
                raise AssertionError(f"0009 migration missing marker: {marker}")
        for column in sorted(IMAGING_ADDITIVE_COLUMNS):
            marker = f'op.add_column("imaging_studies", sa.Column("{column}"'
            if marker not in migration_text:
                raise AssertionError(f"0009 migration missing additive imaging column marker: {column}")

        smoke_text = read_text(SMOKE)
        for phrase in (
            "database_revision",
            "alembic_head",
            "schema_ok",
            "database_revision 必须等于 alembic_head",
            "/api/system/feature-flags",
            "all_dangerous_features_disabled",
            "ENABLE_EMR_REAL_IMPORT",
            "ENABLE_EMR_IMPORT_CASE_UPDATE",
            "ENABLE_EMR_ATTACHMENT_DOWNLOAD",
        ):
            if phrase not in smoke_text:
                raise AssertionError(f"scripts/smoke_petmed.sh missing post-migration smoke gate phrase: {phrase}")

        ci_text = read_text(CI_STATIC)
        if "run_if_exists scripts/validate_diagnostic_data_model_post_migration_verification.py" not in ci_text:
            raise AssertionError("ci_static_checks.sh must run post-migration verification validator")

        print("PASS: Diagnostic data model post-migration verification V1 docs and gates are present")
        return 0
    except AssertionError as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
