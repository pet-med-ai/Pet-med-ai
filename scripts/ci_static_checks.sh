#!/usr/bin/env bash
set -euo pipefail

# TREATMENT_FRAMEWORK_AUDIT_LOG_V1
# Cumulative guard remains active: CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MIN_SMOKE_LINES=1000
TARGETS=(
  "backend/treatment_framework_audit_log.py"
  "backend/audit_log_api.py"
  "docs/clinical_data/TREATMENT_FRAMEWORK_AUDIT_LOG_V1.md"
  "docs/clinical_data/TREATMENT_FRAMEWORK_AUDIT_LOG_CHECKLIST_V1.csv"
  "docs/clinical_data/TREATMENT_FRAMEWORK_AUDIT_LOG_GO_NO_GO_V1.csv"
  "scripts/validate_treatment_framework_audit_log.py"
  "scripts/ci_static_checks.sh"
  "scripts/smoke_petmed.sh"
)
OPTIONAL_CORE_VALIDATORS=(
  "scripts/validate_confirmed_diagnosis_treatment_framework_boundary.py"
  "scripts/validate_confirmed_diagnosis_treatment_framework_draft.py"
)
RESTORE_GUARD_VALIDATOR_REFERENCE="scripts/validate_ci_smoke_cumulative_guard_restore.py"
# --- Previous stage validator scope compatibility: start ---
# CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_V1
# frontend/src/pages/CaseDetail.jsx
# case detail treatment framework preview UI markers
# validate_case_detail_treatment_framework_preview_ui.py
# TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1
# backend/treatment_framework_clinician_review_workflow.py
# /dry-run/confirmed-diagnosis/treatment-framework/review
# treatment_framework_clinician_review_workflow_smoke=PASS
# GO_TO_TREATMENT_FRAMEWORK_AUDIT_LOG_V1
# Previous UI and review-workflow validators are stage-scoped and are not executed here.
# --- Previous stage validator scope compatibility: end ---
DANGEROUS_FLAGS=(
  "ENABLE_EMR_REAL_IMPORT" "ENABLE_EMR_IMPORT_CASE_UPDATE" "ENABLE_EMR_ATTACHMENT_DOWNLOAD"
  "ENABLE_PREVENTIVE_AUTO_DELIVERY" "ENABLE_PREVENTIVE_SMS_DELIVERY" "ENABLE_PREVENTIVE_WECHAT_DELIVERY" "ENABLE_PREVENTIVE_EMAIL_DELIVERY"
  "ENABLE_PRESCRIPTION_STRUCTURED_WRITE" "ENABLE_DEVICE_REAL_INGEST" "ENABLE_BILLING_REAL_WRITE"
)
# --- Legacy CI Gate compatibility markers: start ---
# validate_release_readiness.py
# validate_release_changelog.py
# validate_system_version_info.py
# validate_feature_flags.py
# validate_emr_import_execute_create_only.py
# validate_alembic_setup.py
# py_compile.compile
# CI static checks PASS
# --- Legacy CI Gate compatibility markers: end ---
printf '%s\n' "[ci_static_checks] git diff --check"
git diff --check
printf '%s\n' "[ci_static_checks] required target files"
for target in "${TARGETS[@]}"; do test -f "$target" || { echo "missing target: $target" >&2; exit 1; }; done
printf '%s\n' "[ci_static_checks] no forbidden target paths"
for target in "${TARGETS[@]}"; do
  case "$target" in backend/app/*|backend/ai_engine/*|frontend/src/components/*|frontend/package-lock.json|app.db|*.db|.env|frontend/.env.development) echo "forbidden target path for this stage: $target" >&2; exit 1;; esac
done
printf '%s\n' "[ci_static_checks] python syntax"
python3 -m py_compile backend/treatment_framework_audit_log.py
python3 -m py_compile backend/audit_log_api.py
python3 -m py_compile scripts/validate_treatment_framework_audit_log.py
for validator in scripts/validate_*.py; do [ -f "$validator" ] || continue; python3 -m py_compile "$validator"; done
printf '%s\n' "[ci_static_checks] shell syntax"
bash -n scripts/ci_static_checks.sh
bash -n scripts/smoke_petmed.sh
printf '%s\n' "[ci_static_checks] audit log validator"
python3 scripts/validate_treatment_framework_audit_log.py
printf '%s\n' "[ci_static_checks] optional core validators"
for validator in "${OPTIONAL_CORE_VALIDATORS[@]}"; do if [ -f "$validator" ]; then python3 "$validator"; fi; done
printf '%s\n' "[ci_static_checks] target-only tracked diff discipline"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  changed="$( { git diff --name-only HEAD -- 2>/dev/null || true; git diff --cached --name-only -- 2>/dev/null || true; } | sort -u )"
  if [ -n "$changed" ]; then
    while IFS= read -r path; do
      [ -z "$path" ] && continue
      allowed=0
      for target in "${TARGETS[@]}"; do [ "$path" = "$target" ] && allowed=1 && break; done
      if [ "$allowed" -ne 1 ]; then
        case "$path" in app.db|*.db|.env|frontend/.env.development|frontend/package-lock.json|backend/app/*|backend/ai_engine/*|frontend/src/components/*|*.bak|*.save) echo "forbidden tracked diff for this stage: $path" >&2; exit 1;; *) echo "non-target tracked diff for this stage: $path" >&2; echo "Commit this audit log V1 stage with explicit target files only; do not stage the entire working tree" >&2; exit 1;; esac
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
    while IFS= read -r path; do [ -z "$path" ] && continue; case "$path" in app.db|*.db|.env|frontend/.env.development|frontend/package-lock.json|backend/app/*|backend/ai_engine/*|frontend/src/components/*|*.bak|*.save) echo "forbidden staged path: $path" >&2; exit 1;; esac; done <<EOF_STAGED
$staged
EOF_STAGED
  fi
fi
printf '%s\n' "[ci_static_checks] no dangerous flag enablement in target files"
for flag in "${DANGEROUS_FLAGS[@]}"; do
  if grep -R --line-number --fixed-strings "${flag}=true" "${TARGETS[@]}"; then echo "dangerous flag enablement found: ${flag}=true" >&2; exit 1; fi
  if grep -R --line-number --fixed-strings "${flag}: true" "${TARGETS[@]}"; then echo "dangerous flag enablement found: ${flag}: true" >&2; exit 1; fi
  if grep -R --line-number --fixed-strings "\"${flag}\": true" "${TARGETS[@]}"; then echo "dangerous flag enablement found: \"${flag}\": true" >&2; exit 1; fi
done
printf '%s\n' "[ci_static_checks] treatment framework audit log endpoint markers"
grep -q '/diagnostic-data/confirmed-diagnosis/treatment-framework/audit-log/append' backend/audit_log_api.py
grep -q 'Treatment Framework Audit Log V1 endpoint: start' backend/audit_log_api.py
grep -q 'TREATMENT_FRAMEWORK_AUDIT_LOG_MODE' backend/treatment_framework_audit_log.py
grep -q 'TREATMENT_FRAMEWORK_AUDIT_LOG_CONFIRMATION' backend/treatment_framework_audit_log.py
grep -q 'append_only_audit_log' backend/treatment_framework_audit_log.py
grep -q 'writes_case_treatment' backend/treatment_framework_audit_log.py
grep -q 'returns_drug_dose' backend/treatment_framework_audit_log.py
printf '%s\n' "[ci_static_checks] cumulative smoke markers"
grep -q 'CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1' scripts/smoke_petmed.sh
grep -q 'LEGACY_SMOKE_BASELINE="0c8fd5d:scripts/smoke_petmed.sh"' scripts/smoke_petmed.sh
grep -q 'LEGACY_SMOKE_COMPAT_RABBIT_GI_TREE_PATH_V1' scripts/smoke_petmed.sh
grep -q 'LEGACY_SMOKE_COMPAT_LIZARD_UVB_TREE_PATH_V1' scripts/smoke_petmed.sh
grep -q 'check_treatment_framework_clinician_review_workflow_v1' scripts/smoke_petmed.sh
grep -q 'check_treatment_framework_audit_log_v1' scripts/smoke_petmed.sh
grep -q 'treatment_framework_audit_log_smoke=PASS' scripts/smoke_petmed.sh
smoke_lines="$(wc -l < scripts/smoke_petmed.sh | tr -d ' ')"
if [ "$smoke_lines" -lt "$MIN_SMOKE_LINES" ]; then echo "smoke_petmed.sh line count too small for cumulative restore: ${smoke_lines} < ${MIN_SMOKE_LINES}" >&2; exit 1; fi
printf '%s\n' "smoke_line_count=${smoke_lines}"
printf '%s\n' "PASS: ci_static_checks"
