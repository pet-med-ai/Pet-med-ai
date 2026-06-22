#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/diagnostic_problem_list.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_V1.md",
    "docs/clinical_data/DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_CHECKLIST_V1.csv",
    "docs/clinical_data/DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_GO_NO_GO_V1.csv",
    "scripts/validate_diagnostic_assistance_problem_list.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

FORBIDDEN_PROVIDER_TOKENS = ["openai", "anthropic", "requests.", "httpx.", "urllib.request", "boto3"]
FORBIDDEN_WRITE_TOKENS = ["db.add(", "session.add(", ".commit(", ".flush(", "db.merge(", "session.merge(", "db.delete(", "session.delete(", "insert(", "update(", "delete("]


def fail(message: str) -> None:
    print("FAIL:", message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    return path.read_text(encoding="utf-8")


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail("%s missing %r" % (label, needle))


def assert_not_contains_lower(text: str, forbidden: List[str], label: str) -> None:
    lower = text.lower()
    for token in forbidden:
        if token.lower() in lower:
            fail("%s contains forbidden token %r" % (label, token))


def compile_required_python() -> None:
    for rel in ("backend/diagnostic_problem_list.py", "scripts/validate_diagnostic_assistance_problem_list.py"):
        py_compile.compile(str(ROOT / rel), doraise=True)


def load_problem_module():
    module_path = ROOT / "backend" / "diagnostic_problem_list.py"
    spec = importlib.util.spec_from_file_location("diagnostic_problem_list", str(module_path))
    if spec is None or spec.loader is None:
        fail("cannot load diagnostic_problem_list module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_csv(rel: str, required_columns: List[str], min_rows: int) -> None:
    path = ROOT / rel
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < min_rows:
        fail("%s has too few rows" % rel)
    for col in required_columns:
        if col not in rows[0]:
            fail("%s missing CSV column %s" % (rel, col))


def validate_runtime_contract() -> None:
    module = load_problem_module()
    flags = module.diagnostic_problem_list_safety_flags()
    for key in (
        "writes_database", "creates_case", "updates_case", "creates_diagnostic_report",
        "updates_diagnostic_report", "writes_diagnostic_report", "creates_observation",
        "updates_observation", "creates_imaging_study", "updates_imaging_study",
        "creates_audit_log", "writes_audit_log", "generates_final_diagnosis",
        "generates_confirmed_diagnosis", "generates_definitive_diagnosis",
        "creates_treatment_plan", "writes_treatment_plan", "treatment_recommendation",
        "creates_prescription", "writes_prescription", "drug_dose_recommendation",
        "returns_drug_dose", "returns_drug_route", "returns_drug_frequency",
        "client_facing", "releases_to_client", "calls_external_ai", "calls_external_provider",
        "sends_external_message", "executes_real_import", "executes_real_lab_ingest",
        "executes_real_dicom_ingest", "executes_real_device_ingest",
    ):
        if flags.get(key) is not False:
            fail("safety flag must be false: %s" % key)
    for key in (
        "read_only", "dry_run", "requires_human_review", "clinician_signoff_required",
        "problem_list_preview_only", "not_a_diagnosis", "not_a_treatment_plan",
        "not_a_prescription", "not_client_facing",
    ):
        if flags.get(key) is not True:
            fail("safety flag must be true: %s" % key)

    payload = {
        "chief_complaint": "Vomiting for 2 days with reduced appetite",
        "history": {"duration": "2 days", "energy": "quiet"},
        "lab_summary": {"abnormal_findings": [{"display_name": "ALT", "abnormal_flag": "high", "interpretation": "elevated liver enzyme; clinician review required"}]},
        "imaging_summary": {"summary": {"impression": "abdominal imaging finding requires clinician review"}},
        "clinician_review_workflow": {"review_workflow": {"status": "pending_clinician_review"}},
        "treatment_boundary": {"boundary": {"decision": "review_only"}},
        "drug_dose_safety": {"framework": {"decision": "blocked_for_dose_output"}, "warnings": ["sample medication 2 mg/kg PO q12h must not be returned"]},
        "requested_action": "return_drug_dose",
    }
    result = module.build_diagnostic_assistance_problem_list(payload, case_id=123, case_context={"case_id": 123, "patient_name": "DryRun", "species": "canine"})
    if result.get("mode") != "diagnostic_assistance_problem_list_v1":
        fail("wrong mode")
    if not isinstance(result.get("problem_list_preview"), list):
        fail("problem_list_preview must be a list")
    if len(result["problem_list_preview"]) < 3:
        fail("expected at least 3 problem preview items")
    if not isinstance(result.get("evidence_sources"), list):
        fail("evidence_sources must be a list")
    if result.get("quality_gate", {}).get("status") != "PASS":
        fail("quality_gate status must be PASS")
    if result.get("writes_database") is not False:
        fail("writes_database must be false")
    for key in ("not_a_diagnosis", "not_a_treatment_plan", "not_a_prescription", "not_client_facing", "requires_human_review"):
        if result.get(key) is not True:
            fail("%s must be true" % key)
    forbidden_result_keys = {"final_diagnosis", "confirmed_diagnosis", "definitive_diagnosis", "treatment_plan", "prescription", "drug_dose", "drug_route", "drug_frequency"}
    if forbidden_result_keys.intersection(set(result.keys())):
        fail("result exposes forbidden clinical conclusion/action keys")
    rendered = repr(result).lower()
    for token in ("mg/kg", " q12h", " po ", "maropitant", "ondansetron"):
        if token in rendered:
            fail("result leaked dose/route/frequency/medication text: %s" % token)
    for item in result["problem_list_preview"]:
        for key in ("requires_clinician_review", "not_a_diagnosis", "not_a_treatment_plan", "not_a_prescription", "not_client_facing"):
            if item.get(key) is not True:
                fail("problem item missing true boundary flag: %s" % key)
        if "severity_hint" not in item:
            fail("problem item missing severity_hint")
        if not isinstance(item.get("evidence_sources"), list) or not item["evidence_sources"]:
            fail("problem item missing evidence_sources")


def main() -> int:
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            fail("missing required file: %s" % rel)
    compile_required_python()
    builder = read("backend/diagnostic_problem_list.py")
    api = read("backend/diagnostic_data_api.py")
    docs = read("docs/clinical_data/DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_V1.md")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    assert_contains(builder, "DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_MODE", "builder")
    assert_contains(builder, "def build_diagnostic_assistance_problem_list", "builder")
    assert_contains(builder, "def diagnostic_problem_list_safety_flags", "builder")
    assert_contains(builder, '"writes_database": False', "builder")
    assert_contains(builder, '"requires_human_review": True', "builder")
    assert_contains(builder, '"not_a_diagnosis": True', "builder")
    assert_contains(builder, '"not_a_treatment_plan": True', "builder")
    assert_contains(builder, '"not_a_prescription": True', "builder")
    assert_contains(builder, '"not_client_facing": True', "builder")
    assert_not_contains_lower(builder, FORBIDDEN_PROVIDER_TOKENS, "builder")
    assert_not_contains_lower(builder, FORBIDDEN_WRITE_TOKENS, "builder")
    assert_contains(api, '@router.post("/dry-run/problem-list/build"', "diagnostic_data_api")
    assert_contains(api, "build_diagnostic_assistance_problem_list", "diagnostic_data_api")
    endpoint_block_start = api.find("# --- Diagnostic Assistance Problem List V1 endpoint: start ---")
    endpoint_block_end = api.find("# --- Diagnostic Assistance Problem List V1 endpoint: end ---")
    if endpoint_block_start < 0 or endpoint_block_end < endpoint_block_start:
        fail("endpoint marker block missing")
    endpoint_block = api[endpoint_block_start:endpoint_block_end]
    assert_not_contains_lower(endpoint_block, FORBIDDEN_WRITE_TOKENS, "problem-list endpoint")
    for phrase in ("dry-run problem-list preview", "not automatic diagnosis", "must not write any database row", "No drug dose", "Differential Diagnosis Candidates V1"):
        assert_contains(docs, phrase, "stage doc")
    assert_contains(ci, "validate_diagnostic_assistance_problem_list.py", "ci_static_checks")
    assert_contains(smoke, "problem-list/build", "smoke_petmed")
    assert_contains(smoke, "validate_diagnostic_assistance_problem_list.py", "smoke_petmed")
    validate_csv("docs/clinical_data/DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_CHECKLIST_V1.csv", ["area", "item", "required", "evidence", "pass_condition", "status"], 8)
    validate_csv("docs/clinical_data/DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_GO_NO_GO_V1.csv", ["gate", "go_condition", "no_go_condition", "evidence", "status"], 8)
    validate_runtime_contract()
    print("Diagnostic Assistance Problem List V1 validator PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
