#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_source_collection_execution_controlled_pilot.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_execution_controlled_pilot.py",
]

SPECIES_GROUPS = {
    "rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish",
    "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider",
}

REVIEW_DOMAINS = {
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
}

PROHIBITED_FIELD_NAMES = {
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


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    return path.read_text(encoding="utf-8")


def load_module():
    path = ROOT / "backend" / "exotics_drug_dose_source_review_source_collection_execution_controlled_pilot.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_source_collection_controlled_pilot", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load controlled pilot module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_required_files() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)


def assert_matrix() -> None:
    matrix_path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_MATRIX_V1.csv"
    with matrix_path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)
    if len(rows) != expected_count:
        fail("matrix row count mismatch: expected %d got %d" % (expected_count, len(rows)))
    seen = set()
    for row in rows:
        species = row.get("species_group")
        domain = row.get("review_domain")
        if species not in SPECIES_GROUPS:
            fail("unexpected species_group in matrix: %s" % species)
        if domain not in REVIEW_DOMAINS:
            fail("unexpected review_domain in matrix: %s" % domain)
        key = (species, domain)
        if key in seen:
            fail("duplicate matrix row: %s %s" % key)
        seen.add(key)
        if row.get("dose_output_enabled") != "false":
            fail("dose output must stay disabled in matrix")
        if row.get("route_or_frequency_capture_enabled") != "false":
            fail("route/frequency capture must stay disabled in matrix")
        if row.get("stores_usable_medication_instruction") != "false":
            fail("usable medication instruction storage must stay disabled")
        if row.get("pilot_execution_allowed_now") != "false":
            fail("pilot execution must not be allowed by default")
        prohibited = row.get("prohibited_capture") or ""
        for field in PROHIBITED_FIELD_NAMES:
            if field not in prohibited:
                fail("matrix prohibited_capture missing field: %s" % field)


def assert_module_behavior() -> None:
    module = load_module()
    result = module.build_exotics_source_collection_execution_controlled_pilot()
    if result.get("mode") != "exotics_drug_dose_source_review_source_collection_execution_controlled_pilot_v1":
        fail("mode mismatch")
    rows = result.get("controlled_pilot_rows") or []
    if len(rows) != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("backend controlled pilot row count mismatch")
    required_false = [
        "writes_database",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "creates_prescription",
        "returns_drug_dose",
        "returns_drug_route",
        "returns_drug_frequency",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "dose_output_enabled",
        "pilot_execution_allowed_now",
        "collection_execution_started",
        "is_dose_engine",
        "is_prescription_engine",
        "is_treatment_plan_engine",
    ]
    for key in required_false:
        if result.get(key) is not False:
            fail("expected %s=false" % key)
    if result.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if result.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    summary = result.get("summary") or {}
    if summary.get("current_level") != "controlled_pilot_shell_only_not_collection_execution":
        fail("current_level mismatch")
    if summary.get("source_review_status") != "controlled_pilot_shell_ready_not_started":
        fail("source_review_status mismatch")
    for field in PROHIBITED_FIELD_NAMES:
        if field not in result.get("prohibited_capture_fields", []):
            fail("backend prohibited_capture_fields missing: %s" % field)


def assert_docs_and_hooks() -> None:
    doc = read("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_V1.md")
    for needle in (
        "controlled_pilot_shell_only_not_collection_execution",
        "is_dose_engine=false",
        "is_prescription_engine=false",
        "captures_numeric_dose_value=false",
        "captures_route_or_frequency_text=false",
        "collection_execution_started=false",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_V1",
    ):
        if needle not in doc:
            fail("doc missing expected content: %s" % needle)
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    validator_name = "validate_exotics_drug_dose_source_review_source_collection_execution_controlled_pilot.py"
    if validator_name not in ci:
        fail("ci_static_checks missing controlled pilot validator")
    if validator_name not in smoke:
        fail("smoke missing controlled pilot validator")


def main() -> None:
    assert_required_files()
    assert_matrix()
    assert_module_behavior()
    assert_docs_and_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Source Collection Execution Controlled Pilot V1")


if __name__ == "__main__":
    main()
