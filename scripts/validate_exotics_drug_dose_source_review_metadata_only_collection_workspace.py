#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

BACKEND = ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_collection_workspace.py"
DOC = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_V1.md"
MATRIX = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_MATRIX_V1.csv"
CHECKLIST = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GO_NO_GO_V1.csv"
CI = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

REQUIRED_FILES = [BACKEND, DOC, MATRIX, CHECKLIST, GO_NO_GO, CI, SMOKE]
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
FORBIDDEN_EXECUTION_MARKERS = [
    "db.add(",
    "db.commit(",
    "@router.",
    "FastAPI",
    "requests.post(",
    "httpx.post(",
    "OpenAI(",
]
FORBIDDEN_VALUE_COLUMNS = {
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


def read(path: Path) -> str:
    if not path.exists():
        fail("missing required file: %s" % path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def load_module() -> Any:
    py_compile.compile(str(BACKEND), doraise=True)
    spec = importlib.util.spec_from_file_location("metadata_only_workspace", str(BACKEND))
    if spec is None or spec.loader is None:
        fail("unable to load backend module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_text() -> None:
    for path in REQUIRED_FILES:
        if not path.exists():
            fail("missing file: %s" % path.relative_to(ROOT))
    backend_text = read(BACKEND)
    for marker in FORBIDDEN_EXECUTION_MARKERS:
        if marker in backend_text:
            fail("backend helper must remain artifact-only; forbidden marker: %s" % marker)
    doc_text = read(DOC)
    for needle in (
        "Exotics Drug Dose Source Review Metadata-only Collection Workspace V1",
        "metadata_only_collection_workspace_schema_only_not_execution",
        "source_review_status=metadata_only_workspace_defined_not_populated",
        "dose_output_enabled=false",
        "captures_numeric_dose_value=false",
        "captures_route_or_frequency_text=false",
        "stores_usable_medication_instruction=false",
        "collection_execution_started=false",
        "collection_execution_allowed_now=false",
        "writes_database=false",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_V1",
    ):
        if needle not in doc_text:
            fail("doc missing expected content: %s" % needle)


def assert_matrix() -> None:
    with MATRIX.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS)
    if len(rows) != expected_count:
        fail("matrix row count expected %d got %d" % (expected_count, len(rows)))
    header = set(rows[0].keys()) if rows else set()
    if header.intersection(FORBIDDEN_VALUE_COLUMNS):
        fail("matrix header contains forbidden value-capture columns: %s" % sorted(header.intersection(FORBIDDEN_VALUE_COLUMNS)))
    seen_species = {row.get("species_group") for row in rows}
    seen_domains = {row.get("review_domain") for row in rows}
    if seen_species != set(EXPECTED_SPECIES):
        fail("species mismatch: %s" % sorted(seen_species))
    if seen_domains != set(EXPECTED_DOMAINS):
        fail("review domain mismatch: %s" % sorted(seen_domains))
    for row in rows:
        if row.get("workspace_status") != "defined_not_populated":
            fail("workspace_status must be defined_not_populated")
        if row.get("source_collection_execution_status") != "not_started":
            fail("source collection execution must not start")
        if row.get("numeric_value_capture_status") != "blocked":
            fail("numeric value capture must be blocked")
        if row.get("route_frequency_capture_status") != "blocked":
            fail("route/frequency capture must be blocked")
        if row.get("usable_medication_instruction_status") != "blocked":
            fail("usable medication instruction capture must be blocked")
        if row.get("go_no_go_status") != "NO_GO_TO_SOURCE_COLLECTION_EXECUTION":
            fail("go_no_go_status must block source collection execution")


def assert_module_behavior() -> None:
    module = load_module()
    summary = module.build_metadata_only_collection_workspace_summary()
    if summary.get("mode") != "exotics_drug_dose_source_review_metadata_only_collection_workspace_v1":
        fail("mode mismatch")
    if summary.get("workspace_row_count") != len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS):
        fail("workspace row count mismatch")
    checks = {
        "writes_database": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }
    for key, expected in checks.items():
        if summary.get(key) is not expected:
            fail("summary[%s] expected %r got %r" % (key, expected, summary.get(key)))
    if summary.get("quality_gate", {}).get("status") != "PASS":
        fail("quality gate must PASS")


def assert_ci_and_smoke_hooks() -> None:
    ci = read(CI)
    smoke = read(SMOKE)
    if "Exotics Drug Dose Source Review Metadata-only Collection Workspace V1 static checks" not in ci:
        fail("ci_static_checks missing metadata-only workspace block")
    if "python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace.py" not in ci:
        fail("ci_static_checks missing metadata-only workspace validator command")
    if "Exotics Drug Dose Source Review Metadata-only Collection Workspace V1 smoke" not in smoke:
        fail("smoke missing metadata-only workspace block")
    if "validate_exotics_drug_dose_source_review_metadata_only_collection_workspace.py" not in smoke:
        fail("smoke missing metadata-only workspace validator")


def main() -> None:
    assert_files_and_text()
    assert_matrix()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Collection Workspace V1")


if __name__ == "__main__":
    main()
