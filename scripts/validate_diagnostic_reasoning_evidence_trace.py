#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import json
import py_compile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/diagnostic_reasoning_evidence_trace.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/DIAGNOSTIC_REASONING_EVIDENCE_TRACE_V1.md",
    "docs/clinical_data/DIAGNOSTIC_REASONING_EVIDENCE_TRACE_CHECKLIST_V1.csv",
    "docs/clinical_data/DIAGNOSTIC_REASONING_EVIDENCE_TRACE_GO_NO_GO_V1.csv",
    "scripts/validate_diagnostic_reasoning_evidence_trace.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

FORBIDDEN_PROVIDER_TOKENS = [
    "openai", "anthropic", "gemini", "requests.post", "httpx.post", "aiohttp",
    "emr_real_import", "pacs", "dicomweb", "device_gateway", "send_sms", "send_email",
]

FORBIDDEN_WRITE_TOKENS = [
    "db.add(", "session.add(", ".commit(", ".flush(", ".merge(", "db.delete(", "session.delete(",
    "insert(", "update(", "delete(", "create_audit", "auditlog(", "backgroundtasks", "celery", "rq.enqueue",
]

FORBIDDEN_OUTPUT_PHRASES = [
    "mg/kg",
    "mcg/kg",
    "ml/kg",
    " q12h",
    " q8h",
    " q24h",
    " po ",
    " iv ",
    " im ",
    " sc ",
    " sq ",
]


def fail(message: str) -> None:
    print("Diagnostic Reasoning Evidence Trace V1 validator FAIL: %s" % message)
    raise SystemExit(1)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail("%s missing %r" % (label, needle))


def assert_not_contains_lower(text: str, needles: List[str], label: str) -> None:
    lowered = text.lower()
    for needle in needles:
        if needle.lower() in lowered:
            fail("%s contains forbidden token %r" % (label, needle))


def validate_csv(rel: str, expected_header: List[str], min_rows: int) -> None:
    path = ROOT / rel
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        fail("%s is empty" % rel)
    if rows[0] != expected_header:
        fail("%s header mismatch: %r" % (rel, rows[0]))
    if len(rows) < min_rows + 1:
        fail("%s has too few rows" % rel)


def compile_required_python() -> None:
    for rel in (
        "backend/diagnostic_reasoning_evidence_trace.py",
        "scripts/validate_diagnostic_reasoning_evidence_trace.py",
    ):
        try:
            py_compile.compile(str(ROOT / rel), doraise=True)
        except py_compile.PyCompileError as exc:
            fail("py_compile failed for %s: %s" % (rel, exc))


