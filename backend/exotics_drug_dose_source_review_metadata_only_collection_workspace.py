# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_MODE = "exotics_drug_dose_source_review_metadata_only_collection_workspace_v1"

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

WORKSPACE_COLUMNS = [
    "workspace_id",
    "species_group",
    "review_domain",
    "workspace_scope",
    "workspace_status",
    "metadata_only_policy",
    "source_collection_execution_status",
    "named_collector_required",
    "second_reviewer_required",
    "source_access_required",
    "copyright_access_required",
    "value_capture_blocker_status",
    "numeric_value_capture_status",
    "route_frequency_capture_status",
    "usable_medication_instruction_status",
    "deidentification_required",
    "human_review_required",
    "clinician_signoff_required",
    "go_no_go_status",
    "notes",
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


def metadata_only_collection_workspace_safety_flags() -> Dict[str, Any]:
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
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "workspace_allows_numeric_values": False,
        "workspace_allows_route_frequency": False,
        "workspace_allows_medication_instruction": False,
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


def build_metadata_only_collection_workspace_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            workspace_id = "workspace:%s:%s" % (species_group, review_domain)
            rows.append({
                "workspace_id": workspace_id,
                "species_group": species_group,
                "review_domain": review_domain,
                "workspace_scope": "exotics_drug_dose_source_review_metadata_only",
                "workspace_status": "defined_not_populated",
                "metadata_only_policy": "metadata_only_no_medication_values",
                "source_collection_execution_status": "not_started",
                "named_collector_required": True,
                "second_reviewer_required": True,
                "source_access_required": True,
                "copyright_access_required": True,
                "value_capture_blocker_status": "required_enabled_before_use",
                "numeric_value_capture_status": "blocked",
                "route_frequency_capture_status": "blocked",
                "usable_medication_instruction_status": "blocked",
                "deidentification_required": True,
                "human_review_required": True,
                "clinician_signoff_required": True,
                "go_no_go_status": "NO_GO_TO_SOURCE_COLLECTION_EXECUTION",
                "notes": "workspace shell only; metadata may be collected later only after governance signoff; no dose, route, frequency, prescription, or treatment protocol",
            })
    return rows


def build_metadata_only_collection_workspace_summary() -> Dict[str, Any]:
    rows = build_metadata_only_collection_workspace_matrix()
    safety = metadata_only_collection_workspace_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_MODE,
        "current_level": "metadata_only_collection_workspace_schema_only_not_execution",
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "source_review_status": "metadata_only_workspace_defined_not_populated",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "workspace_row_count": len(rows),
        "workspace_columns": WORKSPACE_COLUMNS,
        "forbidden_fields": FORBIDDEN_FIELDS,
        "quality_gate": {
            "status": "PASS",
            "metadata_only": True,
            "go_no_go_status": "NO_GO_TO_SOURCE_COLLECTION_EXECUTION",
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
    summary = build_metadata_only_collection_workspace_summary()
    print("%s rows=%s status=%s" % (
        summary["mode"],
        summary["workspace_row_count"],
        summary["quality_gate"]["status"],
    ))
