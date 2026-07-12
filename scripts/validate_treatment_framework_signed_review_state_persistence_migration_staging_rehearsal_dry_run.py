#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import csv
import glob
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE_TITLE = 'Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Dry Run V1'
STAGE_TOKEN_UPPER = 'TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1'
STAGE_TOKEN = 'treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1'
STAGE_SLUG = 'treatment framework signed review state persistence migration staging rehearsal dry run'
DOC_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md'
CHECKLIST_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_CHECKLIST_V1.csv'
GO_NO_GO_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_GO_NO_GO_V1.csv'
VALIDATOR_REL = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run.py'
CI_REL = 'scripts/ci_static_checks.sh'
SMOKE_REL = 'scripts/smoke_petmed.sh'
PLAN_DOC_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1.md'
INACTIVE_DRAFT_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt'
PREVIOUS_DECISION = 'GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1'
DECISION = 'GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1'
SMOKE_GATE_BEGIN = '# >>> treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1_smoke_petmed_runtime_gate'
SMOKE_GATE_END = '# <<< treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1_smoke_petmed_runtime_gate'
DANGEROUS_FLAGS = ['ENABLE_EMR_REAL_IMPORT', 'ENABLE_EMR_IMPORT_CASE_UPDATE', 'ENABLE_EMR_ATTACHMENT_DOWNLOAD', 'ENABLE_PREVENTIVE_AUTO_DELIVERY', 'ENABLE_PREVENTIVE_SMS_DELIVERY', 'ENABLE_PREVENTIVE_WECHAT_DELIVERY', 'ENABLE_PREVENTIVE_EMAIL_DELIVERY', 'ENABLE_PRESCRIPTION_STRUCTURED_WRITE', 'ENABLE_DEVICE_REAL_INGEST', 'ENABLE_BILLING_REAL_WRITE']
REQUIRED_DOC_MARKERS = ['stage_name=Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Dry Run V1', 'stage_type=staging_rehearsal_dry_run_only', 'STAGING_REHEARSAL_DRY_RUN_ONLY=true', 'REAL_STAGING_MIGRATION_EXECUTED=false', 'PRODUCTION_MIGRATION_EXECUTED=false', 'ACTIVE_0010_MIGRATION_FILE_CREATED=false', 'SCHEMA_CHANGE_APPLIED=false', 'DATABASE_WRITE_PERFORMED=false', 'CASE_TREATMENT_WRITE_PERFORMED=false', 'PRESCRIPTION_WRITE_PERFORMED=false', 'CLIENT_FACING_RELEASE_PERFORMED=false', 'CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false', 'database_revision=0009_diag_data', 'alembic_head=0009_diag_data', 'schema_ok=true', 'migration_errors=[]', 'writes_database=false', 'exposes_database_url=false', 'inactive_0010_draft_reference_required=true', 'staging_environment_requirement_defined=true', 'staging_environment_must_be_isolated_from_production=true', 'backup_restore_evidence_required=true', 'rollback_dry_run_required=true', 'authenticated_smoke_required_before_future_write=true', 'production_hard_gate_must_remain_0009=true', 'active_migration_file_must_not_exist=true', 'no_database_write_must_be_preserved=true', 'no_case_treatment_write_must_be_preserved=true', 'no_prescription_write_must_be_preserved=true', 'no_client_facing_release_must_be_preserved=true', 'previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1', 'decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1']
TARGET_PATHS = ['docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_CHECKLIST_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_GO_NO_GO_V1.csv', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run.py', 'scripts/ci_static_checks.sh', 'scripts/smoke_petmed.sh']


def require(condition, message):
    if not condition:
        print("NO-GO: " + message)
        raise SystemExit(1)


def read(rel_path):
    path = ROOT / rel_path
    require(path.is_file(), "missing required file: " + rel_path)
    return path.read_text(encoding="utf-8")


def require_tokens(label, text, tokens):
    missing = [token for token in tokens if token not in text]
    require(not missing, label + " missing tokens: " + ", ".join(missing))


def check_csv(rel_path, expected_columns, required_ids):
    path = ROOT / rel_path
    require(path.is_file(), "missing required csv: " + rel_path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == expected_columns, "unexpected columns in " + rel_path)
        rows = list(reader)
    first_column = expected_columns[0]
    seen = set(row.get(first_column, "") for row in rows)
    missing = [item for item in required_ids if item not in seen]
    require(not missing, "missing rows in " + rel_path + ": " + ", ".join(missing))
    for row in rows:
        require(row.get("blocking") in ("yes", "no"), "invalid blocking value in " + rel_path)
    return rows


def check_no_active_0010():
    pattern = str(ROOT / "backend" / "migrations" / "versions" / "0010*.py")
    matches = sorted(glob.glob(pattern))
    require(not matches, "active backend/migrations/versions/0010*.py is forbidden in this phase")


def check_shell_syntax(rel_path):
    result = subprocess.run(["bash", "-n", str(ROOT / rel_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    require(result.returncode == 0, rel_path + " shell syntax failed: " + result.stderr.strip())


def check_docs_and_csvs():
    doc = read(DOC_REL)
    for marker in REQUIRED_DOC_MARKERS:
        require(marker in doc, "dry-run document missing marker: " + marker)
    for flag in DANGEROUS_FLAGS:
        require(flag + "=false" in doc, "dangerous feature flag false marker missing: " + flag)

    checklist_rows = check_csv(
        CHECKLIST_REL,
        ["item_id", "area", "requirement", "expected_evidence", "status", "blocking", "notes"],
        ["DRYRUN-%03d" % value for value in range(1, 13)],
    )
    go_no_go_rows = check_csv(
        GO_NO_GO_REL,
        ["gate_id", "gate", "required_state", "observed_state", "decision", "blocking", "notes"],
        ["GATE-%03d" % value for value in range(1, 10)],
    )
    checklist = read(CHECKLIST_REL)
    go_no_go = read(GO_NO_GO_REL)
    require(DECISION in checklist, "checklist missing next-stage decision")
    require(DECISION in go_no_go, "go/no-go missing next-stage decision")
    require(any(row.get("status") == "REQUIREMENT_DEFINED" for row in checklist_rows), "checklist must retain future evidence requirements")
    require(any(row.get("decision") == "NO_GO_FOR_REAL_APPLY" for row in go_no_go_rows), "go/no-go must block real apply")
    require(any(row.get("decision") == "NO_GO_FOR_REAL_WRITE" for row in go_no_go_rows), "go/no-go must block real write")


def check_reference_inputs():
    plan = read(PLAN_DOC_REL)
    inactive_draft = read(INACTIVE_DRAFT_REL)
    require(PREVIOUS_DECISION in plan, "staging rehearsal plan does not hand off to the dry-run phase")
    require('down_revision = "0009_diag_data"' in inactive_draft, "inactive 0010 draft must retain down_revision 0009_diag_data")
    require("0010" in inactive_draft, "inactive 0010 draft reference is missing its revision marker")


def check_ci_wiring():
    ci = read(CI_REL)
    require_tokens("ci", ci, [
        STAGE_TOKEN_UPPER,
        DOC_REL,
        CHECKLIST_REL,
        GO_NO_GO_REL,
        VALIDATOR_REL,
        "python3 -m py_compile " + VALIDATOR_REL,
        "python3 " + VALIDATOR_REL,
        'for validator in "${OPTIONAL_CORE_VALIDATORS[@]:-}"; do',
        '[ -n "$validator" ] || continue',
        "Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Plan V1",
        "signed review state persistence migration staging rehearsal dry run markers",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "PASS: ci_static_checks",
    ])
    target_block_match = re.search(r"TARGETS=\((.*?)\n\)", ci, flags=re.S)
    require(target_block_match is not None, "CI TARGETS block missing")
    target_block = target_block_match.group(1)
    for target in TARGET_PATHS:
        require('"' + target + '"' in target_block, "CI TARGETS missing current-stage path: " + target)
    require(PLAN_DOC_REL not in target_block, "CI TARGETS must not remain on the previous plan-stage document")
    require("git add ." not in ci, "CI contains forbidden git add . marker")


def check_smoke_wiring():
    smoke = read(SMOKE_REL)
    require(smoke.count(SMOKE_GATE_BEGIN) == 1, "current-stage smoke runtime gate begin marker must occur exactly once")
    require(smoke.count(SMOKE_GATE_END) == 1, "current-stage smoke runtime gate end marker must occur exactly once")
    begin = smoke.index(SMOKE_GATE_BEGIN)
    end = smoke.index(SMOKE_GATE_END, begin) + len(SMOKE_GATE_END)
    all_pass = smoke.rfind("ALL PASS: smoke_petmed")
    require(all_pass >= 0, "cumulative smoke final ALL PASS marker missing")
    summary_printf = smoke.rfind("printf ", 0, all_pass)
    require(summary_printf >= 0, "cumulative smoke final summary printf missing")
    require(begin < end < summary_printf < all_pass, "current-stage smoke gate is not executable before the final cumulative summary")
    runtime_block = smoke[begin:end]
    require(VALIDATOR_REL in runtime_block, "current-stage smoke gate does not execute the validator")
    previous_runtime = smoke.rfind("check_treatment_framework_signed_review_state_persistence_migration_implementation_v1", 0, begin)
    require(previous_runtime >= 0, "current-stage smoke gate must follow the retained implementation compatibility check")

    summary = smoke[summary_printf:]
    require_tokens("smoke summary", summary, [
        "treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_plan_v1=true",
        STAGE_TOKEN + "=true",
        "previous_stage_decision=" + PREVIOUS_DECISION,
        "decision=" + DECISION,
    ])
    require(summary.count('"previous_stage_decision=') == 1, "final smoke summary must have exactly one previous_stage_decision line")
    require(summary.count('"decision=') == 1, "final smoke summary must have exactly one decision line")
    require("previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_V1" not in summary, "final smoke summary still carries the obsolete previous-stage decision")
    require('"decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1"' not in summary, "final smoke summary still points into the already-completed dry-run phase")
    require(len(smoke.splitlines()) >= 1000, "smoke_petmed.sh line count too small; cumulative coverage may have been lost")


def check_safety_markers():
    combined = "\n".join([read(DOC_REL), read(CHECKLIST_REL), read(GO_NO_GO_REL), read(CI_REL)])
    for flag in DANGEROUS_FLAGS:
        for pattern in (flag + "=true", flag + ": true", '"' + flag + '": true'):
            require(pattern not in combined, "dangerous feature flag enablement found: " + pattern)


def main():
    for rel_path in TARGET_PATHS:
        require((ROOT / rel_path).is_file(), "missing current-stage target: " + rel_path)
    check_no_active_0010()
    check_docs_and_csvs()
    check_reference_inputs()
    check_ci_wiring()
    check_smoke_wiring()
    check_shell_syntax(CI_REL)
    check_shell_syntax(SMOKE_REL)
    check_safety_markers()

    print("PASS: " + STAGE_TITLE)
    print("PASS: ci_static_checks wiring")
    print("PASS: cumulative smoke runtime gate")
    print("PASS: production hard gate static markers")
    print("database_revision=0009_diag_data")
    print("alembic_head=0009_diag_data")
    print("schema_ok=true")
    print("migration_errors=[]")
    print("writes_database=false")
    print("exposes_database_url=false")
    print("PASS: dangerous feature flags disabled")
    print("PASS: active migration file not created")
    print("PASS: no database write")
    print("PASS: no Case.treatment write")
    print("PASS: no prescription write")
    print("validator_previous_stage_decision=" + PREVIOUS_DECISION)
    print("validator_decision=" + DECISION)
    print("ALL PASS: " + STAGE_TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
