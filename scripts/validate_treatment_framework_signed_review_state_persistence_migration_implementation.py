#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import re
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
STAGE = "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1"
NEXT_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_V1"

REQUIRED_FILES = [
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_GO_NO_GO_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt",
    "scripts/validate_treatment_framework_signed_review_state_persistence_migration_implementation.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REFERENCE_FILES = [
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_DECISION_RECORD_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DESIGN_V1.md",
    "backend/treatment_framework_signed_review_state_persistence_migration_dry_run.py",
    "backend/diagnostic_data_api.py",
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
        for pattern in ["{0}=true".format(flag), "{0}: true".format(flag), "\"{0}\": true".format(flag)]:
            require(pattern not in text, "dangerous feature flag enablement found: {0}".format(pattern))


def main() -> int:
    print("Validating Treatment Framework Signed Review State Persistence Migration Implementation V1")

    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), "missing required file: {0}".format(rel))
        require(not rel.startswith("backend/migrations/versions/"), "active migration target forbidden: {0}".format(rel))
    for rel in REFERENCE_FILES:
        require((ROOT / rel).is_file(), "missing reference file: {0}".format(rel))

    active_migration = ROOT / "backend" / "migrations" / "versions" / "0010_treatment_framework_signed_review_states.py"
    require(not active_migration.exists(), "active Alembic revision must not be created in this stage")

    py_compile.compile(str(ROOT / "scripts/validate_treatment_framework_signed_review_state_persistence_migration_implementation.py"), doraise=True)

    doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1.md")
    checklist = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_CHECKLIST_V1.csv")
    go_no_go = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_GO_NO_GO_V1.csv")
    draft = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt")
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    final_doc = read("docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1.md")
    migration_dry_run_backend = read("backend/treatment_framework_signed_review_state_persistence_migration_dry_run.py")

    require_tokens("doc", doc, [
        STAGE,
        "migration_implementation_draft_only=true",
        "migration_apply_allowed=false",
        "migration_enabled=false",
        "active_migration_file_created=false",
        "inactive_migration_draft_created=true",
        "schema_change_enabled=false",
        "persistence_enabled=false",
        "signed_review_state_persistence_enabled=false",
        "review_state_persistence_enabled=false",
        "writes_database=false",
        "no_case_treatment_write=true",
        "no_prescription_write=true",
        "no_dose_route_frequency=true",
        NEXT_DECISION,
    ])
    require_tokens("checklist", checklist, [
        "migration_implementation_draft_only",
        "inactive_migration_draft_created",
        "active_migration_file_created_false",
        "migration_apply_allowed_false",
        "schema_change_enabled_false",
        NEXT_DECISION,
    ])
    require_tokens("go_no_go", go_no_go, [
        "NO_GO_TO_ACTIVE_ALEMBIC_REVISION",
        "NO_GO_TO_MIGRATION_APPLY",
        "NO_GO_TO_SCHEMA_CHANGE",
        "NO_GO_TO_DATABASE_WRITE",
        "NO_GO_TO_CASE_TREATMENT_PERSISTENCE",
        NEXT_DECISION,
    ])
    require_tokens("migration draft", draft, [
        "revision = \"0010_treatment_framework_signed_review_states\"",
        "down_revision = \"0009_diag_data\"",
        "op.create_table(",
        "\"treatment_framework_signed_review_states\"",
        "sa.Column(\"case_id\"",
        "sa.Column(\"confirmed_diagnosis_label\"",
        "sa.Column(\"review_decision\"",
        "sa.Column(\"signed_review_status\"",
        "sa.Column(\"audit_log_reference\"",
        "op.create_index(\"ix_tfsrs_case_id\"",
        "op.drop_table(\"treatment_framework_signed_review_states\")",
        "INACTIVE DRAFT ONLY",
    ])
    compile(draft, "inactive_migration_draft.py.txt", "exec")

    require_tokens("ci", ci, [
        STAGE,
        "validate_treatment_framework_signed_review_state_persistence_migration_implementation.py",
        "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1",
        "validate_treatment_framework_signed_review_state_persistence_migration_final_go_no_go.py",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "signed review state persistence migration implementation markers",
        "PASS: ci_static_checks",
    ])

    optional = optional_block(ci)
    for stage_scoped in [
        "validate_treatment_framework_signed_review_state_persistence_migration_final_go_no_go.py",
        "validate_case_detail_treatment_framework_signed_review_state_persistence_migration_ui.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_dry_run.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_design.py",
        "validate_treatment_framework_signed_review_state_persistence_migration_readiness_review.py",
    ]:
        require(stage_scoped not in optional, "stage-scoped validator must not be re-run in this implementation CI: {0}".format(stage_scoped))
    require("git add ." not in ci, "ci contains legacy-forbidden exact git add marker")
    require("\"${OPTIONAL_CORE_VALIDATORS[@]:-}\"" in ci, "ci optional validator loop must remain Bash 3.2-safe")

    require_tokens("smoke", smoke, [
        "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
        "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"",
        "LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1",
        "LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1",
        "check_treatment_framework_signed_review_state_persistence_migration_final_go_no_go_v1",
        "check_treatment_framework_signed_review_state_persistence_migration_implementation_v1",
        "treatment_framework_signed_review_state_persistence_migration_implementation=PASS",
        "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1",
        NEXT_DECISION,
    ])
    require(
        re.search(
            r"\ncheck_treatment_framework_signed_review_state_persistence_migration_final_go_no_go_v1\s*\ncheck_treatment_framework_signed_review_state_persistence_migration_implementation_v1\s*\n",
            smoke,
        ) is not None,
        "smoke must call migration implementation after final go/no-go",
    )

    require("migration_implementation_allowed=true" in final_doc, "previous final go/no-go did not allow implementation")
    require("migration_apply_allowed=false" in final_doc, "previous final go/no-go apply block missing")
    require("TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_MODE" in migration_dry_run_backend, "migration dry-run backend mode missing")

    combined = "\n".join([doc, checklist, go_no_go, draft, ci, smoke])
    assert_no_dangerous_flags(combined)
    require("alembic upgrade" not in combined, "implementation stage must not include active migration apply command")

    smoke_lines = len(smoke.splitlines())
    require(smoke_lines >= 1000, "smoke_petmed.sh line count too small; cumulative guard may have been lost")

    print("PASS: Treatment Framework Signed Review State Persistence Migration Implementation V1")
    print("migration_implementation_draft_only=true")
    print("migration_apply_allowed=false")
    print("migration_enabled=false")
    print("active_migration_file_created=false")
    print("inactive_migration_draft_created=true")
    print("schema_change_enabled=false")
    print("read_only=true")
    print("writes_database=false")
    print("not_client_facing=true")
    print("requires_human_review=true")
    print("clinician_signoff_required=true")
    print("decision={0}".format(NEXT_DECISION))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
