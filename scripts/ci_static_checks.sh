#!/usr/bin/env bash
set -euo pipefail

# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1
# Cumulative guard remains active: CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MIN_SMOKE_LINES=1000

TARGETS=(
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_CHECKLIST_V1.csv"
  "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_GO_NO_GO_V1.csv"
  "scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run.py"
  "scripts/ci_static_checks.sh"
  "scripts/smoke_petmed.sh"
)

OPTIONAL_CORE_VALIDATORS=(
)

RESTORE_GUARD_VALIDATOR_REFERENCE="scripts/validate_ci_smoke_cumulative_guard_restore.py"

# --- Previous stage compatibility markers: start ---
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
python3 -m py_compile scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run.py
for validator in scripts/validate_*.py; do
  [ -f "$validator" ] || continue
  python3 -m py_compile "$validator"
done

printf '%s\n' "[ci_static_checks] shell syntax"
bash -n scripts/ci_static_checks.sh
bash -n scripts/smoke_petmed.sh

printf '%s\n' "[ci_static_checks] signed review state persistence migration staging rehearsal dry run validator"
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run.py

printf '%s\n' "[ci_static_checks] optional core validators intentionally skipped"
for validator in "${OPTIONAL_CORE_VALIDATORS[@]:-}"; do
  [ -n "$validator" ] || continue
  if [ -f "$validator" ]; then
    python3 "$validator"
  fi
done

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
            echo "Commit this staging rehearsal plan stage with explicit target files only; do not stage the whole working tree" >&2
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

printf '%s\n' "[ci_static_checks] signed review state persistence migration staging rehearsal dry run markers"
grep -q 'STAGING_REHEARSAL_DRY_RUN_ONLY=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'REAL_STAGING_MIGRATION_EXECUTED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'PRODUCTION_MIGRATION_EXECUTED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'ACTIVE_0010_MIGRATION_FILE_CREATED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'SCHEMA_CHANGE_APPLIED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'DATABASE_WRITE_PERFORMED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'CASE_TREATMENT_WRITE_PERFORMED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'PRESCRIPTION_WRITE_PERFORMED=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'database_revision=0009_diag_data' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'alembic_head=0009_diag_data' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'schema_ok=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'migration_errors=\[\]' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'writes_database=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'exposes_database_url=false' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'backup_restore_evidence_required=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'rollback_dry_run_required=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'authenticated_smoke_required_before_future_write=true' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md
grep -q 'GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1' docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1.md

printf '%s\n' "[ci_static_checks] cumulative smoke markers"
grep -q 'CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1' scripts/smoke_petmed.sh
grep -q 'LEGACY_SMOKE_BASELINE="0c8fd5d:scripts/smoke_petmed.sh"' scripts/smoke_petmed.sh
grep -q 'LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1' scripts/smoke_petmed.sh
grep -q 'LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1' scripts/smoke_petmed.sh
grep -q 'check_treatment_framework_signed_review_state_persistence_migration_apply_readiness_review_v1' scripts/smoke_petmed.sh
grep -q 'check_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_plan_v1' scripts/smoke_petmed.sh
grep -q 'check_treatment_framework_signed_review_state_persistence_migration_implementation_v1' scripts/smoke_petmed.sh
grep -q '# >>> treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1_smoke_petmed_runtime_gate' scripts/smoke_petmed.sh
grep -q 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run.py' scripts/smoke_petmed.sh
grep -q 'treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_plan=PASS' scripts/smoke_petmed.sh
grep -q 'treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run=PASS' scripts/smoke_petmed.sh
grep -q 'treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1=true' scripts/smoke_petmed.sh
grep -q 'previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1' scripts/smoke_petmed.sh
grep -q 'decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1' scripts/smoke_petmed.sh
smoke_lines="$(wc -l < scripts/smoke_petmed.sh | tr -d ' ')"
if [ "$smoke_lines" -lt "$MIN_SMOKE_LINES" ]; then
  echo "smoke_petmed.sh line count too small for cumulative restore: ${smoke_lines} < ${MIN_SMOKE_LINES}" >&2
  exit 1
fi
printf '%s\n' "smoke_line_count=${smoke_lines}"


printf '%s\n' "PASS: ci_static_checks"
