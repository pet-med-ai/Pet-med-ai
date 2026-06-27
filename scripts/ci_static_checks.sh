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
run_if_exists scripts/validate_commercial_launch_access_review.py
run_if_exists scripts/validate_commercial_launch_monitoring_alerting_plan.py
run_if_exists scripts/validate_commercial_launch_backup_restore_drill_v2.py
run_if_exists scripts/validate_commercial_launch_legal_consent_pack.py
run_if_exists scripts/validate_commercial_launch_final_go_no_go.py
run_if_exists scripts/validate_commercial_v1_post_go_stabilization.py

# Database / Alembic static gates. These must not connect to production DB.
run_if_exists scripts/validate_commercial_v1_first_clinic_pilot_weekly_review.py
run_if_exists scripts/validate_petmed_clinical_core_roadmap_refresh.py
run_if_exists scripts/validate_diagnostic_data_model_gap_review.py
run_if_exists scripts/validate_diagnostic_report_observation_imagingstudy_design.py
run_if_exists scripts/validate_diagnostic_data_model_migration_readiness_review.py
run_if_exists scripts/validate_diagnostic_data_model_migration.py
run_if_exists scripts/validate_diagnostic_data_model_post_migration_verification.py
run_if_exists scripts/validate_diagnostic_data_readonly_api_dry_run_fixtures.py
run_if_exists scripts/validate_lab_result_dry_run_fixture_parser.py
run_if_exists scripts/validate_imaging_metadata_dry_run_fixture_parser.py
run_if_exists scripts/validate_ai_lab_abnormal_summary.py
run_if_exists scripts/validate_ai_imaging_report_summary.py
run_if_exists scripts/validate_treatment_recommendation_boundary.py
run_if_exists scripts/validate_drug_dose_safety_framework.py
run_if_exists scripts/validate_drug_dose_knowledge_base.py
run_if_exists scripts/validate_clinician_review_workflow_for_diagnostic_summaries.py
run_if_exists scripts/validate_case_detail_diagnostic_data_display.py
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
# --- Diagnostic Assistance Problem List V1 static checks: start ---
echo "[ci_static_checks] Diagnostic Assistance Problem List V1 validator"
python3 scripts/validate_diagnostic_assistance_problem_list.py
# --- Diagnostic Assistance Problem List V1 static checks: end ---
# --- Differential Diagnosis Candidates V1 static checks: start ---
echo "[ci_static_checks] Differential Diagnosis Candidates V1 validator"
python3 scripts/validate_differential_diagnosis_candidates.py
# --- Differential Diagnosis Candidates V1 static checks: end ---
# --- Diagnostic Reasoning Evidence Trace V1 static checks: start ---
echo "[ci_static_checks] Diagnostic Reasoning Evidence Trace V1 validator"
python3 scripts/validate_diagnostic_reasoning_evidence_trace.py
# --- Diagnostic Reasoning Evidence Trace V1 static checks: end ---
# --- Diagnostic Assistance Case Detail UI V1 static checks: start ---
echo "[ci_static_checks] Diagnostic Assistance Case Detail UI V1 validator"
python3 scripts/validate_diagnostic_assistance_case_detail_ui.py
# --- Diagnostic Assistance Case Detail UI V1 static checks: end ---
# --- Clinician Review Persistence V1 static checks: start ---
echo "[ci_static_checks] Clinician Review Persistence V1 validator"
python3 scripts/validate_clinician_review_persistence.py
# --- Clinician Review Persistence V1 static checks: end ---

# --- Diagnostic Summary Audit Log V1 static checks: start ---
echo "[ci_static_checks] Diagnostic Summary Audit Log V1 validator"
python3 scripts/validate_diagnostic_summary_audit_log.py
# --- Diagnostic Summary Audit Log V1 static checks: end ---
# --- DiagnosticReport AI Summary Persistence V1 static checks: start ---
echo "[ci_static_checks] DiagnosticReport AI Summary Persistence V1 static checks"
python3 scripts/validate_diagnosticreport_ai_summary_persistence.py
# --- DiagnosticReport AI Summary Persistence V1 static checks: end ---
# --- Observation Abnormal Flag Review V1 static checks: start ---
echo "[ci_static_checks] Observation Abnormal Flag Review V1 static checks"
python3 scripts/validate_observation_abnormal_flag_review.py
# --- Observation Abnormal Flag Review V1 static checks: end ---
# --- ImagingStudy Review Workflow V1 static checks: start ---
echo "[ci_static_checks] ImagingStudy Review Workflow V1 static checks"
python3 scripts/validate_imagingstudy_review_workflow.py
# --- ImagingStudy Review Workflow V1 static checks: end ---

