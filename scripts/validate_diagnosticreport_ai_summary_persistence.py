#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/diagnostic_report_ai_summary_persistence.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_V1.md",
    "docs/clinical_data/DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_CHECKLIST_V1.csv",
    "docs/clinical_data/DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_GO_NO_GO_V1.csv",
    "scripts/validate_diagnosticreport_ai_summary_persistence.py",
]

REQUIRED_SNIPPETS = {
    "backend/diagnostic_report_ai_summary_persistence.py": [
        "DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_MODE = \"diagnosticreport_ai_summary_persistence_v1\"",
        "AI_SUMMARY_PERSISTENCE_CONFIRMATION = \"I_UNDERSTAND_THIS_WRITES_DIAGNOSTICREPORT_AI_SUMMARY_ONLY\"",
        "REQUIRED_AUDIT_SOURCE = \"diagnostic_summary_audit_log_v1\"",
        "\"writes_ai_summary\": writes",
        "\"writes_ai_summary_status\": writes",
        "\"writes_audit_log\": False",
        "\"persists_reasoning_trace\": False",
        "\"generates_final_diagnosis\": False",
        "\"creates_treatment_plan\": False",
        "\"writes_prescription\": False",
        "\"returns_drug_dose\": False",
        "\"requires_human_review\": True",
        "\"clinician_signoff_required\": True",
        "db.commit()",
    ],
    "backend/diagnostic_data_api.py": [
        "# --- DiagnosticReport AI Summary Persistence V1 endpoint: start ---",
        "@router.post(\"/diagnostic-reports/{report_id}/ai-summary/persistence/apply\"",
        "apply_diagnosticreport_ai_summary_persistence",
        "\"message\": \"diagnosticreport_ai_summary_persistence_applied\"",
        "# --- DiagnosticReport AI Summary Persistence V1 endpoint: end ---",
    ],
    "docs/clinical_data/DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_V1.md": [
        "DiagnosticReport AI Summary Persistence V1",
        "POST /api/diagnostic-data/diagnostic-reports/{report_id}/ai-summary/persistence/apply",
        "I_UNDERSTAND_THIS_WRITES_DIAGNOSTICREPORT_AI_SUMMARY_ONLY",
        "DiagnosticReport.ai_summary",
        "final diagnosis",
        "GO_TO_OBSERVATION_ABNORMAL_FLAG_REVIEW_V1",
    ],
}

PROHIBITED_API_BLOCK_SNIPPETS = [
    "db.commit(",
    "db.add(",
    "db.delete(",
    "AuditLog(",
    "Observation(",
    "ImagingStudy(",
    "requests.post(",
    "httpx.post(",
    "OpenAI(",
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
    path = ROOT / "backend" / "diagnostic_report_ai_summary_persistence.py"
    spec = importlib.util.spec_from_file_location("diagnostic_report_ai_summary_persistence", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load diagnostic_report_ai_summary_persistence module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_snippets() -> None:
    for rel in REQUIRED_FILES:
        read(rel)
    for rel, snippets in REQUIRED_SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))

    api = read("backend/diagnostic_data_api.py")
    endpoint_count = api.count("/diagnostic-reports/{report_id}/ai-summary/persistence/apply")
    if endpoint_count != 1:
        fail("expected exactly one DiagnosticReport AI summary persistence endpoint, got %d" % endpoint_count)
    if "# --- DiagnosticReport AI Summary Persistence V1 endpoint: start ---" not in api:
        fail("endpoint start marker missing")
    endpoint_block = api.split("# --- DiagnosticReport AI Summary Persistence V1 endpoint: start ---", 1)[1].split("# --- DiagnosticReport AI Summary Persistence V1 endpoint: end ---", 1)[0]
    for snippet in PROHIBITED_API_BLOCK_SNIPPETS:
        if snippet in endpoint_block:
            fail("prohibited snippet in diagnostic_data_api endpoint block: %s" % snippet)


