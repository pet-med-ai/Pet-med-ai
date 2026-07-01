#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "frontend/src/pages/CaseDetail.jsx",
    "docs/clinical_data/CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_V1.md",
    "docs/clinical_data/CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_CHECKLIST_V1.csv",
    "docs/clinical_data/CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_GO_NO_GO_V1.csv",
    "scripts/validate_case_detail_treatment_framework_preview_ui.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

FORBIDDEN_CASE_DETAIL_SNIPPETS = [
    "/api/cases/${data.id}/treatment",
    "/api/prescriptions",
    "writes_case_treatment: true",
    "creates_prescription: true",
    "writes_prescription: true",
    "returns_drug_dose: true",
    "returns_drug_route: true",
    "returns_drug_frequency: true",
    "confirmation_source: \"ai\"",
    "ai_generated: true",
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


def require_tokens(label: str, text: str, tokens) -> None:
    missing = [token for token in tokens if token not in text]
    require(not missing, "{0} missing tokens: {1}".format(label, ", ".join(missing)))


def main() -> int:
    print("Validating Case Detail Treatment Framework Preview UI V1")

    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))

    case_detail = read("frontend/src/pages/CaseDetail.jsx")
    doc = read("docs/clinical_data/CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_V1.md")
    checklist = read("docs/clinical_data/CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_CHECKLIST_V1.csv")
    go_no_go = read("docs/clinical_data/CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_GO_NO_GO_V1.csv")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")

    require_tokens("CaseDetail UI", case_detail, [
        "Case Detail Treatment Framework Preview UI V1 state: start",
        "Case Detail Treatment Framework Preview UI V1 actions: start",
        "Case Detail Treatment Framework Preview UI V1 section: start",
        "Case Detail Treatment Framework Preview UI V1 components: start",
        "Case Detail Treatment Framework Preview UI V1 helpers: start",
        "/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/build",
        "confirmed_diagnosis_label: diagnosisLabel",
        "confirmed_by: confirmedBy",
        "confirmation_source: \"clinician\"",
        "ai_generated: false",
        "buildTreatmentFrameworkDiagnosticContext",
        "TreatmentFrameworkPreviewPanel",
        "writes_database=false",
        "writes_case_treatment=false",
        "creates_prescription=false",
        "writes_prescription=false",
        "returns_drug_dose=false",
        "returns_drug_route=false",
        "returns_drug_frequency=false",
        "not_client_facing=true",
        "requires_human_review=true",
        "clinician_signoff_required=true",
    ])

    require_tokens("docs", doc, [
        "CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_V1",
        "confirmation_source=clinician",
        "ai_generated=false",
        "writes_database=false",
        "writes_case_treatment=false",
        "creates_prescription=false",
        "writes_prescription=false",
        "returns_drug_dose=false",
        "returns_drug_route=false",
        "returns_drug_frequency=false",
        "GO_TO_TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1",
    ])
    require_tokens("checklist", checklist, [
        "requires_clinician_confirmed_diagnosis",
        "ai_does_not_confirm_diagnosis",
        "dry_run_endpoint_only",
        "dose_route_frequency_blocked",
        "GO_TO_TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1",
    ])
    require_tokens("go_no_go", go_no_go, [
        "online_smoke",
        "frontend",
        "endpoint_smoke",
        "ui_static_smoke",
        "no_case_treatment_write",
        "no_dose_route_frequency",
    ])

    require_tokens("ci", ci, [
        "CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_V1",
        "frontend/src/pages/CaseDetail.jsx",
        "validate_case_detail_treatment_framework_preview_ui.py",
        "validate_confirmed_diagnosis_treatment_framework_draft.py",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "case detail treatment framework preview UI markers",
        "PASS: ci_static_checks",
    ])
    require("validate_ci_smoke_cumulative_guard_restore.py" in ci, "ci restore guard reference missing")
    require("git add ." not in ci, "ci contains legacy-forbidden exact git add marker")

    require_tokens("smoke", smoke, [
        "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
        "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"",
        "LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1",
        "LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1",
        "check_confirmed_diagnosis_treatment_framework_draft_v1",
        "check_case_detail_treatment_framework_preview_ui_v1",
        "case_detail_treatment_framework_preview_ui=PASS",
        "GO_TO_TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1",
    ])
    require(
        re.search(r"\ncheck_confirmed_diagnosis_treatment_framework_draft_v1\s*\ncheck_case_detail_treatment_framework_preview_ui_v1\s*\n", smoke) is not None,
        "smoke must call UI static check after draft endpoint smoke",
    )

    for snippet in FORBIDDEN_CASE_DETAIL_SNIPPETS:
        require(snippet not in case_detail, "forbidden CaseDetail snippet found: {0}".format(snippet))

    smoke_lines = len(smoke.splitlines())
    require(smoke_lines >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")

    print("PASS: Case Detail Treatment Framework Preview UI V1")
    print("case_detail_treatment_framework_preview_ui=PASS_REQUIRED")
    print("requires_clinician_confirmed_diagnosis=true")
    print("ai_does_not_confirm_diagnosis=true")
    print("read_only=true")
    print("writes_database=false")
    print("writes_case_treatment=false")
    print("creates_prescription=false")
    print("writes_prescription=false")
    print("returns_drug_dose=false")
    print("returns_drug_route=false")
    print("returns_drug_frequency=false")
    print("not_client_facing=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision=GO_TO_TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
