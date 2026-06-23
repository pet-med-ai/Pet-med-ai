# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

OBSERVATION_ABNORMAL_FLAG_REVIEW_MODE = "observation_abnormal_flag_review_v1"
OBSERVATION_ABNORMAL_FLAG_REVIEW_CONFIRMATION = "I_UNDERSTAND_THIS_WRITES_OBSERVATION_ABNORMAL_FLAG_REVIEW_ONLY"

_ALLOWED_ABNORMAL_FLAGS = {
    "normal",
    "high",
    "low",
    "abnormal",
    "critical",
    "not_abnormal",
    "indeterminate",
    "not_reviewed",
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


def observation_abnormal_flag_review_safety_flags(
    *,
    dry_run: bool = True,
    writes_database: bool = False,
) -> Dict[str, Any]:
    writes = bool(writes_database) and not bool(dry_run)
    return {
        "read_only": bool(dry_run),
        "dry_run": bool(dry_run),
        "writes_database": writes,
        "limited_db_write_only": writes,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": False,
        "writes_diagnostic_report": False,
        "writes_diagnostic_report_status_only": False,
        "creates_observation": False,
        "updates_observation": writes,
        "writes_observation_abnormal_flag_only": writes,
        "writes_observation_abnormal_flag": writes,
        "writes_observation_review_status": writes,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "writes_abnormal_summary": False,
        "persists_problem_list": False,
        "persists_differential_candidates": False,
        "persists_reasoning_trace": False,
        "creates_audit_log": False,
        "writes_audit_log": False,
        "requires_existing_audit_log": True,
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
        "observation_abnormal_flag_review_only": True,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any, *, default: bool = True) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _normalize_key(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _normalize_abnormal_flag(value: Any) -> str:
    raw = _normalize_key(value)
    aliases = {
        "n": "normal",
        "wnl": "normal",
        "within_reference": "normal",
        "within_reference_range": "normal",
        "not_abnormal": "not_abnormal",
        "non_abnormal": "not_abnormal",
        "not_flagged": "not_abnormal",
        "h": "high",
        "above_reference": "high",
        "above_reference_range": "high",
        "l": "low",
        "below_reference": "low",
        "below_reference_range": "low",
        "crit": "critical",
        "critical_high": "critical",
        "critical_low": "critical",
        "borderline": "abnormal",
        "flagged": "abnormal",
        "unknown": "indeterminate",
        "uncertain": "indeterminate",
        "pending": "not_reviewed",
        "draft": "not_reviewed",
    }
    raw = aliases.get(raw, raw)
    if raw not in _ALLOWED_ABNORMAL_FLAGS:
        raise ValueError("abnormal_flag must be normal, high, low, abnormal, critical, not_abnormal, indeterminate, or not_reviewed")
    return raw


def _normalize_review_status(value: Any) -> str:
    raw = _normalize_key(value or "reviewed")
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
        raise ValueError("review_status must be pending_clinician_review, reviewed, needs_revision, or rejected")
    return raw


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


def _audit_log_model() -> Any:
    try:
        from backend.models import AuditLog  # type: ignore
        return AuditLog
    except Exception:
        try:
            from models import AuditLog  # type: ignore
            return AuditLog
        except Exception:
            return None


def _lookup_required_audit_log(db: Any, audit_log_id: Any, case_id: int) -> Dict[str, Any]:
    log_id = _text(audit_log_id)
    if not log_id:
        raise ValueError("audit_log_id is required for non-dry-run Observation Abnormal Flag Review V1 writes")

    model = _audit_log_model()
    log = db.get(model, log_id)
    if log is None:
        raise ValueError("audit_log_id was not found")

    log_case_id = getattr(log, "case_id", None)
    if log_case_id is not None and int(log_case_id) != int(case_id):
        raise ValueError("audit_log_id does not belong to the same case")

    event_type = _text(getattr(log, "event_type", "")).lower()
    source = _text(getattr(log, "source", "")).lower()
    if event_type and event_type not in {"diagnostic_summary_review", "ai_review"}:
        raise ValueError("audit_log_id must reference a diagnostic summary review audit log")
    if source and source not in {"diagnostic_summary_audit_log_v1", "pet-med-ai", "clinician_review_persistence_v1"}:
        raise ValueError("audit_log_id source is outside Observation Abnormal Flag Review V1")

    return {
        "audit_log_id": getattr(log, "log_id", log_id),
        "case_id": log_case_id,
        "event_type": getattr(log, "event_type", None),
        "source": getattr(log, "source", None),
    }


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _snapshot_observation(observation: Any) -> Dict[str, Any]:
    return {
        "observation_id": int(getattr(observation, "id")),
        "case_id": int(getattr(observation, "case_id")),
        "diagnostic_report_id": getattr(observation, "diagnostic_report_id", None),
        "code": getattr(observation, "code", None),
        "display_name": getattr(observation, "display_name", None),
        "value_text": getattr(observation, "value_text", None),
        "value_numeric": getattr(observation, "value_numeric", None),
        "unit": getattr(observation, "unit", None),
        "reference_low": getattr(observation, "reference_low", None),
        "reference_high": getattr(observation, "reference_high", None),
        "reference_text": getattr(observation, "reference_text", None),
        "abnormal_flag": getattr(observation, "abnormal_flag", None),
        "review_status": getattr(observation, "review_status", None),
        "source_type": getattr(observation, "source_type", None),
        "updated_at": _iso(getattr(observation, "updated_at", None)),
    }


def apply_observation_abnormal_flag_review(
    *,
    db: Any,
    observation: Any,
    payload: Dict[str, Any],
    observation_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # Bounded abnormal-flag review for an existing Observation.
    # Only Observation.abnormal_flag and Observation.review_status may be written.
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    dangerous_keys = _dangerous_keys_present(payload)
    if dangerous_keys:
        raise ValueError("payload contains fields outside Observation Abnormal Flag Review V1: %s" % ", ".join(dangerous_keys[:12]))

    dangerous_text = _dangerous_text_present(payload)
    if dangerous_text:
        raise ValueError("payload contains drug dose, route, or frequency text outside Observation Abnormal Flag Review V1")

    dry_run = _bool(payload.get("dry_run"), default=True)
    case_id = int(getattr(observation, "case_id"))

    raw_case_id = payload.get("case_id")
    if raw_case_id not in (None, "") and int(raw_case_id) != case_id:
        raise ValueError("case_id does not match observation")

    reviewed_by = _text(payload.get("reviewed_by") or payload.get("clinician_id") or payload.get("operator_id"))
    if not reviewed_by:
        raise ValueError("reviewed_by is required")
    if len(reviewed_by) > 120:
        raise ValueError("reviewed_by must be 120 characters or fewer")

    flag_value = (
        payload.get("abnormal_flag")
        if payload.get("abnormal_flag") not in (None, "")
        else payload.get("new_abnormal_flag")
    )
    if flag_value in (None, ""):
        raise ValueError("abnormal_flag is required")
    abnormal_flag = _normalize_abnormal_flag(flag_value)
    review_status = _normalize_review_status(payload.get("review_status") or payload.get("status") or "reviewed")

    confirmation = _text(payload.get("abnormal_flag_review_confirmation") or payload.get("confirmation"))
    confirmation_required = not dry_run
    if confirmation_required and confirmation != OBSERVATION_ABNORMAL_FLAG_REVIEW_CONFIRMATION:
        raise ValueError("abnormal_flag_review_confirmation must equal %s" % OBSERVATION_ABNORMAL_FLAG_REVIEW_CONFIRMATION)

    audit_reference: Optional[Dict[str, Any]] = None
    if not dry_run:
        audit_reference = _lookup_required_audit_log(db, payload.get("audit_log_id"), case_id)

    before = _snapshot_observation(observation)
    persisted = False

    if not dry_run:
        observation.abnormal_flag = abnormal_flag
        observation.review_status = review_status
        db.commit()
        db.refresh(observation)
        persisted = True

    after = _snapshot_observation(observation)
    if dry_run:
        after = dict(before)
        after.update({
            "abnormal_flag": abnormal_flag,
            "review_status": review_status,
            "reviewed_by": reviewed_by,
            "reviewed_at": "DRY_RUN_PREVIEW",
        })

    safety = observation_abnormal_flag_review_safety_flags(
        dry_run=dry_run,
        writes_database=persisted,
    )

    review_result = {
        "decision": "observation_abnormal_flag_review_preview" if dry_run else "observation_abnormal_flag_review_persisted",
        "dry_run": dry_run,
        "persisted": persisted,
        "observation_id": int(getattr(observation, "id")),
        "case_id": case_id,
        "diagnostic_report_id": getattr(observation, "diagnostic_report_id", None),
        "reviewed_by": reviewed_by,
        "audit_log_id": payload.get("audit_log_id") if not dry_run else None,
        "audit_reference": audit_reference,
        "before": before,
        "after": after,
        "allowed_persisted_fields": ["abnormal_flag", "review_status"],
        "blocked_persisted_fields": [
            "case",
            "diagnostic_report",
            "imaging_study",
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
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
    }

    quality_gate = {
        "status": "PASS",
        "decision": review_result["decision"],
        "dry_run": dry_run,
        "confirmation_required": confirmation_required,
        "confirmation_valid": (not confirmation_required) or confirmation == OBSERVATION_ABNORMAL_FLAG_REVIEW_CONFIRMATION,
        "audit_log_required": not dry_run,
        "audit_log_present": bool(audit_reference) if not dry_run else None,
        "writes_database": bool(safety["writes_database"]),
        "updates_case": False,
        "updates_diagnostic_report": False,
        "updates_observation": bool(safety["updates_observation"]),
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "writes_audit_log": False,
        "persists_reasoning_trace": False,
        "blocks_final_diagnosis": True,
        "blocks_treatment_plan": True,
        "blocks_prescription_write": True,
        "blocks_drug_dose_output": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    return {
        "mode": OBSERVATION_ABNORMAL_FLAG_REVIEW_MODE,
        "case_id": case_id,
        "observation_context": observation_context or None,
        "dry_run": dry_run,
        "observation_abnormal_flag_review": review_result,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
