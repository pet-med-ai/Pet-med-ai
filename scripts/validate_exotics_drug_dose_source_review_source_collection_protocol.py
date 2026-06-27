#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
import re
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
MODE = "exotics_drug_dose_source_review_source_collection_protocol_v1"

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_source_collection_protocol.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_protocol.py",
]

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

FORBIDDEN_VALUE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b)",
    re.IGNORECASE,
)


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    return path.read_text(encoding="utf-8")


def require_text(rel: str, snippets: List[str]) -> None:
    text = read(rel)
    for snippet in snippets:
        if snippet not in text:
            fail("missing snippet in %s: %s" % (rel, snippet))


def load_module():
    path = ROOT / "backend" / "exotics_drug_dose_source_review_source_collection_protocol.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_source_collection_protocol", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load source collection protocol module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    require_text("backend/exotics_drug_dose_source_review_source_collection_protocol.py", [
        "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_MODE",
        "source_collection_protocol_only_not_dose_engine",
        "ALLOWED_COLLECTION_FIELDS",
        "FORBIDDEN_COLLECTION_FIELDS",
        "build_source_collection_protocol_matrix",
        "validate_source_collection_record",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "is_dose_engine",
        "is_prescription_engine",
        "is_treatment_plan_engine",
        "requires_human_review",
        "clinician_signoff_required",
    ])

    require_text("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1.md", [
        "Exotics Drug Dose Source Review Source Collection Protocol V1",
        "source_collection_protocol_only_not_dose_engine",
        "source_collection_protocol_ready_not_started",
        "dose_output_enabled=false",
        "captures_numeric_dose_value=false",
        "captures_route_or_frequency_text=false",
        "stores_usable_medication_instruction=false",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_V1",
    ])

    ci = read("scripts/ci_static_checks.sh")
    if "Exotics Drug Dose Source Review Source Collection Protocol V1 static checks" not in ci:
        fail("ci_static_checks missing source collection protocol block")
    if "python3 scripts/validate_exotics_drug_dose_source_review_source_collection_protocol.py" not in ci:
        fail("ci_static_checks missing source collection protocol validator")

    smoke = read("scripts/smoke_petmed.sh")
    if "Exotics Drug Dose Source Review Source Collection Protocol V1 smoke" not in smoke:
        fail("smoke script missing source collection protocol block")


def assert_matrix() -> None:
    path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_MATRIX_V1.csv"
    rows = list(csv.DictReader(path.open("r", encoding="utf-8")))
    expected_count = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)
    if len(rows) != expected_count:
        fail("matrix row count expected %d got %d" % (expected_count, len(rows)))

    species = {row.get("species_group") for row in rows}
    domains = {row.get("review_domain") for row in rows}
    if species != set(SPECIES_GROUPS):
        fail("matrix species groups mismatch: %s" % sorted(species))
    if domains != set(REVIEW_DOMAINS):
        fail("matrix review domains mismatch: %s" % sorted(domains))

    for row in rows:
        if row.get("collection_scope") != "source_metadata_collection_protocol_only":
            fail("matrix row must stay metadata-only")
        for key in (
            "dose_output_enabled",
            "captures_numeric_dose_value",
            "captures_route_or_frequency_text",
            "prescription_instruction_allowed",
            "client_facing_allowed",
            "evidence_abstraction_ready",
        ):
            if row.get(key) != "false":
                fail("matrix %s must be false" % key)
        if "numeric_dose_value" not in (row.get("forbidden_capture") or ""):
            fail("matrix must name numeric_dose_value as forbidden capture")
        if "route_text" not in (row.get("forbidden_capture") or ""):
            fail("matrix must name route_text as forbidden capture")
        if "frequency_text" not in (row.get("forbidden_capture") or ""):
            fail("matrix must name frequency_text as forbidden capture")


def assert_no_numeric_medication_values() -> None:
    targets = [
        "backend/exotics_drug_dose_source_review_source_collection_protocol.py",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1.md",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_MATRIX_V1.csv",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_CHECKLIST_V1.csv",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_GO_NO_GO_V1.csv",
    ]
    for rel in targets:
        text = read(rel)
        if FORBIDDEN_VALUE_PATTERN.search(text):
            fail("forbidden numeric medication amount/frequency pattern found in %s" % rel)


def assert_module_behavior() -> None:
    module = load_module()
    if module.EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_MODE != MODE:
        fail("mode constant mismatch")

    flags = module.exotics_drug_dose_source_review_source_collection_protocol_safety_flags()
    for key in (
        "writes_database",
        "returns_drug_dose",
        "returns_drug_route",
        "returns_drug_frequency",
        "dose_output_enabled",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "is_dose_engine",
        "is_prescription_engine",
        "is_treatment_plan_engine",
    ):
        if flags.get(key) is not False:
            fail("safety flag must be false: %s" % key)
    if flags.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if flags.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")

    review = module.build_source_collection_protocol_review()
    if review.get("current_level") != "source_collection_protocol_only_not_dose_engine":
        fail("current_level mismatch")
    if review.get("source_review_status") != "source_collection_protocol_ready_not_started":
        fail("source_review_status mismatch")
    if review.get("protocol_row_count") != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("protocol row count mismatch")
    if review.get("dose_output_enabled") is not False:
        fail("review must keep dose_output_enabled=false")

    good = {
        "source_collection_id": "candidate-source-001",
        "species_group": "rabbit",
        "review_domain": "analgesia_and_pain_control_source_review",
        "source_type": "exotics_textbook_metadata_only",
        "citation_key": "metadata-only-example",
        "publication_or_edition_metadata": "edition metadata only",
        "reviewer_initials": "QA",
    }
    result = module.validate_source_collection_record(good)
    if result.get("record_valid_for_protocol") is not True:
        fail("valid metadata-only record should pass")

    bad_field = dict(good)
    bad_field["numeric_dose_value"] = "blocked"
    try:
        module.validate_source_collection_record(bad_field)
        fail("record with numeric_dose_value should fail")
    except ValueError:
        pass

    bad_text = dict(good)
    bad_text["species_applicability_note"] = "contains 5 mg/kg and must be blocked"
    try:
        module.validate_source_collection_record(bad_text)
        fail("record with numeric medication amount text should fail")
    except ValueError:
        pass


def main() -> None:
    assert_files_and_snippets()
    assert_matrix()
    assert_no_numeric_medication_values()
    assert_module_behavior()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Source Collection Protocol V1")


if __name__ == "__main__":
    main()
