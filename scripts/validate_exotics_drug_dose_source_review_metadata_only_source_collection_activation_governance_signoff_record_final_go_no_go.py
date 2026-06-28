#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BACKEND = ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_final_go_no_go.py"
DOC = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_V1.md"
MATRIX = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_MATRIX_V1.csv"
CHECKLIST = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_V1.csv"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

EXPECTED_SPECIES = {
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
}

EXPECTED_DOMAINS = {
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
}

FORBIDDEN_RUNTIME_PATTERNS = (
    "mg/kg",
    "mcg/kg",
    "ug/kg",
    " q12",
    " q24",
    " sid",
    " bid",
    " tid",
    " qid",
)


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail("missing required file: %s" % path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def load_backend():
    spec = importlib.util.spec_from_file_location("exotics_final_go_no_go", str(BACKEND))
    if spec is None or spec.loader is None:
        fail("unable to load backend helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def require_snippets() -> None:
    required = {
        BACKEND: [
            "MODE =",
            "GOVERNANCE_DECISION = \"NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION\"",
            "\"is_dose_engine\": False",
            "\"is_prescription_engine\": False",
            "\"is_treatment_plan_engine\": False",
            "\"dose_output_enabled\": False",
            "\"captures_numeric_dose_value\": False",
            "\"captures_route_or_frequency_text\": False",
            "\"stores_usable_medication_instruction\": False",
            "\"collection_activation_allowed_now\": False",
            "\"collection_execution_started\": False",
            "\"collection_execution_allowed_now\": False",
            "\"pilot_execution_allowed_now\": False",
            "build_final_go_no_go_matrix",
            "build_summary",
        ],
        DOC: [
            "Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record Final Go/No-Go V1",
            "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
            "not a dose engine",
            "not a prescription engine",
            "not a treatment-plan engine",
            "numeric_dose_value",
            "route_text",
            "frequency_text",
            "decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_REPORT_V1",
        ],
        CI_STATIC: [
            "validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_final_go_no_go.py",
        ],
        SMOKE: [
            "Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record Final Go/No-Go V1 validator",
            "validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_final_go_no_go.py",
        ],
    }
    for path, snippets in required.items():
        text = read(path)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (path.relative_to(ROOT), snippet))


def check_module() -> None:
    py_compile.compile(str(BACKEND), doraise=True)
    module = load_backend()
    summary = module.build_summary()
    if summary.get("governance_decision") != "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION":
        fail("governance decision must remain NO_GO")
    false_keys = [
        "writes_database",
        "is_dose_engine",
        "is_prescription_engine",
        "is_treatment_plan_engine",
        "dose_output_enabled",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "collection_activation_allowed_now",
        "collection_execution_started",
        "collection_execution_allowed_now",
        "pilot_execution_allowed_now",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
        "returns_drug_dose",
        "returns_drug_route",
        "returns_drug_frequency",
        "client_facing",
    ]
    for key in false_keys:
        if summary.get(key) is not False:
            fail("%s must be false" % key)
    if summary.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if summary.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    matrix = module.build_final_go_no_go_matrix()
    if len(matrix) != len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS):
        fail("backend matrix row count mismatch")
    if {row["species_group"] for row in matrix} != EXPECTED_SPECIES:
        fail("backend matrix species coverage mismatch")
    if {row["review_domain"] for row in matrix} != EXPECTED_DOMAINS:
        fail("backend matrix domain coverage mismatch")


def check_csvs() -> None:
    for path in (MATRIX, CHECKLIST, GO_NO_GO):
        if not path.exists():
            fail("missing CSV: %s" % path.relative_to(ROOT))
    with MATRIX.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS):
        fail("matrix row count mismatch")
    if {row.get("species_group") for row in rows} != EXPECTED_SPECIES:
        fail("matrix species coverage mismatch")
    if {row.get("review_domain") for row in rows} != EXPECTED_DOMAINS:
        fail("matrix review domain coverage mismatch")
    for row in rows:
        if row.get("governance_decision") != "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION":
            fail("matrix governance_decision must be NO_GO")
        if row.get("collection_activation_status") != "not_allowed":
            fail("matrix collection_activation_status must be not_allowed")
        if row.get("collection_execution_status") != "not_started":
            fail("matrix collection_execution_status must be not_started")
        if row.get("numeric_value_capture_status") != "blocked":
            fail("matrix numeric value capture must be blocked")
        if row.get("route_frequency_capture_status") != "blocked":
            fail("matrix route/frequency capture must be blocked")
        if row.get("usable_medication_instruction_status") != "blocked":
            fail("matrix usable medication instruction must be blocked")


def check_no_runtime_dose_content() -> None:
    combined = "\n".join(
        read(path).lower()
        for path in (BACKEND, DOC, MATRIX, CHECKLIST, GO_NO_GO)
    )
    for needle in FORBIDDEN_RUNTIME_PATTERNS:
        if needle in combined:
            fail("runtime dose-like text is not allowed: %s" % needle.strip())


def main() -> None:
    for path in (BACKEND, Path(__file__)):
        py_compile.compile(str(path), doraise=True)
    require_snippets()
    check_module()
    check_csvs()
    check_no_runtime_dose_content()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record Final Go/No-Go V1")


if __name__ == "__main__":
    main()
