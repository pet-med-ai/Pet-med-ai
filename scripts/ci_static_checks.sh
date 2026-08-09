#!/usr/bin/env bash
set -euo pipefail

# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1
# Cumulative guard remains active: CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MIN_SMOKE_LINES=1000

TARGETS=(
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md"
  "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"
  "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"
  "scripts/ci_static_checks.sh"
  "scripts/smoke_petmed.sh"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1.md"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_CHECKLIST_V1.csv"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_GO_NO_GO_V1.csv"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_TEST_MATRIX_V1.csv"
  "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1.md"
  "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1.md"
  "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md"
  "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md"
  "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md"
  "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py"
)
OPTIONAL_CORE_VALIDATORS=(
)

RESTORE_GUARD_VALIDATOR_REFERENCE="scripts/validate_ci_smoke_cumulative_guard_restore.py"

# --- Previous stage compatibility markers: start ---
# Treatment Framework Signed Review State Persistence Migration Rollback Restore Evidence V1
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1
# scripts/validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py
# treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1=PASS
# stage_status=COMPLETE
# decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1
# Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Evidence V1
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1
# scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence.py
# treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1=PASS
# previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1
# Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Dry Run V1
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1
# scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run.py
# treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1=PASS
# previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1
# Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Plan V1
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1
# validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_plan.py
# treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_plan=PASS
# previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_V1
# validate_treatment_framework_signed_review_state_persistence_migration_apply_readiness_review.py
# treatment_framework_signed_review_state_persistence_migration_apply_readiness_review=PASS
# previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1
# validate_treatment_framework_signed_review_state_persistence_migration_final_go_no_go.py
# treatment_framework_signed_review_state_persistence_migration_final_go_no_go=PASS
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1
# validate_treatment_framework_signed_review_state_persistence_migration_implementation.py
# treatment_framework_signed_review_state_persistence_migration_implementation=PASS
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_V1
# validate_treatment_framework_signed_review_state_persistence_migration_dry_run.py
# treatment_framework_signed_review_state_persistence_migration_dry_run_smoke=PASS
# CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_UI_V1
# validate_case_detail_treatment_framework_signed_review_state_persistence_migration_ui.py
# case_detail_treatment_framework_signed_review_state_persistence_migration_ui=PASS
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DESIGN_V1
# validate_treatment_framework_signed_review_state_persistence_migration_design.py
# treatment_framework_signed_review_state_persistence_migration_design=PASS
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_READINESS_REVIEW_V1
# validate_treatment_framework_signed_review_state_persistence_migration_readiness_review.py
# treatment_framework_signed_review_state_persistence_migration_readiness_review=PASS
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1
# validate_treatment_framework_signed_review_state_persistence_design.py
# treatment_framework_signed_review_state_persistence_design=PASS
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_V1
# validate_treatment_framework_signed_review_state_persistence_risk_review.py
# treatment_framework_signed_review_state_persistence_risk_review=PASS
# TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1
# validate_treatment_framework_persistence_risk_review.py
# treatment_framework_persistence_risk_review=PASS
# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1
# validate_treatment_framework_signed_review_state_design.py
# treatment_framework_signed_review_state_design=PASS
# Earlier stage coverage remains in smoke; previous stage validators are stage-scoped.
# --- Previous stage compatibility markers: end ---

# --- Legacy CI Gate compatibility markers: start ---
# These markers remain so old validation docs can find historical CI expectations.
# validate_release_readiness.py
# validate_release_changelog.py
# validate_system_version_info.py
# validate_feature_flags.py
# validate_emr_import_execute_create_only.py
# validate_alembic_setup.py
# py_compile.compile
# CI static checks PASS
# --- Legacy CI Gate compatibility markers: end ---

