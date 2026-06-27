# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

EXOTICS_DRUG_DOSE_SOURCE_EVIDENCE_ABSTRACTION_MODE = "exotics_drug_dose_source_evidence_abstraction_v1"
SPECIES_GROUPS = ['rabbit', 'bird', 'ferret', 'turtle', 'lizard', 'snake', 'amphibian', 'fish', 'guinea_pig', 'hamster', 'chinchilla', 'rat_mouse', 'hedgehog', 'sugar_glider']
REVIEW_DOMAINS = ['analgesia_and_pain_control_source_review', 'antimicrobial_source_review', 'antiparasitic_source_review', 'fluid_and_supportive_care_source_review', 'sedation_anesthesia_risk_source_review', 'emergency_stabilization_source_review']


def exotics_drug_dose_source_evidence_abstraction_safety_flags() -> Dict[str, Any]:
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
        "source_evidence_abstraction_only": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_species(value: Any) -> Optional[str]:
    key = _text(value).lower().replace("-", "_").replace(" ", "_")
    if key in SPECIES_GROUPS:
        return key
    aliases = {
        "avian": "bird",
        "chelonian": "turtle",
        "tortoise": "turtle",
        "terrapin": "turtle",
        "rat": "rat_mouse",
        "mouse": "rat_mouse",
        "mice": "rat_mouse",
        "sugar_glider": "sugar_glider",
        "glider": "sugar_glider",
    }
    return aliases.get(key)


def _normalize_domain(value: Any) -> Optional[str]:
    key = _text(value).lower().replace("-", "_").replace(" ", "_")
    if key in REVIEW_DOMAINS:
        return key
    return None


def build_source_evidence_abstraction_template(
    *,
    species_group: Optional[str] = None,
    review_domain: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a redacted abstraction template for source review.

    This template intentionally excludes any field for numeric amount,
    route text, frequency text, prescription directions, or treatment
    protocol content. It is for source-review workflow design only.
    """
    species = _normalize_species(species_group) if species_group else None
    domain = _normalize_domain(review_domain) if review_domain else None

    abstraction_fields = [
        {"field": "source_id", "allowed": True, "note": "internal source identifier only"},
        {"field": "source_type", "allowed": True, "note": "textbook, formulary, review, label, guideline, or peer-reviewed source"},
        {"field": "citation_metadata", "allowed": True, "note": "bibliographic metadata without usable dosing content"},
        {"field": "species_applicability", "allowed": True, "note": "species or taxonomic applicability"},
        {"field": "indication_category", "allowed": True, "note": "high-level use category only"},
        {"field": "evidence_strength_hint", "allowed": True, "note": "qualitative only; no numeric confidence"},
        {"field": "contraindication_theme", "allowed": True, "note": "qualitative safety theme"},
        {"field": "monitoring_theme", "allowed": True, "note": "qualitative monitoring theme"},
        {"field": "source_conflict_note", "allowed": True, "note": "whether sources conflict; no dosing details"},
        {"field": "numeric_amount", "allowed": False, "note": "blocked"},
        {"field": "route_text", "allowed": False, "note": "blocked"},
        {"field": "frequency_text", "allowed": False, "note": "blocked"},
        {"field": "prescription_direction", "allowed": False, "note": "blocked"},
        {"field": "treatment_protocol", "allowed": False, "note": "blocked"},
    ]

    safety = exotics_drug_dose_source_evidence_abstraction_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_EVIDENCE_ABSTRACTION_MODE,
        "current_level": "evidence_abstraction_template_only_not_dose_engine",
        "species_group": species,
        "review_domain": domain,
        "species_groups": SPECIES_GROUPS,
        "review_domains": REVIEW_DOMAINS,
        "abstraction_fields": abstraction_fields,
        "quality_gate": {
            "status": "PASS",
            "is_dose_engine": False,
            "is_prescription_engine": False,
            "dose_output_enabled": False,
            "captures_numeric_dose_value": False,
            "captures_route_or_frequency_text": False,
            "source_review_status": "evidence_abstraction_protocol_ready_not_started",
            "drug_dose_status": "not_reviewed_not_enabled",
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "safety": safety,
        **safety,
    }


def build_source_evidence_abstraction_matrix() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species in SPECIES_GROUPS:
        for domain in REVIEW_DOMAINS:
            rows.append({
                "species_group": species,
                "review_domain": domain,
                "abstraction_stage": "metadata_and_safety_theme_only",
                "citation_metadata_allowed": True,
                "species_applicability_allowed": True,
                "indication_category_allowed": True,
                "evidence_strength_hint_allowed": True,
                "contraindication_theme_allowed": True,
                "monitoring_theme_allowed": True,
                "numeric_dose_value_allowed": False,
                "route_text_allowed": False,
                "frequency_text_allowed": False,
                "prescription_direction_allowed": False,
                "treatment_protocol_allowed": False,
                "human_review_required": True,
                "source_review_status": "not_started",
            })
    return rows
