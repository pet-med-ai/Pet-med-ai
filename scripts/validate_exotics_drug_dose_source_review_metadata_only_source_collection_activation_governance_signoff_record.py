#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
MODE = "exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_v1"
GOVERNANCE_DECISION = "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION"
NEXT = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_V1"

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
]

FILES = {
    "backend": ROOT / "backend" / "exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record.py",
    "doc": ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_V1.md",
    "matrix": ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_MATRIX_V1.csv",
    "checklist": ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_CHECKLIST_V1.csv",
    "go_no_go": ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_GO_NO_GO_V1.csv",
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
    spec = importlib.util.spec_from_file_location("exotics_activation_governance_signoff_record", str(path))
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
        "build_signoff_record_row",
        "build_matrix",
        "quality_gate",
        '"writes_database": False',
        '"is_dose_engine": False',
        '"is_prescription_engine": False',
        '"is_treatment_plan_engine": False',
        '"dose_output_enabled": False',
        '"captures_numeric_dose_value": False',
        '"captures_route_or_frequency_text": False',
        '"stores_usable_medication_instruction": False',
        '"collection_activation_allowed_now": False',
        '"collection_execution_started": False',
        '"collection_execution_allowed_now": False',
        '"pilot_execution_allowed_now": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
    ]
    for item in required:
        if item not in text:
            fail("backend missing expected marker: %s" % item)
    module = load_backend_module()
    gate = module.quality_gate()
    if gate.get("mode") != MODE:
        fail("backend quality gate mode mismatch")
    if gate.get("governance_decision") != GOVERNANCE_DECISION:
        fail("backend governance decision mismatch")
    if gate.get("collection_activation_allowed_now") is not False:
        fail("collection activation must remain false")
    if gate.get("dose_output_enabled") is not False:
        fail("dose output must remain false")
    if len(module.build_matrix()) != len(SPECIES_GROUPS) * len(REVIEW_DOMAINS):
        fail("backend matrix row count mismatch")


def assert_matrix() -> None:
    rows = load_rows(FILES["matrix"])
    expected_count = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)
    if len(rows) != expected_count:
        fail("matrix row count expected %d got %d" % (expected_count, len(rows)))
    headers = set(rows[0].keys()) if rows else set()
    for forbidden in FORBIDDEN_VALUE_FIELDS:
        if forbidden in headers:
            fail("matrix has forbidden header: %s" % forbidden)
    seen = set()
    for row in rows:
        species = row.get("species_group")
        domain = row.get("review_domain")
        if species not in SPECIES_GROUPS:
            fail("unexpected species_group: %r" % species)
        if domain not in REVIEW_DOMAINS:
            fail("unexpected review_domain: %r" % domain)
        key = (species, domain)
        if key in seen:
            fail("duplicate matrix row: %r" % (key,))
        seen.add(key)
        if row.get("governance_decision") != GOVERNANCE_DECISION:
            fail("governance decision mismatch in row")
        if row.get("collection_activation_status") != "not_started":
            fail("collection activation must be not_started")
        if row.get("collection_execution_status") != "not_started":
            fail("collection execution must be not_started")
        blob = " ".join(str(value) for value in row.values())
        for forbidden in FORBIDDEN_VALUE_FIELDS:
            if forbidden in blob:
                fail("matrix cell contains forbidden token: %s" % forbidden)


def assert_docs_and_hooks() -> None:
    doc = read(FILES["doc"])
    required_doc = [
        "Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record V1",
        GOVERNANCE_DECISION,
        "collection_activation_allowed_now=false",
        "collection_execution_started=false",
        "no drug dose",
        "no drug route",
        "no drug frequency",
        NEXT,
    ]
    for item in required_doc:
        if item not in doc:
            fail("doc missing: %s" % item)
    checklist = load_rows(FILES["checklist"])
    if not checklist:
        fail("checklist empty")
    go_no_go = load_rows(FILES["go_no_go"])
    if not go_no_go:
        fail("go/no-go empty")
    ci = read(FILES["ci"])
    smoke = read(FILES["smoke"])
    validator_name = "validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record.py"
    if validator_name not in ci:
        fail("ci_static_checks missing validator hook")
    if validator_name not in smoke:
        fail("smoke missing validator hook")


def main() -> None:
    for path in FILES.values():
        if not path.exists():
            fail("missing required file: %s" % path.relative_to(ROOT))
    assert_backend()
    assert_matrix()
    assert_docs_and_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record V1")


if __name__ == "__main__":
    main()
