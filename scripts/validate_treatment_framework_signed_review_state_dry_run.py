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
    "backend/treatment_framework_signed_review_state.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_GO_NO_GO_V1.csv",
    "scripts/validate_treatment_framework_signed_review_state_dry_run.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REFERENCE_FILES = [
    "backend/treatment_framework_audit_log.py",
    "backend/treatment_framework_clinician_review_workflow.py",
    "backend/confirmed_diagnosis_treatment_framework.py",
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
    "persists_signed_review_state\": True",
    "signed_review_state_persistence_enabled=true",
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


def read(rel_path: str) -> str:
    path = ROOT / rel_path
    require(path.is_file(), "missing required file: {0}".format(rel_path))
    return path.read_text(encoding="utf-8")


def require_tokens(label: str, text: str, tokens: Iterable[str]) -> None:
    missing = [token for token in tokens if token not in text]
    require(not missing, "{0} missing tokens: {1}".format(label, ", ".join(missing)))


def load_module(path: str):
    module_path = ROOT / path
    spec = importlib.util.spec_from_file_location("treatment_framework_signed_review_state_under_test", str(module_path))
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


def optional_block(ci_text: str) -> str:
    match = re.search(r"OPTIONAL_CORE_VALIDATORS=\(([\s\S]*?)\)\n", ci_text)
    require(match is not None, "OPTIONAL_CORE_VALIDATORS block missing")
    return match.group(1)


