#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record.py"
DOC = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_V1.md"
MATRIX = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_MATRIX_V1.csv"
CHECKLIST = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_GO_NO_GO_V1.csv"
VALIDATOR = ROOT / "scripts" / "validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record.py"
CI = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

FORBIDDEN_COLUMNS = set(['numeric_dose_value', 'dose_unit', 'route_text', 'frequency_text', 'duration_text', 'prescription_direction', 'treatment_protocol', 'client_instruction', 'copied_table_text', 'copyrighted_full_text'])
DOSE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
    re.IGNORECASE,
)


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail("missing required file: %s" % path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def load_helper():
    py_compile.compile(str(HELPER), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_workspace_governance_signoff_record", str(HELPER))
    if spec is None or spec.loader is None:
        fail("unable to load helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_no_real_dose_patterns() -> None:
    for path in (HELPER, DOC, CHECKLIST, GO_NO_GO):
        text = read(path)
        match = DOSE_PATTERN.search(text)
        if match:
            fail("actual medication value/route/frequency pattern found in %s: %s" % (path.relative_to(ROOT), match.group(0)))


def assert_matrix(module) -> None:
    with MATRIX.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = len(module.SPECIES_GROUPS) * len(module.REVIEW_DOMAINS)
    if len(rows) != expected:
        fail("matrix row count mismatch: expected %d got %d" % (expected, len(rows)))
    headers = set(rows[0].keys()) if rows else set()
    forbidden_headers = sorted(headers & FORBIDDEN_COLUMNS)
    if forbidden_headers:
        fail("forbidden medication columns present in matrix: %s" % ", ".join(forbidden_headers))
    required_headers = set(module.ALLOWED_METADATA_ONLY_FIELDS)
    missing = sorted(required_headers - headers)
    if missing:
        fail("matrix missing required headers: %s" % ", ".join(missing))
    for row in rows:
        if row.get("collection_execution_status") != "not_started_not_allowed":
            fail("collection execution status must remain not_started_not_allowed")
        if row.get("signoff_record_status") != "schema_defined_no_signed_record":
            fail("signoff record status must be schema_defined_no_signed_record")
        if row.get("signoff_completed_status") != "not_completed":
            fail("signoff must not be completed")
        if row.get("go_no_go_status") != "NO_GO_TO_COLLECTION_EXECUTION":
            fail("governance decision must be NO_GO_TO_COLLECTION_EXECUTION")
        if row.get("human_review_required") != "true":
            fail("human_review_required must be true")
        if row.get("clinician_signoff_required") != "true":
            fail("clinician_signoff_required must be true")


def assert_helper_summary(module) -> None:
    summary = module.summarize_governance_signoff_record()
    checks = {
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "metadata_only_workspace_validation_defined": True,
        "metadata_only_workspace_validation_executed": False,
        "metadata_only_workspace_validation_report_defined": True,
        "metadata_only_workspace_validation_report_has_collection_results": False,
        "governance_signoff_defined": True,
        "governance_signoff_completed": False,
        "governance_signoff_record_defined": True,
        "governance_signoff_record_completed": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "writes_database": False,
    }
    for key, expected in checks.items():
        if summary.get(key) is not expected:
            fail("helper summary %s expected %r got %r" % (key, expected, summary.get(key)))
    if summary.get("governance_decision") != "NO_GO_TO_COLLECTION_EXECUTION":
        fail("governance decision mismatch")
    if summary.get("drug_dose_status") != "not_reviewed_not_enabled":
        fail("drug dose status mismatch")
    if summary.get("source_review_status") != "metadata_only_workspace_governance_signoff_record_defined_no_collection_execution":
        fail("source review status mismatch")


def assert_text_requirements() -> None:
    doc = read(DOC)
    for needle in (
        "Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record V1",
        "NO_GO_TO_COLLECTION_EXECUTION",
        "metadata_only_workspace_governance_signoff_record_schema_only_not_collection_execution",
        "dose_output_enabled=false",
        "collection_execution_started=false",
        "governance_signoff_record_completed=false",
        "requires_human_review=true",
        "clinician_signoff_required=true",
    ):
        if needle not in doc:
            fail("doc missing expected content: %s" % needle)

    ci = read(CI)
    smoke = read(SMOKE)
    validator_name = "validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record.py"
    if validator_name not in ci:
        fail("ci_static_checks missing validator hook")
    if validator_name not in smoke:
        fail("smoke_petmed missing validator hook")


def main() -> None:
    for path in (HELPER, DOC, MATRIX, CHECKLIST, GO_NO_GO, VALIDATOR, CI, SMOKE):
        if not path.exists():
            fail("missing required file: %s" % path.relative_to(ROOT))
    module = load_helper()
    assert_matrix(module)
    assert_helper_summary(module)
    assert_text_requirements()
    assert_no_real_dose_patterns()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record V1")


if __name__ == "__main__":
    main()