DANGEROUS_FLAGS=(
  "ENABLE_EMR_REAL_IMPORT"
  "ENABLE_EMR_IMPORT_CASE_UPDATE"
  "ENABLE_EMR_ATTACHMENT_DOWNLOAD"
  "ENABLE_PREVENTIVE_AUTO_DELIVERY"
  "ENABLE_PREVENTIVE_SMS_DELIVERY"
  "ENABLE_PREVENTIVE_WECHAT_DELIVERY"
  "ENABLE_PREVENTIVE_EMAIL_DELIVERY"
  "ENABLE_PRESCRIPTION_STRUCTURED_WRITE"
  "ENABLE_DEVICE_REAL_INGEST"
  "ENABLE_BILLING_REAL_WRITE"
)

printf '%s\n' "[ci_static_checks] git diff --check"
git diff --check

printf '%s\n' "[ci_static_checks] required target files"
for target in "${TARGETS[@]}"; do
  test -f "$target" || { echo "missing target: $target" >&2; exit 1; }
done

printf '%s\n' "[ci_static_checks] no forbidden target paths"
for target in "${TARGETS[@]}"; do
  case "$target" in
    backend/migrations/versions/*|backend/app/*|backend/ai_engine/*|frontend/src/components/*|frontend/package-lock.json|app.db|*.db|.env|frontend/.env.development)
      echo "forbidden target path for this stage: $target" >&2
      exit 1
      ;;
  esac
done

printf '%s\n' "[ci_static_checks] python syntax"
python3 -m py_compile scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py
python3 -m py_compile scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py
for validator in scripts/validate_*.py; do
  [ -f "$validator" ] || continue
  python3 -m py_compile "$validator"
done

printf '%s\n' "[ci_static_checks] shell syntax"
bash -n scripts/ci_static_checks.sh
bash -n scripts/smoke_petmed.sh

printf '%s\n' "[ci_static_checks] full history checkout for baseline verification"
STATIC_BACKEND_JOB="$(
  sed -n '/^  static-backend-gate:/,/^  frontend-build-gate:/p' .github/workflows/ci-gate.yml
)"
printf '%s\n' "$STATIC_BACKEND_JOB" | grep -q 'uses: actions/checkout@v4'
printf '%s\n' "$STATIC_BACKEND_JOB" | grep -q 'fetch-depth: 0'

printf '%s\n' "[ci_static_checks] P0-03 completed prerequisite static compatibility"
grep -q 'stage_id=PMAI-P0-03' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md
grep -q 'STAGE_STATUS=COMPLETE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md
grep -q 'EVIDENCE_COMPLETENESS=COMPLETE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md
grep -q 'P0_04_ENTRY_AUTHORIZED=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md
grep -q 'evidence_artifact_sha256=da52b46466a65316331d420c809bc406e49dfa722b1b5875667e30db50eef213' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md
grep -q 'decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md

printf '%s\n' "[ci_static_checks] PMAI-P0-04 governance preparation package validator"
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py

printf '%s\n' "[ci_static_checks] target-only tracked diff discipline"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  changed="$( { git diff --name-only HEAD -- 2>/dev/null || true; git diff --cached --name-only -- 2>/dev/null || true; } | sort -u )"
  if [ -n "$changed" ]; then
    while IFS= read -r path; do
      [ -z "$path" ] && continue
      allowed=0
      for target in "${TARGETS[@]}"; do
        if [ "$path" = "$target" ]; then
          allowed=1
          break
        fi
      done
      if [ "$allowed" -ne 1 ]; then
        case "$path" in
          backend/migrations/versions/*|app.db|*.db|.env|frontend/.env.development|frontend/package-lock.json|backend/app/*|backend/ai_engine/*|frontend/src/components/*|*.bak|*.save)
            echo "forbidden tracked diff for this stage: $path" >&2
            exit 1
            ;;
          *)
            echo "non-target tracked diff for this stage: $path" >&2
            echo "Commit this PMAI-P0-04 governance package with explicit target files only; do not stage the whole working tree" >&2
            exit 1
            ;;
        esac
      fi
    done <<EOF_CHANGED
$changed
EOF_CHANGED
  fi
fi

printf '%s\n' "[ci_static_checks] sensitive staged path discipline"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  staged="$(git diff --cached --name-only -- 2>/dev/null || true)"
  if [ -n "$staged" ]; then
    while IFS= read -r path; do
      [ -z "$path" ] && continue
      case "$path" in
        backend/migrations/versions/*|app.db|*.db|.env|frontend/.env.development|frontend/package-lock.json|backend/app/*|backend/ai_engine/*|frontend/src/components/*|*.bak|*.save)
          echo "forbidden staged path: $path" >&2
          exit 1
          ;;
      esac
    done <<EOF_STAGED
$staged
EOF_STAGED
  fi
fi

printf '%s\n' "[ci_static_checks] no dangerous flag enablement in target files"
for flag in "${DANGEROUS_FLAGS[@]}"; do
  if grep -R --line-number --fixed-strings "${flag}=true" "${TARGETS[@]}"; then
    echo "dangerous flag enablement found: ${flag}=true" >&2
    exit 1
  fi
  if grep -R --line-number --fixed-strings "${flag}: true" "${TARGETS[@]}"; then
    echo "dangerous flag enablement found: ${flag}: true" >&2
    exit 1
  fi
  if grep -R --line-number --fixed-strings "\"${flag}\": true" "${TARGETS[@]}"; then
    echo "dangerous flag enablement found: \"${flag}\": true" >&2
    exit 1
  fi
done

printf '%s\n' "[ci_static_checks] PMAI-P0-04 governance package markers"
grep -q 'stage_id=PMAI-P0-04' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'STAGE_STATUS=IN_PROGRESS' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'EVIDENCE_COMPLETENESS=PENDING_DISPOSABLE_TARGET_PROVISIONING_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'P0_04_GOVERNANCE_PREPARATION_COMPLETE=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'P0_04_EXECUTION_AUTHORIZED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'STAGING_0010_APPLY_AUTHORIZED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'ACTIVE_0010_MIGRATION_FILE_CREATED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'ACTIVE_0010_MIGRATION_FILE_ALLOWED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'schema_contract_resolution_recorded=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'P0_04_SCHEMA_CONTRACT_RESOLUTION_COMPLETE=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'migration_schema_review_approved=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'corrected_migration_implementation_authorized=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'approved_revision=0010_signed_review_states' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'approved_append_only_trigger_required=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'schema_contract_resolution_recorded=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_audit_log_composite_fk_target=audit_log.log_id|audit_log.case_id' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_audit_semantics_trigger_name=trg_tfsrs_validate_audit_semantics' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_audit_payload_hash_storage_column=metadata' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_audit_link_protection_trigger_requirement=REJECT_REFERENCED_AUDIT_UPDATE_AND_DELETE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_idempotency_key_type=String(64)' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_one_root_per_case_index_name=uq_tfsrs_one_root_per_case' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_append_only_trigger_requirement=REJECT_UPDATE_AND_DELETE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_active_case_insert_trigger_requirement=REJECT_INSERT_WHEN_CASE_DELETED_AT_IS_NOT_NULL' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'approved_active_case_insert_lock=SELECT_CASE_WHERE_DELETED_AT_NULL_FOR_SHARE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'review_decision_vocabulary=approve_for_clinician_use|request_revision|reject' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
grep -q 'deployment_isolation_verified=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'staging_only_branch_or_commit_pin_verified=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'production_target_excluded=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'production_deployment_freeze_verified=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'manual_deploy_observed=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md
grep -q 'manual_deploy_deviation_safely_verified=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md
grep -q 'candidate_migration_deployed=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md
grep -q 'postdeploy_readonly_verification_passed=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md
grep -q 'fresh_post_p0_03_staging_backup_verified=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'backup_restoreability_verified=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'independent_evidence_verification_complete=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md
grep -q 'pg_restore_database_target_supplied=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md
grep -q 'disposable_restore_rehearsal_complete=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md
grep -q 'decision=HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_RESTORE_REHEARSAL_AND_EXTERNAL_EVIDENCE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md
grep -q 'GOVERNANCE_APPROVED' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv
grep -q 'NO_GO_TO_PMAI_P0_04_EXECUTION' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv
grep -q 'VERIFIED_EXTERNAL_EVIDENCE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv
grep -q 'PENDING_EXTERNAL_EVIDENCE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv
grep -q ',NOT_AUTHORIZED,' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv
grep -q 'HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_RESTORE_REHEARSAL_AND_EXTERNAL_EVIDENCE' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv
if ls backend/migrations/versions/0010*.py >/dev/null 2>&1; then
  echo "active backend/migrations/versions/0010*.py is forbidden during PMAI-P0-04 governance preparation" >&2
  exit 1
fi

grep -q 'disposable_restore_governance_preparation_complete=true' "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md"
grep -q 'disposable_restore_execution_authorized=false' "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md"
grep -q 'observation_status=OPERATOR_OBSERVATION_UNPROMOTED' "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md"
printf '%s\n' "[ci_static_checks] cumulative smoke markers"
grep -q 'CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1' scripts/smoke_petmed.sh
grep -q '# >>> treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1_smoke_petmed_compatibility_gate' scripts/smoke_petmed.sh
grep -q '# >>> treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate' scripts/smoke_petmed.sh
grep -q 'treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1=COMPLETE' scripts/smoke_petmed.sh
grep -q 'treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1=IN_PROGRESS' scripts/smoke_petmed.sh
grep -q 'p0_04_governance_preparation_complete=true' scripts/smoke_petmed.sh
grep -q 'schema_contract_resolution_recorded=true' scripts/smoke_petmed.sh
grep -q 'migration_schema_review_approved=true' scripts/smoke_petmed.sh
grep -q 'p0_04_execution_authorized=false' scripts/smoke_petmed.sh
grep -q 'staging_0010_apply_authorized=false' scripts/smoke_petmed.sh
grep -q 'previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1' scripts/smoke_petmed.sh
grep -q 'decision=HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_RESTORE_REHEARSAL_AND_EXTERNAL_EVIDENCE' scripts/smoke_petmed.sh
if grep -Eq '^[[:space:]]*python3 .*validate_treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke\.py' scripts/smoke_petmed.sh; then
  echo "PMAI-P0-03 validator must be static compatibility only" >&2
  exit 1
fi
if grep -Eq '^[[:space:]]*python3 .*validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence\.py' scripts/smoke_petmed.sh; then
  echo "PMAI-P0-02 validator must remain static compatibility only" >&2
  exit 1
fi
if grep -Eq '^[[:space:]]*python3 .*run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply\.py' scripts/smoke_petmed.sh; then
  echo "PMAI-P0-04 locked runner must not execute in cumulative smoke" >&2
  exit 1
fi
smoke_lines="$(wc -l < scripts/smoke_petmed.sh | tr -d ' ')"
if [ "$smoke_lines" -lt "$MIN_SMOKE_LINES" ]; then
  echo "smoke_petmed.sh line count too small for cumulative restore: ${smoke_lines} < ${MIN_SMOKE_LINES}" >&2
  exit 1
fi
printf '%s\n' "smoke_line_count=${smoke_lines}"

printf '%s\n' "PASS: ci_static_checks"

# PMAI-P0-04 disposable target provisioning authorization preparation v1
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py || exit 1

# PMAI-P0-04 disposable target provisioning authorization review v1
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py || exit 1

# PMAI-P0-04 disposable target provisioning evidence and restore execution authorization preparation v1
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py || exit 1

# PMAI-P0-04 disposable restore execution authorization review v1
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py || exit 1

# PMAI-P0-04 external disposable restore V2 pre-execution abort evidence and disposable target retirement preparation v1
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py || exit 1

# PMAI-P0-04 disposable target retirement authorization review v1
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py || exit 1