def main() -> int:
    print("Validating Treatment Framework Signed Review State Dry Run V1")

    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))
    for rel in REFERENCE_FILES:
        require((ROOT / rel).is_file(), "missing reference file from previous stages: {0}".format(rel))

    py_compile.compile(str(ROOT / "backend/treatment_framework_signed_review_state.py"), doraise=True)
    py_compile.compile(str(ROOT / "backend/diagnostic_data_api.py"), doraise=True)
    py_compile.compile(str(ROOT / "scripts/validate_treatment_framework_signed_review_state_dry_run.py"), doraise=True)

    backend_text = read("backend/treatment_framework_signed_review_state.py")
    endpoint_text = read("backend/diagnostic_data_api.py")
    doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1.md")
    checklist = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_CHECKLIST_V1.csv")
    go_no_go = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_GO_NO_GO_V1.csv")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")

    require_tokens("backend", backend_text, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_MODE",
        "build_treatment_framework_signed_review_state",
        "treatment_framework_signed_review_state_safety_flags",
        "signed_review_state_preview_only",
        "review_state_persistence_enabled",
        "audit log reference is required",
    ])
    require_tokens("endpoint", endpoint_text, [
        "/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/build",
        "Treatment Framework Signed Review State Dry Run V1 endpoint: start",
        "Treatment Framework Signed Review State Dry Run V1 endpoint: end",
    ])
    endpoint_block_match = re.search(
        r"# --- Treatment Framework Signed Review State Dry Run V1 endpoint: start ---([\s\S]*?)# --- Treatment Framework Signed Review State Dry Run V1 endpoint: end ---",
        endpoint_text,
    )
    require(endpoint_block_match is not None, "endpoint block not found")
    executable_to_scan = backend_text + "\n" + endpoint_block_match.group(1)
    for snippet in FORBIDDEN_EXECUTABLE_SNIPPETS:
        require(snippet not in executable_to_scan, "forbidden executable snippet found: {0}".format(snippet))

    require_tokens("doc", doc, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1",
        "signed_review_state_dry_run_only=true",
        "signed_review_state_persistence_enabled=false",
        "review_state_persistence_enabled=false",
        "writes_database=false",
        "no_case_treatment_write=true",
        "no_case_treatment_persistence=true",
        "no_prescription_write=true",
        "no_dose_route_frequency=true",
        "not_client_facing=true",
        "GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_UI_V1",
    ])
    require_tokens("checklist", checklist, [
        "dry_run_only",
        "persistence_disabled",
        "audit_reference",
        "no_case_treatment_write",
        "no_prescription_write",
        "no_dose_route_frequency",
    ])
    require_tokens("go_no_go", go_no_go, [
        "signed_review_endpoint",
        "signed_review_persistence",
        "GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_UI_V1",
    ])

    require_tokens("ci", ci, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1",
        "backend/treatment_framework_signed_review_state.py",
        "validate_treatment_framework_signed_review_state_dry_run.py",
        "signed review state dry-run markers",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "PASS: ci_static_checks",
    ])
    optional = optional_block(ci)
    for stage_scoped in [
        "validate_treatment_framework_signed_review_state_design.py",
        "validate_treatment_framework_persistence_risk_review.py",
        "validate_treatment_framework_audit_log.py",
        "validate_treatment_framework_clinician_review_workflow.py",
        "validate_case_detail_treatment_framework_preview_ui.py",
        "validate_confirmed_diagnosis_treatment_framework_draft.py",
        "validate_ci_smoke_cumulative_guard_restore.py",
    ]:
        require(stage_scoped not in optional, "stage-scoped validator must not be re-run in signed review dry-run CI: {0}".format(stage_scoped))
    require("${OPTIONAL_CORE_VALIDATORS[@]:-}" in ci, "Bash 3.2-safe empty optional validator loop missing")
    require("git add ." not in ci, "ci contains legacy-forbidden exact git add marker")

    require_tokens("smoke", smoke, [
        "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
        "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"",
        "check_treatment_framework_persistence_risk_review_v1",
        "check_treatment_framework_signed_review_state_design_v1",
        "check_treatment_framework_signed_review_state_dry_run_v1",
        "/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/build",
        "treatment_framework_signed_review_state_dry_run_smoke=PASS",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1",
        "GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_UI_V1",
    ])
    require(
        re.search(
            r"\ncheck_treatment_framework_signed_review_state_design_v1\s*\ncheck_treatment_framework_signed_review_state_dry_run_v1\s*\n",
            smoke,
        ) is not None,
        "smoke must call signed review state dry-run after design smoke",
    )

    module = load_module("backend/treatment_framework_signed_review_state.py")
    builder = module.build_treatment_framework_signed_review_state
    safety_flags = module.treatment_framework_signed_review_state_safety_flags()

    for key, expected in {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "writes_case_treatment": False,
        "persists_treatment_framework": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "writes_audit_log": False,
        "creates_signed_review_state": False,
        "persists_signed_review_state": False,
        "signed_review_state_preview_only": True,
        "review_state_persistence_enabled": False,
        "not_client_facing": True,
        "client_release_allowed": False,
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
        "audit_log_result": {"decision": "audit_log_append_preview", "append_only": True, "persisted": False},
        "signed_by": "doctor-3",
        "signoff_decision": "sign_internal_review",
    }
    result = builder(valid_payload, case_context={"case_id": 123, "species": "dog"})

    expect_value(result, "message", "treatment_framework_signed_review_state_built")
    expect_value(result, "mode", "treatment_framework_signed_review_state_dry_run_v1")
    expect_value(result, "case_id", 123)
    require(result.get("confirmed_diagnosis", {}).get("confirmation_source") == "clinician_entered", "confirmation source not normalized")
    require(result.get("confirmed_diagnosis", {}).get("ai_generated") is False, "ai_generated not false")

    state = result.get("signed_review_state_preview") or {}
    expect_value(state, "signed_review_status", "signed_internal_review_preview")
    expect_value(state, "dry_run", True)
    expect_value(state, "persisted", False)
    expect_value(state, "signed_review_state_persisted", False)
    expect_value(state, "case_treatment_persisted", False)
    expect_value(state, "prescription_created", False)
    expect_value(state, "client_release_allowed", False)
    expect_value(state, "review_state_persistence_enabled", False)

    qg = result.get("quality_gate") or {}
    for key, expected in {
        "status": "PASS",
        "requires_confirmed_diagnosis": True,
        "requires_clinician_confirmed_diagnosis": True,
        "ai_does_not_confirm_diagnosis": True,
        "audit_log_reference_present": True,
        "signed_review_state_preview_only": True,
        "review_state_persistence_enabled": False,
        "writes_database": False,
        "writes_case_treatment": False,
        "persists_treatment_framework": False,
        "blocks_prescription": True,
        "blocks_dose": True,
        "blocks_route_frequency": True,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }.items():
        expect_value(qg, key, expected)

    for key, expected in {
        "read_only": True,
        "writes_database": False,
        "writes_case_treatment": False,
        "persists_treatment_framework": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "writes_audit_log": False,
        "creates_signed_review_state": False,
        "persists_signed_review_state": False,
        "signed_review_state_preview_only": True,
        "review_state_persistence_enabled": False,
        "not_client_facing": True,
        "client_release_allowed": False,
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
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": False, "treatment_framework_preview": preview, "reviewed_by": "doctor", "review_decision": "approve_for_clinician_use", "signed_by": "doctor", "signoff_decision": "sign_internal_review"}, "audit log reference")
    bad_preview_payload = dict(valid_payload)
    bad_preview_payload["treatment_framework_preview"] = {"bad": "10 mg/kg"}
    expect_value_error(builder, bad_preview_payload, "forbidden")

    smoke_lines = len(smoke.splitlines())
    require(smoke_lines >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")

    print("PASS: Treatment Framework Signed Review State Dry Run V1")
    print("signed_review_state_dry_run_only=true")
    print("signed_review_state_persistence_enabled=false")
    print("review_state_persistence_enabled=false")
    print("read_only=true")
    print("writes_database=false")
    print("no_case_treatment_write=true")
    print("no_case_treatment_persistence=true")
    print("no_prescription_write=true")
    print("no_dose_route_frequency=true")
    print("not_client_facing=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision=GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_UI_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
