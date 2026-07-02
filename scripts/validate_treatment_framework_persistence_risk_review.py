#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import re
import sys
from pathlib import Path
from typing import Iterable, List


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/clinical_data/TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_GO_NO_GO_V1.csv",
    "scripts/validate_treatment_framework_persistence_risk_review.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REFERENCE_FILES = [
    "backend/treatment_framework_audit_log.py",
    "backend/audit_log_api.py",
    "backend/treatment_framework_clinician_review_workflow.py",
    "backend/confirmed_diagnosis_treatment_framework.py",
]

FORBIDDEN_TARGET_EXACT = {
    "app.db",
    ".env",
    "frontend/.env.development",
    "frontend/package-lock.json",
}

FORBIDDEN_TARGET_PREFIXES = (
    "backend/app/",
    "backend/ai_engine/",
    "frontend/src/components/",
)

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

FORBIDDEN_NEW_TARGET_SNIPPETS = [
    "Case.treatment =",
    "case.treatment =",
    ".treatment =",
    "creates_prescription\": True",
    "writes_prescription\": True",
    "returns_drug_dose\": True",
    "returns_drug_route\": True",
    "returns_drug_frequency\": True",
    "persistence_enabled=true",
    "review_state_persistence_enabled=true",
    "client_release_allowed=true",
    "not_client_facing=false",
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


def assert_target_scope() -> None:
    for target in REQUIRED_FILES:
        require(target not in FORBIDDEN_TARGET_EXACT, "forbidden target exact path: {0}".format(target))
        for prefix in FORBIDDEN_TARGET_PREFIXES:
            require(not target.startswith(prefix), "forbidden target prefix: {0}".format(target))


def assert_no_dangerous_flags(text: str) -> None:
    for flag in DANGEROUS_FLAGS:
        patterns = [
            "{0}=true".format(flag),
            "{0}: true".format(flag),
            '"{0}": true'.format(flag),
        ]
        for pattern in patterns:
            require(pattern not in text, "dangerous feature flag enablement found: {0}".format(pattern))


def assert_no_forbidden_new_target_snippets(text: str) -> None:
    for snippet in FORBIDDEN_NEW_TARGET_SNIPPETS:
        require(snippet not in text, "forbidden persistence-risk target snippet found: {0}".format(snippet))


def main() -> int:
    print("Validating Treatment Framework Persistence Risk Review V1")

    assert_target_scope()

    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))
    for rel in REFERENCE_FILES:
        require((ROOT / rel).is_file(), "missing reference file from previous stages: {0}".format(rel))

    py_compile.compile(str(ROOT / "scripts/validate_treatment_framework_persistence_risk_review.py"), doraise=True)

    doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1.md")
    checklist = read("docs/clinical_data/TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_CHECKLIST_V1.csv")
    go_no_go = read("docs/clinical_data/TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_GO_NO_GO_V1.csv")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    audit_backend = read("backend/treatment_framework_audit_log.py")
    audit_api = read("backend/audit_log_api.py")

    require_tokens("doc", doc, [
        "TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1",
        "persistence_enabled=false",
        "no_business_logic_change=true",
        "writes_database=false",
        "no_case_treatment_write=true",
        "no_case_treatment_persistence=true",
        "no_prescription_write=true",
        "no_dose_route_frequency=true",
        "not_client_facing=true",
        "append_only_audit_allowed_only=true",
        "signed_review_state_requires_future_design=true",
        "NO_GO_TO_CASE_TREATMENT_PERSISTENCE",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1",
    ])
    require_tokens("checklist", checklist, [
        "persistence_enabled_false",
        "no_case_treatment_write",
        "no_prescription_write",
        "no_dose_route_frequency",
        "append_only_audit_allowed_only",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1",
    ])
    require_tokens("go_no_go", go_no_go, [
        "case_treatment_persistence",
        "NO_GO_TO_CASE_TREATMENT_PERSISTENCE",
        "no_prescription_write=true",
        "no_dose_route_frequency=true",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1",
    ])

    require_tokens("ci", ci, [
        "TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1",
        "validate_treatment_framework_persistence_risk_review.py",
        "TREATMENT_FRAMEWORK_AUDIT_LOG_V1",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "persistence risk review markers",
        "PASS: ci_static_checks",
    ])
    optional = optional_block(ci)
    for stage_scoped in [
        "validate_treatment_framework_audit_log.py",
        "validate_treatment_framework_clinician_review_workflow.py",
        "validate_case_detail_treatment_framework_preview_ui.py",
        "validate_confirmed_diagnosis_treatment_framework_draft.py",
        "validate_ci_smoke_cumulative_guard_restore.py",
    ]:
        require(stage_scoped not in optional, "stage-scoped validator must not be re-run in this risk-review CI: {0}".format(stage_scoped))
    require("git add ." not in ci, "ci contains legacy-forbidden exact git add marker")

    require_tokens("smoke", smoke, [
        "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
        "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"",
        "LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1",
        "LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1",
        "check_confirmed_diagnosis_treatment_framework_draft_v1",
        "check_case_detail_treatment_framework_preview_ui_v1",
        "check_treatment_framework_clinician_review_workflow_v1",
        "check_treatment_framework_audit_log_v1",
        "treatment_framework_audit_log_smoke=PASS",
        "check_treatment_framework_persistence_risk_review_v1",
        "treatment_framework_persistence_risk_review=PASS",
        "GO_TO_TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1",
    ])
    require(
        re.search(
            r"\ncheck_treatment_framework_audit_log_v1\s*\ncheck_treatment_framework_persistence_risk_review_v1\s*\n",
            smoke,
        ) is not None,
        "smoke must call persistence risk review after audit log smoke",
    )

    require("TREATMENT_FRAMEWORK_AUDIT_LOG_MODE" in audit_backend, "previous audit log backend mode missing")
    require("append_only_audit_log" in audit_backend, "previous audit log append-only safety missing")
    require("/confirmed-diagnosis/treatment-framework/audit-log/append" in audit_api, "previous treatment framework audit log endpoint missing")

    combined_targets = "\n".join([doc, checklist, go_no_go, ci, smoke])
    assert_no_dangerous_flags(combined_targets)
    assert_no_forbidden_new_target_snippets(combined_targets)

    smoke_lines = len(smoke.splitlines())
    require(smoke_lines >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")

    print("PASS: Treatment Framework Persistence Risk Review V1")
    print("persistence_enabled=false")
    print("review_state_persistence_enabled=false")
    print("no_business_logic_change=true")
    print("read_only=true")
    print("writes_database=false")
    print("no_case_treatment_write=true")
    print("no_case_treatment_persistence=true")
    print("no_prescription_write=true")
    print("no_dose_route_frequency=true")
    print("not_client_facing=true")
    print("append_only_audit_allowed_only=true")
    print("signed_review_state_requires_future_design=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