def assert_module_behavior() -> None:
    module = load_module()
    if module.DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_MODE != "diagnosticreport_ai_summary_persistence_v1":
        fail("mode constant mismatch")

    dry_payload = {
        "diagnostic_report_id": 456,
        "dry_run": True,
        "reviewed_by": "Dr Smoke",
        "ai_summary": "Clinician-reviewed summary: lab and imaging abnormalities require continued professional review.",
        "source_preview_ids": ["problem-list-preview", "evidence-trace-preview"],
    }
    dry_plan = module.build_diagnosticreport_ai_summary_persistence_plan(dry_payload, report_id=456, report_context={"report_id": 456})
    if dry_plan.get("mode") != "diagnosticreport_ai_summary_persistence_v1":
        fail("dry plan mode mismatch")
    if dry_plan.get("writes_database") is not False:
        fail("dry plan must not write database")
    if dry_plan.get("writes_ai_summary") is not False:
        fail("dry plan must not write ai_summary")
    if dry_plan.get("writes_audit_log") is not False:
        fail("dry plan must not write audit log")
    if dry_plan.get("persists_reasoning_trace") is not False:
        fail("dry plan must not persist reasoning trace")
    if dry_plan.get("generates_final_diagnosis") is not False:
        fail("dry plan must not generate final diagnosis")
    if dry_plan.get("creates_treatment_plan") is not False:
        fail("dry plan must not create treatment plan")
    if dry_plan.get("writes_prescription") is not False:
        fail("dry plan must not write prescription")
    if dry_plan.get("returns_drug_dose") is not False:
        fail("dry plan must not return drug dose")
    if dry_plan.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if dry_plan.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")

    commit_payload = dict(dry_payload)
    commit_payload["dry_run"] = False
    try:
        module.build_diagnosticreport_ai_summary_persistence_plan(commit_payload, report_id=456, report_context={"report_id": 456})
        fail("commit payload without confirmation/audit log should fail")
    except ValueError as exc:
        text = str(exc)
        if "I_UNDERSTAND_THIS_WRITES_DIAGNOSTICREPORT_AI_SUMMARY_ONLY" not in text:
            fail("missing confirmation error text")

    commit_payload["persistence_confirmation"] = module.AI_SUMMARY_PERSISTENCE_CONFIRMATION
    commit_payload["audit_log_id"] = "audit-smoke-id"
    commit_plan = module.build_diagnosticreport_ai_summary_persistence_plan(commit_payload, report_id=456, report_context={"report_id": 456})
    if commit_plan.get("writes_database") is not True:
        fail("confirmed commit plan should advertise writes_database=true")
    if commit_plan.get("writes_ai_summary") is not True:
        fail("confirmed commit plan should advertise writes_ai_summary=true")
    if commit_plan.get("writes_audit_log") is not False:
        fail("AI summary persistence must not write audit log")
    if commit_plan.get("quality_gate", {}).get("status") != "PASS":
        fail("quality gate should PASS")

    dangerous_payload = dict(dry_payload)
    dangerous_payload["final_diagnosis"] = "blocked"
    try:
        module.build_diagnosticreport_ai_summary_persistence_plan(dangerous_payload, report_id=456, report_context={"report_id": 456})
        fail("dangerous payload should fail")
    except ValueError:
        pass

    dose_payload = dict(dry_payload)
    dose_payload["ai_summary"] = "Clinician-reviewed summary includes 1 mg/kg, which must be blocked."
    try:
        module.build_diagnosticreport_ai_summary_persistence_plan(dose_payload, report_id=456, report_context={"report_id": 456})
        fail("dose payload should fail")
    except ValueError:
        pass

    print(json.dumps({
        "mode": dry_plan.get("mode"),
        "dry_run_writes_database": dry_plan.get("writes_database"),
        "commit_writes_database": commit_plan.get("writes_database"),
        "commit_writes_ai_summary": commit_plan.get("writes_ai_summary"),
        "quality_gate": commit_plan.get("quality_gate", {}).get("status"),
    }, ensure_ascii=False))


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "DiagnosticReport AI Summary Persistence V1 static checks" not in ci:
        fail("ci_static_checks missing DiagnosticReport AI Summary Persistence V1 block")
    if "python3 scripts/validate_diagnosticreport_ai_summary_persistence.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "DiagnosticReport AI Summary Persistence V1 smoke" not in smoke:
        fail("smoke missing DiagnosticReport AI Summary Persistence V1 block")
    if "diagnosticreport_ai_summary_persistence_applied" not in smoke:
        fail("smoke missing endpoint assertion")


def main() -> None:
    assert_snippets()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS DiagnosticReport AI Summary Persistence V1")


if __name__ == "__main__":
    main()
