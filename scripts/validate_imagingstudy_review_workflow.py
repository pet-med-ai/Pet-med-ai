#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/imagingstudy_review_workflow.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/IMAGINGSTUDY_REVIEW_WORKFLOW_V1.md",
    "docs/clinical_data/IMAGINGSTUDY_REVIEW_WORKFLOW_CHECKLIST_V1.csv",
    "docs/clinical_data/IMAGINGSTUDY_REVIEW_WORKFLOW_GO_NO_GO_V1.csv",
    "scripts/validate_imagingstudy_review_workflow.py",
]

REQUIRED_SNIPPETS = {
    "backend/imagingstudy_review_workflow.py": [
        'IMAGINGSTUDY_REVIEW_WORKFLOW_MODE = "imagingstudy_review_workflow_v1"',
        'IMAGINGSTUDY_REVIEW_WORKFLOW_CONFIRMATION = "I_UNDERSTAND_THIS_WRITES_IMAGINGSTUDY_REVIEW_WORKFLOW_ONLY"',
        '"writes_database": writes',
        '"updates_case": False',
        '"updates_diagnostic_report": False',
        '"updates_observation": False',
        '"updates_imaging_study": writes',
        '"writes_imaging_study_review_status": writes',
        '"writes_imaging_study_reviewed_by": writes',
        '"writes_imaging_study_reviewed_at": writes',
        '"writes_imaging_study_abnormal_flag": writes',
        '"writes_imaging_study_report_text": False',
        '"writes_ai_summary": False',
        '"writes_audit_log": False',
        '"persists_reasoning_trace": False',
        '"generates_final_diagnosis": False',
        '"creates_treatment_plan": False',
        '"writes_prescription": False',
        '"returns_drug_dose": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
        'imaging_study.review_status = review_status',
        'imaging_study.reviewed_by = reviewed_by',
        'imaging_study.reviewed_at = now',
        'imaging_study.abnormal_flag = abnormal_flag',
        'db.commit()',
    ],
    "backend/diagnostic_data_api.py": [
        "# --- ImagingStudy Review Workflow V1 endpoint: start ---",
        '@router.post("/imaging-studies/{imaging_study_id}/review-workflow/apply"',
        "apply_imagingstudy_review_workflow",
        '"message": "imagingstudy_review_workflow_applied"',
        "# --- ImagingStudy Review Workflow V1 endpoint: end ---",
    ],
    "docs/clinical_data/IMAGINGSTUDY_REVIEW_WORKFLOW_V1.md": [
        "ImagingStudy Review Workflow V1",
        "POST /api/diagnostic-data/imaging-studies/{imaging_study_id}/review-workflow/apply",
        "I_UNDERSTAND_THIS_WRITES_IMAGINGSTUDY_REVIEW_WORKFLOW_ONLY",
        "ImagingStudy.review_status",
        "ImagingStudy.reviewed_by",
        "ImagingStudy.reviewed_at",
        "ImagingStudy.abnormal_flag",
        "no DiagnosticReport write",
        "no Observation write",
        "no AuditLog write",
        "GO_TO_CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_V1",
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
    "Observation(",
    "AuditLog(",
]

PROHIBITED_API_ENDPOINT_SNIPPETS = [
    "db.commit()",
    "db.add(",
    "imaging_study.review_status =",
    "imaging_study.reviewed_by =",
    "imaging_study.reviewed_at =",
    "imaging_study.abnormal_flag =",
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
    path = ROOT / "backend" / "imagingstudy_review_workflow.py"
    spec = importlib.util.spec_from_file_location("imagingstudy_review_workflow", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load imagingstudy_review_workflow module")
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
    endpoint_count = api_text.count("/imaging-studies/{imaging_study_id}/review-workflow/apply")
    if endpoint_count != 1:
        fail("expected exactly one ImagingStudy Review Workflow endpoint, got %d" % endpoint_count)
    endpoint_block = api_text.split("# --- ImagingStudy Review Workflow V1 endpoint: start ---", 1)[1].split("# --- ImagingStudy Review Workflow V1 endpoint: end ---", 1)[0]
    for snippet in PROHIBITED_API_ENDPOINT_SNIPPETS:
        if snippet in endpoint_block:
            fail("prohibited API endpoint snippet in ImagingStudy block: %s" % snippet)

    helper_text = read("backend/imagingstudy_review_workflow.py")
    for snippet in PROHIBITED_HELPER_SNIPPETS:
        if snippet in helper_text:
            fail("prohibited helper snippet in imagingstudy review workflow module: %s" % snippet)


def assert_module_behavior() -> None:
    module = load_module()
    if module.IMAGINGSTUDY_REVIEW_WORKFLOW_MODE != "imagingstudy_review_workflow_v1":
        fail("mode constant mismatch")

    class FakeImagingStudy:
        id = 7
        case_id = 123
        modality = "radiograph"
        body_part = "abdomen"
        taken_at = None
        study_uid = "study-smoke"
        accession_number = "acc-smoke"
        source_type = "manual"
        source_system = "smoke"
        abnormal_flag = "not_reviewed"
        review_status = "pending_clinician_review"
        reviewed_by = None
        reviewed_at = None
        ai_summary_status = "not_generated"
        report_text = "review text exists"
        updated_at = None

    class FakeAuditLog:
        pass

    class FakeDb:
        committed = False
        refreshed = False
        def get(self, model, key):
            log = FakeAuditLog()
            log.log_id = key
            log.case_id = 123
            log.event_type = "diagnostic_summary_review"
            log.source = "diagnostic_summary_audit_log_v1"
            return log
        def commit(self):
            self.committed = True
        def refresh(self, obj):
            self.refreshed = True

    module._audit_log_model = lambda: FakeAuditLog

    dry_payload = {
        "case_id": 123,
        "dry_run": True,
        "reviewed_by": "Dr Smoke",
        "review_status": "reviewed",
        "abnormal_flag": "abnormal",
        "note": "Imaging metadata review only; not a diagnosis.",
    }
    fake = FakeImagingStudy()
    dry_plan = module.apply_imagingstudy_review_workflow(
        db=FakeDb(),
        imaging_study=fake,
        payload=dry_payload,
        imaging_context={"imaging_study_id": 7},
    )
    if dry_plan.get("mode") != "imagingstudy_review_workflow_v1":
        fail("dry plan mode mismatch")
    if dry_plan.get("writes_database") is not False:
        fail("dry-run plan must not write database")
    if dry_plan.get("updates_imaging_study") is not False:
        fail("dry-run must not update ImagingStudy")
    if dry_plan.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if dry_plan.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    if dry_plan.get("writes_audit_log") is not False:
        fail("must not write audit log")
    if dry_plan.get("persists_reasoning_trace") is not False:
        fail("must not persist reasoning trace")
    if dry_plan.get("generates_final_diagnosis") is not False:
        fail("must not generate final diagnosis")
    if dry_plan.get("creates_treatment_plan") is not False:
        fail("must not create treatment plan")
    if dry_plan.get("writes_prescription") is not False:
        fail("must not write prescription")
    if dry_plan.get("returns_drug_dose") is not False:
        fail("must not return drug dose")
    if dry_plan.get("updates_observation") is not False:
        fail("Observation writes must remain closed")
    if dry_plan.get("updates_diagnostic_report") is not False:
        fail("DiagnosticReport writes must remain closed")

    commit_payload = dict(dry_payload)
    commit_payload["dry_run"] = False
    try:
        module.apply_imagingstudy_review_workflow(db=FakeDb(), imaging_study=FakeImagingStudy(), payload=commit_payload)
        fail("commit payload without confirmation should fail")
    except ValueError as exc:
        if "I_UNDERSTAND_THIS_WRITES_IMAGINGSTUDY_REVIEW_WORKFLOW_ONLY" not in str(exc):
            fail("missing confirmation error text")

    commit_payload["imagingstudy_review_confirmation"] = module.IMAGINGSTUDY_REVIEW_WORKFLOW_CONFIRMATION
    commit_payload["audit_log_id"] = "audit-smoke"
    db = FakeDb()
    image = FakeImagingStudy()
    commit_plan = module.apply_imagingstudy_review_workflow(db=db, imaging_study=image, payload=commit_payload)
    if commit_plan.get("writes_database") is not True:
        fail("confirmed commit should advertise writes_database=true")
    if commit_plan.get("updates_imaging_study") is not True:
        fail("confirmed commit should update ImagingStudy")
    if db.committed is not True or db.refreshed is not True:
        fail("confirmed commit should call commit and refresh")
    if image.review_status != "reviewed" or image.reviewed_by != "Dr Smoke" or image.abnormal_flag != "abnormal":
        fail("confirmed commit did not update only expected imaging study fields")
    if commit_plan.get("quality_gate", {}).get("status") != "PASS":
        fail("quality gate should PASS")

    dangerous_payload = {
        "case_id": 123,
        "dry_run": True,
        "reviewed_by": "Dr Smoke",
        "final_diagnosis": "blocked",
    }
    try:
        module.apply_imagingstudy_review_workflow(db=FakeDb(), imaging_study=FakeImagingStudy(), payload=dangerous_payload)
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
    if "ImagingStudy Review Workflow V1 static checks" not in ci:
        fail("ci_static_checks missing ImagingStudy Review Workflow V1 block")
    if "python3 scripts/validate_imagingstudy_review_workflow.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "ImagingStudy Review Workflow V1 smoke" not in smoke:
        fail("smoke missing ImagingStudy Review Workflow V1 block")
    if "imagingstudy_review_workflow_applied" not in smoke:
        fail("smoke missing endpoint assertion")


def main() -> None:
    assert_snippets()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS ImagingStudy Review Workflow V1")


if __name__ == "__main__":
    main()
