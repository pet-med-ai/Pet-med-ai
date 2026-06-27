# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_MODE = "exotics_drug_dose_source_review_source_collection_governance_go_no_go_v1"

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

REQUIRED_GOVERNANCE_GATES = [
    "named_collector_assigned",
    "second_reviewer_assigned",
    "source_access_verified",
    "copyright_access_verified",
    "metadata_only_workspace_ready",
    "value_capture_blocker_enabled",
    "human_review_required",
    "clinician_signoff_required",
    "no_client_facing_use",
]

FORBIDDEN_FIELDS = [
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


def governance_go_no_go_safety_flags() -> Dict[str, Any]:
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
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "source_collection_execution_started": False,
        "source_collection_execution_allowed_now": False,
        "pilot_execution_allowed_now": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "downloads_attachments": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "client_facing": False,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def build_governance_go_no_go_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "species_group": species_group,
                "review_domain": review_domain,
                "go_no_go_gate": "source_collection_execution_governance",
                "governance_status": "defined_not_approved",
                "governance_decision": "NO_GO_TO_COLLECTION_EXECUTION",
                "required_gates": ";".join(REQUIRED_GOVERNANCE_GATES),
                "collection_execution_allowed": False,
                "numeric_value_capture_allowed": False,
                "route_frequency_capture_allowed": False,
                "usable_medication_instruction_allowed": False,
                "requires_human_review": True,
                "clinician_signoff_required": True,
                "notes": "metadata-only governance shell; no dose, route, frequency, prescription, or treatment protocol capture",
            })
    return rows


def build_governance_go_no_go_summary() -> Dict[str, Any]:
    rows = build_governance_go_no_go_matrix()
    safety = governance_go_no_go_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_MODE,
        "current_level": "source_collection_governance_go_no_go_only_not_execution",
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "source_review_status": "governance_go_no_go_defined_no_collection_execution",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "pilot_execution_allowed_now": False,
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "matrix_row_count": len(rows),
        "required_governance_gates": REQUIRED_GOVERNANCE_GATES,
        "forbidden_fields": FORBIDDEN_FIELDS,
        "quality_gate": {
            "status": "PASS",
            "go_no_go_status": "NO_GO_TO_COLLECTION_EXECUTION",
            "metadata_only": True,
            "blocks_numeric_dose_capture": True,
            "blocks_route_frequency_capture": True,
            "blocks_usable_medication_instruction": True,
            "blocks_collection_execution": True,
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "safety": safety,
        **safety,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_governance_go_no_go_summary(), ensure_ascii=False, indent=2))
