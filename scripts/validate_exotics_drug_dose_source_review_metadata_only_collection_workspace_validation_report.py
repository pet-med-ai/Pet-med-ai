#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report.py",
]

SPECIES_GROUPS = [
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

REVIEW_DOMAINS = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]

FORBIDDEN_COLUMNS = {
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

REQUIRED_SNIPPETS = {
    "backend/exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report.py": [
        "metadata_only_workspace_validation_report_shell_only_not_collection_execution",
        "dose_output_enabled",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "collection_execution_allowed_now",
        "NO_GO_TO_COLLECTION_EXECUTION",
    ],
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_V1.md": [
        "Exotics Drug Dose Source Review Metadata-only Collection Workspace Validation Report V1",
        "metadata_only_workspace_validation_report_shell_only_not_collection_execution",
        "NO_GO_TO_COLLECTION_EXECUTION",
        "no DB write",
        "no final diagnosis",
        "no treatment plan",
        "no prescription",
        "no drug dose",
    ],
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_GO_NO_GO_V1.csv": [
        "NO_GO_TO_COLLECTION_EXECUTION",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_V1",
    ],
}


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        fail("missing required file: %s" % rel)
    return p.read_text(encoding="utf-8")


def load_module():
    path = ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report.py"
    spec = importlib.util.spec_from_file_location("validation_report", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if not p.exists():
            fail("missing required file: %s" % rel)
        if p.suffix == ".py":
            py_compile.compile(str(p), doraise=True)

    for rel, snippets in REQUIRED_SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))

    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report.py" not in ci:
        fail("ci_static_checks missing validation report validator")
    if "Metadata-only Collection Workspace Validation Report V1" not in smoke:
        fail("smoke missing validation report block")


def assert_matrix() -> None:
    matrix_path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_MATRIX_V1.csv"
    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)
    if len(rows) != expected:
        fail("matrix row count mismatch: expected %d got %d" % (expected, len(rows)))

    fieldnames = set(rows[0].keys()) if rows else set()
    bad_fields = sorted(fieldnames & FORBIDDEN_COLUMNS)
    if bad_fields:
        fail("matrix contains forbidden medication instruction fields: %s" % ", ".join(bad_fields))

    seen = {(row.get("species_group"), row.get("review_domain")) for row in rows}
    missing = []
    for species in SPECIES_GROUPS:
        for domain in REVIEW_DOMAINS:
            if (species, domain) not in seen:
                missing.append("%s/%s" % (species, domain))
    if missing:
        fail("matrix missing species/domain rows: %s" % ", ".join(missing[:20]))

    for row in rows:
        if row.get("go_no_go_status") != "NO_GO_TO_COLLECTION_EXECUTION":
            fail("go_no_go_status must remain NO_GO_TO_COLLECTION_EXECUTION")
        if row.get("collection_execution_status") != "not_started":
            fail("collection_execution_status must remain not_started")
        if row.get("numeric_value_capture_status") != "not_captured":
            fail("numeric value capture must remain not_captured")
        if row.get("route_frequency_capture_status") != "not_captured":
            fail("route/frequency capture must remain not_captured")
        if row.get("usable_medication_instruction_status") != "not_stored":
            fail("usable medication instruction must remain not_stored")


def assert_backend_behavior() -> None:
    module = load_module()
    summary = module.assert_metadata_only_workspace_validation_report_safe()
    if summary.get("mode") != "exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report_v1":
        fail("mode mismatch")
    if summary.get("current_level") != "metadata_only_workspace_validation_report_shell_only_not_collection_execution":
        fail("current_level mismatch")
    if summary.get("coverage_complete") is not True:
        fail("coverage_complete must be true")
    false_keys = [
        "is_dose_engine",
        "is_prescription_engine",
        "is_treatment_plan_engine",
        "dose_output_enabled",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "collection_execution_started",
        "collection_execution_allowed_now",
        "writes_database",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
        "returns_drug_dose",
        "returns_drug_route",
        "returns_drug_frequency",
        "client_facing",
        "calls_external_ai",
        "calls_external_provider",
    ]
    for key in false_keys:
        if summary.get(key) is not False:
            fail("%s must be false" % key)
    true_keys = [
        "metadata_only_workspace_defined",
        "metadata_only_workspace_validation_defined",
        "metadata_only_workspace_validation_report_defined",
        "read_only",
        "not_client_facing",
        "requires_human_review",
        "clinician_signoff_required",
    ]
    for key in true_keys:
        if summary.get(key) is not True:
            fail("%s must be true" % key)
    if summary.get("governance_decision") != "NO_GO_TO_COLLECTION_EXECUTION":
        fail("governance_decision must remain NO_GO_TO_COLLECTION_EXECUTION")


def main() -> None:
    assert_files_and_snippets()
    assert_matrix()
    assert_backend_behavior()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Collection Workspace Validation Report V1")


if __name__ == "__main__":
    main()
