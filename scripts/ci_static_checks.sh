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
run_if_exists scripts/validate_commercial_launch_readiness.py
run_if_exists scripts/validate_commercial_launch_feature_scope_lock.py
run_if_exists scripts/validate_commercial_launch_ops_runbook.py

# Database / Alembic static gates. These must not connect to production DB.
run_if_exists scripts/validate_alembic_setup.py
run_if_exists scripts/validate_emr_import_execution_result_model.py

# EMR import safety gates
run_if_exists scripts/validate_emr_import_execute_create_only.py
run_if_exists scripts/validate_emr_import_pilot0_checklist.py
run_if_exists scripts/validate_emr_import_pilot0_dry_run_rehearsal.py
run_if_exists scripts/validate_emr_import_pilot0_rehearsal_report.py
run_if_exists scripts/validate_emr_import_pilot0_readiness_review.py
run_if_exists scripts/validate_security_hardening.py
run_if_exists scripts/validate_clinical_docs_export_spec.py
run_if_exists scripts/validate_clinical_docs_template_assets.py
run_if_exists scripts/validate_clinical_docs_export_api.py
run_if_exists scripts/validate_clinical_docs_export_ui.py
run_if_exists scripts/validate_clinical_docs_export_smoke.py
run_if_exists scripts/validate_clinical_docs_export_ui_online_verification.py
run_if_exists scripts/validate_clinical_docs_pdf_conversion_design.py
run_if_exists scripts/validate_preventive_care_reminder_spec.py
run_if_exists scripts/validate_preventive_care_reminder_model.py
run_if_exists scripts/validate_preventive_care_rule_engine_dry_run.py
run_if_exists scripts/validate_preventive_care_reminder_api.py
run_if_exists scripts/validate_preventive_care_notification_queue.py
run_if_exists scripts/validate_preventive_care_notification_queue_ui.py
run_if_exists scripts/validate_preventive_care_online_verification.py
run_if_exists scripts/validate_preventive_care_release_record.py
run_if_exists scripts/validate_preventive_care_ops_dashboard.py
run_if_exists scripts/validate_preventive_care_ops_dashboard_online_verification.py
run_if_exists scripts/validate_preventive_care_weekly_ops_runbook.py
run_if_exists scripts/validate_preventive_care_notification_queue_monthly_review.py
run_if_exists scripts/validate_automated_reminder_delivery_risk_review.py
run_if_exists scripts/validate_automated_reminder_delivery_design.py
run_if_exists scripts/validate_automated_reminder_delivery_model.py
run_if_exists scripts/validate_automated_reminder_delivery_eligibility_dry_run.py
run_if_exists scripts/validate_automated_reminder_delivery_template_registry.py
run_if_exists scripts/validate_automated_reminder_delivery_api_dry_run.py
run_if_exists scripts/validate_automated_reminder_delivery_manual_approval_ui.py
run_if_exists scripts/validate_automated_reminder_delivery_pilot_runbook.py
run_if_exists scripts/validate_preventive_care_reminder_ui.py
run_if_exists scripts/validate_emr_import_pilot0_final_go_no_go.py
run_if_exists scripts/validate_emr_import_pilot0_execution_window.py
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
import subprocess
import sys

try:
    result = subprocess.run(
        ["git", "ls-files", "backend", "scripts"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    targets = [
        Path(line.strip())
        for line in result.stdout.splitlines()
        if line.strip().endswith(".py")
    ]
except Exception as exc:
    print(f"git ls-files failed, falling back to tracked-safe rglob: {exc}")
    targets = []
    for root in (Path("backend"), Path("scripts")):
        if root.exists():
            for path in root.rglob("*.py"):
                if "__pycache__" not in path.parts:
                    targets.append(path)

errors = []
for path in sorted(set(targets)):
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        errors.append(f"{path}: {exc}")

if errors:
    print("Python compile failures:")
    for item in errors:
        print("  " + item)
    sys.exit(1)

print(f"Compiled {len(set(targets))} git-tracked Python files")
PY

echo "CI static checks PASS"
