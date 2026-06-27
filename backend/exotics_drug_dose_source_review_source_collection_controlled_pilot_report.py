# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_MODE = (
    "exotics_drug_dose_source_review_source_collection_controlled_pilot_report_v1"
)

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

FORBIDDEN_EVIDENCE_COLUMNS = [
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


def exotics_drug_dose_source_review_source_collection_controlled_pilot_report_safety_flags() -> Dict[str, Any]:
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
        "generates_final_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_treatment_plan": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "dose_output_enabled": False,
        "collection_execution_started": False,
        "pilot_execution_allowed_now": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
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


def build_source_collection_controlled_pilot_report_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "pilot_report_id": "pilot-report-%s-%s" % (species_group, review_domain),
                "species_group": species_group,
                "review_domain": review_domain,
                "pilot_scope_status": "controlled_pilot_shell_only",
                "source_collection_execution_status": "not_started",
                "source_registry_status": "schema_ready_not_populated",
                "evidence_table_status": "schema_ready_no_values",
                "collection_output_status": "metadata_only_report_shell",
                "collector_assignment_status": "required_before_execution",
                "second_reviewer_status": "required_before_execution",
                "source_access_status": "required_before_execution",
                "copyright_access_status": "required_before_execution",
                "value_capture_policy": "metadata_only_no_medication_values",
                "numeric_value_capture_status": "forbidden",
                "route_frequency_capture_status": "forbidden",
                "usable_medication_instruction_status": "forbidden",
                "report_status": "template_ready_no_collection_results",
                "go_no_go_status": "NO_GO_FOR_DOSE_ENGINE",
                "human_review_required": True,
                "clinician_signoff_required": True,
                "notes": "Controlled pilot report shell only; no source values, no medication instructions, no dose output.",
            })
    return rows


def build_source_collection_controlled_pilot_report() -> Dict[str, Any]:
    matrix = build_source_collection_controlled_pilot_report_matrix()
    safety = exotics_drug_dose_source_review_source_collection_controlled_pilot_report_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_MODE,
        "current_level": "controlled_pilot_report_shell_only_not_collection_execution",
        "source_review_status": "controlled_pilot_report_shell_ready_no_collection_results",
        "drug_dose_status": "not_reviewed_not_enabled",
        "pilot_report_matrix": matrix,
        "forbidden_evidence_columns": FORBIDDEN_EVIDENCE_COLUMNS,
        "quality_gate": {
            "status": "PASS",
            "matrix_rows": len(matrix),
            "species_group_count": len(SPECIES_GROUPS),
            "review_domain_count": len(REVIEW_DOMAINS),
            "collection_execution_started": False,
            "pilot_execution_allowed_now": False,
            "is_dose_engine": False,
            "is_prescription_engine": False,
            "is_treatment_plan_engine": False,
            "dose_output_enabled": False,
            "captures_numeric_dose_value": False,
            "captures_route_or_frequency_text": False,
            "stores_usable_medication_instruction": False,
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "decision": "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_V1",
        "safety": safety,
        **safety,
    }
