# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_MODE = "exotics_drug_dose_source_review_source_collection_execution_controlled_pilot_v1"

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

CONTROLLED_PILOT_DECISION = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_V1"

PROHIBITED_CAPTURE_FIELDS = [
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

ALLOWED_METADATA_FIELDS = [
    "source_collection_id",
    "source_type",
    "source_locator",
    "citation_key",
    "publication_or_edition_metadata",
    "species_applicability_note",
    "indication_category",
    "contraindication_theme",
    "monitoring_theme",
    "source_conflict_note",
    "reviewer_initials",
    "second_reviewer_required",
    "collection_status",
    "abstraction_ready_without_values",
]


def exotics_source_collection_execution_controlled_pilot_safety_flags() -> Dict[str, Any]:
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
        "pilot_execution_allowed_now": False,
        "collection_execution_started": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "downloads_attachments": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "not_client_facing": True,
    }


def _pilot_row(species_group: str, review_domain: str) -> Dict[str, Any]:
    return {
        "controlled_pilot_id": "pilot-%s-%s" % (species_group.replace("_", "-"), review_domain.replace("_", "-")),
        "species_group": species_group,
        "review_domain": review_domain,
        "execution_readiness_reference": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_V1",
        "source_collection_protocol_reference": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1",
        "source_registry_reference": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_V1",
        "evidence_table_reference": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_V1",
        "pilot_scope": "manual_metadata_only_source_collection_shell",
        "pilot_batch_status": "planned_not_started",
        "collector_assignment_status": "required_before_start",
        "second_reviewer_status": "required_before_start",
        "source_access_status": "required_before_start",
        "copyright_access_status": "required_before_start",
        "workspace_status": "metadata_only_workspace_required_before_start",
        "allowed_metadata_fields": list(ALLOWED_METADATA_FIELDS),
        "prohibited_capture_fields": list(PROHIBITED_CAPTURE_FIELDS),
        "dose_output_enabled": False,
        "route_or_frequency_capture_enabled": False,
        "stores_usable_medication_instruction": False,
        "pilot_execution_allowed_now": False,
        "go_no_go": "NO_GO_FOR_REAL_COLLECTION_UNTIL_REVIEWERS_ACCESS_WORKSPACE_AND_COPYRIGHT_ARE_APPROVED",
    }


def build_exotics_source_collection_execution_controlled_pilot() -> Dict[str, Any]:
    pilot_rows: List[Dict[str, Any]] = [
        _pilot_row(species_group, review_domain)
        for species_group in SPECIES_GROUPS
        for review_domain in REVIEW_DOMAINS
    ]
    safety = exotics_source_collection_execution_controlled_pilot_safety_flags()
    summary = {
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "controlled_pilot_row_count": len(pilot_rows),
        "pilot_batch_status": "planned_not_started",
        "pilot_execution_allowed_now": False,
        "collection_execution_started": False,
        "metadata_only_collection_policy": True,
        "source_collection_values_allowed": False,
        "current_level": "controlled_pilot_shell_only_not_collection_execution",
        "source_review_status": "controlled_pilot_shell_ready_not_started",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
    }
    quality_gate = {
        "status": "PASS",
        "decision": CONTROLLED_PILOT_DECISION,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "blocks_dose_engine": True,
        "blocks_prescription_engine": True,
        "blocks_treatment_plan_engine": True,
        "blocks_numeric_dose_capture": True,
        "blocks_route_frequency_capture": True,
        "blocks_client_facing_output": True,
        "blocks_collection_execution_until_go_no_go": True,
    }
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_MODE,
        "summary": summary,
        "controlled_pilot_rows": pilot_rows,
        "allowed_metadata_fields": list(ALLOWED_METADATA_FIELDS),
        "prohibited_capture_fields": list(PROHIBITED_CAPTURE_FIELDS),
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
