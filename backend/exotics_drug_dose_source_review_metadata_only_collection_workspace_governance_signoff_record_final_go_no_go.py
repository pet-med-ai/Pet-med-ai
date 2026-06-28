# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

MODE = "exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_final_go_no_go_v1"
CURRENT_LEVEL = "metadata_only_workspace_governance_signoff_record_final_go_no_go_schema_only_not_collection_execution"
GOVERNANCE_DECISION = "NO_GO_TO_COLLECTION_EXECUTION"
NEXT_DECISION = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_V1"

SPECIES_GROUPS = [
    "rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish",
    "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider",
]

REVIEW_DOMAINS = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]

FORBIDDEN_CAPTURE_FIELDS = [
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


def safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
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
        "creates_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "client_facing": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def build_final_go_no_go_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "final_go_no_go_id": "final-go-no-go-%s-%s" % (species_group, review_domain),
                "species_group": species_group,
                "review_domain": review_domain,
                "governance_signoff_record_validation_report_status": "shell_defined_no_collection_results",
                "clinical_owner_status": "required_not_completed",
                "second_reviewer_status": "required_not_completed",
                "source_access_status": "required_not_completed",
                "copyright_access_status": "required_not_completed",
                "metadata_only_workspace_status": "defined_not_populated",
                "metadata_only_validation_status": "defined_not_executed",
                "forbidden_value_capture_status": "blocked",
                "collection_execution_started": False,
                "collection_execution_allowed_now": False,
                "pilot_execution_allowed_now": False,
                "dose_output_enabled": False,
                "governance_decision": GOVERNANCE_DECISION,
                "next_required_stage": NEXT_DECISION,
                "human_review_required": True,
                "clinician_signoff_required": True,
            })
    return rows


def build_final_go_no_go_summary() -> Dict[str, Any]:
    matrix = build_final_go_no_go_matrix()
    safety = safety_flags()
    return {
        "mode": MODE,
        "current_level": CURRENT_LEVEL,
        "source_review_status": "metadata_only_workspace_governance_signoff_record_final_go_no_go_defined_no_collection_execution",
        "drug_dose_status": "not_reviewed_not_enabled",
        "governance_decision": GOVERNANCE_DECISION,
        "decision": NEXT_DECISION,
        "matrix_row_count": len(matrix),
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "forbidden_capture_fields": list(FORBIDDEN_CAPTURE_FIELDS),
        "matrix": matrix,
        "safety": safety,
        **safety,
    }
