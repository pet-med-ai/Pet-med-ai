#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/differential_diagnosis_candidates.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/DIFFERENTIAL_DIAGNOSIS_CANDIDATES_V1.md",
    "docs/clinical_data/DIFFERENTIAL_DIAGNOSIS_CANDIDATES_CHECKLIST_V1.csv",
    "docs/clinical_data/DIFFERENTIAL_DIAGNOSIS_CANDIDATES_GO_NO_GO_V1.csv",
    "scripts/validate_differential_diagnosis_candidates.py",
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


def assert_not_contains_lower(text: str, needles, label: str) -> None:
    lowered = text.lower()
    for needle in needles:
        if needle.lower() in lowered:
            fail("%s contains forbidden token %r" % (label, needle))


def compile_required_python() -> None:
    for rel in (
        "backend/differential_diagnosis_candidates.py",
        "backend/diagnostic_data_api.py",
        "scripts/validate_differential_diagnosis_candidates.py",
    ):
        try:
            py_compile.compile(str(ROOT / rel), doraise=True)
        except py_compile.PyCompileError as exc:
            fail("py_compile failed for %s: %s" % (rel, exc))


def load_candidate_module():
    path = ROOT / "backend" / "differential_diagnosis_candidates.py"
    spec = importlib.util.spec_from_file_location("differential_diagnosis_candidates", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load differential_diagnosis_candidates module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_csv(rel: str, expected_headers, minimum_rows: int) -> None:
    path = ROOT / rel
    if not path.exists():
        fail("missing csv: %s" % rel)
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        fail("csv has no rows: %s" % rel)
    if list(rows[0].keys()) != list(expected_headers):
        fail("csv headers mismatch for %s" % rel)
    if len(rows) < minimum_rows:
        fail("csv row count too small for %s" % rel)


def walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            for nested in walk_dicts(child):
                yield nested
    elif isinstance(value, list):
        for child in value:
            for nested in walk_dicts(child):
                yield nested


def validate_runtime_contract() -> None:
    module = load_candidate_module()
    flags = module.differential_diagnosis_candidates_safety_flags()
    for key in (
        "writes_database", "creates_case", "updates_case", "creates_diagnostic_report",
        "updates_diagnostic_report", "writes_diagnostic_report", "writes_ai_summary",
        "creates_observation", "updates_observation", "creates_imaging_study",
        "updates_imaging_study", "creates_audit_log", "writes_audit_log",
        "generates_final_diagnosis", "generates_confirmed_diagnosis",
        "generates_definitive_diagnosis", "generates_diagnostic_conclusion",
        "ranks_candidates_as_final_diagnosis", "returns_probability",
        "returns_numeric_confidence", "creates_treatment_plan", "writes_treatment_plan",
        "treatment_recommendation", "creates_prescription", "writes_prescription",
        "drug_dose_recommendation", "returns_drug_dose", "returns_drug_route",
        "returns_drug_frequency", "client_facing", "releases_to_client",
        "calls_external_ai", "calls_external_provider", "sends_external_message",
        "executes_real_import", "executes_real_lab_ingest", "executes_real_dicom_ingest",
        "executes_real_device_ingest",
    ):
        if flags.get(key) is not False:
            fail("safety flag must be false: %s" % key)
    for key in (
        "read_only", "dry_run", "requires_human_review", "clinician_signoff_required",
        "differential_candidates_preview_only", "not_a_diagnosis",
        "not_a_final_diagnosis", "not_a_confirmed_diagnosis",
        "not_a_definitive_diagnosis", "not_a_treatment_plan",
        "not_a_prescription", "not_client_facing",
    ):
        if flags.get(key) is not True:
            fail("safety flag must be true: %s" % key)

    payload = {
        "problem_list_preview": [
            {
                "problem_id": "problem-001",
                "category": "presenting_complaint",
                "title": "Vomiting and reduced appetite require clinician review",
                "severity_hint": "medium",
                "evidence_sources": [
                    {"source_type": "case", "field": "chief_complaint", "snippet": "Vomiting for 2 days with reduced appetite"},
                    {"source_type": "history", "field": "duration", "snippet": "Quiet and less active"},
                ],
            },
            {
                "problem_id": "problem-002",
                "category": "lab_abnormality",
                "title": "Laboratory abnormality requires clinician review: ALT",
                "severity_hint": "medium",
                "evidence_sources": [
                    {"source_type": "lab_abnormal_summary", "field": "interpretation", "snippet": "ALT high; liver enzyme pattern requires review"},
                ],
            },
            {
                "problem_id": "problem-003",
                "category": "imaging_abnormality",
                "title": "Abdominal ultrasound imaging finding requires clinician review",
                "severity_hint": "high",
                "evidence_sources": [
                    {"source_type": "imaging_report_summary", "field": "impression", "snippet": "Abdominal imaging lesion noted; sample medication 2 mg/kg PO q12h must not be returned"},
                ],
            },
        ],
        "requested_action": "return_drug_dose",
    }
    result = module.build_differential_diagnosis_candidates(payload, case_id=123, case_context={"case_id": 123, "patient_name": "DryRun", "species": "canine"})
    if result.get("mode") != "differential_diagnosis_candidates_v1":
        fail("wrong mode")
    if result.get("writes_database") is not False:
        fail("writes_database must be false")
    for key in (
        "not_a_diagnosis", "not_a_final_diagnosis", "not_a_confirmed_diagnosis",
        "not_a_definitive_diagnosis", "not_a_treatment_plan", "not_a_prescription",
        "not_client_facing", "requires_human_review", "clinician_signoff_required",
    ):
        if result.get(key) is not True:
            fail("%s must be true" % key)
    candidates = result.get("differential_diagnosis_candidates_preview")
    if not isinstance(candidates, list):
        fail("differential_diagnosis_candidates_preview must be a list")
    if len(candidates) < 2:
        fail("expected at least 2 candidate preview items")
    if result.get("quality_gate", {}).get("status") != "PASS":
        fail("quality_gate status must be PASS")
    if result.get("quality_gate", {}).get("dangerous_requested_action_blocked") is not True:
        fail("dangerous requested action should be blocked")
    forbidden_exact_keys = {
        "final_diagnosis", "confirmed_diagnosis", "definitive_diagnosis",
        "diagnostic_conclusion", "treatment_plan", "prescription",
        "drug_dose", "drug_route", "drug_frequency", "probability",
        "numeric_confidence", "confidence_score",
    }
    for mapping in walk_dicts(result):
        exposed = forbidden_exact_keys.intersection(set(mapping.keys()))
        if exposed:
            fail("result exposes forbidden exact keys: %s" % sorted(exposed))
    rendered = repr(result).lower()
    for token in ("mg/kg", " q12h", " po ", "maropitant", "ondansetron"):
        if token in rendered:
            fail("result leaked dose/route/frequency/medication text: %s" % token)
    for item in candidates:
        if item.get("candidate_type") != "differential_candidate_preview":
            fail("candidate_type must be differential_candidate_preview")
        for key in (
            "requires_clinician_review", "clinician_signoff_required", "not_a_diagnosis",
            "not_a_final_diagnosis", "not_a_confirmed_diagnosis",
            "not_a_definitive_diagnosis", "not_a_treatment_plan",
            "not_a_prescription", "not_client_facing",
        ):
            if item.get(key) is not True:
                fail("candidate item missing true boundary flag: %s" % key)
        for required in ("candidate_label", "system_category", "evidence_fit_hint", "severity_hint", "supporting_evidence_sources", "contradicting_or_missing_evidence"):
            if required not in item:
                fail("candidate item missing %s" % required)
        if not isinstance(item.get("supporting_evidence_sources"), list) or not item["supporting_evidence_sources"]:
            fail("candidate item missing supporting evidence")
        if item.get("evidence_fit_hint") not in {
            "strong_signal_for_review", "moderate_signal_for_review",
            "limited_signal_for_review", "insufficient_signal",
        }:
            fail("invalid evidence_fit_hint")


def main() -> int:
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            fail("missing required file: %s" % rel)
    compile_required_python()
    builder = read("backend/differential_diagnosis_candidates.py")
    api = read("backend/diagnostic_data_api.py")
    docs = read("docs/clinical_data/DIFFERENTIAL_DIAGNOSIS_CANDIDATES_V1.md")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    assert_contains(builder, "DIFFERENTIAL_DIAGNOSIS_CANDIDATES_MODE", "builder")
    assert_contains(builder, "def build_differential_diagnosis_candidates", "builder")
    assert_contains(builder, "def differential_diagnosis_candidates_safety_flags", "builder")
    assert_contains(builder, '"writes_database": False', "builder")
    assert_contains(builder, '"requires_human_review": True', "builder")
    assert_contains(builder, '"not_a_diagnosis": True', "builder")
    assert_contains(builder, '"not_a_treatment_plan": True', "builder")
    assert_contains(builder, '"not_a_prescription": True', "builder")
    assert_contains(builder, '"not_client_facing": True', "builder")
    assert_contains(builder, '"returns_probability": False', "builder")
    assert_contains(builder, '"returns_numeric_confidence": False', "builder")
    assert_not_contains_lower(builder, FORBIDDEN_PROVIDER_TOKENS, "builder")
    assert_not_contains_lower(builder, FORBIDDEN_WRITE_TOKENS, "builder")
    assert_contains(api, '@router.post("/dry-run/differential-diagnosis/candidates/build"', "diagnostic_data_api")
    assert_contains(api, "build_differential_diagnosis_candidates", "diagnostic_data_api")
    endpoint_block_start = api.find("# --- Differential Diagnosis Candidates V1 endpoint: start ---")
    endpoint_block_end = api.find("# --- Differential Diagnosis Candidates V1 endpoint: end ---")
    if endpoint_block_start < 0 or endpoint_block_end < endpoint_block_start:
        fail("endpoint marker block missing")
    endpoint_block = api[endpoint_block_start:endpoint_block_end]
    assert_not_contains_lower(endpoint_block, FORBIDDEN_WRITE_TOKENS, "differential candidates endpoint")
    for phrase in (
        "not automatic diagnosis", "must not write any database row",
        "No final diagnosis", "No treatment plan", "No drug dose",
        "Diagnostic Reasoning Evidence Trace V1",
    ):
        assert_contains(docs, phrase, "stage doc")
    assert_contains(ci, "validate_differential_diagnosis_candidates.py", "ci_static_checks")
    assert_contains(smoke, "differential-diagnosis/candidates/build", "smoke_petmed")
    assert_contains(smoke, "validate_differential_diagnosis_candidates.py", "smoke_petmed")
    validate_csv("docs/clinical_data/DIFFERENTIAL_DIAGNOSIS_CANDIDATES_CHECKLIST_V1.csv", ["area", "item", "required", "evidence", "pass_condition", "status"], 10)
    validate_csv("docs/clinical_data/DIFFERENTIAL_DIAGNOSIS_CANDIDATES_GO_NO_GO_V1.csv", ["gate", "go_condition", "no_go_condition", "evidence", "status"], 10)
    validate_runtime_contract()
    print("Differential Diagnosis Candidates V1 validator PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
