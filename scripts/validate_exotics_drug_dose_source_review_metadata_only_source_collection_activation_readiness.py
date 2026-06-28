#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

BACKEND = ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness.py"
DOC = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_V1.md"
MATRIX = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_MATRIX_V1.csv"
CHECKLIST = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_GO_NO_GO_V1.csv"
CI = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

EXPECTED_SPECIES = [
    "rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish",
    "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider",
]
EXPECTED_DOMAINS = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]
FORBIDDEN_HEADERS = {
    "numeric_dose_value", "dose_unit", "route_text", "frequency_text", "duration_text",
    "prescription_direction", "treatment_protocol", "client_instruction", "copied_table_text", "copyrighted_full_text",
}


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail("missing file: %s" % path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def load_module():
    py_compile.compile(str(BACKEND), doraise=True)
    spec = importlib.util.spec_from_file_location("activation_readiness", str(BACKEND))
    if spec is None or spec.loader is None:
        fail("unable to load backend helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        fail("missing csv: %s" % path.relative_to(ROOT))
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def assert_backend() -> None:
    module = load_module()
    summary = module.build_activation_readiness_summary()
    if summary.get("mode") != "exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_v1":
        fail("mode mismatch")
    if summary.get("governance_decision") != "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION":
        fail("governance decision must remain NO-GO to activation")
    expected_count = len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS)
    if summary.get("matrix_row_count") != expected_count:
        fail("matrix row count mismatch")
    required_false = [
        "writes_database", "source_collection_activation", "source_collection_execution",
        "collection_activation_allowed_now", "collection_execution_started", "collection_execution_allowed_now",
        "pilot_execution_allowed_now", "is_dose_engine", "is_prescription_engine", "is_treatment_plan_engine",
        "dose_output_enabled", "captures_numeric_dose_value", "captures_route_or_frequency_text",
        "stores_usable_medication_instruction", "generates_final_diagnosis", "creates_treatment_plan",
        "creates_prescription", "returns_drug_dose", "returns_drug_route", "returns_drug_frequency",
    ]
    for key in required_false:
        if summary.get(key) is not False:
            fail("%s must be false" % key)
    if summary.get("activation_readiness_defined") is not True:
        fail("activation_readiness_defined must be true")
    if summary.get("activation_readiness_passed") is not False:
        fail("activation_readiness_passed must be false")
    if summary.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if summary.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")


def assert_docs_and_csv() -> None:
    doc = read(DOC)
    for snippet in (
        "Exotics Drug Dose Source Review Metadata-only Source Collection Activation Readiness V1",
        "governance_decision=NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
        "collection_activation_allowed_now=false",
        "collection_execution_allowed_now=false",
        "is_dose_engine=false",
        "is_prescription_engine=false",
        "dose_output_enabled=false",
        "captures_numeric_dose_value=false",
        "captures_route_or_frequency_text=false",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_V1",
    ):
        if snippet not in doc:
            fail("doc missing snippet: %s" % snippet)

    rows = read_csv(MATRIX)
    if len(rows) != len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS):
        fail("matrix row count mismatch")
    headers = set(rows[0].keys()) if rows else set()
    forbidden = headers & FORBIDDEN_HEADERS
    if forbidden:
        fail("matrix contains forbidden medication instruction headers: %s" % sorted(forbidden))
    species = {row.get("species_group") for row in rows}
    domains = {row.get("review_domain") for row in rows}
    if species != set(EXPECTED_SPECIES):
        fail("species coverage mismatch")
    if domains != set(EXPECTED_DOMAINS):
        fail("review domain coverage mismatch")
    for row in rows:
        if row.get("governance_decision") != "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION":
            fail("all rows must remain NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION")
        if row.get("collection_activation_allowed_now") != "false":
            fail("collection activation must remain blocked")
        if row.get("collection_execution_allowed_now") != "false":
            fail("collection execution must remain blocked")
        if row.get("dose_output_enabled") != "false":
            fail("dose output must remain disabled")

    if not read_csv(CHECKLIST):
        fail("checklist must not be empty")
    if not read_csv(GO_NO_GO):
        fail("go/no-go csv must not be empty")


def assert_hooks() -> None:
    ci = read(CI)
    smoke = read(SMOKE)
    validator_name = "validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness.py"
    if validator_name not in ci:
        fail("ci_static_checks missing validator")
    if validator_name not in smoke:
        fail("smoke script missing validator")


def main() -> None:
    for path in (BACKEND, DOC, MATRIX, CHECKLIST, GO_NO_GO, CI, SMOKE):
        read(path)
    assert_backend()
    assert_docs_and_csv()
    assert_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Source Collection Activation Readiness V1")


if __name__ == "__main__":
    main()
