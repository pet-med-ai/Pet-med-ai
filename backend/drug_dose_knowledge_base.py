# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DRUG_DOSE_KNOWLEDGE_BASE_MODE = "drug_dose_knowledge_base_v1"

ROOT = Path(__file__).resolve().parents[1]
KB_FILE = ROOT / "docs" / "clinical_data" / "drug_dose_knowledge_base" / "drug_dose_kb_v1.json"


def drug_dose_knowledge_base_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "creates_treatment_plan": False,
        "treatment_recommendation": False,
        "drug_recommendation": False,
        "drug_dose_recommendation": False,
        "dose_calculation": False,
        "dose_calculation_enabled": False,
        "dose_lookup_enabled": False,
        "returns_numeric_dose": False,
        "returns_route_frequency": False,
        "client_facing_dose_output": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "numeric_dose_values_redacted": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_kb() -> Dict[str, Any]:
    if not KB_FILE.exists():
        return {
            "mode": DRUG_DOSE_KNOWLEDGE_BASE_MODE,
            "version": "v1",
            "monographs": [],
        }
    return json.loads(KB_FILE.read_text(encoding="utf-8"))


def _monographs() -> List[Dict[str, Any]]:
    data = _load_kb()
    rows = data.get("monographs") or []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _public_monograph(row: Dict[str, Any]) -> Dict[str, Any]:
    dose_policy = row.get("dose_policy") if isinstance(row.get("dose_policy"), dict) else {}
    return {
        "drug_key": _text(row.get("drug_key")),
        "display_name": _text(row.get("display_name")),
        "drug_class": _text(row.get("drug_class")),
        "allowed_species": list(row.get("allowed_species") or []),
        "review_status": _text(row.get("review_status")) or "template_only_not_clinically_approved",
        "minimum_inputs": list(row.get("minimum_inputs") or []),
        "warning_flags": list(row.get("warning_flags") or []),
        "contraindication_screen": list(row.get("contraindication_screen") or []),
        "clinician_review_notes": list(row.get("clinician_review_notes") or []),
        "source_review": row.get("source_review") if isinstance(row.get("source_review"), dict) else {},
        "dose_policy": {
            "dose_fields_present": True,
            "numeric_dose_values_redacted": True,
            "dose_calculation_enabled": False,
            "dose_lookup_enabled": False,
            "returns_numeric_dose": False,
            "returns_route_frequency": False,
            "requires_clinician_source_review": bool(dose_policy.get("requires_clinician_source_review", True)),
            "reason": "Drug Dose Knowledge Base V1 exposes safety metadata only; numeric dose values are gated and not returned.",
        },
        "safety": drug_dose_knowledge_base_flags(),
    }


def list_drug_dose_monographs() -> List[Dict[str, Any]]:
    return [_public_monograph(row) for row in _monographs()]


def get_drug_dose_monograph(drug_key: str) -> Optional[Dict[str, Any]]:
    needle = _text(drug_key).lower()
    if not needle:
        return None
    for row in _monographs():
        if _text(row.get("drug_key")).lower() == needle:
            return _public_monograph(row)
    return None


def _case_species(payload: Dict[str, Any], case_context: Optional[Dict[str, Any]]) -> str:
    return (_text(payload.get("species")) or _text((case_context or {}).get("species"))).lower()


def _missing_inputs(payload: Dict[str, Any], monograph: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    minimum = monograph.get("minimum_inputs") if isinstance(monograph.get("minimum_inputs"), list) else []
    for key in minimum:
        key_text = _text(key)
        if not key_text:
            continue
        if key_text in {"species"}:
            if not _text(payload.get("species")):
                missing.append(key_text)
        elif key_text in {"weight_kg"}:
            if payload.get("weight_kg") in (None, ""):
                missing.append(key_text)
        else:
            if key_text not in payload or payload.get(key_text) in (None, "", []):
                missing.append(key_text)
    return missing


def review_drug_dose_knowledge_base(
    payload: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Review a drug key against the gated dose knowledge-base shell.

    This is not a dose lookup, dose calculator, prescription engine, or treatment
    recommendation engine. Numeric dose values remain redacted and disabled.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    drug_key = _text(payload.get("drug_key") or payload.get("drug_name") or payload.get("medication")).lower()
    monograph = get_drug_dose_monograph(drug_key)

    if not monograph:
        decision = "blocked_unknown_drug"
        species_allowed = False
        missing_inputs: List[str] = []
    else:
        species = _case_species(payload, case_context)
        allowed_species = [str(item).lower() for item in monograph.get("allowed_species", [])]
        species_allowed = bool(species and species in allowed_species)
        missing_inputs = _missing_inputs(payload, monograph)

        if not species_allowed:
            decision = "blocked_species_constraint"
        else:
            decision = "kb_review_only_no_dose_output"

    quality_gate = {
        "status": "PASS",
        "decision": decision,
        "dose_calculation_enabled": False,
        "numeric_dose_output_allowed": False,
        "route_frequency_output_allowed": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "minimum_inputs_complete": not missing_inputs if monograph else False,
    }

    safety = drug_dose_knowledge_base_flags()
    return {
        "mode": DRUG_DOSE_KNOWLEDGE_BASE_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "drug_key": drug_key or None,
        "monograph": monograph,
        "knowledge_base_review": {
            "decision": decision,
            "species_allowed": species_allowed,
            "missing_inputs": missing_inputs,
            "numeric_dose_values_redacted": True,
            "dose_calculation_enabled": False,
            "returns_numeric_dose": False,
            "returns_route_frequency": False,
            "not_a_prescription": True,
            "not_a_treatment_plan": True,
            "not_a_drug_dose_recommendation": True,
            "human_review_required": True,
            "clinician_signoff_required": True,
        },
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
