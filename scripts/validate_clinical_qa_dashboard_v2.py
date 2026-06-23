#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/clinical_qa_dashboard.py",
    "backend/diagnostic_data_api.py",
    "docs/clinical_data/CLINICAL_QA_DASHBOARD_V2.md",
    "docs/clinical_data/CLINICAL_QA_DASHBOARD_CHECKLIST_V2.csv",
    "docs/clinical_data/CLINICAL_QA_DASHBOARD_GO_NO_GO_V2.csv",
    "scripts/validate_clinical_qa_dashboard_v2.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REQUIRED_SNIPPETS = {
    "backend/clinical_qa_dashboard.py": [
        'CLINICAL_QA_DASHBOARD_MODE = "clinical_qa_dashboard_v2"',
        '"writes_database": False',
        '"updates_diagnostic_report": False',
        '"updates_observation": False',
        '"updates_imaging_study": False',
        '"writes_ai_summary": False',
        '"writes_audit_log": False',
        '"persists_reasoning_trace": False',
        '"generates_final_diagnosis": False',
        '"creates_treatment_plan": False',
        '"writes_prescription": False',
        '"returns_drug_dose": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
        '"not_client_facing": True',
        "build_clinical_qa_dashboard",
        "qa_queue",
        "diagnostic_summary_audit_log_count",
    ],
    "backend/diagnostic_data_api.py": [
        "# --- Clinical QA Dashboard V2 endpoint: start ---",
        '@router.get("/clinical-qa-dashboard/v2/summary"',
        "build_clinical_qa_dashboard",
        "clinical_qa_dashboard_v2_summary",
        "Case.owner_id == owner_id",
        "DiagnosticReport.case_id.in_(case_ids)",
        "Observation.case_id.in_(case_ids)",
        "ImagingStudy.case_id.in_(case_ids)",
        "AuditLog.case_id.in_(case_ids)",
        "# --- Clinical QA Dashboard V2 endpoint: end ---",
    ],
    "docs/clinical_data/CLINICAL_QA_DASHBOARD_V2.md": [
        "Clinical QA Dashboard V2",
        "GET /api/diagnostic-data/clinical-qa-dashboard/v2/summary",
        "writes_database=false",
        "not_client_facing=true",
        "GO_TO_OPS_DASHBOARD_CLINICAL_CORE_V2",
    ],
}

FORBIDDEN_ENDPOINT_SNIPPETS = [
    "db.add(",
    "db.commit(",
    "db.delete(",
    "AuditLog(",
    "Case(",
    "DiagnosticReport(",
    "Observation(",
    "ImagingStudy(",
    "OpenAI(",
    "requests.post(",
    "httpx.post(",
    "pydicom",
    "pynetdicom",
    "dicomweb",
]


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    return path.read_text(encoding="utf-8")


def load_module():
    path = ROOT / "backend" / "clinical_qa_dashboard.py"
    spec = importlib.util.spec_from_file_location("clinical_qa_dashboard", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load clinical_qa_dashboard module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        read(rel)
    for rel, snippets in REQUIRED_SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))

    api_text = read("backend/diagnostic_data_api.py")
    if api_text.count("/clinical-qa-dashboard/v2/summary") != 1:
        fail("expected exactly one Clinical QA Dashboard V2 endpoint")
    block = api_text.split("# --- Clinical QA Dashboard V2 endpoint: start ---", 1)[1].split("# --- Clinical QA Dashboard V2 endpoint: end ---", 1)[0]
    for snippet in FORBIDDEN_ENDPOINT_SNIPPETS:
        if snippet in block:
            fail("forbidden snippet in Clinical QA Dashboard V2 endpoint: %s" % snippet)


def assert_module_behavior() -> None:
    module = load_module()
    payload = {
        "cases": [{"case_id": 1}],
        "diagnostic_reports": [
            {"report_id": 10, "case_id": 1, "status": "reviewed", "ai_summary_status": "persisted", "has_ai_summary": True},
            {"report_id": 11, "case_id": 1, "status": "draft", "ai_summary_status": "not_generated", "has_ai_summary": False},
        ],
        "observations": [
            {"observation_id": 20, "case_id": 1, "abnormal_flag": "high", "review_status": "pending_clinician_review"},
            {"observation_id": 21, "case_id": 1, "abnormal_flag": "normal", "review_status": "reviewed"},
        ],
        "imaging_studies": [
            {"imaging_study_id": 30, "case_id": 1, "abnormal_flag": "abnormal", "review_status": "draft"},
        ],
        "audit_logs": [
            {"log_id": "log_1", "case_id": 1, "event_type": "diagnostic_summary_review", "source": "diagnostic_summary_audit_log_v1"},
        ],
    }
    result = module.build_clinical_qa_dashboard(payload, case_context={"case_id": 1})
    if result.get("mode") != "clinical_qa_dashboard_v2":
        fail("mode mismatch")
    for key in (
        "writes_database",
        "updates_diagnostic_report",
        "updates_observation",
        "updates_imaging_study",
        "writes_ai_summary",
        "writes_audit_log",
        "persists_reasoning_trace",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
        "returns_drug_dose",
    ):
        if result.get(key) is not False:
            fail("expected %s false" % key)
    if result.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if result.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    if result.get("not_client_facing") is not True:
        fail("not_client_facing must be true")
    if result.get("quality_gate", {}).get("status") != "PASS":
        fail("quality_gate.status must PASS")
    metrics = result.get("metrics") or {}
    if metrics.get("diagnostic_reports_total") != 2:
        fail("diagnostic report metric mismatch")
    if metrics.get("observation_abnormal_flag_review_gap_count") != 1:
        fail("observation review gap metric mismatch")
    if metrics.get("imagingstudy_review_gap_count") != 1:
        fail("imaging review gap metric mismatch")
    if not isinstance(result.get("qa_queue"), list) or not result["qa_queue"]:
        fail("qa_queue should contain review gap items")


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Clinical QA Dashboard V2 static checks" not in ci:
        fail("ci_static_checks missing Clinical QA Dashboard V2 block")
    if "python3 scripts/validate_clinical_qa_dashboard_v2.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "Clinical QA Dashboard V2 smoke" not in smoke:
        fail("smoke missing Clinical QA Dashboard V2 block")
    if "clinical_qa_dashboard_v2_summary" not in smoke:
        fail("smoke missing endpoint assertion")


def main() -> None:
    assert_files_and_snippets()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Clinical QA Dashboard V2")


if __name__ == "__main__":
    main()
