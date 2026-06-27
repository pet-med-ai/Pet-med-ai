#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BACKEND = ROOT / "backend" / "exotics_drug_dose_source_review_source_collection_governance_go_no_go.py"
DOC = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_V1.md"
MATRIX = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_MATRIX_V1.csv"
CHECKLIST = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_V1.csv"
CI = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

EXPECTED_SPECIES = {
    "rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish",
    "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider",
}
EXPECTED_DOMAINS = {
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
}
FORBIDDEN_FIELDS = [
    "numeric_dose_value", "dose_unit", "route_text", "frequency_text", "duration_text",
    "prescription_direction", "treatment_protocol", "client_instruction",
    "copied_table_text", "copyrighted_full_text",
]
DOSE_VALUE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b", re.I)
ROUTE_FREQ_RE = re.compile(r"\b(?:q\d{1,2}h|sid|bid|tid|qid|po|iv|im|sc|sq)\b", re.I)


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail("missing required file: %s" % path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def load_module():
    spec = importlib.util.spec_from_file_location("governance_go_no_go", str(BACKEND))
    if spec is None or spec.loader is None:
        fail("unable to import backend helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_no_forbidden_values() -> None:
    for path in (BACKEND, DOC, MATRIX, CHECKLIST, GO_NO_GO):
        text = read(path)
        if DOSE_VALUE_RE.search(text):
            fail("forbidden numeric medication amount in %s" % path.relative_to(ROOT))
        # Forbidden field names are intentionally listed as blocked schema fields.
        # Do not reject the names themselves; reject actual medication amount patterns.
    # Route/frequency abbreviations are too short for broad document scanning; matrix rows must still block them.


def assert_module() -> None:
    module = load_module()
    if module.EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_MODE != "exotics_drug_dose_source_review_source_collection_governance_go_no_go_v1":
        fail("mode mismatch")
    summary = module.build_governance_go_no_go_summary()
    required_false = [
        "is_dose_engine", "is_prescription_engine", "is_treatment_plan_engine",
        "dose_output_enabled", "captures_numeric_dose_value", "captures_route_or_frequency_text",
        "stores_usable_medication_instruction", "collection_execution_started",
        "collection_execution_allowed_now", "pilot_execution_allowed_now", "writes_database",
        "generates_final_diagnosis", "creates_treatment_plan", "writes_prescription",
        "returns_drug_dose", "returns_drug_route", "returns_drug_frequency",
    ]
    for key in required_false:
        if summary.get(key) is not False:
            fail("summary flag must be false: %s" % key)
    for key in ("requires_human_review", "clinician_signoff_required", "not_client_facing"):
        if summary.get(key) is not True:
            fail("summary flag must be true: %s" % key)
    if summary.get("source_review_status") != "governance_go_no_go_defined_no_collection_execution":
        fail("source_review_status mismatch")
    if summary.get("drug_dose_status") != "not_reviewed_not_enabled":
        fail("drug_dose_status mismatch")
    if summary.get("matrix_row_count") != len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS):
        fail("matrix row count mismatch")
    if summary.get("quality_gate", {}).get("go_no_go_status") != "NO_GO_TO_COLLECTION_EXECUTION":
        fail("quality gate must block collection execution")


def assert_matrix() -> None:
    with MATRIX.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS):
        fail("matrix row count mismatch: %d" % len(rows))
    species = {row.get("species_group") for row in rows}
    domains = {row.get("review_domain") for row in rows}
    if species != EXPECTED_SPECIES:
        fail("matrix species mismatch: %r" % sorted(species))
    if domains != EXPECTED_DOMAINS:
        fail("matrix domains mismatch: %r" % sorted(domains))
    for row in rows:
        if row.get("governance_decision") != "NO_GO_TO_COLLECTION_EXECUTION":
            fail("every matrix row must block collection execution")
        for column in ("collection_execution_allowed", "numeric_value_capture_allowed", "route_frequency_capture_allowed", "usable_medication_instruction_allowed"):
            if str(row.get(column)).lower() != "false":
                fail("matrix column must be false: %s" % column)
        for column in ("requires_human_review", "clinician_signoff_required"):
            if str(row.get(column)).lower() != "true":
                fail("matrix column must be true: %s" % column)


def assert_docs_and_hooks() -> None:
    doc = read(DOC)
    for needle in (
        "Exotics Drug Dose Source Review Source Collection Governance Go/No-Go V1",
        "NO_GO_TO_COLLECTION_EXECUTION",
        "dose_output_enabled=false",
        "collection_execution_allowed_now=false",
        "no drug dose",
        "no drug route",
        "no drug frequency",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_V1",
    ):
        if needle not in doc:
            fail("doc missing expected text: %s" % needle)
    ci = read(CI)
    smoke = read(SMOKE)
    validator_name = "validate_exotics_drug_dose_source_review_source_collection_governance_go_no_go.py"
    if validator_name not in ci:
        fail("ci_static_checks missing validator hook")
    if validator_name not in smoke:
        fail("smoke_petmed missing validator hook")


def main() -> None:
    for path in (BACKEND, DOC, MATRIX, CHECKLIST, GO_NO_GO, CI, SMOKE):
        read(path)
    assert_no_forbidden_values()
    assert_module()
    assert_matrix()
    assert_docs_and_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Source Collection Governance Go/No-Go V1")


if __name__ == "__main__":
    main()
