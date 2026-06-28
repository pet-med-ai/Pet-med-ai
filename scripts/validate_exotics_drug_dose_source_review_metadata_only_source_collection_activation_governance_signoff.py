#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODE = "exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_v1"

SPECIES_GROUPS = [
    "rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish",
    "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider",
]

REVIEW_DOMAINS = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

FORBIDDEN_MATRIX_COLUMNS = {
    "numeric_dose_value", "dose_unit", "route_text", "frequency_text", "duration_text",
    "prescription_direction", "treatment_protocol", "client_instruction",
    "copied_table_text", "copyrighted_full_text",
}

REQUIRED_MATRIX_COLUMNS = {
    "activation_governance_signoff_id", "species_group", "review_domain",
    "activation_governance_scope", "activation_readiness_final_go_no_go_status",
    "clinical_owner_signoff_status", "second_reviewer_signoff_status",
    "source_access_signoff_status", "copyright_access_signoff_status",
    "metadata_only_workspace_signoff_status", "forbidden_value_scanner_signoff_status",
    "value_capture_blocker_signoff_status", "activation_signoff_status",
    "activation_allowed_now", "collection_execution_started", "collection_execution_allowed_now",
    "pilot_execution_allowed_now", "go_no_go_status", "human_review_required",
    "clinician_signoff_required", "next_required_stage",
}


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
    path = ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("activation_governance_signoff", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load helper module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_hooks() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    validator_name = "validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff.py"
    if validator_name not in read("scripts/ci_static_checks.sh"):
        fail("ci_static_checks missing activation governance signoff validator")
    if validator_name not in read("scripts/smoke_petmed.sh"):
        fail("smoke_petmed missing activation governance signoff validator")

    doc = read("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_V1.md")
    for needle in (
        "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
        "collection_activation_allowed_now=false",
        "collection_execution_started=false",
        "dose_output_enabled=false",
        "captures_numeric_dose_value=false",
        "captures_route_or_frequency_text=false",
    ):
        if needle not in doc:
            fail("doc missing expected safety marker: %s" % needle)


def assert_matrix() -> None:
    path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_MATRIX_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected_count = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)
    if len(rows) != expected_count:
        fail("matrix row count mismatch: expected %d got %d" % (expected_count, len(rows)))

    fieldnames = set(rows[0].keys()) if rows else set()
    missing = sorted(REQUIRED_MATRIX_COLUMNS - fieldnames)
    if missing:
        fail("matrix missing required columns: %s" % ", ".join(missing))

    forbidden = sorted(FORBIDDEN_MATRIX_COLUMNS & fieldnames)
    if forbidden:
        fail("matrix contains forbidden medication-value columns: %s" % ", ".join(forbidden))

    expected_pairs = {(species, domain) for species in SPECIES_GROUPS for domain in REVIEW_DOMAINS}
    seen = set()
    for row in rows:
        seen.add((row.get("species_group"), row.get("review_domain")))
        if row.get("activation_allowed_now") != "false":
            fail("activation_allowed_now must stay false")
        if row.get("collection_execution_started") != "false":
            fail("collection_execution_started must stay false")
        if row.get("collection_execution_allowed_now") != "false":
            fail("collection_execution_allowed_now must stay false")
        if row.get("pilot_execution_allowed_now") != "false":
            fail("pilot_execution_allowed_now must stay false")
        if row.get("go_no_go_status") != "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION":
            fail("unexpected go_no_go_status: %s" % row.get("go_no_go_status"))
        if row.get("human_review_required") != "true":
            fail("human_review_required must be true")
        if row.get("clinician_signoff_required") != "true":
            fail("clinician_signoff_required must be true")

    if seen != expected_pairs:
        fail("matrix species/review domain coverage mismatch")


def assert_module_behavior() -> None:
    module = load_module()
    report = module.build_report()

    if report.get("mode") != MODE:
        fail("mode mismatch")
    if report.get("matrix_row_count") != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("report matrix row count mismatch")

    required_false = [
        "writes_database", "is_dose_engine", "is_prescription_engine", "is_treatment_plan_engine",
        "dose_output_enabled", "captures_numeric_dose_value", "captures_route_or_frequency_text",
        "stores_usable_medication_instruction", "collection_activation_allowed_now",
        "source_collection_execution_started", "source_collection_execution_allowed_now",
        "pilot_execution_allowed_now", "generates_final_diagnosis", "creates_treatment_plan",
        "writes_prescription", "returns_drug_dose", "returns_drug_route", "returns_drug_frequency",
    ]
    for key in required_false:
        if report.get(key) is not False:
            fail("%s must be False" % key)

    if report.get("requires_human_review") is not True:
        fail("requires_human_review must be True")
    if report.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be True")
    if report.get("governance_decision") != "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION":
        fail("governance decision mismatch")

    forbidden = set(getattr(module, "FORBIDDEN_FIELDS", []))
    if not FORBIDDEN_MATRIX_COLUMNS.issubset(forbidden):
        fail("helper forbidden field list incomplete")


def main() -> None:
    assert_files_and_hooks()
    assert_matrix()
    assert_module_behavior()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff V1")


if __name__ == "__main__":
    main()
