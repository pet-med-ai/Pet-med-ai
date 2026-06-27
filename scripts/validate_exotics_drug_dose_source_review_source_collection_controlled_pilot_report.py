#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STAGE = "exotics_drug_dose_source_review_source_collection_controlled_pilot_report_v1"

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_source_collection_controlled_pilot_report.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_source_collection_controlled_pilot_report.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
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

MEDICATION_VALUE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
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
    path = ROOT / "backend" / "exotics_drug_dose_source_review_source_collection_controlled_pilot_report.py"
    spec = importlib.util.spec_from_file_location("exotics_controlled_pilot_report", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_required_files() -> None:
    for rel in REQUIRED_FILES:
        read(rel)


def assert_module_behavior() -> None:
    module = load_module()
    report = module.build_source_collection_controlled_pilot_report()
    if report.get("mode") != STAGE:
        fail("mode mismatch")
    if report.get("current_level") != "controlled_pilot_report_shell_only_not_collection_execution":
        fail("current_level mismatch")
    expected_rows = len(module.SPECIES_GROUPS) * len(module.REVIEW_DOMAINS)
    matrix = report.get("pilot_report_matrix") or []
    if len(matrix) != expected_rows:
        fail("pilot report matrix row count mismatch")
    for key in (
        "is_dose_engine",
        "is_prescription_engine",
        "is_treatment_plan_engine",
        "dose_output_enabled",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "collection_execution_started",
        "pilot_execution_allowed_now",
        "writes_database",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
        "returns_drug_dose",
        "returns_drug_route",
        "returns_drug_frequency",
    ):
        if report.get(key) is not False:
            fail("%s must be false" % key)
    for key in ("requires_human_review", "clinician_signoff_required", "not_client_facing"):
        if report.get(key) is not True:
            fail("%s must be true" % key)
    forbidden = set(report.get("forbidden_evidence_columns") or [])
    if not FORBIDDEN_COLUMNS.issubset(forbidden):
        fail("forbidden evidence columns missing from backend helper")
    for row in matrix:
        if row.get("source_collection_execution_status") != "not_started":
            fail("matrix row must keep source collection execution not_started")
        if row.get("numeric_value_capture_status") != "forbidden":
            fail("matrix row must forbid numeric value capture")
        if row.get("route_frequency_capture_status") != "forbidden":
            fail("matrix row must forbid route/frequency capture")


def assert_matrix_csv() -> None:
    path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_MATRIX_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 84:
        fail("expected 84 matrix rows, got %d" % len(rows))
    fieldnames = set(rows[0].keys()) if rows else set()
    if FORBIDDEN_COLUMNS.intersection(fieldnames):
        fail("matrix contains forbidden medication value columns: %s" % sorted(FORBIDDEN_COLUMNS.intersection(fieldnames)))
    species = {row.get("species_group") for row in rows}
    for required in ("rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish", "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider"):
        if required not in species:
            fail("missing species group in matrix: %s" % required)
    for row in rows:
        if row.get("source_collection_execution_status") != "not_started":
            fail("CSV matrix must keep source collection execution not_started")
        if row.get("go_no_go_status") != "NO_GO_FOR_DOSE_ENGINE":
            fail("CSV matrix must stay NO_GO_FOR_DOSE_ENGINE")


def assert_no_medication_values() -> None:
    for rel in REQUIRED_FILES[:5]:
        text = read(rel)
        if MEDICATION_VALUE_PATTERN.search(text):
            fail("medication value, route, or frequency-like text found in %s" % rel)


def assert_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "validate_exotics_drug_dose_source_review_source_collection_controlled_pilot_report.py" not in ci:
        fail("ci_static_checks missing controlled pilot report validator")
    if "Exotics Drug Dose Source Review Source Collection Controlled Pilot Report V1" not in smoke:
        fail("smoke script missing controlled pilot report block")
    if "validate_exotics_drug_dose_source_review_source_collection_controlled_pilot_report.py" not in smoke:
        fail("smoke script missing controlled pilot report validator")


def main() -> None:
    assert_required_files()
    assert_module_behavior()
    assert_matrix_csv()
    assert_no_medication_values()
    assert_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Source Collection Controlled Pilot Report V1")


if __name__ == "__main__":
    main()
