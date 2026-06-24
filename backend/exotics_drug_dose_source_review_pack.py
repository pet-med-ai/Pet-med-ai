# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_MODE = "exotics_drug_dose_source_review_pack_v1"

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

REQUIRED_SOURCE_FIELDS: List[str] = [
    "source_title",
    "edition_or_revision_date",
    "author_or_organization",
    "species_scope",
    "drug_or_domain_scope",
    "contraindication_notes",
    "reviewer_id",
    "review_date",
    "review_status",
]


def exotics_drug_dose_source_review_pack_safety_flags() -> Dict[str, Any]:
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
        "dose_output_enabled": False,
        "drug_dose_recommendation": False,
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
        "source_review_required": True,
    }


def build_exotics_drug_dose_source_review_pack() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for domain in REVIEW_DOMAINS:
            rows.append({
                "species_group": species_group,
                "review_domain": domain,
                "source_review_status": "required_not_started",
                "source_pack_required": True,
                "dose_values_present": False,
                "dose_output_enabled": False,
                "clinician_review_required": True,
                "review_artifact_required_fields": list(REQUIRED_SOURCE_FIELDS),
            })

    quality_gate = {
        "status": "PASS",
        "decision": "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_V1",
        "matrix_row_count": len(rows),
        "source_review_status": "required_not_started",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "blocks_prescription_write": True,
        "blocks_treatment_plan": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    safety = exotics_drug_dose_source_review_pack_safety_flags()
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_MODE,
        "current_level": "source_review_pack_only_not_dose_engine",
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "species_groups": list(SPECIES_GROUPS),
        "review_domains": list(REVIEW_DOMAINS),
        "required_source_fields": list(REQUIRED_SOURCE_FIELDS),
        "matrix": rows,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }


def validate_exotics_drug_dose_source_review_pack() -> Dict[str, Any]:
    pack = build_exotics_drug_dose_source_review_pack()
    if pack["dose_output_enabled"] is not False:
        raise ValueError("dose output must remain disabled")
    if pack["returns_drug_dose"] is not False:
        raise ValueError("drug dose output must remain disabled")
    if not pack["matrix"]:
        raise ValueError("source review matrix must not be empty")
    for row in pack["matrix"]:
        if row.get("dose_values_present") is not False:
            raise ValueError("source review pack must not contain dose values")
        if row.get("source_review_status") != "required_not_started":
            raise ValueError("source review status must remain required_not_started")
    return pack
