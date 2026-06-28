# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_FINAL_GO_NO_GO_MODE = "exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report_final_go_no_go_v1"

SPECIES_GROUPS = ['rabbit', 'bird', 'ferret', 'turtle', 'lizard', 'snake', 'amphibian', 'fish', 'guinea_pig', 'hamster', 'chinchilla', 'rat_mouse', 'hedgehog', 'sugar_glider']

REVIEW_DOMAINS = ['analgesia_and_pain_control_source_review', 'antimicrobial_source_review', 'antiparasitic_source_review', 'fluid_and_supportive_care_source_review', 'sedation_anesthesia_risk_source_review', 'emergency_stabilization_source_review']

ALLOWED_FINAL_GO_NO_GO_FIELDS = [
    "activation_final_go_no_go_id",
    "species_group",
    "review_domain",
    "final_go_no_go_scope",
    "readiness_report_status",
    "activation_readiness_status",
    "clinical_owner_activation_status",
    "second_reviewer_activation_status",
    "source_access_activation_status",
    "copyright_access_activation_status",
    "metadata_only_workspace_status",
    "metadata_only_validation_status",
    "forbidden_value_scanner_status",
    "pilot_sample_limit_status",
    "halt_rule_status",
    "final_go_no_go_status",
    "governance_decision",
    "collection_activation_status",
    "collection_execution_status",
    "human_review_required",
    "clinician_signoff_required",
    "next_required_stage",
]

FORBIDDEN_VALUE_FIELDS = ['numeric_dose_value', 'dose_unit', 'route_text', 'frequency_text', 'duration_text', 'prescription_direction', 'treatment_protocol', 'client_instruction', 'copied_table_text', 'copyrighted_full_text']


def activation_readiness_report_final_go_no_go_safety_flags() -> Dict[str, Any]:
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
        "starts_source_collection_activation": False,
        "starts_source_collection_execution": False,
        "collection_activation_allowed_now": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "pilot_execution_allowed_now": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "dose_output_enabled": False,
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
        "downloads_attachments": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def build_activation_readiness_report_final_go_no_go_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "activation_final_go_no_go_id": "activation-final-go-no-go:%s:%s" % (species_group, review_domain),
                "species_group": species_group,
                "review_domain": review_domain,
                "final_go_no_go_scope": "metadata_only_source_collection_activation_readiness_report_final_go_no_go",
                "readiness_report_status": "report_shell_defined_no_collection_results",
                "activation_readiness_status": "defined_not_passed",
                "clinical_owner_activation_status": "required_not_completed",
                "second_reviewer_activation_status": "required_not_completed",
                "source_access_activation_status": "required_not_verified",
                "copyright_access_activation_status": "required_not_verified",
                "metadata_only_workspace_status": "defined_not_populated",
                "metadata_only_validation_status": "defined_not_executed",
                "forbidden_value_scanner_status": "required_before_activation",
                "pilot_sample_limit_status": "required_before_activation",
                "halt_rule_status": "required_before_activation",
                "final_go_no_go_status": "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
                "governance_decision": "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
                "collection_activation_status": "not_started_not_allowed",
                "collection_execution_status": "not_started_not_allowed",
                "human_review_required": True,
                "clinician_signoff_required": True,
                "next_required_stage": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_V1",
            })
    return rows


def build_activation_readiness_report_final_go_no_go() -> Dict[str, Any]:
    matrix = build_activation_readiness_report_final_go_no_go_matrix()
    safety = activation_readiness_report_final_go_no_go_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_FINAL_GO_NO_GO_MODE,
        "current_level": "metadata_only_source_collection_activation_readiness_report_final_go_no_go_schema_only_not_activation",
        "source_review_status": "metadata_only_source_collection_activation_readiness_report_final_go_no_go_defined_no_activation",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "activation_readiness_defined": True,
        "activation_readiness_passed": False,
        "activation_readiness_report_defined": True,
        "activation_readiness_report_has_collection_results": False,
        "activation_readiness_report_final_go_no_go_defined": True,
        "activation_readiness_report_final_go_no_go_decision": "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
        "collection_activation_allowed_now": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "pilot_execution_allowed_now": False,
        "governance_decision": "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "matrix_row_count": len(matrix),
        "allowed_final_go_no_go_fields": list(ALLOWED_FINAL_GO_NO_GO_FIELDS),
        "forbidden_value_fields": list(FORBIDDEN_VALUE_FIELDS),
        "matrix": matrix,
        "quality_gate": {
            "status": "PASS",
            "matrix_complete": len(matrix) == len(SPECIES_GROUPS) * len(REVIEW_DOMAINS),
            "no_numeric_dose_capture": True,
            "no_route_or_frequency_capture": True,
            "no_usable_medication_instruction": True,
            "no_collection_activation": True,
            "no_collection_execution": True,
            "governance_decision": "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION",
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "safety": safety,
        **safety,
    }
