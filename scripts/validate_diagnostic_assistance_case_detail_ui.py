#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

CASE_DETAIL = ROOT / "frontend" / "src" / "pages" / "CaseDetail.jsx"
DOC = ROOT / "docs" / "clinical_data" / "DIAGNOSTIC_ASSISTANCE_CASE_DETAIL_UI_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "DIAGNOSTIC_ASSISTANCE_CASE_DETAIL_UI_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "DIAGNOSTIC_ASSISTANCE_CASE_DETAIL_UI_GO_NO_GO_V1.csv"
CI = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"


def fail(message: str) -> None:
    print("Diagnostic Assistance Case Detail UI V1 validator FAIL: %s" % message)
    sys.exit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail("missing required file: %s" % path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail("missing %s: %s" % (label, needle))


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        fail("forbidden %s: %s" % (label, needle))


def main() -> int:
    case_detail = read(CASE_DETAIL)
    doc = read(DOC)
    checklist = read(CHECKLIST)
    go_no_go = read(GO_NO_GO)
    ci = read(CI)
    smoke = read(SMOKE)

    require(case_detail, "DiagnosticAssistancePanel", "case detail UI panel")
    require(case_detail, "buildDiagnosticAssistancePreview", "case detail preview action")
    require(case_detail, "/api/diagnostic-data/dry-run/problem-list/build", "problem list dry-run endpoint")
    require(case_detail, "/api/diagnostic-data/dry-run/differential-diagnosis/candidates/build", "differential candidates dry-run endpoint")
    require(case_detail, "/api/diagnostic-data/dry-run/diagnostic-reasoning/evidence-trace/build", "evidence trace dry-run endpoint")
    require(case_detail, "problem_list_preview", "problem list preview wire")
    require(case_detail, "differential_diagnosis_candidates_preview", "differential candidates preview wire")
    require(case_detail, "diagnostic_reasoning_evidence_trace_preview", "evidence trace preview wire")

    for flag in [
        "dry_run=true",
        "writes_database=false",
        "writes_audit_log=false",
        "persists_reasoning_trace=false",
        "not_a_diagnosis=true",
        "not_a_treatment_plan=true",
        "not_a_prescription=true",
        "not_client_facing=true",
        "requires_human_review=true",
    ]:
        require(case_detail, flag, "visible safety flag")

    for phrase in [
        "finalDiagnosis",
        "confirmedDiagnosis",
        "definitiveDiagnosis",
        "treatmentPlan",
        "prescription_id",
        "dose_mg_per_kg",
        "dose_value",
        "route_instruction",
        "frequency_instruction",
        "client_facing_summary",
        "releaseToClient",
        "writePrescription",
        "persistReasoningTrace",
    ]:
        forbid(case_detail, phrase, "UI persistence or clinical output phrase")

    for endpoint in [
        "/api/diagnostic-data/dry-run/problem-list/build",
        "/api/diagnostic-data/dry-run/differential-diagnosis/candidates/build",
        "/api/diagnostic-data/dry-run/diagnostic-reasoning/evidence-trace/build",
    ]:
        count = case_detail.count(endpoint)
        if count != 1:
            fail("endpoint %s should appear exactly once, got %s" % (endpoint, count))

    for required in [
        "not a diagnosis",
        "not a treatment plan",
        "not a prescription",
        "not client-facing",
        "writes_database=false",
    ]:
        require(doc.lower(), required.lower(), "doc boundary")

    require(checklist, "No database writes", "checklist no DB write")
    require(checklist, "No final diagnosis", "checklist no final diagnosis")
    require(checklist, "No drug dose route frequency", "checklist no drug dose route frequency")
    require(go_no_go, "GO_TO_CLINICIAN_REVIEW_PERSISTENCE_V1", "go/no-go next decision")

    require(ci, "validate_diagnostic_assistance_case_detail_ui.py", "CI validator hook")
    require(smoke, "validate_diagnostic_assistance_case_detail_ui.py", "smoke validator hook")

    print("Diagnostic Assistance Case Detail UI V1 validator PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
