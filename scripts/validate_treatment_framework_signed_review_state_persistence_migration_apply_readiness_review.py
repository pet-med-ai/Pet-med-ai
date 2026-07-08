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
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_GO_NO_GO_V1.csv",
    "scripts/validate_treatment_framework_signed_review_state_persistence_migration_apply_readiness_review.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REFERENCE_FILES = [
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt",
]

FORBIDDEN_TARGET_EXACT = {".env", "frontend/.env.development", "frontend/package-lock.json", "app.db"}
FORBIDDEN_TARGET_PREFIXES = ("backend/app/", "backend/ai_engine/", "frontend/src/components/", "backend/migrations/versions/")
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
    "op.add_column(",
    "migration_enabled=true",
    "schema_change_enabled=true",
    "writes_database=true",
    "signed_review_state_persistence_enabled=true",
    "review_state_persistence_enabled=true",
    "Case.treatment =",
    "case.treatment =",
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
        require(snippet not in text, "forbidden apply-readiness snippet found: {0}".format(snippet))


def assert_target_scope() -> None:
    for target in REQUIRED_FILES:
        require(target not in FORBIDDEN_TARGET_EXACT, "forbidden target exact path: {0}".format(target))
        require(not target.endswith(".db"), "database target forbidden: {0}".format(target))
        for prefix in FORBIDDEN_TARGET_PREFIXES:
            require(not target.startswith(prefix), "forbidden target prefix: {0}".format(target))


def assert_no_active_0010_migration() -> None:
    versions = ROOT / "backend" / "migrations" / "versions"
    if not versions.is_dir():
        return
    active = sorted(path.name for path in versions.glob("0010*.py"))
    require(not active, "active 0010 migration file is forbidden in apply readiness review: {0}".format(", ".join(active)))


def main() -> int:
    print("Validating Treatment Framework Signed Review State Persistence Migration Apply Readiness Review V1")
    assert_target_scope()
    assert_no_active_0010_migration()

    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))
    for rel in REFERENCE_FILES:
        require((ROOT / rel).is_file(), "missing reference file: {0}".format(rel))

    py_compile.compile(str(ROOT / "scripts/validate_treatment_framework_signed_review_state_persistence_migration_apply_readiness_review.py"), doraise=True)

    doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_V1.md")
    checklist = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_CHECKLIST_V1.csv")
    go_no_go = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_GO_NO_GO_V1.csv")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    final_doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1.md")
    implementation_doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1.md")
    inactive_draft = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt")

    require_tokens("doc", doc, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_V1",
        "apply_readiness_review_only=true",
        "active_migration_file_created=false",
        "active_migration_file_allowed=false",
        "production_migration_apply_allowed=false",
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
        "staging_rehearsal_required=true",
        "rollback_dry_run_required=true",
        "backup_restore_evidence_required=true",
        "authenticated_smoke_required_before_write=true",
        "append_only_audit_linkage_required=true",
        "NO_GO_TO_PRODUCTION_MIGRATION_APPLY",
        "NO_GO_TO_ACTIVE_MIGRATION_FILE_ON_MAIN",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1",
    ])
    require_tokens("checklist", checklist, [
        "apply_readiness_review_only",
        "active_migration_file_created_false",
        "production_migration_apply_allowed_false",
        "staging_rehearsal_required",
        "rollback_dry_run_required",
        "backup_restore_evidence_required",
        "authenticated_smoke_required_before_write",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1",
    ])
    require_tokens("go_no_go", go_no_go, [
        "NO_GO_TO_PRODUCTION_MIGRATION_APPLY",
        "NO_GO_TO_ACTIVE_MIGRATION_FILE_ON_MAIN",
        "NO_GO_TO_DATABASE_WRITE",
        "NO_GO_TO_CASE_TREATMENT_PERSISTENCE",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1",
    ])
    require_tokens("ci", ci, [
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_V1",
        "validate_treatment_framework_signed_review_state_persistence_migration_apply_readiness_review.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_final_go_no_go.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_implementation.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_dry_run.py",
        "validate_treatment_framework_persistence_risk_review.py",
        "validate_treatment_framework_signed_review_state_design.py",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "signed review state persistence migration apply readiness review markers",
        "PASS: ci_static_checks",
    ])
    optional = optional_block(ci)
    for stage_scoped in [
        "validate_treatment_framework_signed_review_state_persistence_migration_final_go_no_go.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_implementation.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_dry_run.py",
        "validate_case_detail_treatment_framework_signed_review_state_persistence_migration_ui.py",
        "validate_ci_smoke_cumulative_guard_restore.py",
    ]:
        require(stage_scoped not in optional, "stage-scoped validator must not be re-run in this apply readiness CI: {0}".format(stage_scoped))
    require("git add ." not in ci, "ci contains legacy-forbidden exact git add marker")
    require('"${OPTIONAL_CORE_VALIDATORS[@]:-}"' in ci, "ci optional validator loop must remain Bash 3.2-safe")

    require_tokens("smoke", smoke, [
        "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
        "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"",
        "LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1",
        "LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1",
        "check_treatment_framework_signed_review_state_persistence_migration_final_go_no_go_v1",
        "check_treatment_framework_signed_review_state_persistence_migration_apply_readiness_review_v1",
        "treatment_framework_signed_review_state_persistence_migration_apply_readiness_review=PASS",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1",
    ])
    require(
        re.search(
            r"\ncheck_treatment_framework_signed_review_state_persistence_migration_final_go_no_go_v1\s*\ncheck_treatment_framework_signed_review_state_persistence_migration_apply_readiness_review_v1\s*\n",
            smoke,
        ) is not None,
        "smoke must call apply readiness review after final go/no-go",
    )

    require("GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1" in final_doc, "previous final go/no-go decision missing")
    require("inactive_migration_draft_created=true" in implementation_doc, "implementation stage must remain inactive draft")
    require("revision = \"0010_tfsrs\"" in inactive_draft, "inactive 0010 draft revision missing")
    require("down_revision = \"0009_diag_data\"" in inactive_draft, "inactive 0010 draft down_revision missing")

    combined_targets = "\n".join([doc, checklist, go_no_go, ci, smoke])
    assert_no_dangerous_flags(combined_targets)
    assert_no_forbidden_snippets(combined_targets)

    smoke_lines = len(smoke.splitlines())
    require(smoke_lines >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")

    print("PASS: Treatment Framework Signed Review State Persistence Migration Apply Readiness Review V1")
    print("apply_readiness_review_only=true")
    print("active_migration_file_created=false")
    print("active_migration_file_allowed=false")
    print("production_migration_apply_allowed=false")
    print("migration_apply_allowed=false")
    print("migration_enabled=false")
    print("schema_change_enabled=false")
    print("read_only=true")
    print("writes_database=false")
    print("no_case_treatment_write=true")
    print("no_case_treatment_persistence=true")
    print("no_prescription_write=true")
    print("no_dose_route_frequency=true")
    print("not_client_facing=true")
    print("staging_rehearsal_required=true")
    print("rollback_dry_run_required=true")
    print("backup_restore_evidence_required=true")
    print("authenticated_smoke_required_before_write=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
