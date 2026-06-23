# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

CLINICIAN_REVIEW_PERSISTENCE_MODE = "clinician_review_persistence_v1"
PERSISTENCE_CONFIRMATION = "I_UNDERSTAND_THIS_WRITES_REVIEW_STATUS_ONLY"

_ALLOWED_TARGET_TYPES = {
    "diagnostic_report": "diagnostic_report",
    "diagnostic_reports": "diagnostic_report",
    "report": "diagnostic_report",
}

_ALLOWED_REVIEW_STATUS = {
    "pending_clinician_review",
    "reviewed",
    "needs_revision",
    "rejected",
}

_DANGEROUS_KEYS = {
    "final_diagnosis",
    "confirmed_diagnosis",
    "definitive_diagnosis",
    "diagnostic_conclusion",
    "diagnosis",
    "treatment_plan",
    "prescription",
    "drug_dose",
    "drug_route",
    "drug_frequency",
    "dose",
    "route",
    "frequency",
    "probability",
    "numeric_confidence",
    "confidence_score",
}


def clinician_review_persistence_safety_flags(
    *,
    dry_run: bool = True,
    writes_database: bool = False,
    item_count: int = 0,
) -> Dict[str, Any]:
    writes = bool(writes_database) and not bool(dry_run) and int(item_count or 0) > 0
    return {
        "read_only": bool(dry_run),
        "dry_run": bool(dry_run),
        "writes_database": writes,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": writes,
        "writes_diagnostic_report": writes,
        "writes_diagnostic_report_status_only": writes,
        "creates_observation": False,
        "updates_observation": False,
        "writes_observation_review_status_only": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "writes_imaging_study_review_status_only": False,
        "writes_ai_summary": False,
        "writes_abnormal_summary": False,
        "persists_problem_list": False,
        "persists_differential_candidates": False,
        "persists_reasoning_trace": False,
        "creates_audit_log": False,
        "writes_audit_log": False,
        "signs_final_report": False,
        "final_signoff_persisted": False,
        "releases_to_client": False,
        "client_release_allowed": False,
        "client_facing": False,
        "not_client_facing": True,
        "generates_final_diagnosis": False,
        "generates_confirmed_diagnosis": False,
        "generates_definitive_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "returns_probability": False,
        "returns_numeric_confidence": False,
        "creates_treatment_plan": False,
        "writes_treatment_plan": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
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
        "review_status_persistence_allowed": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _normalize_target_type(value: Any) -> str:
    raw = _text(value).lower().replace("-", "_").replace(" ", "_")
    normalized = _ALLOWED_TARGET_TYPES.get(raw)
    if not normalized:
        raise ValueError("target_type must be diagnostic_report in Clinician Review Persistence V1")
    return normalized


def _normalize_review_status(value: Any) -> str:
    raw = _text(value).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "pending": "pending_clinician_review",
        "pending_review": "pending_clinician_review",
        "needs_review": "pending_clinician_review",
        "approved": "reviewed",
        "accepted": "reviewed",
        "mark_reviewed": "reviewed",
        "revision_requested": "needs_revision",
        "request_revision": "needs_revision",
        "revise": "needs_revision",
        "reject": "rejected",
    }
    raw = aliases.get(raw, raw)
    if raw not in _ALLOWED_REVIEW_STATUS:
        raise ValueError("review_status must be one of pending_clinician_review, reviewed, needs_revision, rejected")
    return raw


def _items_from_payload(payload: Dict[str, Any]) -> List[Any]:
    for key in ("review_items", "items", "targets"):
        value = payload.get(key)
        if value is not None:
            if not isinstance(value, list):
                raise ValueError("%s must be a list" % key)
            return value
    return []


