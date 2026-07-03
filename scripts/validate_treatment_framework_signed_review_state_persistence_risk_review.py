#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_GO_NO_GO_V1.csv",
    "scripts/validate_treatment_framework_signed_review_state_persistence_risk_review.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REFERENCE_FILES = [
    "backend/treatment_framework_signed_review_state.py",
    "backend/diagnostic_data_api.py",
    "frontend/src/pages/CaseDetail.jsx",
]

DANGEROUS_FLAGS = [
    "ENABLE_EMR_REAL_IMPORT",
    "ENABLE_EMR_IMPORT_CASE_UPDATE",
    "ENABLE_EMR_ATTACHMENT_DOWNLOAD",
    "ENABLE_PREVENTIVE_AUTO_DELIVERY",
    "ENABLE_PREVENTIVE_SMS_DELIVERY",
    "ENABLE_PREVENTIVE_WECHAT_DELIVERY",
    "ENABLE_PREVENTIVE_EMAIL_DELIVERY",
    "ENABLE_PRESCRIPTION_STRUCTURED_WRITE",
    "ENABLE_DEVICE_REAL_INGEST",
    "ENABLE_BILLING_REAL_WRITE",
]

FORBIDDEN_TARGET_SNIPPETS = [
    "Case.treatment =",
    "case.treatment =",
    ".treatment =",
    "signed_review_state_persistence_enabled=true",
    "review_state_persistence_enabled=true",
    "persistence_enabled=true",
    "writes_database=true",
    "client_release_allowed=true",
    "not_client_facing=false",
    "creates_prescription=true",
    "writes_prescription=true",
    "returns_drug_dose=true",
    "returns_drug_route=true",
    "returns_drug_frequency=true",
    "alembic upgrade",
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


def require_tokens(label: str, text: str, tokens: Iterable[str]) -> None:
    missing = [token for token in tokens if token not in text]
    require(not missing, "{0} missing tokens: {1}".format(label, ", ".join(missing)))


def optional_block(ci_text: str) -> str:
    match = re.search(r"OPTIONAL_CORE_VALIDATORS=\(([\s\S]*?)\)\n", ci_text)
    require(match is not None, "OPTIONAL_CORE_VALIDATORS block missing")
    return match.group(1)


def assert_no_dangerous_flags(text: str) -> None:
    for flag in DANGEROUS_FLAGS:
        for pattern in [
            "{0}=true".format(flag),
            "{0}: true".format(flag),
            '"{0}": true'.format(flag),
        ]:
            require(pattern not in text, "dangerous feature flag enablement found: {0}".format(pattern))


def assert_no_forbidden_snippets(text: str) -> None:
    for snippet in FORBIDDEN_TARGET_SNIPPETS:
        require(snippet not in text, "forbidden signed review state persistence risk snippet found: {0}".format(snippet))


def main() -> int:
    print("Validating Treatment Framework Signed Review State Persistence Risk Review V1")

    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))
    for rel in REFERENCE_FILES:
        require((ROOT / rel).is_file(), "missing reference file from previous stages: {0}".format(rel))

    py_compile.compile(str(ROOT / "scripts/validate_treatment_framework_signed_review_state_persistence_risk_review.py"), doraise=True)

    doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_V1.md")
    checklist = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_CHECKLIST_V1.csv")
    go_no_go = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_GO_NO_GO_V1.csv")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    signed_backend = read("backend/treatment_framework_signed_review_state.py")
    endpoint = read("backend/diagnostic_data_api.py")
    case_detail = read("frontend/src/pages/CaseDetail.jsx")

    require_tokens("doc", doc, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_V1",
        "persistence_enabled=false",
        "signed_review_state_persistence_enabled=false",
        "review_state_persistence_enabled=false",
        "signed_review_state_persistence_design_required=true",
        "signed_review_state_persistence_dry_run_required_before_write=true",
        "migration_readiness_required=true",
        "no_business_logic_change=true",
        "no_backend_endpoint_change=true",
        "no_frontend_ui_change=true",
        "no_migration=true",
        "writes_database=false",
        "no_case_treatment_write=true",
        "no_case_treatment_persistence=true",
        "no_prescription_write=true",
        "no_dose_route_frequency=true",
        "not_client_facing=true",
        "NO_GO_TO_SIGNED_REVIEW_STATE_PERSISTENCE",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1",
    ])
    require_tokens("checklist", checklist, [
        "signed_review_state_persistence_enabled_false",
        "review_state_persistence_enabled_false",
        "no_case_treatment_write",
        "no_case_treatment_persistence",
        "no_prescription_write",
        "no_dose_route_frequency",
        "persistence_design_required",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1",
    ])
    require_tokens("go_no_go", go_no_go, [
        "signed_review_state_persistence",
        "NO_GO_TO_SIGNED_REVIEW_STATE_PERSISTENCE",
        "case_treatment_persistence",
        "prescription_write",
        "dose_route_frequency",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1",
    ])

    require_tokens("ci", ci, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_V1",
        "validate_treatment_framework_signed_review_state_persistence_risk_review.py",
        "CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_UI_V1",
        "validate_case_detail_treatment_framework_signed_review_state_ui.py",
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1",
        "validate_treatment_framework_signed_review_state_dry_run.py",
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1",
        "validate_treatment_framework_signed_review_state_design.py",
        "TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1",
        "validate_treatment_framework_persistence_risk_review.py",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "signed review state persistence risk review markers",
        "PASS: ci_static_checks",
    ])
    optional = optional_block(ci)
    for stage_scoped in [
        "validate_case_detail_treatment_framework_signed_review_state_ui.py",
        "validate_treatment_framework_signed_review_state_dry_run.py",
        "validate_treatment_framework_signed_review_state_design.py",
        "validate_treatment_framework_persistence_risk_review.py",
        "validate_treatment_framework_audit_log.py",
        "validate_case_detail_treatment_framework_preview_ui.py",
    ]:
        require(stage_scoped not in optional, "stage-scoped validator must not be re-run in this risk-review CI: {0}".format(stage_scoped))
    require("git add ." not in ci, "ci contains legacy-forbidden exact git add marker")
    require('"${OPTIONAL_CORE_VALIDATORS[@]:-}"' in ci, "ci optional validator loop must remain Bash 3.2-safe")

    require_tokens("smoke", smoke, [
        "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
        "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"",
        "LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1",
        "LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1",
        "check_case_detail_treatment_framework_signed_review_state_ui_v1",
        "case_detail_treatment_framework_signed_review_state_ui=PASS",
        "check_treatment_framework_signed_review_state_persistence_risk_review_v1",
        "treatment_framework_signed_review_state_persistence_risk_review=PASS",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_V1",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1",
    ])
    require(
        re.search(
            r"\ncheck_case_detail_treatment_framework_signed_review_state_ui_v1\s*\ncheck_treatment_framework_signed_review_state_persistence_risk_review_v1\s*\n",
            smoke,
        ) is not None,
        "smoke must call signed review state persistence risk review after signed review state UI static check",
    )

    require("TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_MODE" in signed_backend, "signed review state backend mode missing")
    require("signed_review_state_preview_only" in signed_backend, "signed review state preview-only safety missing")
    require("persists_signed_review_state" in signed_backend, "signed review state persistence safety missing")
    require("/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/build" in endpoint, "signed review state dry-run endpoint missing")
    require("Case Detail Treatment Framework Signed Review State UI V1" in case_detail, "signed review state UI marker missing")

    combined_targets = "\n".join([doc, checklist, go_no_go, ci, smoke])
    assert_no_dangerous_flags(combined_targets)
    assert_no_forbidden_snippets(combined_targets)

    smoke_lines = len(smoke.splitlines())
    require(smoke_lines >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")

    print("PASS: Treatment Framework Signed Review State Persistence Risk Review V1")
    print("persistence_enabled=false")
    print("signed_review_state_persistence_enabled=false")
    print("review_state_persistence_enabled=false")
    print("signed_review_state_persistence_design_required=true")
    print("signed_review_state_persistence_dry_run_required_before_write=true")
    print("migration_readiness_required=true")
    print("no_business_logic_change=true")
    print("read_only=true")
    print("writes_database=false")
    print("no_case_treatment_write=true")
    print("no_case_treatment_persistence=true")
    print("no_prescription_write=true")
    print("no_dose_route_frequency=true")
    print("not_client_facing=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
