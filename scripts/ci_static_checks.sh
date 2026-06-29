#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGETS=(
  "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_V1.md"
  "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_CHECKLIST_V1.csv"
  "docs/clinical_data/CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_BOUNDARY_GO_NO_GO_V1.csv"
  "scripts/validate_confirmed_diagnosis_treatment_framework_boundary.py"
  "scripts/ci_static_checks.sh"
  "scripts/smoke_petmed.sh"
)

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

printf '%s\n' "[ci_static_checks] python syntax"
python3 -m py_compile scripts/validate_confirmed_diagnosis_treatment_framework_boundary.py

printf '%s\n' "[ci_static_checks] shell syntax"
bash -n scripts/ci_static_checks.sh
bash -n scripts/smoke_petmed.sh

printf '%s\n' "[ci_static_checks] boundary validator"
python3 scripts/validate_confirmed_diagnosis_treatment_framework_boundary.py

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
          app.db|*.db|.env|frontend/.env.development|frontend/package-lock.json|backend/app/*|backend/ai_engine/*|frontend/src/components/*|*.bak|*.save)
            echo "forbidden tracked diff for this stage: $path" >&2
            exit 1
            ;;
          *)
            echo "non-target tracked diff for this stage: $path" >&2
            echo "Commit this Boundary V1 stage with explicit target files only; do not use git add ." >&2
            exit 1
            ;;
        esac
      fi
    done <<EOF_CHANGED
$changed
EOF_CHANGED
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
done

printf '%s\n' "PASS: ci_static_checks"
