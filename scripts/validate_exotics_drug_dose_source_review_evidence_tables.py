#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODE = "exotics_drug_dose_source_review_evidence_tables_v1"

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_evidence_tables.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_SCHEMA_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_evidence_tables.py",
]

SPECIES = {
    "rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish",
    "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider",
}
DOMAINS = {
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
}
BLOCKED_COLUMNS = {
    "numeric_dose_value",
    "dose_unit",
    "route_text",
    "frequency_text",
    "duration_text",
    "prescription_direction",
    "treatment_protocol",
    "client_instruction",
}

# Applies to generated docs and CSV files, not this validator source.
FORBIDDEN_DOSE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|ml|iu|units)\b|\bq\d{1,2}h\b|\b(?:sid|bid|tid|qid|po|iv|im|sc|sq)\b",
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
    path = ROOT / "backend" / "exotics_drug_dose_source_review_evidence_tables.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_drug_dose_source_review_evidence_tables", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load evidence tables module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module

def assert_files_and_text() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    doc = read("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_V1.md")
    for needle in (
        "Exotics Drug Dose Source Review Evidence Tables V1",
        "evidence_tables_schema_only_not_dose_engine",
        "is_dose_engine=false",
        "dose_output_enabled=false",
        "no prescription",
        "no drug dose",
        "decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_V1",
    ):
        if needle not in doc:
            fail("doc missing expected text: %s" % needle)

    scan_targets = [
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_V1.md",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_MATRIX_V1.csv",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_SCHEMA_V1.csv",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_CHECKLIST_V1.csv",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_GO_NO_GO_V1.csv",
    ]
    for rel in scan_targets:
        text = read(rel)
        if FORBIDDEN_DOSE_PATTERN.search(text):
            fail("forbidden usable medication instruction pattern in %s" % rel)

def assert_matrix() -> None:
    path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_MATRIX_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(SPECIES) * len(DOMAINS):
        fail("matrix row count mismatch: %s" % len(rows))
    seen_species = {row.get("species_group") for row in rows}
    seen_domains = {row.get("review_domain") for row in rows}
    if seen_species != SPECIES:
        fail("matrix species mismatch: %s" % sorted(seen_species))
    if seen_domains != DOMAINS:
        fail("matrix domain mismatch: %s" % sorted(seen_domains))
    for row in rows:
        for key in (
            "numeric_dose_value_column_present",
            "route_text_column_present",
            "frequency_text_column_present",
            "prescription_direction_column_present",
            "treatment_protocol_column_present",
        ):
            if row.get(key) != "false":
                fail("%s must be false for %s/%s" % (key, row.get("species_group"), row.get("review_domain")))
        if row.get("human_review_required") != "true":
            fail("human_review_required must be true")

def assert_schema() -> None:
    path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_SCHEMA_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_name = {row.get("column_name"): row for row in rows}
    for name in BLOCKED_COLUMNS:
        row = by_name.get(name)
        if not row:
            fail("missing blocked schema column: %s" % name)
        if row.get("allowed") != "false":
            fail("blocked schema column must have allowed=false: %s" % name)
        if row.get("column_status") != "blocked":
            fail("blocked schema column must have column_status=blocked: %s" % name)

def assert_module_behavior() -> None:
    module = load_module()
    result = module.build_evidence_table_schema(species_group="rabbit", review_domain="antimicrobial_source_review")
    if result.get("mode") != MODE:
        fail("mode mismatch")
    if result.get("is_dose_engine") is not False:
        fail("must not be dose engine")
    if result.get("is_prescription_engine") is not False:
        fail("must not be prescription engine")
    if result.get("dose_output_enabled") is not False:
        fail("dose output must be disabled")
    if result.get("returns_drug_dose") is not False:
        fail("must not return drug dose")
    if result.get("captures_numeric_dose_value") is not False:
        fail("must not capture numeric dose value")
    if result.get("captures_route_or_frequency_text") is not False:
        fail("must not capture route/frequency text")
    if result.get("stores_usable_dose_content") is not False:
        fail("must not store usable dose content")
    if result.get("writes_database") is not False:
        fail("must not write database")
    blocked = result.get("blocked_columns") or []
    for name in BLOCKED_COLUMNS:
        if name not in blocked:
            fail("blocked column missing from module schema: %s" % name)
    manifest = module.build_evidence_table_manifest()
    if len(manifest) != len(SPECIES) * len(DOMAINS):
        fail("module manifest count mismatch")
    for row in manifest:
        if row.get("numeric_dose_value_column_present") is not False:
            fail("module manifest must keep numeric dose columns absent")

def assert_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "validate_exotics_drug_dose_source_review_evidence_tables.py" not in ci:
        fail("ci_static_checks missing evidence tables validator")
    if "Exotics Drug Dose Source Review Evidence Tables V1" not in smoke:
        fail("smoke missing evidence tables block")

def main() -> None:
    assert_files_and_text()
    assert_matrix()
    assert_schema()
    assert_module_behavior()
    assert_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Evidence Tables V1")

if __name__ == "__main__":
    main()
