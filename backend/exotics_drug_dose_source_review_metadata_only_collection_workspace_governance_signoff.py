# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_MODE = "exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_v1"

SPECIES_GROUPS = [
    "rabbit",
    "bird",
    "ferret",
    "turtle",
    "lizard",
    "snake",
    "amphibian",
    "fish",
    "guinea_pig",
    "hamster",
    "chinchilla",
    "rat_mouse",
    "hedgehog",
    "sugar_glider",
]

REVIEW_DOMAINS = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]

FORBIDDEN_COLUMNS = [
    "numeric_dose_value",
    "dose_unit",
    "route_text",
    "frequency_text",
    "duration_text",
    "prescription_direction",
    "treatment_protocol",
    "client_instruction",
    "copied_table_text",
    "copyrighted_full_text",
]

ALLOWED_METADATA_ONLY_FIELDS = [
    "governance_signoff_id",
    "species_group",
    "review_domain",
    "workspace_scope",
    "workspace_status",
    "workspace_validation_status",
    "validation_report_status",
    "named_clinical_owner_status",
    "second_reviewer_status",
    "source_access_status",
    "copyright_access_status",
    "metadata_only_policy",
    "value_capture_blocker_status",
    "collection_execution_status",
    "governance_signoff_status",
    "go_no_go_status",
    "human_review_required",
    "clinician_signoff_required",
    "next_required_stage",
]


def safety_flags() -> Dict[str, Any]:
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
        "writes_audit_log": False,
        "creates_audit_log": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "metadata_only_workspace_validation_defined": True,
        "metadata_only_workspace_validation_executed": False,
        "metadata_only_workspace_validation_report_defined": True,
        "metadata_only_workspace_validation_report_has_collection_results": False,
        "governance_signoff_defined": True,
        "governance_signoff_completed": False,
        "source_review_status": "metadata_only_workspace_governance_signoff_defined_no_collection_execution",
        "drug_dose_status": "not_reviewed_not_enabled",
        "governance_decision": "NO_GO_TO_COLLECTION_EXECUTION",
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
    }


def build_governance_signoff_matrix() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "governance_signoff_id": "gov-signoff-%s-%s" % (species_group, review_domain),
                "species_group": species_group,
                "review_domain": review_domain,
                "workspace_scope": "metadata_only_source_review_workspace",
                "workspace_status": "defined_not_populated",
                "workspace_validation_status": "defined_not_executed",
                "validation_report_status": "defined_no_collection_results",
                "named_clinical_owner_status": "required_not_assigned",
                "second_reviewer_status": "required_not_assigned",
                "source_access_status": "required_not_verified",
                "copyright_access_status": "required_not_verified",
                "metadata_only_policy": "metadata_only_no_medication_values",
                "value_capture_blocker_status": "enabled_forbidden_value_columns_absent",
                "collection_execution_status": "not_started_not_allowed",
                "governance_signoff_status": "defined_not_signed",
                "go_no_go_status": "NO_GO_TO_COLLECTION_EXECUTION",
                "human_review_required": "true",
                "clinician_signoff_required": "true",
                "next_required_stage": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_V1",
            })
    return rows


def summarize_governance_signoff() -> Dict[str, Any]:
    rows = build_governance_signoff_matrix()
    flags = safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_MODE,
        "current_level": "metadata_only_workspace_governance_signoff_schema_only_not_collection_execution",
        "matrix_rows": len(rows),
        "species_groups": list(SPECIES_GROUPS),
        "review_domains": list(REVIEW_DOMAINS),
        "allowed_metadata_only_fields": list(ALLOWED_METADATA_ONLY_FIELDS),
        "forbidden_columns": list(FORBIDDEN_COLUMNS),
        "governance_decision": "NO_GO_TO_COLLECTION_EXECUTION",
        "source_review_status": "metadata_only_workspace_governance_signoff_defined_no_collection_execution",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "metadata_only_workspace_validation_defined": True,
        "metadata_only_workspace_validation_executed": False,
        "metadata_only_workspace_validation_report_defined": True,
        "metadata_only_workspace_validation_report_has_collection_results": False,
        "governance_signoff_defined": True,
        "governance_signoff_completed": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "safety": flags,
        **flags,
    }