def load_builder():
    path = ROOT / "backend" / "diagnostic_reasoning_evidence_trace.py"
    spec = importlib.util.spec_from_file_location("diagnostic_reasoning_evidence_trace", str(path))
    if spec is None or spec.loader is None:
        fail("could not load diagnostic_reasoning_evidence_trace module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_safety_false(data: Dict[str, Any], keys: List[str]) -> None:
    for key in keys:
        if data.get(key) is not False:
            fail("expected %s false, got %r" % (key, data.get(key)))


def assert_safety_true(data: Dict[str, Any], keys: List[str]) -> None:
    for key in keys:
        if data.get(key) is not True:
            fail("expected %s true, got %r" % (key, data.get(key)))


def validate_runtime_contract() -> None:
    module = load_builder()
    payload = {
        "problem_list_preview": [
            {
                "problem_id": "problem-001",
                "category": "presenting_complaint",
                "title": "Vomiting requires clinician review",
                "severity_hint": "medium",
                "evidence_sources": [
                    {
                        "source_type": "case",
                        "field": "chief_complaint",
                        "snippet": "Vomiting for 2 days; owner asks about 2 mg/kg PO q12h medication instructions",
                    }
                ],
            },
            {
                "problem_id": "problem-002",
                "category": "lab_abnormality",
                "title": "ALT abnormality requires clinician review",
                "severity_hint": "medium",
                "evidence_sources": [
                    {
                        "source_type": "lab_abnormal_summary",
                        "field": "ALT",
                        "snippet": "ALT high; hepatobiliary involvement should be reviewed by clinician",
                    }
                ],
            },
        ],
        "differential_diagnosis_candidates_preview": [
            {
                "candidate_key": "gastrointestinal_process_candidate",
                "candidate_label": "Gastrointestinal disease process candidate",
                "system_category": "gastrointestinal",
                "severity_hint": "medium",
                "supporting_evidence_sources": [
                    {
                        "source_type": "problem_list_preview",
                        "field": "chief_complaint",
                        "snippet": "Vomiting and appetite change",
                    }
                ],
                "contradicting_or_missing_evidence": [
                    "hydration status and abdominal palpation findings not supplied"
                ],
                "evidence_fit_hint": "moderate_signal_for_review",
            },
            {
                "candidate_key": "hepatobiliary_process_candidate",
                "candidate_label": "Hepatobiliary involvement candidate",
                "system_category": "hepatobiliary",
                "severity_hint": "medium",
                "supporting_evidence_sources": [
                    {
                        "source_type": "lab_abnormal_summary",
                        "field": "ALT",
                        "snippet": "ALT is above reference interval",
                    }
                ],
            },
        ],
    }
    result = module.build_diagnostic_reasoning_evidence_trace(payload, case_id=123, case_context={"case_id": 123})
    if result.get("mode") != "diagnostic_reasoning_evidence_trace_v1":
        fail("unexpected mode")
    assert_safety_true(result, [
        "read_only", "dry_run", "requires_human_review", "clinician_signoff_required",
        "not_a_diagnosis", "not_a_treatment_plan", "not_a_prescription", "not_client_facing",
    ])
    assert_safety_false(result, [
        "writes_database", "creates_case", "updates_case", "writes_diagnostic_report",
        "writes_ai_summary", "creates_audit_log", "writes_audit_log", "persists_reasoning_trace",
        "generates_final_diagnosis", "generates_confirmed_diagnosis", "generates_definitive_diagnosis",
        "generates_diagnostic_conclusion", "returns_probability", "returns_numeric_confidence",
        "creates_treatment_plan", "writes_treatment_plan", "creates_prescription", "writes_prescription",
        "drug_dose_recommendation", "returns_drug_dose", "returns_drug_route", "returns_drug_frequency",
        "client_facing", "releases_to_client", "calls_external_ai", "calls_external_provider",
    ])
    traces = result.get("diagnostic_reasoning_evidence_trace_preview")
    if not isinstance(traces, list) or len(traces) < 2:
        fail("expected at least two trace preview items")
    if not isinstance(result.get("evidence_source_index"), list) or not result["evidence_source_index"]:
        fail("expected evidence_source_index")
    if result.get("quality_gate", {}).get("status") != "PASS":
        fail("quality gate not PASS")
    allowed_hints = {
        "strong_signal_for_review", "moderate_signal_for_review",
        "limited_signal_for_review", "insufficient_signal",
    }
    for item in traces:
        for key in (
            "requires_clinician_review", "clinician_signoff_required", "not_a_diagnosis",
            "not_a_final_diagnosis", "not_a_confirmed_diagnosis", "not_a_definitive_diagnosis",
            "not_a_diagnostic_conclusion", "not_a_treatment_plan", "not_a_prescription",
            "not_a_drug_dose", "not_client_facing",
        ):
            if item.get(key) is not True:
                fail("trace item missing true boundary flag: %s" % key)
        for required in (
            "trace_id", "candidate_key", "candidate_label", "system_category", "evidence_fit_hint",
            "severity_hint", "supporting_evidence_sources", "contradicting_or_missing_evidence",
            "reasoning_trace_steps", "review_questions",
        ):
            if required not in item:
                fail("trace item missing %s" % required)
        if item.get("evidence_fit_hint") not in allowed_hints:
            fail("invalid evidence_fit_hint")
        if not isinstance(item.get("supporting_evidence_sources"), list):
            fail("supporting_evidence_sources must be list")
        if not isinstance(item.get("reasoning_trace_steps"), list) or len(item["reasoning_trace_steps"]) < 4:
            fail("reasoning trace steps incomplete")
    output_text = json.dumps(result, ensure_ascii=False).lower()
    for phrase in FORBIDDEN_OUTPUT_PHRASES:
        if phrase in output_text:
            fail("runtime output contains forbidden phrase %r" % phrase)


def main() -> int:
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            fail("missing required file: %s" % rel)
    compile_required_python()
    builder = read("backend/diagnostic_reasoning_evidence_trace.py")
    api = read("backend/diagnostic_data_api.py")
    docs = read("docs/clinical_data/DIAGNOSTIC_REASONING_EVIDENCE_TRACE_V1.md")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")

    assert_contains(builder, "DIAGNOSTIC_REASONING_EVIDENCE_TRACE_MODE", "builder")
    assert_contains(builder, "def build_diagnostic_reasoning_evidence_trace", "builder")
    assert_contains(builder, "def diagnostic_reasoning_evidence_trace_safety_flags", "builder")
    assert_contains(builder, '"writes_database": False', "builder")
    assert_contains(builder, '"requires_human_review": True', "builder")
    assert_contains(builder, '"clinician_signoff_required": True', "builder")
    assert_contains(builder, '"not_a_diagnosis": True', "builder")
    assert_contains(builder, '"not_a_treatment_plan": True', "builder")
    assert_contains(builder, '"not_a_prescription": True', "builder")
    assert_contains(builder, '"not_client_facing": True', "builder")
    assert_contains(builder, '"returns_probability": False', "builder")
    assert_contains(builder, '"returns_numeric_confidence": False', "builder")
    assert_contains(builder, '"persists_reasoning_trace": False', "builder")
    assert_not_contains_lower(builder, FORBIDDEN_PROVIDER_TOKENS, "builder")
    assert_not_contains_lower(builder, FORBIDDEN_WRITE_TOKENS, "builder")

    assert_contains(api, '@router.post("/dry-run/diagnostic-reasoning/evidence-trace/build"', "diagnostic_data_api")
    assert_contains(api, "build_diagnostic_reasoning_evidence_trace", "diagnostic_data_api")
    endpoint_block_start = api.find("# --- Diagnostic Reasoning Evidence Trace V1 endpoint: start ---")
    endpoint_block_end = api.find("# --- Diagnostic Reasoning Evidence Trace V1 endpoint: end ---")
    if endpoint_block_start < 0 or endpoint_block_end < endpoint_block_start:
        fail("endpoint marker block missing")
    endpoint_block = api[endpoint_block_start:endpoint_block_end]
    assert_not_contains_lower(endpoint_block, FORBIDDEN_WRITE_TOKENS, "diagnostic reasoning endpoint")

    for phrase in (
        "not automatic diagnosis",
        "must not write any database row",
        "No final diagnosis",
        "No treatment plan",
        "No drug dose",
        "No probability",
        "GO_TO_DIAGNOSTIC_ASSISTANCE_CASE_DETAIL_UI_V1",
    ):
        assert_contains(docs, phrase, "stage doc")
    assert_contains(ci, "validate_diagnostic_reasoning_evidence_trace.py", "ci_static_checks")
    assert_contains(smoke, "diagnostic-reasoning/evidence-trace/build", "smoke_petmed")
    assert_contains(smoke, "validate_diagnostic_reasoning_evidence_trace.py", "smoke_petmed")

    validate_csv(
        "docs/clinical_data/DIAGNOSTIC_REASONING_EVIDENCE_TRACE_CHECKLIST_V1.csv",
        ["area", "item", "required", "evidence", "pass_condition", "status"],
        10,
    )
    validate_csv(
        "docs/clinical_data/DIAGNOSTIC_REASONING_EVIDENCE_TRACE_GO_NO_GO_V1.csv",
        ["gate", "go_condition", "no_go_condition", "evidence", "status"],
        10,
    )
    validate_runtime_contract()
    print("Diagnostic Reasoning Evidence Trace V1 validator PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
