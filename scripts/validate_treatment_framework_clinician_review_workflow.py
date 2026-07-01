#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import py_compile
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/treatment_framework_clinician_review_workflow.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_GO_NO_GO_V1.csv",
    "scripts/validate_treatment_framework_clinician_review_workflow.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

FORBIDDEN_EXECUTABLE_SNIPPETS = [
    ".commit(",
    ".add(",
    "Case.treatment",
    "writes_case_treatment\": True",
    "creates_prescription\": True",
    "writes_prescription\": True",
    "returns_drug_dose\": True",
    "returns_drug_route\": True",
    "returns_drug_frequency\": True",
]

FORBIDDEN_PREVIEW_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\s*/\s*kg\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\b", re.IGNORECASE),
    re.compile(r"\bq\s*\d+\s*h\b", re.IGNORECASE),
    re.compile(r"\b(?:SID|BID|TID|QID|q12h|q24h|q8h|q6h|q4h)\b", re.IGNORECASE),
    re.compile(r"\b(?:PO|IV|IM|SC|SQ|subcutaneous|intravenous|intramuscular|oral)\b", re.IGNORECASE),
    re.compile(r"\b(?:prescribe|prescription|dispense|administer)\b", re.IGNORECASE),
]


def fail(message: str) -> None:
    print("NO-GO: {0}".format(message))
    sys.exit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load_module(path: str):
    module_path = ROOT / path
    spec = importlib.util.spec_from_file_location("treatment_framework_clinician_review_workflow_under_test", str(module_path))
    require(spec is not None and spec.loader is not None, "failed to load module spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            for nested in walk_strings(item):
                yield nested
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            for nested in walk_strings(item):
                yield nested


def forbidden_preview_hits(value: Dict[str, Any]) -> List[str]:
    hits: List[str] = []
    for text in walk_strings(value):
        for pattern in FORBIDDEN_PREVIEW_PATTERNS:
            if pattern.search(text):
                hits.append(text)
                break
    return hits


def expect_value(container: Dict[str, Any], key: str, expected: Any) -> None:
    actual = container.get(key)
    require(actual == expected, "{0}: expected {1!r}, got {2!r}".format(key, expected, actual))


def expect_value_anywhere(result: Dict[str, Any], key: str, expected: Any) -> None:
    if key in result:
        expect_value(result, key, expected)
        return
    safety = result.get("safety") or {}
    require(isinstance(safety, dict), "safety must be a dict")
    expect_value(safety, key, expected)


def expect_value_error(func, payload: Dict[str, Any], contains: str) -> None:
    try:
        func(payload)
    except ValueError as exc:
        require(contains in str(exc), "ValueError message mismatch: {0!r}".format(str(exc)))
        return
    fail("expected ValueError containing {0!r}".format(contains))


def main() -> int:
    print("Validating Treatment Framework Clinician Review Workflow V1")

    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))

    py_compile.compile(str(ROOT / "backend/treatment_framework_clinician_review_workflow.py"), doraise=True)
    py_compile.compile(str(ROOT / "backend/diagnostic_data_api.py"), doraise=True)
    py_compile.compile(str(ROOT / "scripts/validate_treatment_framework_clinician_review_workflow.py"), doraise=True)

    backend_text = read("backend/treatment_framework_clinician_review_workflow.py")
    endpoint_text = read("backend/diagnostic_data_api.py")
    smoke_text = read("scripts/smoke_petmed.sh")
    ci_text = read("scripts/ci_static_checks.sh")
    doc_text = read("docs/clinical_data/TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1.md")

    require("TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_MODE" in backend_text, "missing backend mode constant")
    require("build_treatment_framework_clinician_review_workflow" in backend_text, "missing backend builder")
    require("treatment_framework_clinician_review_workflow_safety_flags" in backend_text, "missing backend safety flags")
    require("/dry-run/confirmed-diagnosis/treatment-framework/review" in endpoint_text, "missing review endpoint path")
    require("Treatment Framework Clinician Review Workflow V1 endpoint: start" in endpoint_text, "missing endpoint start marker")
    require("Treatment Framework Clinician Review Workflow V1 endpoint: end" in endpoint_text, "missing endpoint end marker")
    require("TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1" in ci_text, "ci stage marker missing")
    require("validate_treatment_framework_clinician_review_workflow.py" in ci_text, "ci review validator missing")
    # --- Previous stage validator scope checks: start ---
    require("CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_V1" in ci_text, "ci previous UI stage compatibility marker missing")
    require("frontend/src/pages/CaseDetail.jsx" in ci_text, "ci previous UI frontend target marker missing")
    require("case detail treatment framework preview UI markers" in ci_text, "ci previous UI marker text missing")
    optional_core_match = re.search(r"OPTIONAL_CORE_VALIDATORS=\(([\s\S]*?)\)\n", ci_text)
    require(optional_core_match is not None, "optional core validators block missing")
    optional_core_body = optional_core_match.group(1)
    require(
        "validate_case_detail_treatment_framework_preview_ui.py" not in optional_core_body,
        "case detail UI stage validator must not be re-run in Review Workflow CI",
    )
    require(
        "validate_ci_smoke_cumulative_guard_restore.py" not in optional_core_body,
        "restore stage validator must not be re-run in Review Workflow CI",
    )
    # --- Previous stage validator scope checks: end ---
    require("check_treatment_framework_clinician_review_workflow_v1" in smoke_text, "missing review workflow smoke function")
    require("treatment_framework_clinician_review_workflow_smoke=PASS" in smoke_text, "missing review workflow smoke PASS marker")
    require("case_detail_treatment_framework_preview_ui=PASS" in smoke_text, "case detail UI smoke marker lost")
    require("LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1" in smoke_text, "legacy rabbit compatibility marker lost")
    require("LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1" in smoke_text, "legacy lizard compatibility marker lost")
    require("GO_TO_TREATMENT_FRAMEWORK_AUDIT_LOG_V1" in doc_text, "missing next-stage decision in doc")
    require(
        re.search(r"\ncheck_confirmed_diagnosis_treatment_framework_draft_v1\s*\ncheck_case_detail_treatment_framework_preview_ui_v1\s*\ncheck_treatment_framework_clinician_review_workflow_v1\s*\n", smoke_text) is not None,
        "missing review workflow smoke invocation order",
    )

    endpoint_block_match = re.search(
        r"# --- Treatment Framework Clinician Review Workflow V1 endpoint: start ---([\s\S]*?)# --- Treatment Framework Clinician Review Workflow V1 endpoint: end ---",
        endpoint_text,
    )
    require(endpoint_block_match is not None, "endpoint block not found")
    endpoint_block = endpoint_block_match.group(1)
    executable_to_scan = backend_text + "\n" + endpoint_block
    for snippet in FORBIDDEN_EXECUTABLE_SNIPPETS:
        require(snippet not in executable_to_scan, "forbidden executable snippet found: {0}".format(snippet))

    module = load_module("backend/treatment_framework_clinician_review_workflow.py")
    builder = module.build_treatment_framework_clinician_review_workflow
    safety_flags = module.treatment_framework_clinician_review_workflow_safety_flags()

    for key, expected in {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "writes_case_treatment": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "writes_audit_log": False,
        "persists_review_state": False,
        "review_decision_preview_only": True,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "external_ai_provider_call": False,
        "ai_does_not_confirm_diagnosis": True,
    }.items():
        expect_value(safety_flags, key, expected)

    preview = {
        "treatment_goals": ["stabilize patient status under clinician direction"],
        "care_priority_hint": "clinician_review_required",
        "supportive_care_categories": ["comfort_support_review"],
        "monitoring_parameters": ["vital_signs_trend"],
    }
    valid_payload = {
        "case_id": 123,
        "confirmed_diagnosis_label": "clinician confirmed pancreatitis",
        "confirmed_by": "doctor-1",
        "confirmation_source": "clinician",
        "ai_generated": False,
        "treatment_framework_preview": preview,
        "reviewed_by": "doctor-2",
        "review_decision": "approve_for_clinician_use",
        "review_note": "reviewed internally",
    }
    result = builder(valid_payload, case_context={"case_id": 123, "species": "dog"})

    expect_value(result, "message", "treatment_framework_clinician_review_workflow_built")
    expect_value(result, "mode", "treatment_framework_clinician_review_workflow_v1")
    expect_value(result, "case_id", 123)
    require(result.get("confirmed_diagnosis", {}).get("confirmation_source") == "clinician_entered", "confirmation source not normalized")
    require(result.get("confirmed_diagnosis", {}).get("ai_generated") is False, "ai_generated not false")

    workflow = result.get("review_workflow") or {}
    expect_value(workflow, "review_decision", "approve_for_clinician_use")
    expect_value(workflow, "review_status", "approved_internal_clinician_preview")
    expect_value(workflow, "dry_run", True)
    expect_value(workflow, "review_decision_preview_only", True)
    expect_value(workflow, "final_signoff_persisted", False)
    expect_value(workflow, "review_status_persisted", False)
    expect_value(workflow, "client_release_allowed", False)
    expect_value(workflow, "persistence_allowed", False)

    qg = result.get("quality_gate") or {}
    for key, expected in {
        "status": "PASS",
        "requires_confirmed_diagnosis": True,
        "requires_clinician_confirmed_diagnosis": True,
        "ai_does_not_confirm_diagnosis": True,
        "review_decision_allowed": True,
        "review_decision_preview_only": True,
        "writes_database": False,
        "writes_case_treatment": False,
        "blocks_prescription": True,
        "blocks_dose": True,
        "blocks_route_frequency": True,
        "not_client_facing": True,
    }.items():
        expect_value(qg, key, expected)

    for key, expected in {
        "read_only": True,
        "writes_database": False,
        "writes_case_treatment": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "writes_audit_log": False,
        "persists_review_state": False,
        "review_decision_preview_only": True,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "external_ai_provider_call": False,
        "ai_does_not_confirm_diagnosis": True,
    }.items():
        expect_value_anywhere(result, key, expected)

    hits = forbidden_preview_hits(result.get("treatment_framework_preview") or {})
    require(not hits, "forbidden preview wording found: {0}".format(hits))

    expect_value_error(builder, {"case_id": 1, "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": False}, "confirmed diagnosis by clinician is required")
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "ai", "ai_generated": False}, "confirmed diagnosis by clinician is required")
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": True}, "AI generated diagnosis cannot be used")
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": False, "treatment_framework_preview": preview, "reviewed_by": "doctor"}, "review_decision")
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": False, "treatment_framework_preview": {"bad": "10 mg/kg"}, "reviewed_by": "doctor", "review_decision": "reject"}, "forbidden")

    smoke_lines = len(smoke_text.splitlines())
    require(smoke_lines >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")

    print("PASS: Treatment Framework Clinician Review Workflow V1")
    print("treatment_framework_clinician_review_workflow_smoke=PASS_REQUIRED")
    print("requires_clinician_confirmed_diagnosis=true")
    print("ai_does_not_confirm_diagnosis=true")
    print("read_only=true")
    print("writes_database=false")
    print("writes_case_treatment=false")
    print("creates_prescription=false")
    print("writes_prescription=false")
    print("returns_drug_dose=false")
    print("returns_drug_route=false")
    print("returns_drug_frequency=false")
    print("writes_audit_log=false")
    print("persists_review_state=false")
    print("review_decision_preview_only=true")
    print("not_client_facing=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("case_detail_ui_stage_validator_not_rerun=true")
    print("case_detail_treatment_framework_preview_ui_preserved_by_smoke=true")
    print("decision=GO_TO_TREATMENT_FRAMEWORK_AUDIT_LOG_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
