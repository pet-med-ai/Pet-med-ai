# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE = "diagnostic_summary_audit_log_v1"
AUDIT_LOG_CONFIRMATION = "I_UNDERSTAND_THIS_APPENDS_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ONLY"

_ALLOWED_TARGET_TYPES = {
    "case": "case_diagnostic_assistance",
    "case_diagnostic_assistance": "case_diagnostic_assistance",
    "diagnostic_assistance": "case_diagnostic_assistance",
    "clinical_review_workflow": "clinical_review_workflow",
    "diagnostic_report": "diagnostic_report",
    "diagnostic_reports": "diagnostic_report",
    "report": "diagnostic_report",
}

_ALLOWED_ACTIONS = {
    "review_previewed",
    "summary_reviewed",
    "summary_needs_revision",
    "summary_rejected",
    "review_status_persisted",
    "clinician_review_completed",
    "diagnostic_assistance_reviewed",
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
    "ai_summary",
    "abnormal_summary",
    "client_facing_summary",
    "client_message",
}

_DOSE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
    re.IGNORECASE,
)


def diagnostic_summary_audit_log_safety_flags(
    *,
    dry_run: bool = True,
    writes_audit_log: bool = False,
) -> Dict[str, Any]:
    writes = bool(writes_audit_log) and not bool(dry_run)
    return {
        "read_only": bool(dry_run),
        "dry_run": bool(dry_run),
        "writes_database": writes,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": False,
        "writes_diagnostic_report": False,
        "writes_diagnostic_report_status_only": False,
        "creates_observation": False,
        "updates_observation": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "writes_abnormal_summary": False,
        "persists_problem_list": False,
        "persists_differential_candidates": False,
        "persists_reasoning_trace": False,
        "creates_audit_log": writes,
        "writes_audit_log": writes,
        "append_only_audit_log": True,
        "updates_audit_log": False,
        "deletes_audit_log": False,
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
        "diagnostic_summary_audit_log_only": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _normalize_key(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _normalize_target_type(value: Any) -> str:
    raw = _normalize_key(value or "case_diagnostic_assistance")
    normalized = _ALLOWED_TARGET_TYPES.get(raw)
    if not normalized:
        raise ValueError("target_type must be case_diagnostic_assistance, clinical_review_workflow, or diagnostic_report")
    return normalized


def _normalize_action(value: Any) -> str:
    raw = _normalize_key(value or "summary_reviewed")
    aliases = {
        "reviewed": "summary_reviewed",
        "accepted": "summary_reviewed",
        "approve": "summary_reviewed",
        "approved": "summary_reviewed",
        "needs_review": "review_previewed",
        "previewed": "review_previewed",
        "needs_revision": "summary_needs_revision",
        "revision_requested": "summary_needs_revision",
        "request_revision": "summary_needs_revision",
        "rejected": "summary_rejected",
        "reject": "summary_rejected",
        "review_status_persistence": "review_status_persisted",
        "persistence_applied": "review_status_persisted",
        "clinician_review": "clinician_review_completed",
    }
    raw = aliases.get(raw, raw)
    if raw not in _ALLOWED_ACTIONS:
        raise ValueError("action_taken is outside Diagnostic Summary Audit Log V1 allowed actions")
    return raw


def _normalize_review_status(value: Any) -> str:
    raw = _normalize_key(value or "reviewed")
    aliases = {
        "pending": "pending_clinician_review",
        "pending_review": "pending_clinician_review",
        "needs_review": "pending_clinician_review",
        "approved": "reviewed",
        "accepted": "reviewed",
        "revision_requested": "needs_revision",
        "request_revision": "needs_revision",
        "reject": "rejected",
    }
    raw = aliases.get(raw, raw)
    if raw not in _ALLOWED_REVIEW_STATUS:
        raise ValueError("review_status must be pending_clinician_review, reviewed, needs_revision, or rejected")
    return raw


def _clean_text(value: Any, *, max_len: int = 1000) -> str:
    text = _text(value)
    if len(text) > max_len:
        text = text[:max_len]
    return text


def _clean_list(value: Any, *, max_items: int = 20, max_len: int = 120) -> List[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, list):
        raw_items = value
    else:
        raise ValueError("source_preview_ids/source_modes must be a list or string")
    items: List[str] = []
    seen = set()
    for raw in raw_items[:max_items]:
        item = _clean_text(raw, max_len=max_len)
        if item and item not in seen:
            items.append(item)
            seen.add(item)
    return items


def _dangerous_keys_present(payload: Dict[str, Any]) -> List[str]:
    found: List[str] = []

    def walk(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                normalized = _normalize_key(key_text)
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


def _dangerous_text_present(payload: Dict[str, Any]) -> List[str]:
    hits: List[str] = []

    def walk(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, (prefix + str(key) + ".") if prefix else (str(key) + "."))
        elif isinstance(value, list):
            for idx, child in enumerate(value[:50]):
                walk(child, "%s%d." % (prefix, idx))
        elif isinstance(value, str):
            match = _DOSE_PATTERN.search(value)
            if match:
                hits.append("%s%s" % (prefix, match.group(0)))

    walk(payload)
    return hits[:12]


def _positive_int_or_none(value: Any, *, label: str) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except Exception as exc:
        raise ValueError("%s must be a positive integer" % label) from exc
    if parsed <= 0:
        raise ValueError("%s must be a positive integer" % label)
    return parsed


def build_diagnostic_summary_audit_log_event(
    payload: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    dangerous_keys = _dangerous_keys_present(payload)
    if dangerous_keys:
        raise ValueError("payload contains fields outside Diagnostic Summary Audit Log V1: %s" % ", ".join(dangerous_keys[:12]))

    dangerous_text = _dangerous_text_present(payload)
    if dangerous_text:
        raise ValueError("payload contains drug dose, route, or frequency text outside Diagnostic Summary Audit Log V1")

    parsed_case_id = _positive_int_or_none(payload.get("case_id") or case_id, label="case_id")
    if parsed_case_id is None:
        raise ValueError("case_id is required")

    dry_run = _bool(payload.get("dry_run"), default=True)
    clinician_id = _clean_text(payload.get("clinician_id") or payload.get("reviewed_by") or payload.get("operator_id"), max_len=100)
    if not clinician_id:
        raise ValueError("clinician_id or reviewed_by is required")

    target_type = _normalize_target_type(payload.get("target_type") or payload.get("target") or "case_diagnostic_assistance")
    target_id = _positive_int_or_none(
        payload.get("target_id") or payload.get("diagnostic_report_id") or payload.get("report_id"),
        label="target_id",
    )
    if target_type == "diagnostic_report" and target_id is None:
        raise ValueError("target_id is required when target_type is diagnostic_report")

    action_taken = _normalize_action(payload.get("action_taken") or payload.get("review_action"))
    review_status = _normalize_review_status(payload.get("review_status") or payload.get("status") or action_taken)

    confirmation = _text(payload.get("audit_log_confirmation") or payload.get("confirmation"))
    confirmation_required = not dry_run
    if confirmation_required and confirmation != AUDIT_LOG_CONFIRMATION:
        raise ValueError("audit_log_confirmation must equal %s" % AUDIT_LOG_CONFIRMATION)

    request_id = _clean_text(payload.get("request_id"), max_len=100)
    if not request_id:
        request_id = "diag-summary-audit-%s-%s" % (parsed_case_id, uuid4().hex[:12])

    note = _clean_text(payload.get("note") or payload.get("review_note"), max_len=1000)
    override_reason = _clean_text(payload.get("override_reason") or payload.get("reason"), max_len=1000)
    session_uid = _clean_text(payload.get("session_uid"), max_len=64) or None
    source_preview_ids = _clean_list(payload.get("source_preview_ids") or payload.get("source_preview_id"))
    source_modes = _clean_list(payload.get("source_modes") or payload.get("source_mode"), max_items=12)

    safety = diagnostic_summary_audit_log_safety_flags(
        dry_run=dry_run,
        writes_audit_log=(not dry_run),
    )

    metadata = {
        "stage": DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE,
        "case_id": parsed_case_id,
        "target_type": target_type,
        "target_id": target_id,
        "review_status": review_status,
        "source_preview_ids": source_preview_ids,
        "source_modes": source_modes,
        "confirmation_required": confirmation_required,
        "confirmation_valid": (not confirmation_required) or confirmation == AUDIT_LOG_CONFIRMATION,
        "case_context_present": bool(case_context),
        "audit_scope": "diagnostic_summary_review_only",
        "blocked_writes": [
            "case",
            "diagnostic_report",
            "observation",
            "imaging_study",
            "ai_summary",
            "reasoning_trace",
            "treatment_plan",
            "prescription",
        ],
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
    }

    audit_event = {
        "request_id": request_id,
        "patient_token": "case:%s" % parsed_case_id,
        "clinician_id": clinician_id,
        "model_version": DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE,
        "confidence": None,
        "suggested_action": "diagnostic_summary_audit_only:%s" % action_taken,
        "action_taken": action_taken,
        "override_reason": override_reason or None,
        "note": note or None,
        "case_id": parsed_case_id,
        "session_uid": session_uid,
        "event_type": "diagnostic_summary_review",
        "source": DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE,
        "metadata": metadata,
    }

    audit_log_result = {
        "decision": "audit_log_append_preview" if dry_run else "audit_log_append_requested",
        "dry_run": dry_run,
        "will_append_audit_log": not dry_run,
        "persisted": False,
        "audit_log_id": None,
        "append_only": True,
        "can_update": False,
        "can_delete": False,
        "case_id": parsed_case_id,
        "target_type": target_type,
        "target_id": target_id,
        "action_taken": action_taken,
        "review_status": review_status,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
    }

    quality_gate = {
        "status": "PASS",
        "decision": audit_log_result["decision"],
        "dry_run": dry_run,
        "confirmation_required": confirmation_required,
        "confirmation_valid": metadata["confirmation_valid"],
        "writes_database": bool(safety["writes_database"]),
        "writes_audit_log": bool(safety["writes_audit_log"]),
        "append_only_audit_log": True,
        "updates_case": False,
        "updates_diagnostic_report": False,
        "updates_observation": False,
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "persists_reasoning_trace": False,
        "blocks_final_diagnosis": True,
        "blocks_treatment_plan": True,
        "blocks_prescription_write": True,
        "blocks_drug_dose_output": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    return {
        "mode": DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE,
        "case_id": parsed_case_id,
        "case_context": case_context or None,
        "dry_run": dry_run,
        "audit_event": audit_event,
        "audit_log_result": audit_log_result,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
