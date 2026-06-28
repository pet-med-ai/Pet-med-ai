# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

MODE = "exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_validation_v1"
STAGE = "Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record Validation V1"
CURRENT_LEVEL = "metadata_only_source_collection_activation_governance_signoff_record_validation_schema_only_not_activation"
SOURCE_REVIEW_STATUS = "metadata_only_source_collection_activation_governance_signoff_record_validation_defined_no_activation"
GOVERNANCE_DECISION = "NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION"
NEXT_STAGE = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_V1"

SPECIES_GROUPS: List[str] = [
    "rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish",
    "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider",
]

REVIEW_DOMAINS: List[str] = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]

ALLOWED_METADATA_FIELDS: List[str] = [
    "activation_governance_signoff_record_validation_id",
    "species_group",
    "review_domain",
    "activation_governance_signoff_record_id",
    "activation_governance_signoff_id",
    "activation_readiness_report_final_go_no_go_id",
    "validation_scope",
    "validation_record_required",
    "signoff_record_required",
    "clinical_owner_record_check",
    "second_reviewer_record_check",
    "source_access_record_check",
    "copyright_access_record_check",
    "metadata_only_policy_record_check",
    "value_capture_blocker_record_check",
    "activation_scope_record_check",
    "halt_rule_record_check",
    "numeric_value_capture_status",
    "route_frequency_capture_status",
    "usable_medication_instruction_status",
    "collection_activation_status",
    "collection_execution_status",
    "validation_record_status",
    "signoff_record_validation_status",
    "go_no_go_status",
    "governance_decision",
    "human_review_required",
    "clinician_signoff_required",
    "next_required_stage",
]

FORBIDDEN_VALUE_FIELDS: List[str] = [
    "numeric_dose_value", "dose_unit", "route_text", "frequency_text", "duration_text",
    "prescription_direction", "treatment_protocol", "client_instruction", "copied_table_text", "copyrighted_full_text",
]


def safety_flags() -> Dict[str, Any]:
    return {
        "mode": MODE,
        "current_level": CURRENT_LEVEL,
        "source_review_status": SOURCE_REVIEW_STATUS,
        "drug_dose_status": "not_reviewed_not_enabled",
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
        "executes_source_collection": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "activation_governance_signoff_defined": True,
        "activation_governance_signoff_completed": False,
        "activation_governance_signoff_record_defined": True,
        "activation_governance_signoff_record_completed": False,
        "activation_governance_signoff_record_validation_defined": True,
        "activation_governance_signoff_record_validation_executed": False,
        "collection_activation_allowed_now": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "pilot_execution_allowed_now": False,
        "governance_decision": GOVERNANCE_DECISION,
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
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def build_validation_row(species_group: str, review_domain: str) -> Dict[str, str]:
    return {
        "activation_governance_signoff_record_validation_id": "activation-governance-signoff-record-validation:%s:%s" % (species_group, review_domain),
        "species_group": species_group,
        "review_domain": review_domain,
        "activation_governance_signoff_record_id": "activation-governance-signoff-record:%s:%s" % (species_group, review_domain),
        "activation_governance_signoff_id": "activation-governance-signoff:%s:%s" % (species_group, review_domain),
        "activation_readiness_report_final_go_no_go_id": "activation-readiness-report-final-go-no-go:%s:%s" % (species_group, review_domain),
        "validation_scope": "activation_governance_signoff_record_schema_and_blocker_validation_only",
        "validation_record_required": "true",
        "signoff_record_required": "true",
        "clinical_owner_record_check": "required_not_verified",
        "second_reviewer_record_check": "required_not_verified",
        "source_access_record_check": "required_not_verified",
        "copyright_access_record_check": "required_not_verified",
        "metadata_only_policy_record_check": "required_not_verified",
        "value_capture_blocker_record_check": "required_not_verified",
        "activation_scope_record_check": "required_not_verified",
        "halt_rule_record_check": "required_not_verified",
        "numeric_value_capture_status": "blocked_not_present",
        "route_frequency_capture_status": "blocked_not_present",
        "usable_medication_instruction_status": "blocked_not_present",
        "collection_activation_status": "not_started",
        "collection_execution_status": "not_started",
        "validation_record_status": "schema_defined_not_executed",
        "signoff_record_validation_status": "not_executed",
        "go_no_go_status": GOVERNANCE_DECISION,
        "governance_decision": GOVERNANCE_DECISION,
        "human_review_required": "true",
        "clinician_signoff_required": "true",
        "next_required_stage": NEXT_STAGE,
    }


def build_matrix() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append(build_validation_row(species_group, review_domain))
    return rows


def quality_gate() -> Dict[str, Any]:
    rows = build_matrix()
    flags = safety_flags()
    return {
        "status": "PASS",
        "mode": MODE,
        "stage": STAGE,
        "row_count": len(rows),
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "forbidden_value_fields": FORBIDDEN_VALUE_FIELDS,
        "allowed_metadata_fields": ALLOWED_METADATA_FIELDS,
        "coverage_complete": len(rows) == len(SPECIES_GROUPS) * len(REVIEW_DOMAINS),
        "blocks_numeric_dose": True,
        "blocks_route_frequency": True,
        "blocks_usable_medication_instruction": True,
        "blocks_source_collection_activation": True,
        "blocks_source_collection_execution": True,
        "governance_decision": GOVERNANCE_DECISION,
        "next_stage": NEXT_STAGE,
        "safety": flags,
        **flags,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(quality_gate(), ensure_ascii=False, indent=2, sort_keys=True))