# --- Clinical Docs Diagnostic Data Merge V1 static checks: start ---
echo "[ci_static_checks] Clinical Docs Diagnostic Data Merge V1 static checks"
python3 scripts/validate_clinical_docs_diagnostic_data_merge.py
# --- Clinical Docs Diagnostic Data Merge V1 static checks: end ---

# --- Clinical QA Dashboard V2 static checks: start ---
echo "[ci_static_checks] Clinical QA Dashboard V2 static checks"
python3 scripts/validate_clinical_qa_dashboard_v2.py
# --- Clinical QA Dashboard V2 static checks: end ---
# --- Ops Dashboard Clinical Core V2 static checks: start ---
echo "[ci_static_checks] Ops Dashboard Clinical Core V2 static checks"
python3 scripts/validate_ops_dashboard_clinical_core_v2.py
# --- Ops Dashboard Clinical Core V2 static checks: end ---


# --- Exotics Knowledge Coverage Gap Review V1 static checks: start ---
echo "[ci_static_checks] Exotics Knowledge Coverage Gap Review V1 static checks"
python3 scripts/validate_exotics_knowledge_coverage_gap_review.py
# --- Exotics Knowledge Coverage Gap Review V1 static checks: end ---
# --- Exotics Rabbit Deepening V1 static checks: start ---
echo "[ci_static_checks] Exotics Rabbit Deepening V1 static checks"
python3 scripts/validate_exotics_rabbit_deepening.py
# --- Exotics Rabbit Deepening V1 static checks: end ---

# --- Exotics Avian Deepening V1 static checks: start ---
echo "[ci_static_checks] Exotics Avian Deepening V1 static checks"
python3 scripts/validate_exotics_avian_deepening.py
# --- Exotics Avian Deepening V1 static checks: end ---
# --- Exotics Reptile Split V1 static checks: start ---
echo "[ci_static_checks] Exotics Reptile Split V1 static checks"
python3 scripts/validate_exotics_reptile_split.py
# --- Exotics Reptile Split V1 static checks: end ---

# --- Exotics Small Mammal Split V1 static checks: start ---
echo "[ci_static_checks] Exotics Small Mammal Split V1 validator"
python3 scripts/validate_exotics_small_mammal_split.py
# --- Exotics Small Mammal Split V1 static checks: end ---

# --- Exotics Ferret Deepening V1 static checks: start ---
echo "[ci_static_checks] Exotics Ferret Deepening V1 validator"
python3 scripts/validate_exotics_ferret_deepening.py
# --- Exotics Ferret Deepening V1 static checks: end ---
# --- Exotics Lab / Imaging Interpretation Readiness V1 static checks: start ---
echo "[ci_static_checks] Exotics Lab / Imaging Interpretation Readiness V1 static checks"
python3 scripts/validate_exotics_lab_imaging_interpretation_readiness.py
# --- Exotics Lab / Imaging Interpretation Readiness V1 static checks: end ---
# --- Exotics Drug Dose Source Review Pack V1 static checks: start ---
echo "[ci_static_checks] Exotics Drug Dose Source Review Pack V1 static checks"
python3 scripts/validate_exotics_drug_dose_source_review_pack.py
# --- Exotics Drug Dose Source Review Pack V1 static checks: end ---
# --- Exotics Drug Dose Source Review Controlled Research V1 static checks: start ---
echo "[ci_static_checks] Exotics Drug Dose Source Review Controlled Research V1 static checks"
python3 scripts/validate_exotics_drug_dose_source_review_controlled_research.py
# --- Exotics Drug Dose Source Review Controlled Research V1 static checks: end ---

# --- Exotics Drug Dose Source Evidence Abstraction V1 static checks: start ---
echo "[ci_static_checks] Exotics Drug Dose Source Evidence Abstraction V1 static checks"
python3 scripts/validate_exotics_drug_dose_source_evidence_abstraction.py
# --- Exotics Drug Dose Source Evidence Abstraction V1 static checks: end ---
