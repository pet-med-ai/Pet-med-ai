#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/diagnostic_summary_audit_log.py",
    "backend/audit_log_api.py",
    "docs/clinical_data/DIAGNOSTIC_SUMMARY_AUDIT_LOG_V1.md",
    "docs/clinical_data/DIAGNOSTIC_SUMMARY_AUDIT_LOG_CHECKLIST_V1.csv",
    "docs/clinical_data/DIAGNOSTIC_SUMMARY_AUDIT_LOG_GO_NO_GO_V1.csv",
    "scripts/validate_diagnostic_summary_audit_log.py",
]

REQUIRED_SNIPPETS = {
    "backend/diagnostic_summary_audit_log.py": [
        "DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE = \"diagnostic_summary_audit_log_v1\"",
        "AUDIT_LOG_CONFIRMATION = \"I_UNDERSTAND_THIS_APPENDS_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ONLY\"",
        "\"writes_audit_log\": writes",
        "\"append_only_audit_log\": True",
        "\"updates_case\": False",
        "\"updates_diagnostic_report\": False",
        "\"updates_observation\": False",
        "\"updates_imaging_study\": False",
        "\"writes_ai_summary\": False",
        "\"persists_reasoning_trace\": False",
        "\"generates_final_diagnosis\": False",
        "\"creates_treatment_plan\": False",
        "\"writes_prescription\": False",
        "\"returns_drug_dose\": False",
        "\"returns_probability\": False",
        "\"requires_human_review\": True",
        "\"clinician_signoff_required\": True",
    ],
    "backend/audit_log_api.py": [
        "# --- Diagnostic Summary Audit Log V1 endpoint: start ---",
        "@router.post(\"/diagnostic-data/diagnostic-summary/audit-log/append\"",
        "build_diagnostic_summary_audit_log_event",
        "AuditLog(",
        "confidence=None",
        "db.add(obj)",
        "db.commit()",
        "\"message\": \"diagnostic_summary_audit_log_appended\"",
        "\"writes_diagnostic_report\": False",
        "\"writes_ai_summary\": False",
        "\"writes_audit_log\": True",
        "# --- Diagnostic Summary Audit Log V1 endpoint: end ---",
    ],
    "docs/clinical_data/DIAGNOSTIC_SUMMARY_AUDIT_LOG_V1.md": [
        "Diagnostic Summary Audit Log V1",
        "POST /api/diagnostic-data/diagnostic-summary/audit-log/append",
        "I_UNDERSTAND_THIS_APPENDS_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ONLY",
        "AuditLog",
        "append-only",
        "no DiagnosticReport write",
        "no AI summary write",
        "no persisted reasoning trace",
        "GO_TO_DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_V1",
    ],
}

PROHIBITED_ENDPOINT_SNIPPETS = [
    "target.status =",
    "target.review_status =",
    ".ai_summary =",
    ".abnormal_summary =",
    "Case(",
    "DiagnosticReport(",
    "Observation(",
    "ImagingStudy(",
    "create_prescription(",
    "write_prescription(",
    "create_treatment_plan(",
    "OpenAI(",
    "requests.post(",
    "httpx.post(",
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
    path = ROOT / "backend" / "diagnostic_summary_audit_log.py"
    spec = importlib.util.spec_from_file_location("diagnostic_summary_audit_log", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load diagnostic_summary_audit_log module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    for rel, snippets in REQUIRED_SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))

    api_text = read("backend/audit_log_api.py")
    endpoint_count = api_text.count("@router.post(\"/diagnostic-data/diagnostic-summary/audit-log/append\"")
    if endpoint_count != 1:
        fail("expected exactly one diagnostic summary audit log endpoint, got %d" % endpoint_count)

    block = api_text.split("# --- Diagnostic Summary Audit Log V1 endpoint: start ---", 1)[1].split("# --- Diagnostic Summary Audit Log V1 endpoint: end ---", 1)[0]
    for snippet in PROHIBITED_ENDPOINT_SNIPPETS:
        if snippet in block:
            fail("prohibited endpoint snippet: %s" % snippet)


