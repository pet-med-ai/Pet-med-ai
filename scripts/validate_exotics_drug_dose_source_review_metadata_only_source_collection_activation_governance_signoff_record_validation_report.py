#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
MODE = "exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_validation_report_v1"
GOVERNANCE_DECISION = "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION"
NEXT = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_V1"

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
FORBIDDEN_VALUE_FIELDS = [
    "numeric_dose_value", "dose_unit", "route_text", "frequency_text", "duration_text",
    "prescription_direction", "treatment_protocol", "client_instruction", "copied_table_text", "copyrighted_full_text",
]
FILES = {
    "backend": ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_validation_report.py",
    "doc": ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_V1.md",
    "matrix": ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_MATRIX_V1.csv",
    "checklist": ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_CHECKLIST_V1.csv",
    "go_no_go": ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_GO_NO_GO_V1.csv",
    "ci": ROOT / "scripts" / "ci_static_checks.sh",
    "smoke": ROOT / "scripts" / "smoke_petmed.sh",
}


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail("missing file: %s" % path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def load_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        fail("missing csv: %s" % path.relative_to(ROOT))
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_backend_module():
    path = FILES["backend"]
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_activation_governance_signoff_record_validation_report", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_backend() -> None:
    text = read(FILES["backend"])
    required = [
        'MODE = "%s"' % MODE,
        'GOVERNANCE_DECISION = "%s"' % GOVERNANCE_DECISION,
        "build_report_row", "build_matrix", "quality_gate",
        '"writes_database": False',
        '"starts_source_collection_activation": False',
        '"starts_source_collection_execution": False',
        '"dose_output_enabled": False',
        '"captures_numeric_dose_value": False',
        '"captures_route_or_frequency_text": False',
        '"stores_usable_medication_instruction": False',
        '"activation_governance_signoff_record_validation_report_defined": True',
        '"activation_governance_signoff_record_validation_report_has_collection_results": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
    ]
    for needle in required:
        if needle not in text:
            fail("backend helper missing: %s" % needle)
    for forbidden in ("db.add(", "db.commit(", "requests.post(", "httpx.post(", "OpenAI("):
        if forbidden in text:
            fail("backend helper must be non-executing and read-only; forbidden marker: %s" % forbidden)
    for forbidden in FORBIDDEN_VALUE_FIELDS:
        if forbidden not in text:
            fail("backend forbidden value field not declared: %s" % forbidden)


def assert_module_behavior() -> None:
    module = load_backend_module()
    gate = module.quality_gate()
    if gate.get("mode") != MODE:
        fail("mode mismatch")
    if gate.get("governance_decision") != GOVERNANCE_DECISION:
        fail("governance decision mismatch")
    if gate.get("row_count") != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("row count mismatch")
    for key in [
        "writes_database",
        "dose_output_enabled",
        "captures_numeric_dose_value",
        "captures_route_or_frequency_text",
        "stores_usable_medication_instruction",
        "starts_source_collection_activation",
        "starts_source_collection_execution",
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
    ]:
        if gate.get(key) is not False:
            fail("safety flag must be false: %s" % key)
    for key in ["requires_human_review", "clinician_signoff_required", "not_client_facing"]:
        if gate.get(key) is not True:
            fail("safety flag must be true: %s" % key)
    rows = module.build_matrix()
    if len(rows) != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("backend matrix row count mismatch")


def assert_matrix() -> None:
    rows = load_rows(FILES["matrix"])
    if len(rows) != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("matrix row count mismatch: %d" % len(rows))
    pairs = {(row.get("species_group"), row.get("review_domain")) for row in rows}
    expected = {(species, domain) for species in SPECIES_GROUPS for domain in REVIEW_DOMAINS}
    if pairs != expected:
        fail("matrix species/domain coverage mismatch")
    header = set(rows[0].keys()) if rows else set()
    for forbidden in FORBIDDEN_VALUE_FIELDS:
        if forbidden in header:
            fail("forbidden field appears in matrix header: %s" % forbidden)
    for row in rows:
        if row.get("governance_decision") != GOVERNANCE_DECISION:
            fail("matrix row governance decision mismatch")
        if row.get("collection_activation_status") != "not_started":
            fail("collection activation must remain not_started")
        if row.get("collection_execution_status") != "not_started":
            fail("collection execution must remain not_started")
        if row.get("validation_report_has_collection_results") != "false":
            fail("validation report must not contain collection results")
        if row.get("numeric_value_capture_status") != "blocked_not_present":
            fail("numeric value capture must be blocked_not_present")
        if row.get("route_frequency_capture_status") != "blocked_not_present":
            fail("route/frequency capture must be blocked_not_present")
        if row.get("usable_medication_instruction_status") != "blocked_not_present":
            fail("usable medication instruction must be blocked_not_present")


def assert_docs_and_hooks() -> None:
    doc = read(FILES["doc"])
    for needle in [
        "Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record Validation Report V1",
        MODE,
        GOVERNANCE_DECISION,
        "activation_governance_signoff_record_validation_report_defined=true",
        "activation_governance_signoff_record_validation_report_has_collection_results=false",
        "collection_activation_allowed_now=false",
        "collection_execution_started=false",
        "dose_output_enabled=false",
        NEXT,
    ]:
        if needle not in doc:
            fail("doc missing: %s" % needle)
    for forbidden in FORBIDDEN_VALUE_FIELDS:
        if forbidden not in doc:
            fail("doc missing forbidden field boundary: %s" % forbidden)
    checklist = read(FILES["checklist"])
    go_no_go = read(FILES["go_no_go"])
    if "no_numeric_dose_capture" not in checklist:
        fail("checklist missing no_numeric_dose_capture")
    if "NO_GO" not in go_no_go or "source_collection_activation" not in go_no_go:
        fail("go/no-go missing source collection activation NO_GO")
    ci = read(FILES["ci"])
    smoke = read(FILES["smoke"])
    validator_cmd = "python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_validation_report.py"
    if validator_cmd not in ci:
        fail("ci_static_checks missing validator command")
    if validator_cmd not in smoke:
        fail("smoke missing validator command")


def main() -> None:
    assert_backend()
    assert_module_behavior()
    assert_matrix()
    assert_docs_and_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record Validation Report V1")


if __name__ == "__main__":
    main()
