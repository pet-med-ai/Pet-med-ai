#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/observation_abnormal_flag_review.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/OBSERVATION_ABNORMAL_FLAG_REVIEW_V1.md",
    "docs/clinical_data/OBSERVATION_ABNORMAL_FLAG_REVIEW_CHECKLIST_V1.csv",
    "docs/clinical_data/OBSERVATION_ABNORMAL_FLAG_REVIEW_GO_NO_GO_V1.csv",
    "scripts/validate_observation_abnormal_flag_review.py",
]

REQUIRED_SNIPPETS = {
    "backend/observation_abnormal_flag_review.py": [
        'OBSERVATION_ABNORMAL_FLAG_REVIEW_MODE = "observation_abnormal_flag_review_v1"',
        'OBSERVATION_ABNORMAL_FLAG_REVIEW_CONFIRMATION = "I_UNDERSTAND_THIS_WRITES_OBSERVATION_ABNORMAL_FLAG_REVIEW_ONLY"',
        '"writes_database": writes',
        '"updates_case": False',
        '"updates_diagnostic_report": False',
        '"updates_observation": writes',
        '"writes_observation_abnormal_flag_only": writes',
        '"writes_ai_summary": False',
        '"writes_audit_log": False',
        '"persists_reasoning_trace": False',
        '"generates_final_diagnosis": False',
        '"creates_treatment_plan": False',
        '"writes_prescription": False',
        '"returns_drug_dose": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
        'observation.abnormal_flag = abnormal_flag',
        'observation.review_status = review_status',
        'db.commit()',
    ],
    "backend/diagnostic_data_api.py": [
        "# --- Observation Abnormal Flag Review V1 endpoint: start ---",
        '@router.post("/observations/{observation_id}/abnormal-flag/review/apply"',
        "apply_observation_abnormal_flag_review",
        '"message": "observation_abnormal_flag_review_applied"',
        "# --- Observation Abnormal Flag Review V1 endpoint: end ---",
    ],
    "docs/clinical_data/OBSERVATION_ABNORMAL_FLAG_REVIEW_V1.md": [
        "Observation Abnormal Flag Review V1",
        "POST /api/diagnostic-data/observations/{observation_id}/abnormal-flag/review/apply",
        "I_UNDERSTAND_THIS_WRITES_OBSERVATION_ABNORMAL_FLAG_REVIEW_ONLY",
        "Observation.abnormal_flag",
        "Observation.review_status",
        "no DiagnosticReport write",
        "no AuditLog write",
        "GO_TO_IMAGINGSTUDY_REVIEW_WORKFLOW_V1",
    ],
}

PROHIBITED_HELPER_SNIPPETS = [
    "create_prescription(",
    "write_prescription(",
    "create_treatment_plan(",
    "OpenAI(",
    "requests.post(",
    "httpx.post(",
    "db.add(",
    "DiagnosticReport(",
    "ImagingStudy(",
    "AuditLog(",
]

