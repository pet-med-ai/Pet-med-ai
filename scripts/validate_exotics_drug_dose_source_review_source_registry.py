#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_source_registry.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_source_registry.py",
]

DOSE_PATTERN = re.compile(
    r"\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid)\b",
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


def load_module():
    path = ROOT / "backend" / "exotics_drug_dose_source_review_source_registry.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("source_registry", str(path))
    if spec is None or spec.loader is None:
        fail("unable to import source registry helper")
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


def assert_no_usable_dose_content() -> None:
    scan_targets = [
        "backend/exotics_drug_dose_source_review_source_registry.py",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_MATRIX_V1.csv",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_CHECKLIST_V1.csv",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_GO_NO_GO_V1.csv",
    ]
    for rel in scan_targets:
        text = read(rel)
        match = DOSE_PATTERN.search(text)
        if match:
            fail("found forbidden usable dose-like text in %s: %s" % (rel, match.group(0)))

    forbidden_snippets = [
        "prescription_direction,true",
        "prescription_instruction_allowed,true",
        "dose_output_enabled,true",
        "captures_numeric_dose_value,true",
        "captures_route_or_frequency_text,true",
        "stores_usable_medication_instruction,true",
    ]
    combined = "\n".join(read(rel) for rel in scan_targets).lower()
    for snippet in forbidden_snippets:
        if snippet in combined:
            fail("forbidden enabled capability marker present: %s" % snippet)


def assert_module_behavior() -> None:
    module = load_module()
    if module.EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_MODE != "exotics_drug_dose_source_review_source_registry_v1":
        fail("mode constant mismatch")

    matrix = module.build_source_registry_matrix()
    expected_count = len(module.SPECIES_GROUPS) * len(module.REVIEW_DOMAINS)
    if len(matrix) != expected_count:
        fail("source registry matrix count mismatch")

    summary = module.build_source_registry_summary()
    required_false = [
        "writes_database",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
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
    ]
    for key in required_false:
        if summary.get(key) is not False:
            fail("%s must be false" % key)
    if summary.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if summary.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    if summary.get("decision") != "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1":
        fail("decision mismatch")


def assert_matrix_csv() -> None:
    path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_MATRIX_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    module = load_module()
    expected_count = len(module.SPECIES_GROUPS) * len(module.REVIEW_DOMAINS)
    if len(rows) != expected_count:
        fail("CSV matrix row count mismatch: expected %d got %d" % (expected_count, len(rows)))
    for row in rows:
        for key in (
            "dose_output_enabled",
            "captures_numeric_dose_value",
            "captures_route_or_frequency_text",
            "prescription_instruction_allowed",
        ):
            if row.get(key) != "false":
                fail("matrix %s must be false for row %s" % (key, row.get("registry_id")))
        if row.get("review_status") != "registry_slot_created_not_populated":
            fail("matrix review_status should remain not populated")


def assert_docs_and_hooks() -> None:
    doc = read("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_V1.md")
    for snippet in (
        "Exotics Drug Dose Source Review Source Registry V1",
        "source_registry_schema_only_not_dose_engine",
        "dose_output_enabled=false",
        "captures_numeric_dose_value=false",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1",
    ):
        if snippet not in doc:
            fail("doc missing snippet: %s" % snippet)

    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "validate_exotics_drug_dose_source_review_source_registry.py" not in ci:
        fail("ci_static_checks missing source registry validator hook")
    if "validate_exotics_drug_dose_source_review_source_registry.py" not in smoke:
        fail("smoke script missing source registry validator hook")


def main() -> None:
    assert_required_files()
    assert_no_usable_dose_content()
    assert_module_behavior()
    assert_matrix_csv()
    assert_docs_and_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Source Registry V1")


if __name__ == "__main__":
    main()
