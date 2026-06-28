#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report.py",
]

REQUIRED_PREVIOUS_VALIDATORS = [
    "scripts/validate_exotic_kb.py",
    "scripts/validate_exotic_intake_templates.py",
    "scripts/validate_exotics_drug_dose_source_review_pack.py",
    "scripts/validate_exotics_drug_dose_source_review_controlled_research.py",
    "scripts/validate_exotics_drug_dose_source_evidence_abstraction.py",
    "scripts/validate_exotics_drug_dose_source_review_evidence_tables.py",
    "scripts/validate_exotics_drug_dose_source_review_source_registry.py",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_protocol.py",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_execution_readiness.py",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_execution_controlled_pilot.py",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_controlled_pilot_report.py",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_governance_go_no_go.py",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace.py",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_validation.py",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report.py",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff.py",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record.py",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation.py",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report.py",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_final_go_no_go.py",
]

SPECIES_GROUPS = ['rabbit', 'bird', 'ferret', 'turtle', 'lizard', 'snake', 'amphibian', 'fish', 'guinea_pig', 'hamster', 'chinchilla', 'rat_mouse', 'hedgehog', 'sugar_glider']
REVIEW_DOMAINS = ['analgesia_and_pain_control_source_review', 'antimicrobial_source_review', 'antiparasitic_source_review', 'fluid_and_supportive_care_source_review', 'sedation_anesthesia_risk_source_review', 'emergency_stabilization_source_review']
FORBIDDEN_FIELDS = ['numeric_dose_value', 'dose_unit', 'route_text', 'frequency_text', 'duration_text', 'prescription_direction', 'treatment_protocol', 'client_instruction', 'copied_table_text', 'copyrighted_full_text']


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    return path.read_text(encoding="utf-8")


def load_module():
    path = ROOT / "backend/exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report.py"
    spec = importlib.util.spec_from_file_location("activation_readiness_report", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_syntax() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)
    for rel in REQUIRED_PREVIOUS_VALIDATORS:
        path = ROOT / rel
        if not path.exists():
            fail("missing previous validator: %s" % rel)


def assert_text_markers() -> None:
    backend = read("backend/exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report.py")
    doc = read("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_V1.md")
    ci = read("scripts/ci_static_checks.sh") if (ROOT / "scripts/ci_static_checks.sh").exists() else ""
    smoke = read("scripts/smoke_petmed.sh") if (ROOT / "scripts/smoke_petmed.sh").exists() else ""
    required_backend = [
        "exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report_v1",
        "build_activation_readiness_report",
        "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
        "collection_activation_allowed_now",
        "collection_execution_allowed_now",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "returns_drug_dose",
        "requires_human_review",
        "clinician_signoff_required",
    ]
    for marker in required_backend:
        if marker not in backend:
            fail("backend helper missing marker: %s" % marker)
    required_doc = [
        "Exotics Drug Dose Source Review Metadata-only Source Collection Activation Readiness Report V1",
        "metadata_only_source_collection_activation_readiness_report_shell_only_not_activation",
        "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
        "no source collection activation",
        "no drug dose",
        "decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_FINAL_GO_NO_GO_V1",
    ]
    for marker in required_doc:
        if marker not in doc:
            fail("doc missing marker: %s" % marker)
    if "validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report.py" not in ci:
        fail("ci_static_checks missing activation readiness report validator")
    if "Exotics Drug Dose Source Review Metadata-only Source Collection Activation Readiness Report V1" not in smoke:
        fail("smoke missing activation readiness report block")


def assert_matrix() -> None:
    path = ROOT / "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_MATRIX_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)
    if len(rows) != expected_count:
        fail("matrix row count expected %d got %d" % (expected_count, len(rows)))
    combos = {(row.get("species_group"), row.get("review_domain")) for row in rows}
    for species in SPECIES_GROUPS:
        for domain in REVIEW_DOMAINS:
            if (species, domain) not in combos:
                fail("matrix missing combo: %s / %s" % (species, domain))
    header = rows[0].keys() if rows else []
    for forbidden in FORBIDDEN_FIELDS:
        if forbidden in header:
            fail("forbidden field present in matrix header: %s" % forbidden)
    for row in rows:
        if row.get("go_no_go_status") != "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION":
            fail("matrix row must remain NO_GO to activation")
        if row.get("collection_activation_status") != "not_started_not_allowed":
            fail("collection activation status must remain not_started_not_allowed")
        if row.get("collection_execution_status") != "not_started_not_allowed":
            fail("collection execution status must remain not_started_not_allowed")


def assert_module_behavior() -> None:
    module = load_module()
    report = module.build_activation_readiness_report()
    if report.get("mode") != "exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report_v1":
        fail("mode mismatch")
    if report.get("current_level") != "metadata_only_source_collection_activation_readiness_report_shell_only_not_activation":
        fail("current_level mismatch")
    if report.get("governance_decision") != "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION":
        fail("governance_decision must remain NO-GO")
    expected_false = [
        "dose_output_enabled",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "activation_readiness_passed",
        "activation_readiness_report_has_collection_results",
        "collection_activation_allowed_now",
        "collection_execution_started",
        "collection_execution_allowed_now",
        "pilot_execution_allowed_now",
        "writes_database",
        "creates_case",
        "updates_case",
        "writes_ai_summary",
        "writes_audit_log",
        "starts_source_collection_activation",
        "starts_source_collection_execution",
        "is_dose_engine",
        "is_prescription_engine",
        "is_treatment_plan_engine",
        "returns_drug_dose",
        "returns_drug_route",
        "returns_drug_frequency",
        "client_facing",
    ]
    for key in expected_false:
        if report.get(key) is not False:
            fail("%s must be false" % key)
    expected_true = [
        "activation_readiness_defined",
        "activation_readiness_report_defined",
        "requires_human_review",
        "clinician_signoff_required",
        "not_client_facing",
    ]
    for key in expected_true:
        if report.get(key) is not True:
            fail("%s must be true" % key)
    matrix = report.get("matrix") or []
    if len(matrix) != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("module matrix row count mismatch")
    for row in matrix:
        for forbidden in FORBIDDEN_FIELDS:
            if forbidden in row:
                fail("forbidden field in module row: %s" % forbidden)


def main() -> None:
    assert_files_and_syntax()
    assert_text_markers()
    assert_matrix()
    assert_module_behavior()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Source Collection Activation Readiness Report V1")


if __name__ == "__main__":
    main()
