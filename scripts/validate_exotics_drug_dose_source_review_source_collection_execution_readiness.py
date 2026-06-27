#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import json
import py_compile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_source_collection_execution_readiness.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_execution_readiness.py",
]

SPECIES_GROUPS = {
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

REVIEW_DOMAINS = {
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
}

FORBIDDEN_VALUES = (
    "numeric medication amount",
    "give this medicine",
    "prescribe this medicine",
)

PROHIBITED_BACKEND_SNIPPETS = (
    "db.add(",
    "db.commit(",
    "db.delete(",
    "requests.post(",
    "httpx.post(",
    "OpenAI(",
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


def load_module() -> Any:
    path = ROOT / "backend" / "exotics_drug_dose_source_review_source_collection_execution_readiness.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_source_collection_execution_readiness", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend readiness module")
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

    backend = read("backend/exotics_drug_dose_source_review_source_collection_execution_readiness.py")
    for snippet in PROHIBITED_BACKEND_SNIPPETS:
        if snippet in backend:
            fail("backend helper must remain read-only and local-only: %s" % snippet)

    required_backend = [
        "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_MODE",
        "source_collection_execution_readiness_only_not_execution",
        "collection_execution_started",
        '"writes_database": False',
        '"is_dose_engine": False',
        '"is_prescription_engine": False',
        '"captures_numeric_dose_value": False',
        '"captures_route_or_frequency_text": False',
        '"stores_usable_medication_instruction": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
    ]
    for snippet in required_backend:
        if snippet not in backend:
            fail("backend helper missing snippet: %s" % snippet)

    doc = read("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_V1.md")
    required_doc = [
        "Exotics Drug Dose Source Review Source Collection Execution Readiness V1",
        "source_collection_execution_readiness_only_not_execution",
        "collection_execution_status=not_started_until_next_stage_go",
        "captures_numeric_dose_value=false",
        "captures_route_or_frequency_text=false",
        "stores_usable_medication_instruction=false",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_V1",
    ]
    for snippet in required_doc:
        if snippet not in doc:
            fail("doc missing snippet: %s" % snippet)

    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "validate_exotics_drug_dose_source_review_source_collection_execution_readiness.py" not in ci:
        fail("ci_static_checks missing execution readiness validator")
    if "validate_exotics_drug_dose_source_review_source_collection_execution_readiness.py" not in smoke:
        fail("smoke script missing execution readiness validator")


def assert_matrix() -> None:
    matrix_path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_MATRIX_V1.csv"
    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected_count = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)
    if len(rows) != expected_count:
        fail("readiness matrix row count mismatch: expected %d got %d" % (expected_count, len(rows)))

    species = {row.get("species_group") for row in rows}
    domains = {row.get("review_domain") for row in rows}
    if species != SPECIES_GROUPS:
        fail("species group mismatch: %s" % sorted(species))
    if domains != REVIEW_DOMAINS:
        fail("review domain mismatch: %s" % sorted(domains))

    for idx, row in enumerate(rows, 1):
        if row.get("dose_output_enabled") != "false":
            fail("row %d dose_output_enabled must be false" % idx)
        if row.get("route_or_frequency_capture_enabled") != "false":
            fail("row %d route_or_frequency_capture_enabled must be false" % idx)
        if row.get("collection_execution_status") != "not_started":
            fail("row %d collection_execution_status must be not_started" % idx)
        if row.get("value_capture_policy") != "metadata_only_no_medication_values":
            fail("row %d must keep metadata-only value capture policy" % idx)
        for forbidden in FORBIDDEN_VALUES:
            if forbidden.lower() in json.dumps(row, ensure_ascii=False).lower():
                fail("row %d contains forbidden value text: %s" % (idx, forbidden))


def assert_module_behavior() -> None:
    module = load_module()
    result = module.build_exotics_source_collection_execution_readiness()
    if result.get("mode") != "exotics_drug_dose_source_review_source_collection_execution_readiness_v1":
        fail("mode mismatch")
    if result.get("writes_database") is not False:
        fail("writes_database must be false")
    if result.get("is_dose_engine") is not False:
        fail("is_dose_engine must be false")
    if result.get("is_prescription_engine") is not False:
        fail("is_prescription_engine must be false")
    if result.get("dose_output_enabled") is not False:
        fail("dose_output_enabled must be false")
    if result.get("captures_numeric_dose_value") is not False:
        fail("captures_numeric_dose_value must be false")
    if result.get("captures_route_or_frequency_text") is not False:
        fail("captures_route_or_frequency_text must be false")
    if result.get("stores_usable_medication_instruction") is not False:
        fail("stores_usable_medication_instruction must be false")
    if result.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if result.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    summary = result.get("summary") or {}
    if summary.get("collection_execution_started") is not False:
        fail("collection execution must not be started")
    rows = result.get("readiness_matrix") or []
    if len(rows) != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("module readiness matrix count mismatch")


def main() -> None:
    assert_files_and_snippets()
    assert_matrix()
    assert_module_behavior()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Source Collection Execution Readiness V1")


if __name__ == "__main__":
    main()