PROHIBITED_API_ENDPOINT_SNIPPETS = [
    "db.commit()",
    "db.add(",
    "observation.abnormal_flag =",
    "observation.review_status =",
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
    path = ROOT / "backend" / "observation_abnormal_flag_review.py"
    spec = importlib.util.spec_from_file_location("observation_abnormal_flag_review", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load observation_abnormal_flag_review module")
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

    helper_text = read("backend/observation_abnormal_flag_review.py")
    for snippet in PROHIBITED_HELPER_SNIPPETS:
        if snippet in helper_text:
            fail("prohibited helper snippet: %s" % snippet)

    api_text = read("backend/diagnostic_data_api.py")
    endpoint_count = api_text.count("/observations/{observation_id}/abnormal-flag/review/apply")
    if endpoint_count != 1:
        fail("expected exactly one Observation Abnormal Flag Review endpoint, got %d" % endpoint_count)

    endpoint_block = api_text.split("# --- Observation Abnormal Flag Review V1 endpoint: start ---", 1)[1].split("# --- Observation Abnormal Flag Review V1 endpoint: end ---", 1)[0]
    for snippet in PROHIBITED_API_ENDPOINT_SNIPPETS:
        if snippet in endpoint_block:
            fail("prohibited API endpoint snippet: %s" % snippet)


class FakeObservation:
    def __init__(self) -> None:
        self.id = 88
        self.case_id = 777
        self.diagnostic_report_id = 55
        self.code = "ALT"
        self.display_name = "ALT"
        self.value_text = None
        self.value_numeric = 220.0
        self.unit = "U/L"
        self.reference_low = 10.0
        self.reference_high = 100.0
        self.reference_text = "10-100"
        self.abnormal_flag = "normal"
        self.review_status = "draft"
        self.source_type = "manual"
        self.updated_at = None


class FakeAuditLog:
    log_id = "audit-smoke-1"
    case_id = 777
    event_type = "diagnostic_summary_review"
    source = "diagnostic_summary_audit_log_v1"


class FakeDb:
    def __init__(self) -> None:
        self.committed = False
        self.refreshed = False
        self.audit = FakeAuditLog()

    def get(self, model, key):  # noqa: ANN001
        if str(key) == "audit-smoke-1":
            return self.audit
        return None

    def commit(self) -> None:
        self.committed = True

    def refresh(self, obj) -> None:  # noqa: ANN001
        self.refreshed = True


def assert_module_behavior() -> None:
    module = load_module()
    if module.OBSERVATION_ABNORMAL_FLAG_REVIEW_MODE != "observation_abnormal_flag_review_v1":
        fail("mode constant mismatch")

    obs = FakeObservation()
    db = FakeDb()
    dry_payload = {
        "case_id": 777,
        "dry_run": True,
        "reviewed_by": "Dr Smoke",
        "abnormal_flag": "high",
        "review_status": "reviewed",
        "note": "abnormal flag review only",
    }
    dry_result = module.apply_observation_abnormal_flag_review(
        db=db,
        observation=obs,
        payload=dry_payload,
        observation_context={"observation_id": obs.id},
    )
    if dry_result.get("mode") != "observation_abnormal_flag_review_v1":
        fail("dry result mode mismatch")
    if dry_result.get("writes_database") is not False:
        fail("dry_run must not write database")
    if dry_result.get("updates_observation") is not False:
        fail("dry_run must not update observation")
    if dry_result.get("writes_audit_log") is not False:
        fail("dry_run must not write audit log")
    if dry_result.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if dry_result.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    if dry_result.get("generates_final_diagnosis") is not False:
        fail("must not generate final diagnosis")
    if dry_result.get("creates_treatment_plan") is not False:
        fail("must not create treatment plan")
    if dry_result.get("writes_prescription") is not False:
        fail("must not write prescription")
    if dry_result.get("returns_drug_dose") is not False:
        fail("must not return drug dose")
    if obs.abnormal_flag != "normal" or obs.review_status != "draft":
        fail("dry_run mutated observation")

    commit_payload = dict(dry_payload)
    commit_payload["dry_run"] = False
    try:
        module.apply_observation_abnormal_flag_review(db=db, observation=obs, payload=commit_payload)
        fail("commit without confirmation should fail")
    except ValueError as exc:
        if "I_UNDERSTAND_THIS_WRITES_OBSERVATION_ABNORMAL_FLAG_REVIEW_ONLY" not in str(exc):
            fail("missing confirmation error text")

    commit_payload["abnormal_flag_review_confirmation"] = module.OBSERVATION_ABNORMAL_FLAG_REVIEW_CONFIRMATION
    try:
        module.apply_observation_abnormal_flag_review(db=db, observation=obs, payload=commit_payload)
        fail("commit without audit_log_id should fail")
    except ValueError as exc:
        if "audit_log_id" not in str(exc):
            fail("missing audit_log_id error text")

    commit_payload["audit_log_id"] = "audit-smoke-1"
    commit_result = module.apply_observation_abnormal_flag_review(db=db, observation=obs, payload=commit_payload)
    if commit_result.get("writes_database") is not True:
        fail("confirmed commit should write database")
    if commit_result.get("updates_observation") is not True:
        fail("confirmed commit should update observation")
    if commit_result.get("writes_observation_abnormal_flag_only") is not True:
        fail("confirmed commit should advertise abnormal flag review write only")
    if commit_result.get("updates_diagnostic_report") is not False:
        fail("must not update diagnostic report")
    if commit_result.get("updates_imaging_study") is not False:
        fail("must not update imaging study")
    if commit_result.get("writes_audit_log") is not False:
        fail("must not write audit log")
    if obs.abnormal_flag != "high" or obs.review_status != "reviewed":
        fail("observation fields not updated as expected")
    if db.committed is not True or db.refreshed is not True:
        fail("db commit/refresh not called")

    dangerous_payload = {
        "case_id": 777,
        "dry_run": True,
        "reviewed_by": "Dr Smoke",
        "abnormal_flag": "high",
        "final_diagnosis": "blocked",
    }
    try:
        module.apply_observation_abnormal_flag_review(db=FakeDb(), observation=FakeObservation(), payload=dangerous_payload)
        fail("dangerous payload should fail")
    except ValueError:
        pass

    print(json.dumps({
        "mode": dry_result.get("mode"),
        "dry_run_writes_database": dry_result.get("writes_database"),
        "commit_writes_database": commit_result.get("writes_database"),
        "quality_gate": commit_result.get("quality_gate", {}).get("status"),
    }, ensure_ascii=False))


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Observation Abnormal Flag Review V1 static checks" not in ci:
        fail("ci_static_checks missing Observation Abnormal Flag Review V1 block")
    if "python3 scripts/validate_observation_abnormal_flag_review.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "Observation Abnormal Flag Review V1 smoke" not in smoke:
        fail("smoke missing Observation Abnormal Flag Review V1 block")
    if "observation_abnormal_flag_review_applied" not in smoke:
        fail("smoke missing endpoint assertion")


def main() -> None:
    assert_snippets()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Observation Abnormal Flag Review V1")


if __name__ == "__main__":
    main()
