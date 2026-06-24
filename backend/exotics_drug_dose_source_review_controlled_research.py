# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_MODE = "exotics_drug_dose_source_review_controlled_research_v1"

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

PROHIBITED_DOSE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
    re.IGNORECASE,
)

PROHIBITED_KEYS = {
    "dose",
    "dosage",
    "drug_dose",
    "drug_route",
    "drug_frequency",
    "route",
    "frequency",
    "prescription",
    "treatment_plan",
    "final_diagnosis",
    "confirmed_diagnosis",
    "definitive_diagnosis",
    "diagnostic_conclusion",
    "client_message",
    "client_facing_summary",
}


def exotics_drug_dose_source_review_controlled_research_safety_flags() -> Dict[str, Any]:
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
        "persists_reasoning_trace": False,
        "generates_final_diagnosis": False,
        "generates_confirmed_diagnosis": False,
        "generates_definitive_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_treatment_plan": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "dose_output_enabled": False,
        "prescription_engine": False,
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
        "controlled_research_only": True,
        "not_client_facing": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            for text in _walk_strings(child):
                yield text
    elif isinstance(value, list):
        for child in value[:200]:
            for text in _walk_strings(child):
                yield text
    elif isinstance(value, str):
        yield value


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            for nested in _walk_keys(child):
                yield nested
    elif isinstance(value, list):
        for child in value[:200]:
            for nested in _walk_keys(child):
                yield nested


def _normalize_key(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _prohibited_payload_items(payload: Dict[str, Any]) -> List[str]:
    hits: List[str] = []
    for key in _walk_keys(payload):
        normalized = _normalize_key(key)
        if normalized in PROHIBITED_KEYS:
            hits.append("key:%s" % key)
    for text in _walk_strings(payload):
        match = PROHIBITED_DOSE_PATTERN.search(text)
        if match:
            hits.append("text:%s" % match.group(0))
    dedup: List[str] = []
    seen = set()
    for item in hits:
        if item not in seen:
            seen.add(item)
            dedup.append(item)
    return dedup[:20]


def build_exotics_drug_dose_source_review_controlled_research_pack(
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = payload or {}
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    prohibited = _prohibited_payload_items(payload)
    if prohibited:
        raise ValueError(
            "payload contains dose, prescription, or diagnostic output outside controlled source research: "
            + ", ".join(prohibited)
        )

    species_filter = payload.get("species") or payload.get("species_group")
    if species_filter:
        requested = _normalize_key(species_filter)
        species = [item for item in SPECIES_GROUPS if item == requested]
        if not species:
            raise ValueError("species must be one of: " + ", ".join(SPECIES_GROUPS))
    else:
        species = list(SPECIES_GROUPS)

    matrix_preview: List[Dict[str, Any]] = []
    for species_key in species:
        for domain in REVIEW_DOMAINS:
            matrix_preview.append({
                "species_group": species_key,
                "review_domain": domain,
                "controlled_research_status": "not_started",
                "requires_primary_exotics_source": True,
                "requires_species_specific_source": True,
                "requires_clinician_reviewer": True,
                "requires_second_reviewer_for_high_risk": True,
                "dose_output_enabled": False,
                "prescription_enabled": False,
                "notes": "No numerical dose, route, or frequency may be recorded in this stage.",
            })

    source_review_protocol = {
        "allowed_evidence_metadata": [
            "source_title",
            "source_type",
            "species_scope",
            "publication_year",
            "publisher_or_journal",
            "reviewer_id",
            "review_status",
            "limitation_notes",
        ],
        "blocked_evidence_content": [
            "numerical_dose",
            "route_instruction",
            "frequency_instruction",
            "prescription_text",
            "client_instruction",
            "treatment_plan",
        ],
        "minimum_review_controls": [
            "species-specific source required before any future dosing work",
            "contradictory sources must be logged as unresolved",
            "high-risk species and drug classes require second clinical reviewer",
            "no dose values are stored or returned in this stage",
        ],
    }

    safety = exotics_drug_dose_source_review_controlled_research_safety_flags()
    quality_gate = {
        "status": "PASS",
        "decision": "controlled_research_protocol_ready_not_started",
        "species_count": len(species),
        "review_domain_count": len(REVIEW_DOMAINS),
        "matrix_preview_rows": len(matrix_preview),
        "source_review_status": "controlled_research_protocol_ready_not_started",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "prescription_enabled": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "blocks_drug_dose_output": True,
        "blocks_prescription_write": True,
        "blocks_client_facing_release": True,
    }

    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_MODE,
        "current_level": "controlled_research_protocol_only_not_dose_engine",
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "source_review_status": "controlled_research_protocol_ready_not_started",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "species_groups": species,
        "review_domains": REVIEW_DOMAINS,
        "source_review_protocol": source_review_protocol,
        "matrix_preview": matrix_preview,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
