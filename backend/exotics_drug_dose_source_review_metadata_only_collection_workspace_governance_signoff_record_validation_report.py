# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_MODE = "exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report_v1"
CURRENT_LEVEL = "metadata_only_workspace_governance_signoff_record_validation_report_schema_only_not_collection_execution"
SOURCE_REVIEW_STATUS = "metadata_only_workspace_governance_signoff_record_validation_report_defined_no_collection_results"
GOVERNANCE_DECISION = "NO_GO_TO_COLLECTION_EXECUTION"
NEXT_DECISION = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_V1"

SPECIES_GROUPS = ["rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish", "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider"]
REVIEW_DOMAINS = ["analgesia_and_pain_control_source_review", "antimicrobial_source_review", "antiparasitic_source_review", "fluid_and_supportive_care_source_review", "sedation_anesthesia_risk_source_review", "emergency_stabilization_source_review"]
FORBIDDEN_SCHEMA_FIELDS = ["numeric_dose_value", "dose_unit", "route_text", "frequency_text", "duration_text", "prescription_direction", "treatment_protocol", "client_instruction", "copied_table_text", "copyrighted_full_text"]
REPORT_FIELDS = ["validation_report_id", "species_group", "review_domain", "record_validation_scope", "validation_report_status", "governance_signoff_record_status", "record_validation_status", "validation_execution_status", "validation_result_status", "numeric_value_capture_status", "route_frequency_capture_status", "usable_medication_instruction_status", "source_collection_execution_status", "go_no_go_status", "human_review_required", "clinician_signoff_required", "next_required_stage"]


def exotics_metadata_only_workspace_governance_signoff_record_validation_report_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": False,
        "creates_observation": False,
        "updates_observation": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "writes_abnormal_summary": False,
        "creates_audit_log": False,
        "writes_audit_log": False,
        "source_collection_execution": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "pilot_execution_allowed_now": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "generates_final_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "client_facing": False,
        "not_client_facing": True,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def build_governance_signoff_record_validation_report_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "validation_report_id": "governance_signoff_record_validation_report_v1:%s:%s" % (species_group, review_domain),
                "species_group": species_group,
                "review_domain": review_domain,
                "record_validation_scope": "metadata_only_governance_signoff_record_validation_report",
                "validation_report_status": "shell_defined_no_collection_results",
                "governance_signoff_record_status": "defined_not_completed",
                "record_validation_status": "defined_not_executed",
                "validation_execution_status": "not_executed",
                "validation_result_status": "no_collection_results",
                "numeric_value_capture_status": "blocked",
                "route_frequency_capture_status": "blocked",
                "usable_medication_instruction_status": "blocked",
                "source_collection_execution_status": "not_started",
                "go_no_go_status": GOVERNANCE_DECISION,
                "human_review_required": True,
                "clinician_signoff_required": True,
                "next_required_stage": NEXT_DECISION,
            })
    return rows


def build_governance_signoff_record_validation_report() -> Dict[str, Any]:
    matrix = build_governance_signoff_record_validation_report_matrix()
    safety = exotics_metadata_only_workspace_governance_signoff_record_validation_report_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_MODE,
        "current_level": CURRENT_LEVEL,
        "source_review_status": SOURCE_REVIEW_STATUS,
        "drug_dose_status": "not_reviewed_not_enabled",
        "governance_decision": GOVERNANCE_DECISION,
        "next_decision": NEXT_DECISION,
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "matrix_row_count": len(matrix),
        "report_fields": list(REPORT_FIELDS),
        "forbidden_schema_fields": list(FORBIDDEN_SCHEMA_FIELDS),
        "matrix": matrix,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "metadata_only_workspace_validation_defined": True,
        "metadata_only_workspace_validation_executed": False,
        "metadata_only_workspace_validation_report_defined": True,
        "metadata_only_workspace_validation_report_has_collection_results": False,
        "governance_signoff_defined": True,
        "governance_signoff_completed": False,
        "governance_signoff_record_defined": True,
        "governance_signoff_record_completed": False,
        "governance_signoff_record_validation_defined": True,
        "governance_signoff_record_validation_executed": False,
        "governance_signoff_record_validation_report_defined": True,
        "governance_signoff_record_validation_report_has_collection_results": False,
        "quality_gate": {
            "status": "PASS",
            "governance_decision": GOVERNANCE_DECISION,
            "collection_execution_allowed_now": False,
            "dose_output_enabled": False,
            "captures_numeric_dose_value": False,
            "captures_route_or_frequency_text": False,
            "stores_usable_medication_instruction": False,
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "safety": safety,
        **safety,
    }
