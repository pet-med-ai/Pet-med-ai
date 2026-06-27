# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_MODE = "exotics_drug_dose_source_review_source_collection_protocol_v1"

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

ALLOWED_COLLECTION_FIELDS: List[str] = [
    "source_collection_id",
    "species_group",
    "review_domain",
    "source_type",
    "source_locator",
    "citation_key",
    "publication_or_edition_metadata",
    "retrieval_status",
    "copyright_access_status",
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

FORBIDDEN_COLLECTION_FIELDS: List[str] = [
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

_DANGEROUS_VALUE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b)",
    re.IGNORECASE,
)


def exotics_drug_dose_source_review_source_collection_protocol_safety_flags() -> Dict[str, Any]:
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
        "source_collection_protocol_only": True,
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


def build_source_collection_protocol_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "protocol_id": "exotics_source_collection_%s_%s" % (species_group, review_domain),
                "species_group": species_group,
                "review_domain": review_domain,
                "collection_scope": "source_metadata_collection_protocol_only",
                "allowed_source_types": list(SOURCE_TYPES),
                "required_metadata": [
                    "source_locator",
                    "citation_key",
                    "source_type",
                    "publication_or_edition_metadata",
                    "species_applicability_note",
                    "retrieval_status",
                    "copyright_access_status",
                    "reviewer_initials",
                ],
                "forbidden_capture": list(FORBIDDEN_COLLECTION_FIELDS),
                "collection_controls": [
                    "metadata_only",
                    "human_review_required",
                    "second_review_required",
                    "copyright_safe_summary_only",
                    "no_medication_instruction_capture",
                ],
                "source_collection_status": "protocol_defined_not_started",
                "evidence_abstraction_ready": False,
                "dose_output_enabled": False,
                "captures_numeric_dose_value": False,
                "captures_route_or_frequency_text": False,
                "prescription_instruction_allowed": False,
                "client_facing_allowed": False,
                "next_action": "collect_source_metadata_without_dose_route_frequency_or_full_text",
            })
    return rows


def _walk_values(value: Any) -> List[str]:
    values: List[str] = []
    if isinstance(value, dict):
        for item in value.values():
            values.extend(_walk_values(item))
    elif isinstance(value, list):
        for item in value[:100]:
            values.extend(_walk_values(item))
    elif isinstance(value, str):
        values.append(value)
    return values


def validate_source_collection_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("record must be an object")

    forbidden_present = sorted(set(record.keys()).intersection(FORBIDDEN_COLLECTION_FIELDS))
    if forbidden_present:
        raise ValueError("source collection record contains forbidden medication-instruction fields: %s" % ", ".join(forbidden_present))

    for text in _walk_values(record):
        if _DANGEROUS_VALUE_PATTERN.search(text):
            raise ValueError("source collection record contains numeric medication amount or frequency text")

    species_group = str(record.get("species_group") or "").strip()
    review_domain = str(record.get("review_domain") or "").strip()
    source_type = str(record.get("source_type") or "").strip()

    if species_group and species_group not in SPECIES_GROUPS:
        raise ValueError("unsupported species_group for exotics source collection protocol")
    if review_domain and review_domain not in REVIEW_DOMAINS:
        raise ValueError("unsupported review_domain for exotics source collection protocol")
    if source_type and source_type not in SOURCE_TYPES:
        raise ValueError("unsupported source_type for exotics source collection protocol")

    return {
        "record_valid_for_protocol": True,
        "metadata_only": True,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def build_source_collection_protocol_review() -> Dict[str, Any]:
    safety = exotics_drug_dose_source_review_source_collection_protocol_safety_flags()
    matrix = build_source_collection_protocol_matrix()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_MODE,
        "current_level": "source_collection_protocol_only_not_dose_engine",
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "protocol_row_count": len(matrix),
        "matrix": matrix,
        "allowed_collection_fields": list(ALLOWED_COLLECTION_FIELDS),
        "forbidden_collection_fields": list(FORBIDDEN_COLLECTION_FIELDS),
        "source_review_status": "source_collection_protocol_ready_not_started",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "quality_gate": {
            "status": "PASS",
            "decision": "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_V1",
            "matrix_present": True,
            "protocol_only": True,
            "blocks_numeric_dose_capture": True,
            "blocks_route_frequency_capture": True,
            "blocks_prescription_instruction_capture": True,
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "safety": safety,
        **safety,
    }
