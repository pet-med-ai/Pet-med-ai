#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import py_compile
import re
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "backend/treatment_framework_audit_log.py",
    "backend/audit_log_api.py",
    "docs/clinical_data/TREATMENT_FRAMEWORK_AUDIT_LOG_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_AUDIT_LOG_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_AUDIT_LOG_GO_NO_GO_V1.csv",
    "scripts/validate_treatment_framework_audit_log.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
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
    spec = importlib.util.spec_from_file_location("audit_log_under_test", str(ROOT / path))
    require(spec is not None and spec.loader is not None, "failed to load module spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


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


def require_tokens(label: str, text: str, tokens) -> None:
    missing = [token for token in tokens if token not in text]
    require(not missing, "{0} missing tokens: {1}".format(label, ", ".join(missing)))


def main() -> int:
    print("Validating Treatment Framework Audit Log V1")
    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))
    py_compile.compile(str(ROOT / "backend/treatment_framework_audit_log.py"), doraise=True)
    py_compile.compile(str(ROOT / "backend/audit_log_api.py"), doraise=True)
    py_compile.compile(str(ROOT / "scripts/validate_treatment_framework_audit_log.py"), doraise=True)

    backend_text = read("backend/treatment_framework_audit_log.py")
    endpoint_text = read("backend/audit_log_api.py")
    smoke_text = read("scripts/smoke_petmed.sh")
    ci_text = read("scripts/ci_static_checks.sh")
    doc_text = read("docs/clinical_data/TREATMENT_FRAMEWORK_AUDIT_LOG_V1.md")

    require_tokens("backend", backend_text, ["TREATMENT_FRAMEWORK_AUDIT_LOG_MODE", "TREATMENT_FRAMEWORK_AUDIT_LOG_CONFIRMATION", "build_treatment_framework_audit_log_event", "append_only_audit_log", "writes_case_treatment", "returns_drug_dose"])
    require_tokens("endpoint", endpoint_text, ["/diagnostic-data/confirmed-diagnosis/treatment-framework/audit-log/append", "Treatment Framework Audit Log V1 endpoint: start", "Treatment Framework Audit Log V1 endpoint: end", "AuditLog(", "append_only_audit_log"])
    require_tokens("docs", doc_text, ["TREATMENT_FRAMEWORK_AUDIT_LOG_V1", "I_UNDERSTAND_THIS_APPENDS_TREATMENT_FRAMEWORK_AUDIT_LOG_ONLY", "append_only_audit_log=true", "GO_TO_TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1"])
    require_tokens("ci", ci_text, ["TREATMENT_FRAMEWORK_AUDIT_LOG_V1", "backend/treatment_framework_audit_log.py", "backend/audit_log_api.py", "validate_treatment_framework_audit_log.py", "TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1", "treatment framework audit log endpoint markers", "target-only tracked diff discipline", "PASS: ci_static_checks"])
    require_tokens("smoke", smoke_text, ["CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1", "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"", "LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1", "LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1", "check_treatment_framework_clinician_review_workflow_v1", "check_treatment_framework_audit_log_v1", "treatment_framework_audit_log_smoke=PASS", "GO_TO_TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1"])
    require(re.search(r"\ncheck_treatment_framework_clinician_review_workflow_v1\s*\ncheck_treatment_framework_audit_log_v1\s*\n", smoke_text) is not None, "missing audit log smoke invocation order")
    optional_core_match = re.search(r"OPTIONAL_CORE_VALIDATORS=\(([\s\S]*?)\)\n", ci_text)
    require(optional_core_match is not None, "optional core validators block missing")
    optional_block = optional_core_match.group(1)
    require("validate_case_detail_treatment_framework_preview_ui.py" not in optional_block, "case detail UI validator must not be re-run in Audit Log CI")
    require("validate_treatment_framework_clinician_review_workflow.py" not in optional_block, "review workflow validator must not be re-run in Audit Log CI")

    forbidden = ["Case.treatment", "writes_case_treatment\": True", "creates_prescription\": True", "writes_prescription\": True", "returns_drug_dose\": True", "returns_drug_route\": True", "returns_drug_frequency\": True"]
    endpoint_block_match = re.search(r"# --- Treatment Framework Audit Log V1 endpoint: start ---([\s\S]*?)# --- Treatment Framework Audit Log V1 endpoint: end ---", endpoint_text)
    require(endpoint_block_match is not None, "endpoint block not found")
    executable_text = backend_text + "\n" + endpoint_block_match.group(1)
    for snippet in forbidden:
        require(snippet not in executable_text, "forbidden executable snippet found: {0}".format(snippet))

    module = load_module("backend/treatment_framework_audit_log.py")
    builder = module.build_treatment_framework_audit_log_event
    flags = module.treatment_framework_audit_log_safety_flags(dry_run=True, writes_audit_log=False)
    for key, expected in {"read_only": True, "dry_run": True, "writes_database": False, "writes_audit_log": False, "append_only_audit_log": True, "writes_case_treatment": False, "creates_prescription": False, "writes_prescription": False, "returns_drug_dose": False, "returns_drug_route": False, "returns_drug_frequency": False, "not_client_facing": True, "requires_human_review": True, "clinician_signoff_required": True, "ai_does_not_confirm_diagnosis": True}.items():
        expect_value(flags, key, expected)

    preview = {"treatment_goals": ["stabilize patient status under clinician direction"], "care_priority_hint": "clinician_review_required", "supportive_care_categories": ["comfort_support_review"], "monitoring_parameters": ["vital_signs_trend"]}
    valid_payload = {"case_id": 123, "confirmed_diagnosis_label": "clinician confirmed pancreatitis", "confirmed_by": "doctor-1", "confirmation_source": "clinician", "ai_generated": False, "treatment_framework_preview": preview, "reviewed_by": "doctor-2", "review_decision": "approve_for_clinician_use", "review_note": "append audit preview only", "dry_run": True}
    result = builder(valid_payload, case_context={"case_id": 123})
    expect_value(result, "message", "treatment_framework_audit_log_built")
    expect_value(result, "mode", "treatment_framework_audit_log_v1")
    expect_value(result.get("audit_log_result") or {}, "dry_run", True)
    expect_value(result.get("audit_log_result") or {}, "will_append_audit_log", False)
    expect_value(result.get("audit_log_result") or {}, "append_only", True)
    expect_value(result.get("quality_gate") or {}, "writes_audit_log", False)
    expect_value(result.get("quality_gate") or {}, "writes_case_treatment", False)
    expect_value_anywhere(result, "append_only_audit_log", True)
    expect_value_anywhere(result, "writes_case_treatment", False)
    expect_value_anywhere(result, "returns_drug_dose", False)

    append_payload = dict(valid_payload)
    append_payload["dry_run"] = False
    append_payload["audit_log_confirmation"] = module.TREATMENT_FRAMEWORK_AUDIT_LOG_CONFIRMATION
    append_plan = builder(append_payload, case_context={"case_id": 123})
    expect_value(append_plan.get("audit_log_result") or {}, "will_append_audit_log", True)
    expect_value(append_plan.get("quality_gate") or {}, "writes_audit_log", True)
    expect_value_anywhere(append_plan, "append_only_audit_log", True)
    expect_value_anywhere(append_plan, "writes_case_treatment", False)

    expect_value_error(builder, {"case_id": 1, "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": False}, "confirmed diagnosis by clinician is required")
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "ai", "ai_generated": False}, "confirmed diagnosis by clinician is required")
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": True}, "AI generated diagnosis cannot be used")
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": False, "treatment_framework_preview": {"bad": "10 mg/kg"}, "reviewed_by": "doctor", "review_decision": "reject"}, "forbidden")
    expect_value_error(builder, {"case_id": 1, "confirmed_diagnosis_label": "x", "confirmed_by": "doctor", "confirmation_source": "clinician", "ai_generated": False, "treatment_framework_preview": preview, "reviewed_by": "doctor", "review_decision": "approve_for_clinician_use", "dry_run": False}, "audit_log_confirmation")

    require(len(smoke_text.splitlines()) >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")
    print("PASS: Treatment Framework Audit Log V1")
    print("treatment_framework_audit_log_smoke=PASS_REQUIRED")
    print("requires_clinician_confirmed_diagnosis=true")
    print("ai_does_not_confirm_diagnosis=true")
    print("append_only_audit_log=true")
    print("default_dry_run_writes_database=false")
    print("writes_case_treatment=false")
    print("creates_prescription=false")
    print("writes_prescription=false")
    print("returns_drug_dose=false")
    print("returns_drug_route=false")
    print("returns_drug_frequency=false")
    print("not_client_facing=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision=GO_TO_TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
