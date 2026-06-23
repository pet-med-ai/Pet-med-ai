# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_MODE = "diagnosticreport_ai_summary_persistence_v1"
AI_SUMMARY_PERSISTENCE_CONFIRMATION = "I_UNDERSTAND_THIS_WRITES_DIAGNOSTICREPORT_AI_SUMMARY_ONLY"
REQUIRED_AUDIT_SOURCE = "diagnostic_summary_audit_log_v1"

_DOSE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
    re.IGNORECASE,
)

_DANGEROUS_TEXT_PATTERN = re.compile(
    r"(final\s+diagnosis|confirmed\s+diagnosis|definitive\s+diagnosis|diagnostic\s+conclusion|diagnosis\s*:|treatment\s+plan|prescription|drug\s+dose|dosage|最终诊断|确诊|诊断[:：]|诊断为|治疗方案|处方|剂量|给药|用药)",
    re.IGNORECASE,
)

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
    "problem_list_preview",
    "differential_diagnosis_candidates_preview",
    "diagnostic_reasoning_evidence_trace_preview",
    "client_facing_summary",
    "client_message",
}

_ALLOWED_STATUS_ALIASES = {
    "clinician_reviewed": "clinician_reviewed",
    "reviewed": "clinician_reviewed",
    "approved": "clinician_reviewed",
    "accepted": "clinician_reviewed",
    "ai_summary_reviewed": "clinician_reviewed",
}

_ALLOWED_REPORT_REVIEW_STATUS = {"reviewed", "clinician_reviewed"}


