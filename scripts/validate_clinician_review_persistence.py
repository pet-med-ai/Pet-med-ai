#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/clinician_review_persistence.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/CLINICIAN_REVIEW_PERSISTENCE_V1.md",
    "docs/clinical_data/CLINICIAN_REVIEW_PERSISTENCE_CHECKLIST_V1.csv",
    "docs/clinical_data/CLINICIAN_REVIEW_PERSISTENCE_GO_NO_GO_V1.csv",
    "scripts/validate_clinician_review_persistence.py",
    "scripts/validate_diagnostic_data_readonly_api_dry_run_fixtures.py",
]

REQUIRED_SNIPPETS = {
    "backend/clinician_review_persistence.py": [
        "CLINICIAN_REVIEW_PERSISTENCE_MODE = \"clinician_review_persistence_v1\"",
        "PERSISTENCE_CONFIRMATION = \"I_UNDERSTAND_THIS_WRITES_REVIEW_STATUS_ONLY\"",
        "writes_database",
        "\"updates_case\": False",
        "\"writes_ai_summary\": False",
        "\"persists_reasoning_trace\": False",
        "\"writes_audit_log\": False",
        "\"generates_final_diagnosis\": False",
        "\"creates_treatment_plan\": False",
        "\"writes_prescription\": False",
        "\"returns_drug_dose\": False",
        "\"requires_human_review\": True",
        "\"clinician_signoff_required\": True",
        "\"review_status_persistence_allowed\": True",
    ],
    "backend/diagnostic_data_api.py": [
        "# --- Clinician Review Persistence V1 endpoint: start ---",
        "@router.post(\"/clinician-review/persistence/apply\"",
        "build_clinician_review_persistence_plan",
        "db.commit()",
        "db.get(DiagnosticReport",
        "\"message\": \"clinician_review_persistence_applied\"",
        "\"writes_audit_log\": False",
        "\"persists_reasoning_trace\": False",
        "# --- Clinician Review Persistence V1 endpoint: end ---",
    ],
    "docs/clinical_data/CLINICIAN_REVIEW_PERSISTENCE_V1.md": [
        "Clinician Review Persistence V1",
        "POST /api/diagnostic-data/clinician-review/persistence/apply",
        "I_UNDERSTAND_THIS_WRITES_REVIEW_STATUS_ONLY",
        "no AI summary write",
        "no audit log write",
        "no persisted reasoning trace",
        "GO_TO_DIAGNOSTIC_SUMMARY_AUDIT_LOG_V1",
    ],
}

PROHIBITED_API_SNIPPETS = [
    "create_prescription(",
    "write_prescription(",
    "create_treatment_plan(",
    "call_external_ai",
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
    path = ROOT / "backend" / "clinician_review_persistence.py"
    spec = importlib.util.spec_from_file_location("clinician_review_persistence", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load clinician_review_persistence module")
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
    api_text = read("backend/diagnostic_data_api.py")
    endpoint_count = api_text.count("/clinician-review/persistence/apply")
    if endpoint_count != 1:
        fail("expected exactly one clinician review persistence endpoint, got %d" % endpoint_count)
    endpoint_block = api_text.split("# --- Clinician Review Persistence V1 endpoint: start ---", 1)[1].split("# --- Clinician Review Persistence V1 endpoint: end ---", 1)[0]
    for snippet in PROHIBITED_API_SNIPPETS:
        if snippet in endpoint_block:
            fail("prohibited API snippet in endpoint block: %s" % snippet)
    for snippet in (
        "model_map",
        "db.get(Observation",
        "db.get(ImagingStudy",
        "target.review_status =",
        'target_type == "observation"',
        'target_type == "imaging_study"',
    ):
        if snippet in endpoint_block:
            fail("Clinician Review Persistence V1 endpoint must not write Observation or ImagingStudy: %s" % snippet)
    readonly_validator = read("scripts/validate_diagnostic_data_readonly_api_dry_run_fixtures.py")
    if "_strip_later_controlled_write_blocks" not in readonly_validator:
        fail("read-only diagnostic-data validator must exclude later controlled persistence blocks")


def assert_module_behavior() -> None:
    module = load_module()
    if module.CLINICIAN_REVIEW_PERSISTENCE_MODE != "clinician_review_persistence_v1":
        fail("mode constant mismatch")

    dry_payload = {
        "case_id": 123,
        "dry_run": True,
        "reviewed_by": "Dr Smoke",
        "review_items": [
            {"target_type": "diagnostic_report", "target_id": 1, "review_status": "reviewed", "note": "reviewed summary preview"},
        ],
    }
    dry_plan = module.build_clinician_review_persistence_plan(dry_payload, case_id=123, case_context={"case_id": 123})
    if dry_plan.get("mode") != "clinician_review_persistence_v1":
        fail("dry plan mode mismatch")
    if dry_plan.get("writes_database") is not False:
        fail("dry_run plan must not write database")
    if dry_plan.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if dry_plan.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
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
    if len(dry_plan.get("review_items") or []) != 1:
        fail("dry plan review item count mismatch")
    if dry_plan.get("updates_observation") is not False:
        fail("observation writes must remain closed in this stage")
    if dry_plan.get("updates_imaging_study") is not False:
        fail("imaging study writes must remain closed in this stage")

    commit_payload = dict(dry_payload)
    commit_payload["dry_run"] = False
    try:
        module.build_clinician_review_persistence_plan(commit_payload, case_id=123, case_context={"case_id": 123})
        fail("commit payload without confirmation should fail")
    except ValueError as exc:
        if "I_UNDERSTAND_THIS_WRITES_REVIEW_STATUS_ONLY" not in str(exc):
            fail("missing confirmation error text")

    commit_payload["persistence_confirmation"] = module.PERSISTENCE_CONFIRMATION
    commit_plan = module.build_clinician_review_persistence_plan(commit_payload, case_id=123, case_context={"case_id": 123})
    if commit_plan.get("writes_database") is not True:
        fail("confirmed commit plan should advertise writes_database=true")
    if commit_plan.get("quality_gate", {}).get("status") != "PASS":
        fail("quality gate should PASS")

    dangerous_payload = {
        "case_id": 123,
        "dry_run": True,
        "reviewed_by": "Dr Smoke",
        "final_diagnosis": "blocked",
    }
    try:
        module.build_clinician_review_persistence_plan(dangerous_payload, case_id=123, case_context={"case_id": 123})
        fail("dangerous payload should fail")
    except ValueError:
        pass

    print(json.dumps({
        "mode": dry_plan.get("mode"),
        "dry_run_writes_database": dry_plan.get("writes_database"),
        "commit_writes_database": commit_plan.get("writes_database"),
        "quality_gate": commit_plan.get("quality_gate", {}).get("status"),
    }, ensure_ascii=False))


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Clinician Review Persistence V1 static checks" not in ci:
        fail("ci_static_checks missing Clinician Review Persistence V1 block")
    if "python3 scripts/validate_clinician_review_persistence.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "Clinician Review Persistence V1 smoke" not in smoke:
        fail("smoke missing Clinician Review Persistence V1 block")
    if "clinician_review_persistence_applied" not in smoke:
        fail("smoke missing endpoint assertion")


def main() -> None:
    assert_snippets()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Clinician Review Persistence V1")


if __name__ == "__main__":
    main()
