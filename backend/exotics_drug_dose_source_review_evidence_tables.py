# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_MODE = "exotics_drug_dose_source_review_evidence_tables_v1"
SPECIES_GROUPS = ['rabbit', 'bird', 'ferret', 'turtle', 'lizard', 'snake', 'amphibian', 'fish', 'guinea_pig', 'hamster', 'chinchilla', 'rat_mouse', 'hedgehog', 'sugar_glider']
REVIEW_DOMAINS = ['analgesia_and_pain_control_source_review', 'antimicrobial_source_review', 'antiparasitic_source_review', 'fluid_and_supportive_care_source_review', 'sedation_anesthesia_risk_source_review', 'emergency_stabilization_source_review']
ALLOWED_EVIDENCE_TABLE_COLUMNS = ['table_id', 'species_group', 'review_domain', 'source_id', 'source_type', 'citation_key', 'citation_metadata_status', 'species_applicability_note', 'indication_category', 'evidence_strength_hint', 'contraindication_theme', 'monitoring_theme', 'source_conflict_note', 'reviewer_initials', 'review_status']
BLOCKED_EVIDENCE_TABLE_COLUMNS = ['numeric_dose_value', 'dose_unit', 'route_text', 'frequency_text', 'duration_text', 'prescription_direction', 'treatment_protocol', 'client_instruction']


def exotics_drug_dose_source_review_evidence_tables_safety_flags() -> Dict[str, Any]:
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
        "creates_audit_log": False,
        "final_diagnosis": False,
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
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
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
        "source_review_evidence_tables_only": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _normalize_species(value: Any) -> Optional[str]:
    key = _normalize(value)
    aliases = {
        "avian": "bird",
        "chelonian": "turtle",
        "tortoise": "turtle",
        "terrapin": "turtle",
        "rat": "rat_mouse",
        "mouse": "rat_mouse",
        "mice": "rat_mouse",
        "glider": "sugar_glider",
    }
    key = aliases.get(key, key)
    return key if key in SPECIES_GROUPS else None


def _normalize_domain(value: Any) -> Optional[str]:
    key = _normalize(value)
    return key if key in REVIEW_DOMAINS else None


def table_id_for(species_group: str, review_domain: str) -> str:
    species = _normalize_species(species_group)
    domain = _normalize_domain(review_domain)
    if not species:
        raise ValueError("unsupported species_group")
    if not domain:
        raise ValueError("unsupported review_domain")
    return "exotics_evidence_table__%s__%s" % (species, domain)


def build_evidence_table_schema(
    *,
    species_group: Optional[str] = None,
    review_domain: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a metadata-only evidence-table schema.

    The schema intentionally excludes all columns that could store usable
    medication amount, route, frequency, duration, prescription direction,
    client instruction, or treatment protocol content.
    """
    species = _normalize_species(species_group) if species_group else None
    domain = _normalize_domain(review_domain) if review_domain else None
    table_id = table_id_for(species, domain) if species and domain else None
    safety = exotics_drug_dose_source_review_evidence_tables_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_MODE,
        "current_level": "evidence_tables_schema_only_not_dose_engine",
        "table_id": table_id,
        "species_group": species,
        "review_domain": domain,
        "allowed_columns": ALLOWED_EVIDENCE_TABLE_COLUMNS,
        "blocked_columns": BLOCKED_EVIDENCE_TABLE_COLUMNS,
        "evidence_rows_status": "not_started",
        "stores_source_metadata_only": True,
        "stores_usable_dose_content": False,
        "quality_gate": {
            "status": "PASS",
            "is_dose_engine": False,
            "is_prescription_engine": False,
            "dose_output_enabled": False,
            "captures_numeric_dose_value": False,
            "captures_route_or_frequency_text": False,
            "source_review_status": "evidence_tables_schema_ready_not_started",
            "drug_dose_status": "not_reviewed_not_enabled",
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "safety": safety,
        **safety,
    }


def build_evidence_table_manifest() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species in SPECIES_GROUPS:
        for domain in REVIEW_DOMAINS:
            rows.append({
                "table_id": table_id_for(species, domain),
                "species_group": species,
                "review_domain": domain,
                "table_status": "schema_only_no_evidence_rows",
                "source_rows_allowed": True,
                "citation_metadata_required": True,
                "species_applicability_required": True,
                "indication_category_required": True,
                "qualitative_evidence_strength_only": True,
                "contraindication_theme_required": True,
                "monitoring_theme_required": True,
                "source_conflict_review_required": True,
                "numeric_dose_value_column_present": False,
                "route_text_column_present": False,
                "frequency_text_column_present": False,
                "prescription_direction_column_present": False,
                "treatment_protocol_column_present": False,
                "human_review_required": True,
            })
    return rows
