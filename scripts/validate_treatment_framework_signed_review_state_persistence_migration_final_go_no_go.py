#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_DECISION_RECORD_V1.csv",
    "scripts/validate_treatment_framework_signed_review_state_persistence_migration_final_go_no_go.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REFERENCE_FILES = [
    "backend/treatment_framework_signed_review_state_persistence_migration_dry_run.py",
    "backend/diagnostic_data_api.py",
    "frontend/src/pages/CaseDetail.jsx",
    "docs/clinical_data/CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_UI_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_V1.md",
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

FORBIDDEN_SNIPPETS = [
    "alembic upgrade",
    "op.create_table(",
    "Case.treatment =",
    "case.treatment =",
    ".treatment =",
    "migration_enabled=true",
    "migration_file_created=true",
    "schema_change_enabled=true",
    "persistence_enabled=true",
    "signed_review_state_persistence_enabled=true",
    "review_state_persistence_enabled=true",
    "writes_database=true",
    "creates_prescription=true",
    "writes_prescription=true",
    "returns_drug_dose=true",
    "returns_drug_route=true",
    "returns_drug_frequency=true",
    "not_client_facing=false",
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
        for pattern in ["{0}=true".format(flag), "{0}: true".format(flag), '"{0}": true'.format(flag)]:
            require(pattern not in text, "dangerous feature flag enablement found: {0}".format(pattern))


def assert_no_forbidden_snippets(text: str) -> None:
    for snippet in FORBIDDEN_SNIPPETS:
        require(snippet not in text, "forbidden final go/no-go snippet found: {0}".format(snippet))


def read_first_csv_row(rel_path: str) -> dict:
    path = ROOT / rel_path
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(bool(rows), "CSV has no rows: {0}".format(rel_path))
    return rows[0]


def main() -> int:
    print("Validating Treatment Framework Signed Review State Persistence Migration Final Go/No-Go V1")

    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))
    for rel in REFERENCE_FILES:
        require((ROOT / rel).is_file(), "missing reference file: {0}".format(rel))

    py_compile.compile(str(ROOT / "scripts/validate_treatment_framework_signed_review_state_persistence_migration_final_go_no_go.py"), doraise=True)

    doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1.md")
    checklist = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_CHECKLIST_V1.csv")
    decision = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_DECISION_RECORD_V1.csv")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    migration_backend = read("backend/treatment_framework_signed_review_state_persistence_migration_dry_run.py")
    endpoint = read("backend/diagnostic_data_api.py")
    ui = read("frontend/src/pages/CaseDetail.jsx")
    previous_ui_doc = read("docs/clinical_data/CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_UI_V1.md")

    require_tokens("doc", doc, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1",
        "final_go_no_go_only=true",
        "migration_implementation_allowed=true",
        "migration_apply_allowed=false",
        "migration_enabled=false",
        "migration_file_created=false",
        "schema_change_enabled=false",
        "persistence_enabled=false",
        "signed_review_state_persistence_enabled=false",
        "review_state_persistence_enabled=false",
        "writes_database=false",
        "no_case_treatment_write=true",
        "no_case_treatment_persistence=true",
        "no_prescription_write=true",
        "no_dose_route_frequency=true",
        "not_client_facing=true",
        "rollback_plan_required=true",
        "backup_restore_evidence_required=true",
        "authenticated_smoke_required_before_write=true",
        "append_only_audit_linkage_required=true",
        "NO_GO_TO_DATABASE_WRITE",
        "NO_GO_TO_CASE_TREATMENT_PERSISTENCE",
        "NO_GO_TO_PRESCRIPTION_WRITE",
        "NO_GO_TO_DOSE_ROUTE_FREQUENCY_OUTPUT",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1",
    ])
    require_tokens("checklist", checklist, [
        "final_go_no_go_only",
        "migration_implementation_allowed",
        "migration_apply_allowed",
        "database_write_allowed",
        "no_case_treatment_write",
        "no_prescription_write",
        "no_dose_route_frequency",
        "authenticated_smoke_required_before_write",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1",
    ])
    require_tokens("decision", decision, [
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1",
        "migration_apply_allowed",
        "database_write_allowed",
        "schema_change_enabled",
        "signed_review_state_persistence_enabled",
        "0009_diag_data",
    ])
    row = read_first_csv_row("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_DECISION_RECORD_V1.csv")
    expected = {
        "decision": "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1",
        "go_to_migration_implementation": "true",
        "migration_apply_allowed": "false",
        "database_write_allowed": "false",
        "schema_change_enabled": "false",
        "persistence_enabled": "false",
        "signed_review_state_persistence_enabled": "false",
        "review_state_persistence_enabled": "false",
        "no_case_treatment_write": "true",
        "no_prescription_write": "true",
        "no_dose_route_frequency": "true",
        "not_client_facing": "true",
        "production_database_revision": "0009_diag_data",
        "production_alembic_head": "0009_diag_data",
        "production_schema_ok": "true",
        "dangerous_flags_disabled": "true",
    }
    for key, value in expected.items():
        require(str(row.get(key) or "").strip() == value, "decision record {0} must be {1}".format(key, value))

    require_tokens("ci", ci, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1",
        "validate_treatment_framework_signed_review_state_persistence_migration_final_go_no_go.py",
        "CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_UI_V1",
        "validate_case_detail_treatment_framework_signed_review_state_persistence_migration_ui.py",
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_V1",
        "validate_treatment_framework_signed_review_state_persistence_migration_dry_run.py",
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DESIGN_V1",
        "validate_treatment_framework_signed_review_state_persistence_migration_design.py",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "signed review state persistence migration final go/no-go markers",
        "PASS: ci_static_checks",
    ])
    optional = optional_block(ci)
    for stage_scoped in [
        "validate_case_detail_treatment_framework_signed_review_state_persistence_migration_ui.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_dry_run.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_design.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_readiness_review.py",
        "validate_case_detail_treatment_framework_signed_review_state_persistence_ui.py",
        "validate_ci_smoke_cumulative_guard_restore.py",
    ]:
        require(stage_scoped not in optional, "stage-scoped validator must not be re-run in final go/no-go CI: {0}".format(stage_scoped))
    require("git add ." not in ci, "ci contains legacy-forbidden exact git add marker")
    require('"${OPTIONAL_CORE_VALIDATORS[@]:-}"' in ci, "ci optional validator loop must remain Bash 3.2-safe")

    require_tokens("smoke", smoke, [
        "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
        "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"",
        "LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1",
        "LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1",
        "check_case_detail_treatment_framework_signed_review_state_persistence_migration_ui_v1",
        "check_treatment_framework_signed_review_state_persistence_migration_final_go_no_go_v1",
        "treatment_framework_signed_review_state_persistence_migration_final_go_no_go=PASS",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1",
    ])
    require(
        re.search(
            r"\ncheck_case_detail_treatment_framework_signed_review_state_persistence_migration_ui_v1\s*\ncheck_treatment_framework_signed_review_state_persistence_migration_final_go_no_go_v1\s*\n",
            smoke,
        ) is not None,
        "smoke must call final go/no-go after migration UI static check",
    )
    require("TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_MODE" in migration_backend, "migration dry-run backend mode missing")
    require('"writes_database": False' in migration_backend, "migration dry-run backend must keep writes_database false")
    require('"migration_enabled": False' in migration_backend, "migration dry-run backend must keep migration_enabled false")
    require("/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/migration/dry-run" in endpoint, "migration dry-run endpoint missing")
    require("TreatmentFrameworkSignedReviewStateMigrationPanel" in ui, "migration UI panel missing")
    require("GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1" in previous_ui_doc, "previous migration UI decision missing")

    combined_targets = "\n".join([doc, checklist, decision, ci, smoke])
    assert_no_dangerous_flags(combined_targets)
    assert_no_forbidden_snippets(combined_targets)
    smoke_lines = len(smoke.splitlines())
    require(smoke_lines >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")

    print("PASS: Treatment Framework Signed Review State Persistence Migration Final Go/No-Go V1")
    print("final_go_no_go_only=true")
    print("migration_implementation_allowed=true")
    print("migration_apply_allowed=false")
    print("migration_enabled=false")
    print("migration_file_created=false")
    print("schema_change_enabled=false")
    print("persistence_enabled=false")
    print("signed_review_state_persistence_enabled=false")
    print("review_state_persistence_enabled=false")
    print("read_only=true")
    print("writes_database=false")
    print("no_case_treatment_write=true")
    print("no_case_treatment_persistence=true")
    print("no_prescription_write=true")
    print("no_dose_route_frequency=true")
    print("not_client_facing=true")
    print("rollback_plan_required=true")
    print("backup_restore_evidence_required=true")
    print("authenticated_smoke_required_before_write=true")
    print("append_only_audit_linkage_required=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
