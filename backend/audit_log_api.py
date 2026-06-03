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
    from backend.models import AuditLog, Case
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import AuditLog, Case


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