def _dangerous_keys_present(payload: Dict[str, Any]) -> List[str]:
    found: List[str] = []

    def walk(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                normalized = key_text.lower().replace("-", "_").replace(" ", "_")
                if normalized in _DANGEROUS_KEYS:
                    found.append(prefix + key_text if prefix else key_text)
                walk(child, (prefix + key_text + ".") if prefix else (key_text + "."))
        elif isinstance(value, list):
            for idx, child in enumerate(value[:50]):
                walk(child, "%s%d." % (prefix, idx))

    walk(payload)
    dedup: List[str] = []
    seen = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            dedup.append(item)
    return dedup


def _clean_note(value: Any) -> str:
    note = _text(value)
    if len(note) > 500:
        return note[:500]
    return note


def _parse_review_item(value: Any, index: int) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("review_items[%d] must be an object" % index)

    target_type = _normalize_target_type(value.get("target_type") or value.get("type"))
    raw_target_id = value.get("target_id") or value.get("id")
    try:
        target_id = int(raw_target_id)
    except Exception as exc:
        raise ValueError("review_items[%d].target_id must be a positive integer" % index) from exc
    if target_id <= 0:
        raise ValueError("review_items[%d].target_id must be a positive integer" % index)

    review_status = _normalize_review_status(value.get("review_status") or value.get("status") or "reviewed")
    note = _clean_note(value.get("note") or value.get("review_note") or "")
    source_preview_id = _text(value.get("source_preview_id") or value.get("source_id") or "")

    return {
        "index": index,
        "target_type": target_type,
        "target_id": target_id,
        "review_status": review_status,
        "note": note,
        "source_preview_id": source_preview_id or None,
        "allowed_persisted_fields": _allowed_persisted_fields(target_type),
        "blocked_persisted_fields": [
            "ai_summary",
            "abnormal_summary",
            "problem_list_preview",
            "differential_diagnosis_candidates_preview",
            "diagnostic_reasoning_evidence_trace_preview",
            "final_diagnosis",
            "diagnostic_conclusion",
            "treatment_plan",
            "prescription",
            "drug_dose",
        ],
    }


def _allowed_persisted_fields(target_type: str) -> List[str]:
    if target_type == "diagnostic_report":
        return ["status", "reviewed_by", "reviewed_at"]
    if target_type == "observation":
        return ["review_status"]
    if target_type == "imaging_study":
        return ["review_status", "reviewed_by", "reviewed_at"]
    return []


def build_clinician_review_persistence_plan(
    payload: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a bounded clinician review persistence plan.

    The plan allows only review-status persistence for existing diagnostic data
    records owned by the authenticated user. It does not create diagnostic
    records, write AI summaries, persist reasoning traces, create audit logs,
    sign final reports, release client-facing content, write prescriptions,
    or call external providers.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    dangerous_keys = _dangerous_keys_present(payload)
    if dangerous_keys:
        raise ValueError("payload contains fields outside Clinician Review Persistence V1: %s" % ", ".join(dangerous_keys[:12]))

    dry_run = _bool(payload.get("dry_run"))
    reviewed_by = _text(payload.get("reviewed_by") or payload.get("clinician_id") or payload.get("operator_id"))
    if not reviewed_by:
        raise ValueError("reviewed_by is required")
    if len(reviewed_by) > 120:
        raise ValueError("reviewed_by must be 120 characters or fewer")

    raw_items = _items_from_payload(payload)
    review_items = [_parse_review_item(value, index) for index, value in enumerate(raw_items)]

    confirmation = _text(payload.get("persistence_confirmation") or payload.get("confirmation"))
    confirmation_required = not dry_run and len(review_items) > 0
    if confirmation_required and confirmation != PERSISTENCE_CONFIRMATION:
        raise ValueError("persistence_confirmation must equal %s" % PERSISTENCE_CONFIRMATION)

    decision = "review_status_persistence_preview"
    if not review_items:
        decision = "no_review_targets_supplied"
    elif not dry_run:
        decision = "review_status_persistence_requested"

    item_count = len(review_items)
    safety = clinician_review_persistence_safety_flags(
        dry_run=dry_run,
        writes_database=(not dry_run and item_count > 0),
        item_count=item_count,
    )

    quality_gate = {
        "status": "PASS",
        "decision": decision,
        "item_count": item_count,
        "dry_run": dry_run,
        "confirmation_required": confirmation_required,
        "confirmation_valid": (not confirmation_required) or confirmation == PERSISTENCE_CONFIRMATION,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "blocks_ai_summary_write": True,
        "blocks_reasoning_trace_persistence": True,
        "blocks_audit_log_write_until_next_stage": True,
        "blocks_final_diagnosis": True,
        "blocks_treatment_plan": True,
        "blocks_prescription_write": True,
        "blocks_drug_dose_output": True,
    }

    return {
        "mode": CLINICIAN_REVIEW_PERSISTENCE_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "persistence": {
            "decision": decision,
            "reviewed_by": reviewed_by,
            "dry_run": dry_run,
            "review_status_persistence_only": True,
            "persistence_confirmation_required": confirmation_required,
            "confirmation_valid": quality_gate["confirmation_valid"],
            "item_count": item_count,
            "not_a_diagnosis": True,
            "not_a_treatment_plan": True,
            "not_a_prescription": True,
            "not_client_facing": True,
        },
        "review_items": review_items,
        "blocked_actions": [
            "write_ai_summary",
            "write_abnormal_summary",
            "persist_problem_list",
            "persist_differential_candidates",
            "persist_reasoning_trace",
            "create_audit_log",
            "sign_final_report",
            "release_to_client",
            "create_treatment_plan",
            "write_prescription",
            "return_drug_dose_route_or_frequency",
            "call_external_ai_provider",
        ],
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
