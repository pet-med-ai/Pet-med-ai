# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import AuditLog, Case, DiagnosticReport
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import AuditLog, Case, DiagnosticReport


router = APIRouter(prefix="/api", tags=["audit"])


class AuditLogCreateIn(BaseModel):
    """
    Append-only audit log payload.

    V1 intentionally provides only create semantics. There are no update/delete
    routes for audit logs.
    """

    request_id: str = Field(..., min_length=1, max_length=100)
    patient_token: Optional[str] = Field(default=None, max_length=255)
    clinician_id: str = Field(..., min_length=1, max_length=100)
    model_version: Optional[str] = Field(default=None, max_length=100)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    suggested_action: Optional[str] = None
    action_taken: str = Field(..., min_length=1, max_length=100)
    override_reason: Optional[str] = None
    note: Optional[str] = None
    case_id: Optional[int] = None
    session_uid: Optional[str] = Field(default=None, max_length=64)
    event_type: str = Field(default="ai_review", min_length=1, max_length=100)
    source: str = Field(default="pet-med-ai", min_length=1, max_length=100)
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


def _clean(value: Optional[str]) -> str:
    return str(value or "").strip()


def _assert_owned_case_if_present(db: Session, user: Any, case_id: Optional[int]) -> None:
    if case_id is None:
        return

    case = db.get(Case, case_id)
    if not case or getattr(case, "owner_id", None) != getattr(user, "id", None):
        raise HTTPException(status_code=404, detail="Case not found")