def assert_module_behavior() -> None:
    module = load_module()
    if module.DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE != "diagnostic_summary_audit_log_v1":
        fail("mode constant mismatch")

    dry_payload = {
        "case_id": 123,
        "dry_run": True,
        "clinician_id": "Dr Smoke",
        "action_taken": "summary_reviewed",
        "review_status": "reviewed",
        "target_type": "case_diagnostic_assistance",
        "source_preview_ids": ["problem-list", "ddx", "trace"],
        "note": "Dry-run audit event only; no diagnosis or treatment plan.",
    }
    dry_plan = module.build_diagnostic_summary_audit_log_event(dry_payload, case_id=123, case_context={"case_id": 123})
    if dry_plan.get("mode") != "diagnostic_summary_audit_log_v1":
        fail("dry plan mode mismatch")
    if dry_plan.get("writes_database") is not False:
        fail("dry_run plan must not write database")
    if dry_plan.get("writes_audit_log") is not False:
        fail("dry_run plan must not write audit log")
    if dry_plan.get("creates_audit_log") is not False:
        fail("dry_run plan must not create audit log")
    for key in (
        "updates_case",
        "updates_diagnostic_report",
        "updates_observation",
        "updates_imaging_study",
        "writes_ai_summary",
        "persists_reasoning_trace",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
        "returns_drug_dose",
        "returns_probability",
        "returns_numeric_confidence",
    ):
        if dry_plan.get(key) is not False:
            fail("dry plan must keep %s false" % key)
    if dry_plan.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if dry_plan.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")

    write_payload = dict(dry_payload)
    write_payload["dry_run"] = False
    try:
        module.build_diagnostic_summary_audit_log_event(write_payload, case_id=123, case_context={"case_id": 123})
        fail("write payload without confirmation should fail")
    except ValueError as exc:
        if module.AUDIT_LOG_CONFIRMATION not in str(exc):
            fail("missing audit confirmation error text")

    write_payload["audit_log_confirmation"] = module.AUDIT_LOG_CONFIRMATION
    write_plan = module.build_diagnostic_summary_audit_log_event(write_payload, case_id=123, case_context={"case_id": 123})
    if write_plan.get("writes_database") is not True:
        fail("confirmed write plan should advertise writes_database=true")
    if write_plan.get("writes_audit_log") is not True:
        fail("confirmed write plan should advertise writes_audit_log=true")
    if write_plan.get("quality_gate", {}).get("status") != "PASS":
        fail("quality gate should PASS")
    if write_plan.get("audit_event", {}).get("confidence") is not None:
        fail("audit event must not include numeric confidence")

    report_payload = dict(dry_payload)
    report_payload.update({"target_type": "diagnostic_report", "target_id": 42})
    report_plan = module.build_diagnostic_summary_audit_log_event(report_payload, case_id=123, case_context={"case_id": 123})
    if report_plan.get("audit_log_result", {}).get("target_type") != "diagnostic_report":
        fail("diagnostic_report target type not preserved")

    dangerous_payload = dict(dry_payload)
    dangerous_payload["final_diagnosis"] = "blocked"
    try:
        module.build_diagnostic_summary_audit_log_event(dangerous_payload, case_id=123, case_context={"case_id": 123})
        fail("dangerous key payload should fail")
    except ValueError:
        pass

    dose_payload = dict(dry_payload)
    dose_payload["note"] = "Give 5 mg/kg PO"
    try:
        module.build_diagnostic_summary_audit_log_event(dose_payload, case_id=123, case_context={"case_id": 123})
        fail("dose text payload should fail")
    except ValueError:
        pass

    bad_target_payload = dict(dry_payload)
    bad_target_payload["target_type"] = "observation"
    try:
        module.build_diagnostic_summary_audit_log_event(bad_target_payload, case_id=123, case_context={"case_id": 123})
        fail("observation target should fail in this stage")
    except ValueError:
        pass

    print(json.dumps({
        "mode": dry_plan.get("mode"),
        "dry_run_writes_audit_log": dry_plan.get("writes_audit_log"),
        "write_writes_audit_log": write_plan.get("writes_audit_log"),
        "quality_gate": write_plan.get("quality_gate", {}).get("status"),
    }, ensure_ascii=False))


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Diagnostic Summary Audit Log V1 static checks" not in ci:
        fail("ci_static_checks missing Diagnostic Summary Audit Log V1 block")
    if "python3 scripts/validate_diagnostic_summary_audit_log.py" not in ci:
        fail("ci_static_checks missing diagnostic summary audit validator command")
    if "Diagnostic Summary Audit Log V1 smoke" not in smoke:
        fail("smoke missing Diagnostic Summary Audit Log V1 block")
    if "diagnostic_summary_audit_log_appended" not in smoke:
        fail("smoke missing endpoint assertion")


def main() -> None:
    assert_files_and_snippets()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Diagnostic Summary Audit Log V1")


if __name__ == "__main__":
    main()
