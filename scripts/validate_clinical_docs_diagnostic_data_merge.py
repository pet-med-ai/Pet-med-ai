#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/clinical_docs_diagnostic_data_merge.py",
    "backend/clinical_docs_api.py",
    "docs/clinical_data/CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_V1.md",
    "docs/clinical_data/CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_CHECKLIST_V1.csv",
    "docs/clinical_data/CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_GO_NO_GO_V1.csv",
    "scripts/validate_clinical_docs_diagnostic_data_merge.py",
]

SNIPPETS = {
    "backend/clinical_docs_diagnostic_data_merge.py": [
        "CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_MODE = \"clinical_docs_diagnostic_data_merge_v1\"",
        "build_clinical_docs_diagnostic_data_merge",
        "clinical_docs_diagnostic_data_merge_safety_flags",
        "\"writes_database\": False",
        "\"updates_diagnostic_report\": False",
        "\"updates_observation\": False",
        "\"updates_imaging_study\": False",
        "\"writes_ai_summary\": False",
        "\"writes_audit_log\": False",
        "\"generates_final_diagnosis\": False",
        "\"creates_treatment_plan\": False",
        "\"writes_prescription\": False",
        "\"returns_drug_dose\": False",
        "\"requires_human_review\": True",
        "\"clinician_signoff_required\": True",
    ],
    "backend/clinical_docs_api.py": [
        "include_diagnostic_data: bool = Field(default=False)",
        "build_clinical_docs_diagnostic_data_merge",
        "_clinical_docs_diagnostic_data_merge_for_case",
        "_apply_diagnostic_data_context_to_clinical_doc_context",
        "_append_diagnostic_data_section_to_document_xml",
        "diagnostic_data_merge",
        "X-PMAI-Diagnostic-Data-Merge",
        "DiagnosticReport",
        "Observation",
        "ImagingStudy",
    ],
    "docs/clinical_data/CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_V1.md": [
        "Clinical Docs Diagnostic Data Merge V1",
        "POST /api/clinical-docs/render-preview",
        "POST /api/clinical-docs/render",
        "include_diagnostic_data",
        "writes_database=false",
        "GO_TO_CLINICAL_QA_DASHBOARD_V2",
    ],
}

PROHIBITED_CLINICAL_DOCS_API = [
    "db.add(",
    "db.commit(",
    "db.delete(",
    "AuditLog(",
    "requests.get(",
    "requests.post(",
    "httpx.",
    "OpenAI(",
]


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing file: %s" % rel)
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    return path.read_text(encoding="utf-8")


def load_module():
    path = ROOT / "backend" / "clinical_docs_diagnostic_data_merge.py"
    spec = importlib.util.spec_from_file_location("clinical_docs_diagnostic_data_merge", str(path))
    if spec is None or spec.loader is None:
        fail("cannot load clinical_docs_diagnostic_data_merge module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        read(rel)
    for rel, snippets in SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))
    api_text = read("backend/clinical_docs_api.py")
    for snippet in PROHIBITED_CLINICAL_DOCS_API:
        if snippet in api_text:
            fail("clinical docs diagnostic data merge must remain read-only; found %s" % snippet)


def assert_module_behavior() -> None:
    module = load_module()
    reports = [
        {
            "id": 10,
            "report_type": "lab",
            "title": "CBC / Chemistry",
            "status": "reviewed",
            "ai_summary_status": "reviewed",
            "ai_summary": "Reviewed laboratory abnormalities require clinician correlation.",
            "reviewed_by": "Dr Test",
        }
    ]
    observations = [
        {
            "id": 20,
            "display_name": "ALT",
            "value_numeric": 185,
            "unit": "U/L",
            "abnormal_flag": "high",
            "review_status": "reviewed",
        }
    ]
    imaging = [
        {
            "id": 30,
            "modality": "XRAY",
            "body_part": "abdomen",
            "abnormal_flag": "abnormal",
            "review_status": "reviewed",
        }
    ]
    result = module.build_clinical_docs_diagnostic_data_merge(
        reports,
        observations,
        imaging,
        case_id=123,
        case_context={"case_id": 123},
    )
    if result.get("mode") != "clinical_docs_diagnostic_data_merge_v1":
        fail("mode mismatch")
    for key in (
        "writes_database",
        "updates_diagnostic_report",
        "updates_observation",
        "updates_imaging_study",
        "writes_ai_summary",
        "writes_audit_log",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
        "returns_drug_dose",
    ):
        if result.get(key) is not False:
            fail("safety flag must be false: %s" % key)
    if result.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    context = result.get("document_context") or {}
    if "diagnostic.reports.summary" not in context:
        fail("missing diagnostic report document context")
    if "__diagnostic_data_section" not in context:
        fail("missing diagnostic section text")
    if result.get("quality_gate", {}).get("status") != "PASS":
        fail("quality gate must PASS")


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Clinical Docs Diagnostic Data Merge V1 static checks" not in ci:
        fail("ci_static_checks missing stage block")
    if "python3 scripts/validate_clinical_docs_diagnostic_data_merge.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "Clinical Docs Diagnostic Data Merge V1 smoke" not in smoke:
        fail("smoke missing stage block")
    if "/api/clinical-docs/render-preview" not in smoke:
        fail("smoke missing render-preview endpoint")
    if "include_diagnostic_data" not in smoke:
        fail("smoke missing include_diagnostic_data payload")


def main() -> None:
    assert_files_and_snippets()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Clinical Docs Diagnostic Data Merge V1")


if __name__ == "__main__":
    main()
