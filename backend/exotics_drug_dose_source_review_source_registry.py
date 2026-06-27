# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_MODE = "exotics_drug_dose_source_review_source_registry_v1"

SPECIES_GROUPS: List[str] = [
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

REVIEW_DOMAINS: List[str] = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]

SOURCE_TYPES: List[str] = [
    "peer_reviewed_article_metadata_only",
    "exotics_textbook_metadata_only",
    "exotics_formulary_metadata_only",
    "specialty_conference_proceedings_metadata_only",
    "manufacturer_label_or_safety_sheet_metadata_only",
    "institutional_protocol_candidate_metadata_only",
    "expert_review_note_metadata_only",
]

ALLOWED_REGISTRY_FIELDS: List[str] = [
    "registry_id",
    "species_group",
    "review_domain",
    "source_type",
    "citation_key",
    "publication_or_edition_metadata",
    "species_applicability_note",
    "indication_category",
    "evidence_role",
    "evidence_strength_hint",
    "contraindication_theme",
    "monitoring_theme",
    "source_conflict_note",
    "reviewer_initials",
    "review_status",
]

FORBIDDEN_REGISTRY_FIELDS: List[str] = [
    "numeric_dose_value",
    "dose_unit",
    "route_text",
    "frequency_text",
    "duration_text",
    "prescription_direction",
    "treatment_protocol",
    "client_instruction",
]


def exotics_drug_dose_source_review_source_registry_safety_flags() -> Dict[str, Any]:
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
        "persists_reasoning_trace": False,
        "generates_final_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_treatment_plan": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "source_registry_only": True,
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


def build_source_registry_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "registry_id": "exotics_source_registry_%s_%s" % (species_group, review_domain),
                "species_group": species_group,
                "review_domain": review_domain,
                "registry_scope": "source_metadata_registry_only",
                "allowed_source_types": list(SOURCE_TYPES),
                "required_metadata": [
                    "citation_key",
                    "source_type",
                    "publication_or_edition_metadata",
                    "species_applicability_note",
                    "reviewer_initials",
                ],
                "review_controls": [
                    "human_review_required",
                    "second_review_required",
                    "conflict_check_required",
                    "no_medication_instruction_capture",
                ],
                "source_capture_status": "not_started",
                "dose_output_enabled": False,
                "captures_numeric_dose_value": False,
                "captures_route_or_frequency_text": False,
                "prescription_instruction_allowed": False,
                "review_status": "registry_slot_created_not_populated",
                "next_action": "collect_source_metadata_without_medication_instructions",
            })
    return rows


def build_source_registry_summary() -> Dict[str, Any]:
    matrix = build_source_registry_matrix()
    safety = exotics_drug_dose_source_review_source_registry_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_MODE,
        "current_level": "source_registry_schema_only_not_dose_engine",
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "source_type_count": len(SOURCE_TYPES),
        "registry_slot_count": len(matrix),
        "allowed_registry_fields": list(ALLOWED_REGISTRY_FIELDS),
        "forbidden_registry_fields": list(FORBIDDEN_REGISTRY_FIELDS),
        "source_review_status": "source_registry_schema_ready_not_populated",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "decision": "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1",
        "safety": safety,
        **safety,
    }
