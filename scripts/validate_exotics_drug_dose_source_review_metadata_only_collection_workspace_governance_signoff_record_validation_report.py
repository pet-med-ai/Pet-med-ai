#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = "Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record Validation Report V1"
MODE = "exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report_v1"
NEXT_DECISION = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_V1"
SPECIES_GROUPS = ["rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish", "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider"]
REVIEW_DOMAINS = ["analgesia_and_pain_control_source_review", "antimicrobial_source_review", "antiparasitic_source_review", "fluid_and_supportive_care_source_review", "sedation_anesthesia_risk_source_review", "emergency_stabilization_source_review"]
EXPECTED_ROWS = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)

FILES = [
    "backend/exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report.py",
]

FORBIDDEN_RUNTIME_TOKENS = [
    "db.add(", "db.commit(", "db.delete(", "requests.post(", "httpx.post(", "OpenAI(",
    "create_prescription(", "write_prescription(", "create_treatment_plan(",
]


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
    rel = "backend/exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report.py"
    path = ROOT / rel
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_governance_validation_report", str(path))
    if spec is None or spec.loader is None:
        fail("cannot load backend helper module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def check_files() -> None:
    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)


def check_backend_module() -> None:
    module = load_module()
    report = module.build_governance_signoff_record_validation_report()
    if report.get("mode") != MODE:
        fail("mode mismatch")
    if report.get("current_level") != "metadata_only_workspace_governance_signoff_record_validation_report_schema_only_not_collection_execution":
        fail("current_level mismatch")
    if report.get("source_review_status") != "metadata_only_workspace_governance_signoff_record_validation_report_defined_no_collection_results":
        fail("source_review_status mismatch")
    if report.get("governance_decision") != "NO_GO_TO_COLLECTION_EXECUTION":
        fail("governance decision must remain NO_GO_TO_COLLECTION_EXECUTION")
    if report.get("next_decision") != NEXT_DECISION:
        fail("next decision mismatch")
    false_keys = [
        "writes_database", "creates_case", "updates_case", "creates_diagnostic_report", "updates_diagnostic_report",
        "creates_observation", "updates_observation", "creates_imaging_study", "updates_imaging_study",
        "writes_ai_summary", "writes_audit_log", "source_collection_execution", "collection_execution_started",
        "collection_execution_allowed_now", "is_dose_engine", "is_prescription_engine", "is_treatment_plan_engine",
        "dose_output_enabled", "captures_numeric_dose_value", "captures_route_or_frequency_text",
        "stores_usable_medication_instruction", "generates_final_diagnosis", "creates_treatment_plan",
        "writes_prescription", "returns_drug_dose", "returns_drug_route", "returns_drug_frequency",
        "client_facing", "calls_external_ai", "calls_external_provider", "executes_real_import",
        "executes_real_lab_ingest", "executes_real_dicom_ingest", "executes_real_device_ingest",
    ]
    for key in false_keys:
        if report.get(key) is not False:
            fail("expected false safety flag: %s" % key)
    true_keys = [
        "read_only", "dry_run", "not_client_facing", "requires_human_review", "clinician_signoff_required",
        "metadata_only_workspace_defined", "metadata_only_workspace_validation_defined",
        "metadata_only_workspace_validation_report_defined", "governance_signoff_defined",
        "governance_signoff_record_defined", "governance_signoff_record_validation_defined",
        "governance_signoff_record_validation_report_defined",
    ]
    for key in true_keys:
        if report.get(key) is not True:
            fail("expected true flag: %s" % key)
    matrix = report.get("matrix")
    if not isinstance(matrix, list) or len(matrix) != EXPECTED_ROWS:
        fail("matrix row count mismatch")
    seen = set()
    for row in matrix:
        pair = (row.get("species_group"), row.get("review_domain"))
        seen.add(pair)
        if row.get("go_no_go_status") != "NO_GO_TO_COLLECTION_EXECUTION":
            fail("matrix go_no_go_status must remain NO_GO_TO_COLLECTION_EXECUTION")
        if row.get("numeric_value_capture_status") != "blocked":
            fail("numeric value capture must be blocked")
        if row.get("route_frequency_capture_status") != "blocked":
            fail("route/frequency capture must be blocked")
        if row.get("usable_medication_instruction_status") != "blocked":
            fail("usable medication instruction must be blocked")
        if row.get("source_collection_execution_status") != "not_started":
            fail("source collection execution must be not_started")
    expected_pairs = set((species, domain) for species in SPECIES_GROUPS for domain in REVIEW_DOMAINS)
    if seen != expected_pairs:
        fail("matrix species/domain coverage mismatch")


def check_matrix_csv() -> None:
    path = ROOT / "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_MATRIX_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_ROWS:
        fail("CSV matrix row count mismatch")
    required_headers = {"validation_report_id", "species_group", "review_domain", "validation_report_status", "numeric_value_capture_status", "route_frequency_capture_status", "usable_medication_instruction_status", "source_collection_execution_status", "go_no_go_status"}
    if not rows or not required_headers.issubset(set(rows[0].keys())):
        fail("CSV matrix missing required headers")
    for row in rows:
        if row.get("go_no_go_status") != "NO_GO_TO_COLLECTION_EXECUTION":
            fail("CSV go_no_go_status mismatch")
        if row.get("numeric_value_capture_status") != "blocked":
            fail("CSV numeric value capture must be blocked")
        if row.get("route_frequency_capture_status") != "blocked":
            fail("CSV route/frequency capture must be blocked")
        if row.get("usable_medication_instruction_status") != "blocked":
            fail("CSV usable medication instruction must be blocked")


def check_text_contracts() -> None:
    doc = read("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_V1.md")
    for needle in [
        STAGE, "NO_GO_TO_COLLECTION_EXECUTION", "is_dose_engine=false", "is_prescription_engine=false",
        "is_treatment_plan_engine=false", "dose_output_enabled=false", "captures_numeric_dose_value=false",
        "captures_route_or_frequency_text=false", "stores_usable_medication_instruction=false", "no DB write",
        "no final diagnosis", "no treatment plan", "no prescription", "no drug dose", "no drug route",
        "no drug frequency", NEXT_DECISION,
    ]:
        if needle not in doc:
            fail("doc missing expected text: %s" % needle)
    backend = read("backend/exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report.py")
    for token in FORBIDDEN_RUNTIME_TOKENS:
        if token in backend:
            fail("backend helper must remain read-only and non-provider-calling: %s" % token)


def check_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    validator_name = "validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report.py"
    if validator_name not in ci:
        fail("ci_static_checks missing validator hook")
    if validator_name not in smoke:
        fail("smoke_petmed missing validator hook")


def main() -> None:
    check_files()
    check_backend_module()
    check_matrix_csv()
    check_text_contracts()
    check_hooks()
    print("VALIDATOR=PASS %s" % STAGE)


if __name__ == "__main__":
    main()