@router.post("/audit-log", response_model=dict, status_code=201)
def create_audit_log(
    data: AuditLogCreateIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Append one audit event.

    Important:
    - This endpoint only creates audit log rows.
    - No update/delete endpoint is exposed.
    - Use a new audit row for any correction or supplemental note.
    """

    request_id = _clean(data.request_id)
    clinician_id = _clean(data.clinician_id)
    action_taken = _clean(data.action_taken)
    event_type = _clean(data.event_type) or "ai_review"
    source = _clean(data.source) or "pet-med-ai"

    if not request_id:
        raise HTTPException(status_code=422, detail="request_id is required")
    if not clinician_id:
        raise HTTPException(status_code=422, detail="clinician_id is required")
    if not action_taken:
        raise HTTPException(status_code=422, detail="action_taken is required")

    _assert_owned_case_if_present(db, user, data.case_id)

    obj = AuditLog(
        request_id=request_id,
        patient_token=_clean(data.patient_token) or None,
        clinician_id=clinician_id,
        model_version=_clean(data.model_version) or None,
        confidence=data.confidence,
        suggested_action=_clean(data.suggested_action) or None,
        action_taken=action_taken,
        override_reason=_clean(data.override_reason) or None,
        note=_clean(data.note) or None,
        case_id=data.case_id,
        session_uid=_clean(data.session_uid) or None,
        event_type=event_type,
        source=source,
        extra_data=data.metadata or None,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)

    return {
        "message": "created",
        "mode": "append_only",
        "log_id": obj.log_id,
        "request_id": obj.request_id,
        "case_id": obj.case_id,
        "session_uid": obj.session_uid,
        "event_type": obj.event_type,
        "source": obj.source,
        "created_at": obj.created_at.isoformat() if isinstance(obj.created_at, datetime) else None,
        "append_only": True,
        "can_update": False,
        "can_delete": False,
    }

# --- Diagnostic Summary Audit Log V1 endpoint: start ---
@router.post("/diagnostic-data/diagnostic-summary/audit-log/append", response_model=dict)
def append_diagnostic_summary_audit_log(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.diagnostic_summary_audit_log import (
            DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE,
            build_diagnostic_summary_audit_log_event,
            diagnostic_summary_audit_log_safety_flags,
        )
    except ModuleNotFoundError:
        from diagnostic_summary_audit_log import (
            DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE,
            build_diagnostic_summary_audit_log_event,
            diagnostic_summary_audit_log_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    raw_case_id = data.get("case_id")
    if raw_case_id in (None, ""):
        raise HTTPException(status_code=422, detail="case_id is required")

    try:
        case_id = int(raw_case_id)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="case_id must be an integer") from exc

    _assert_owned_case_if_present(db, user, case_id)
    case = db.get(Case, case_id)
    if case is None or getattr(case, "deleted_at", None) is not None:
        raise HTTPException(status_code=404, detail="Case not found")

    normalized_payload = dict(data)
    raw_target_type = str(
        normalized_payload.get("target_type")
        or normalized_payload.get("target")
        or ""
    ).strip().lower().replace("-", "_").replace(" ", "_")
    raw_target_id = (
        normalized_payload.get("diagnostic_report_id")
        or normalized_payload.get("target_id")
        or normalized_payload.get("report_id")
    )

    if raw_target_type in {"diagnostic_report", "diagnostic_reports", "report"} or raw_target_id not in (None, ""):
        if raw_target_id in (None, ""):
            raise HTTPException(status_code=422, detail="diagnostic_report target_id is required")
        try:
            target_id = int(raw_target_id)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="diagnostic_report target_id must be an integer") from exc
        report = db.get(DiagnosticReport, target_id)
        if report is None or int(getattr(report, "case_id", -1)) != int(case.id):
            raise HTTPException(status_code=404, detail="diagnostic report target not found")
        normalized_payload["target_type"] = "diagnostic_report"
        normalized_payload["target_id"] = target_id

    case_payload = {
        "case_id": int(case.id),
        "patient_name": getattr(case, "patient_name", None),
        "species": getattr(case, "species", None),
    }

    try:
        plan = build_diagnostic_summary_audit_log_event(
            normalized_payload,
            case_id=int(case.id),
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    dry_run = bool(plan.get("dry_run"))
    persisted = False
    log_id = None
    created_at = None

    if not dry_run:
        event = plan.get("audit_event") or {}
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        metadata = dict(metadata)
        metadata.update({
            "case_context": case_payload,
            "api_endpoint": "/api/diagnostic-data/diagnostic-summary/audit-log/append",
            "writes_case_database": False,
            "writes_diagnostic_report": False,
            "writes_observation": False,
            "writes_imaging_study": False,
            "writes_ai_summary": False,
            "writes_audit_log": True,
        })

        obj = AuditLog(
            request_id=event["request_id"],
            patient_token=event.get("patient_token"),
            clinician_id=event["clinician_id"],
            model_version=event.get("model_version"),
            confidence=None,
            suggested_action=event.get("suggested_action"),
            action_taken=event["action_taken"],
            override_reason=event.get("override_reason"),
            note=event.get("note"),
            case_id=int(case.id),
            session_uid=event.get("session_uid"),
            event_type=event.get("event_type") or "diagnostic_summary_review",
            source=event.get("source") or DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE,
            extra_data=metadata,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        persisted = True
        log_id = obj.log_id
        created_at = obj.created_at.isoformat() if isinstance(obj.created_at, datetime) else None

    api_safety = diagnostic_summary_audit_log_safety_flags(
        dry_run=dry_run,
        writes_audit_log=persisted,
    )

    audit_log_result = dict(plan.get("audit_log_result") or {})
    audit_log_result.update({
        "persisted": persisted,
        "audit_log_id": log_id,
        "created_at": created_at,
        "append_only": True,
        "can_update": False,
        "can_delete": False,
    })

    quality_gate = dict(plan.get("quality_gate") or {})
    quality_gate.update({
        "status": "PASS",
        "writes_database": bool(api_safety.get("writes_database")),
        "writes_audit_log": bool(api_safety.get("writes_audit_log")),
        "updates_case": False,
        "updates_diagnostic_report": False,
        "updates_observation": False,
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "persists_reasoning_trace": False,
    })

    return {
        "message": "diagnostic_summary_audit_log_appended",
        "mode": DIAGNOSTIC_SUMMARY_AUDIT_LOG_MODE,
        "case": case_payload,
        "audit_event": plan.get("audit_event"),
        "audit_log_result": audit_log_result,
        "quality_gate": quality_gate,
        "safety": api_safety,
        **api_safety,
    }
# --- Diagnostic Summary Audit Log V1 endpoint: end ---

# --- Treatment Framework Audit Log V1 endpoint: start ---
@router.post("/diagnostic-data/confirmed-diagnosis/treatment-framework/audit-log/append", response_model=dict)
def append_treatment_framework_audit_log_endpoint(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.treatment_framework_audit_log import (
            TREATMENT_FRAMEWORK_AUDIT_LOG_MODE,
            build_treatment_framework_audit_log_event,
            treatment_framework_audit_log_safety_flags,
        )
    except ModuleNotFoundError:
        from treatment_framework_audit_log import (
            TREATMENT_FRAMEWORK_AUDIT_LOG_MODE,
            build_treatment_framework_audit_log_event,
            treatment_framework_audit_log_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    raw_case_id = data.get("case_id")
    if raw_case_id in (None, ""):
        raise HTTPException(status_code=422, detail="case_id is required")
    try:
        case_id = int(raw_case_id)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="case_id must be an integer") from exc

    _assert_owned_case_if_present(db, user, case_id)
    case = db.get(Case, case_id)
    if case is None or getattr(case, "deleted_at", None) is not None:
        raise HTTPException(status_code=404, detail="Case not found")

    case_payload = {"case_id": int(case.id), "patient_name": getattr(case, "patient_name", None), "species": getattr(case, "species", None)}
    payload = dict(data)
    payload["case_id"] = int(case.id)

    try:
        plan = build_treatment_framework_audit_log_event(payload, case_context=case_payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    dry_run = bool(plan.get("dry_run"))
    persisted = False
    log_id = None
    created_at = None

    if not dry_run:
        event = plan.get("audit_event") or {}
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        metadata = dict(metadata)
        metadata.update({"case_context": case_payload, "api_endpoint": "/api/diagnostic-data/confirmed-diagnosis/treatment-framework/audit-log/append", "writes_case_treatment": False, "writes_prescription": False, "writes_treatment_framework": False, "writes_audit_log": True, "append_only_audit_log": True})
        obj = AuditLog(
            request_id=event["request_id"],
            patient_token=event.get("patient_token"),
            clinician_id=event["clinician_id"],
            model_version=event.get("model_version"),
            confidence=None,
            suggested_action=event.get("suggested_action"),
            action_taken=event["action_taken"],
            override_reason=event.get("override_reason"),
            note=event.get("note"),
            case_id=int(case.id),
            session_uid=event.get("session_uid"),
            event_type=event.get("event_type") or "treatment_framework_review",
            source=event.get("source") or TREATMENT_FRAMEWORK_AUDIT_LOG_MODE,
            extra_data=metadata,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        persisted = True
        log_id = obj.log_id
        created_at = obj.created_at.isoformat() if isinstance(obj.created_at, datetime) else None

    api_safety = treatment_framework_audit_log_safety_flags(dry_run=dry_run, writes_audit_log=persisted)
    audit_log_result = dict(plan.get("audit_log_result") or {})
    audit_log_result.update({"persisted": persisted, "audit_log_id": log_id, "created_at": created_at, "append_only": True, "can_update": False, "can_delete": False})
    quality_gate = dict(plan.get("quality_gate") or {})
    quality_gate.update({"status": "PASS", "writes_database": bool(api_safety.get("writes_database")), "writes_audit_log": bool(api_safety.get("writes_audit_log")), "writes_case_treatment": False, "writes_prescription": False, "persists_treatment_framework": False, "returns_drug_dose": False, "returns_drug_route": False, "returns_drug_frequency": False})

    return {"message": "treatment_framework_audit_log_appended", "mode": TREATMENT_FRAMEWORK_AUDIT_LOG_MODE, "case": case_payload, "confirmed_diagnosis": plan.get("confirmed_diagnosis"), "review_workflow": plan.get("review_workflow"), "treatment_framework_preview_summary": plan.get("treatment_framework_preview_summary"), "audit_event": plan.get("audit_event"), "audit_log_result": audit_log_result, "quality_gate": quality_gate, "safety": api_safety, **api_safety}
# --- Treatment Framework Audit Log V1 endpoint: end ---
