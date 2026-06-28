#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HELPER = ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation.py"
DOC = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_V1.md"
MATRIX = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_MATRIX_V1.csv"
CHECKLIST = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_GO_NO_GO_V1.csv"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

REQUIRED = [HELPER, DOC, MATRIX, CHECKLIST, GO_NO_GO, CI_STATIC, SMOKE]
MODE = "exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_v1"
NEXT_STAGE = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_V1"
EXPECTED_SPECIES = [
    "rabbit",
    "bird",
    "ferret",
    "turtle",
    "lizard",
    "snake",
    "amphibian",
    "fish",
    "guinea_pig",
    "hamster",
    "chinchilla",
    "rat_mouse",
    "hedgehog",
    "sugar_glider",
]
EXPECTED_DOMAINS = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]
FORBIDDEN_MATRIX_COLUMNS = {
    "numeric_dose_value",
    "dose_unit",
    "route_text",
    "frequency_text",
    "duration_text",
    "prescription_direction",
    "treatment_protocol",
    "client_instruction",
    "copied_table_text",
    "copyrighted_full_text",
}


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def require_file(path: Path) -> None:
    if not path.exists():
        fail("missing required file: %s" % path.relative_to(ROOT))
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)


def read(path: Path) -> str:
    require_file(path)
    return path.read_text(encoding="utf-8")


def load_helper():
    spec = importlib.util.spec_from_file_location("exotics_governance_signoff_record_validation", str(HELPER))
    if spec is None or spec.loader is None:
        fail("unable to load helper module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_text_files() -> None:
    for path in REQUIRED:
        require_file(path)
    doc = read(DOC)
    for needle in (
        "Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record Validation V1",
        "NO_GO_TO_COLLECTION_EXECUTION",
        "current_level=metadata_only_workspace_governance_signoff_record_validation_schema_only_not_collection_execution",
        "captures_numeric_dose_value=false",
        "captures_route_or_frequency_text=false",
        "stores_usable_medication_instruction=false",
        "collection_execution_allowed_now=false",
        "governance_signoff_record_validation_defined=true",
        "governance_signoff_record_validation_executed=false",
        NEXT_STAGE,
    ):
        if needle not in doc:
            fail("doc missing expected content: %s" % needle)
    ci = read(CI_STATIC)
    if "validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation.py" not in ci:
        fail("ci_static_checks missing validator hook")
    smoke = read(SMOKE)
    if "Metadata-only Collection Workspace Governance Signoff Record Validation V1" not in smoke:
        fail("smoke missing stage hook")


def assert_helper() -> None:
    module = load_helper()
    if module.MODE != MODE:
        fail("helper MODE mismatch")
    rows = module.build_validation_rows()
    expected_count = len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS)
    if len(rows) != expected_count:
        fail("helper row count mismatch: %s" % len(rows))
    summary = module.build_summary()
    if summary.get("mode") != MODE:
        fail("summary mode mismatch")
    if summary.get("governance_decision") != "NO_GO_TO_COLLECTION_EXECUTION":
        fail("summary must preserve NO_GO decision")
    for key, expected in (
        ("writes_database", False),
        ("collection_execution_started", False),
        ("collection_execution_allowed_now", False),
        ("is_dose_engine", False),
        ("is_prescription_engine", False),
        ("is_treatment_plan_engine", False),
        ("dose_output_enabled", False),
        ("captures_numeric_dose_value", False),
        ("captures_route_or_frequency_text", False),
        ("stores_usable_medication_instruction", False),
        ("requires_human_review", True),
        ("clinician_signoff_required", True),
    ):
        if summary.get(key) is not expected:
            fail("summary %s expected %r got %r" % (key, expected, summary.get(key)))
    if not set(FORBIDDEN_MATRIX_COLUMNS).issubset(set(module.FORBIDDEN_VALUE_FIELDS)):
        fail("helper forbidden value fields incomplete")


def assert_matrix() -> None:
    with MATRIX.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    forbidden_headers = sorted(set(fieldnames) & FORBIDDEN_MATRIX_COLUMNS)
    if forbidden_headers:
        fail("matrix must not include forbidden value columns: %s" % ", ".join(forbidden_headers))
    expected_count = len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS)
    if len(rows) != expected_count:
        fail("matrix row count expected %d got %d" % (expected_count, len(rows)))
    combos = {(row.get("species_group"), row.get("review_domain")) for row in rows}
    expected = {(species, domain) for species in EXPECTED_SPECIES for domain in EXPECTED_DOMAINS}
    if combos != expected:
        fail("matrix species/domain coverage mismatch")
    for row in rows:
        if row.get("go_no_go_status") != "NO_GO_TO_COLLECTION_EXECUTION":
            fail("matrix row must preserve NO_GO decision")
        if row.get("collection_execution_status") != "not_started":
            fail("collection execution must remain not_started")
        if row.get("numeric_value_capture_status") != "blocked_not_present":
            fail("numeric value capture must stay blocked_not_present")
        if row.get("route_frequency_capture_status") != "blocked_not_present":
            fail("route/frequency capture must stay blocked_not_present")
        if row.get("usable_medication_instruction_status") != "blocked_not_present":
            fail("usable medication instruction must stay blocked_not_present")
        if row.get("human_review_required") != "true" or row.get("clinician_signoff_required") != "true":
            fail("human review and clinician signoff must be required")
        if row.get("next_required_stage") != NEXT_STAGE:
            fail("next_required_stage mismatch")


def main() -> None:
    assert_text_files()
    assert_helper()
    assert_matrix()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record Validation V1")


if __name__ == "__main__":
    main()