def diagnosticreport_ai_summary_persistence_safety_flags(
    *,
    dry_run: bool = True,
    writes_database: bool = False,
) -> Dict[str, Any]:
    writes = bool(writes_database) and not bool(dry_run)
    return {
        "read_only": bool(dry_run),
        "dry_run": bool(dry_run),
        "writes_database": writes,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": writes,
        "writes_diagnostic_report": writes,
        "writes_diagnostic_report_status_only": False,
        "writes_diagnostic_report_ai_summary_only": writes,
        "creates_observation": False,
        "updates_observation": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "writes_ai_summary": writes,
        "writes_ai_summary_status": writes,
        "writes_abnormal_summary": False,
        "persists_problem_list": False,
        "persists_differential_candidates": False,
        "persists_reasoning_trace": False,
        "creates_audit_log": False,
        "writes_audit_log": False,
        "append_only_audit_log": False,
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
        "diagnosticreport_ai_summary_persistence_allowed": True,
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


def _positive_int(value: Any, *, label: str) -> int:
    try:
        parsed = int(value)
    except Exception as exc:
        raise ValueError("%s must be a positive integer" % label) from exc
    if parsed <= 0:
        raise ValueError("%s must be a positive integer" % label)
    return parsed


def _dangerous_keys_present(payload: Dict[str, Any]) -> List[str]:
    found: List[str] = []

    allowed_summary_keys = {"ai_summary", "summary_text", "clinician_reviewed_ai_summary"}

    def walk(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                normalized = _normalize_key(key_text)
                if normalized in _DANGEROUS_KEYS and normalized not in allowed_summary_keys:
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


def _summary_text(payload: Dict[str, Any]) -> str:
    for key in ("ai_summary", "summary_text", "clinician_reviewed_ai_summary"):
        text = _text(payload.get(key))
        if text:
            return text
    nested = payload.get("summary")
    if isinstance(nested, dict):
        for key in ("ai_summary", "summary_text", "clinician_reviewed_ai_summary", "text"):
            text = _text(nested.get(key))
            if text:
                return text
    return ""


def _validate_summary_text(summary: str) -> str:
    summary = _text(summary)
    if len(summary) < 8:
        raise ValueError("ai_summary must contain clinician-reviewed summary text")
    if len(summary) > 5000:
        raise ValueError("ai_summary must be 5000 characters or fewer")
    if _DOSE_PATTERN.search(summary):
        raise ValueError("ai_summary contains drug dose, route, or frequency text outside DiagnosticReport AI Summary Persistence V1")
    if _DANGEROUS_TEXT_PATTERN.search(summary):
        raise ValueError("ai_summary contains diagnosis, treatment, prescription, or client-facing conclusion text outside this stage")
    return summary


def _normalize_ai_summary_status(value: Any) -> str:
    raw = _normalize_key(value or "clinician_reviewed")
    status = _ALLOWED_STATUS_ALIASES.get(raw)
    if not status:
        raise ValueError("ai_summary_status must be clinician_reviewed in DiagnosticReport AI Summary Persistence V1")
    return status


def _clean_reviewed_by(value: Any) -> str:
    reviewed_by = _text(value)
    if not reviewed_by:
        raise ValueError("reviewed_by is required")
    if len(reviewed_by) > 120:
        raise ValueError("reviewed_by must be 120 characters or fewer")
    return reviewed_by


def _report_snapshot(report: Any) -> Dict[str, Any]:
    return {
        "report_id": int(getattr(report, "id")),
        "case_id": int(getattr(report, "case_id")),
        "status": getattr(report, "status", None),
        "ai_summary_present": bool(getattr(report, "ai_summary", None)),
        "ai_summary_status": getattr(report, "ai_summary_status", None),
        "reviewed_by": getattr(report, "reviewed_by", None),
        "reviewed_at": getattr(report, "reviewed_at", None).isoformat() if isinstance(getattr(report, "reviewed_at", None), datetime) else None,
        "report_type": getattr(report, "report_type", None),
        "source_type": getattr(report, "source_type", None),
    }


def build_diagnosticreport_ai_summary_persistence_plan(
    payload: Dict[str, Any],
    *,
    report_id: Optional[int] = None,
    report_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    dangerous_keys = _dangerous_keys_present(payload)
    if dangerous_keys:
        raise ValueError("payload contains fields outside DiagnosticReport AI Summary Persistence V1: %s" % ", ".join(dangerous_keys[:12]))

    parsed_report_id = _positive_int(payload.get("diagnostic_report_id") or payload.get("report_id") or report_id, label="diagnostic_report_id")
    if report_id is not None and int(parsed_report_id) != int(report_id):
        raise ValueError("diagnostic_report_id does not match URL report_id")

    dry_run = _bool(payload.get("dry_run"), default=True)
    summary = _validate_summary_text(_summary_text(payload))
    reviewed_by = _clean_reviewed_by(payload.get("reviewed_by") or payload.get("clinician_id") or payload.get("operator_id"))
    ai_summary_status = _normalize_ai_summary_status(payload.get("ai_summary_status") or payload.get("status"))

    audit_log_id = _text(payload.get("audit_log_id") or payload.get("diagnostic_summary_audit_log_id"))
    confirmation = _text(payload.get("persistence_confirmation") or payload.get("confirmation"))
    confirmation_required = not dry_run
    if confirmation_required:
        if confirmation != AI_SUMMARY_PERSISTENCE_CONFIRMATION:
            raise ValueError("persistence_confirmation must equal %s" % AI_SUMMARY_PERSISTENCE_CONFIRMATION)
        if not audit_log_id:
            raise ValueError("audit_log_id from Diagnostic Summary Audit Log V1 is required for AI summary persistence")
        if len(audit_log_id) > 100:
            raise ValueError("audit_log_id must be 100 characters or fewer")

    source_preview_ids = payload.get("source_preview_ids") or payload.get("source_preview_id") or []
    if isinstance(source_preview_ids, str):
        source_preview_ids = [source_preview_ids]
    if not isinstance(source_preview_ids, list):
        raise ValueError("source_preview_ids must be a list or string")
    source_preview_ids = [_text(item)[:120] for item in source_preview_ids[:20] if _text(item)]

    decision = "ai_summary_persistence_preview" if dry_run else "ai_summary_persistence_requested"
    safety = diagnosticreport_ai_summary_persistence_safety_flags(
        dry_run=dry_run,
        writes_database=not dry_run,
    )

    quality_gate = {
        "status": "PASS",
        "decision": decision,
        "dry_run": dry_run,
        "confirmation_required": confirmation_required,
        "confirmation_valid": (not confirmation_required) or confirmation == AI_SUMMARY_PERSISTENCE_CONFIRMATION,
        "audit_log_required_for_write": True,
        "audit_log_present": bool(audit_log_id),
        "summary_length": len(summary),
        "writes_database": bool(safety["writes_database"]),
        "writes_ai_summary": bool(safety["writes_ai_summary"]),
        "writes_audit_log": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "blocks_problem_list_persistence": True,
        "blocks_differential_candidate_persistence": True,
        "blocks_reasoning_trace_persistence": True,
        "blocks_final_diagnosis": True,
        "blocks_treatment_plan": True,
        "blocks_prescription_write": True,
        "blocks_drug_dose_output": True,
    }

    return {
        "mode": DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_MODE,
        "report_id": parsed_report_id,
        "report_context": report_context or None,
        "dry_run": dry_run,
        "persistence": {
            "decision": decision,
            "target_type": "diagnostic_report",
            "target_id": parsed_report_id,
            "reviewed_by": reviewed_by,
            "ai_summary_status": ai_summary_status,
            "audit_log_id": audit_log_id or None,
            "source_preview_ids": source_preview_ids,
            "persistence_confirmation_required": confirmation_required,
            "confirmation_valid": quality_gate["confirmation_valid"],
            "diagnosticreport_ai_summary_persistence_only": True,
            "not_a_diagnosis": True,
            "not_a_treatment_plan": True,
            "not_a_prescription": True,
            "not_client_facing": True,
        },
        "ai_summary_preview": {
            "text": summary,
            "length": len(summary),
            "status_after": ai_summary_status,
            "clinician_reviewed": True,
            "not_client_facing": True,
        },
        "blocked_actions": [
            "create_case",
            "create_diagnostic_report",
            "update_observation",
            "update_imaging_study",
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


def _load_audit_log_model() -> Any:
    try:
        from backend.models import AuditLog  # type: ignore
    except ModuleNotFoundError:
        from models import AuditLog  # type: ignore
    return AuditLog


def apply_diagnosticreport_ai_summary_persistence(
    *,
    db: Any,
    report: Any,
    payload: Dict[str, Any],
    report_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    plan = build_diagnosticreport_ai_summary_persistence_plan(
        payload,
        report_id=int(getattr(report, "id")),
        report_context=report_context,
    )
    dry_run = bool(plan.get("dry_run"))
    persistence = dict(plan.get("persistence") or {})
    summary = str((plan.get("ai_summary_preview") or {}).get("text") or "")
    status_after = str(persistence.get("ai_summary_status") or "clinician_reviewed")
    reviewed_by = str(persistence.get("reviewed_by") or "").strip()
    audit_log_id = persistence.get("audit_log_id")

    before = _report_snapshot(report)
    persisted = False
    audit_log_verified = False

    if not dry_run:
        report_status = _normalize_key(getattr(report, "status", ""))
        if report_status not in _ALLOWED_REPORT_REVIEW_STATUS:
            raise ValueError("DiagnosticReport.status must be reviewed before ai_summary persistence")

        AuditLog = _load_audit_log_model()
        audit_log = db.get(AuditLog, audit_log_id)
        if audit_log is None:
            raise ValueError("audit_log_id was not found")
        if int(getattr(audit_log, "case_id", -1)) != int(getattr(report, "case_id")):
            raise ValueError("audit_log_id does not belong to the same case")
        audit_source = str(getattr(audit_log, "source", "") or "")
        audit_event_type = str(getattr(audit_log, "event_type", "") or "")
        if audit_source != REQUIRED_AUDIT_SOURCE or audit_event_type != "diagnostic_summary_review":
            raise ValueError("audit_log_id must reference Diagnostic Summary Audit Log V1 diagnostic_summary_review")
        audit_log_verified = True

        now = datetime.utcnow()
        report.ai_summary = summary
        report.ai_summary_status = status_after
        report.reviewed_by = reviewed_by
        report.reviewed_at = now
        db.commit()
        db.refresh(report)
        persisted = True

    after = _report_snapshot(report)
    if dry_run:
        after = dict(before)
        after.update({
            "ai_summary_present": True,
            "ai_summary_status": status_after,
            "reviewed_by": reviewed_by,
            "reviewed_at": "DRY_RUN_PREVIEW",
        })

    api_safety = diagnosticreport_ai_summary_persistence_safety_flags(
        dry_run=dry_run,
        writes_database=persisted,
    )

    persistence_result = {
        "decision": "diagnosticreport_ai_summary_persisted" if persisted else persistence.get("decision"),
        "dry_run": dry_run,
        "persisted": persisted,
        "report_id": int(getattr(report, "id")),
        "case_id": int(getattr(report, "case_id")),
        "audit_log_id": audit_log_id,
        "audit_log_verified": audit_log_verified,
        "reviewed_by": reviewed_by,
        "reviewed_at": after.get("reviewed_at") if persisted else None,
        "before": before,
        "after": after,
        "allowed_persisted_fields": ["ai_summary", "ai_summary_status", "reviewed_by", "reviewed_at"],
        "blocked_persisted_fields": [
            "case",
            "diagnostic_report.status",
            "diagnostic_report.abnormal_summary",
            "observation",
            "imaging_study",
            "audit_log",
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

    quality_gate = dict(plan.get("quality_gate") or {})
    quality_gate.update({
        "status": "PASS",
        "persisted": persisted,
        "writes_database": bool(api_safety.get("writes_database")),
        "updates_diagnostic_report": bool(api_safety.get("updates_diagnostic_report")),
        "writes_ai_summary": bool(api_safety.get("writes_ai_summary")),
        "writes_audit_log": False,
        "creates_audit_log": False,
        "persists_reasoning_trace": False,
        "audit_log_verified": audit_log_verified,
    })

    return {
        "mode": DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_MODE,
        "report_id": int(getattr(report, "id")),
        "case_id": int(getattr(report, "case_id")),
        "persistence": persistence,
        "ai_summary_preview": plan.get("ai_summary_preview"),
        "persistence_result": persistence_result,
        "blocked_actions": plan.get("blocked_actions") or [],
        "quality_gate": quality_gate,
        "safety": api_safety,
        **api_safety,
    }
