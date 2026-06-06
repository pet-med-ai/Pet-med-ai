#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Pet-Med-AI CI static checks"
echo "Python: $(python3 --version)"

run_if_exists() {
  local script="$1"
  if [[ -f "$script" ]]; then
    echo "RUN $script"
    python3 "$script"
  else
    echo "SKIP missing $script"
  fi
}

# Release / upgrade gates
run_if_exists scripts/validate_release_readiness.py
run_if_exists scripts/validate_release_changelog.py
run_if_exists scripts/validate_system_version_info.py
run_if_exists scripts/validate_feature_flags.py
run_if_exists scripts/validate_ops_dashboard.py

# Database / Alembic static gates. These must not connect to production DB.
run_if_exists scripts/validate_alembic_setup.py
run_if_exists scripts/validate_emr_import_execution_result_model.py

# EMR import safety gates
run_if_exists scripts/validate_emr_import_execute_create_only.py
run_if_exists scripts/validate_emr_import_execution_dry_run.py
run_if_exists scripts/validate_emr_import_clinical_approval_api.py
run_if_exists scripts/validate_emr_import_batch_planning_api.py
run_if_exists scripts/validate_emr_import_batch_planning_ui.py
run_if_exists scripts/validate_webhook_inbox_review_action.py
run_if_exists scripts/validate_webhook_inbox_review_api.py
run_if_exists scripts/validate_webhook_inbox_ui.py
run_if_exists scripts/validate_emr_webhook_dry_run.py
run_if_exists scripts/validate_emr_webhook_receipt_persistence.py
run_if_exists scripts/validate_emr_case_mapping_dry_run.py

# KPI / audit / legacy migration gates
run_if_exists scripts/validate_kpi_data_models.py
run_if_exists scripts/validate_kpi_api.py
run_if_exists scripts/validate_kpi_dashboard_frontend.py
run_if_exists scripts/validate_audit_log_model.py
run_if_exists scripts/validate_audit_log_api.py
run_if_exists scripts/validate_ai_review_audit_ui.py
run_if_exists scripts/validate_webhook_inbox_model.py
run_if_exists scripts/validate_emr_import_batch_model.py

echo "RUN Python syntax compilation"
python3 - <<'PY'
from pathlib import Path
import py_compile
import sys

roots = [
    Path("backend"),
    Path("scripts"),
]
exclude_names = {
    "__pycache__",
}
targets = []
for root in roots:
    if not root.exists():
        continue
    for path in root.rglob("*.py"):
        if any(part in exclude_names for part in path.parts):
            continue
        targets.append(path)

errors = []
for path in sorted(targets):
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        errors.append(f"{path}: {exc}")

if errors:
    print("Python compile failures:")
    for item in errors:
        print("  " + item)
    sys.exit(1)

print(f"Compiled {len(targets)} Python files")
PY

echo "CI static checks PASS"
