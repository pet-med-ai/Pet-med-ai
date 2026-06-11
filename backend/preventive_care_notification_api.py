# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import (
        PreventiveCareClientPreference,
        PreventiveCareNotificationQueue,
        PreventiveCareReminder,
    )
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import (
        PreventiveCareClientPreference,
        PreventiveCareNotificationQueue,
        PreventiveCareReminder,
    )


router = APIRouter(prefix="/api/preventive-care/notification-queue", tags=["preventive-care-notification-queue"])


class NotificationDraftIn(BaseModel):
    reminder_id: str = Field(..., min_length=1, max_length=64)
    channel: str = Field(default="phone_call", max_length=50)
    scheduled_for: Optional[str] = None
    message_preview: Optional[str] = None
    reviewed_by: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationReviewIn(BaseModel):
    action: str = Field(default="approve_for_manual_contact", max_length=80)
    reviewed_by: str = Field(..., min_length=1, max_length=100)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationContactedIn(BaseModel):
    contacted_by: str = Field(..., min_length=1, max_length=100)
    contact_result: str = Field(default="manual_contact_completed", max_length=100)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationCancelIn(BaseModel):
    canceled_by: str = Field(..., min_length=1, max_length=100)
    reason: Optional[str] = None
    note: Optional[str] = None


def _now() -> datetime:
    return datetime.utcnow()


def _parse_dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        try:
            return datetime.fromisoformat(text[:10])
        except Exception:
            raise HTTPException(status_code=422, detail=f"invalid datetime/date value: {text}")


def _user_id(user) -> int:
    value = getattr(user, "id", None)
    if value is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return int(value)


def _reminder_or_404(db: Session, reminder_id: str, user) -> PreventiveCareReminder:
    reminder = db.get(PreventiveCareReminder, reminder_id)
    if not reminder or int(reminder.owner_id) != _user_id(user):
        raise HTTPException(status_code=404, detail="preventive care reminder not found")
    return reminder


def _notification_or_404(db: Session, notification_id: str, user) -> PreventiveCareNotificationQueue:
    item = db.get(PreventiveCareNotificationQueue, notification_id)
    if not item or int(item.owner_id) != _user_id(user):
        raise HTTPException(status_code=404, detail="preventive care notification queue item not found")
    return item


def _client_opt_out_snapshot(db: Session, owner_id: int, reminder: PreventiveCareReminder) -> bool:
    pref = (
        db.query(PreventiveCareClientPreference)
        .filter(PreventiveCareClientPreference.owner_id == owner_id)
        .first()
    )
    return bool(getattr(reminder, "client_opt_out", False) or (pref and pref.opt_out_all))


def _default_message_preview(reminder: PreventiveCareReminder) -> str:
    pet_name = reminder.pet_name or "您的宠物"
    category = reminder.category or "预防保健"
    due = reminder.due_date.date().isoformat() if reminder.due_date else "近期"
    return (
        f"【预防保健提醒】{pet_name} 可能已到 {category} 的复核时间（{due}）。"
        "请联系医院确认具体接种/驱虫方案。此提醒不替代兽医诊断和处方。"
    )


def _notification_payload(item: PreventiveCareNotificationQueue) -> Dict[str, Any]:
    return {
        "notification_id": item.notification_id,
        "reminder_id": item.reminder_id,
        "owner_id": item.owner_id,
        "case_id": item.case_id,
        "channel": item.channel,
        "status": item.status,
        "scheduled_for": item.scheduled_for.isoformat() if item.scheduled_for else None,
        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
        "manual_review_required": item.manual_review_required,
        "reviewed_by": item.reviewed_by,
        "client_opt_out_snapshot": item.client_opt_out_snapshot,
        "message_preview": item.message_preview,
        "failure_code": item.failure_code,
        "failure_reason": item.failure_reason,
        "metadata": item.extra_data,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.get("", response_model=dict)
def list_notification_queue(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(PreventiveCareNotificationQueue).filter(PreventiveCareNotificationQueue.owner_id == _user_id(user))
    if status:
        q = q.filter(PreventiveCareNotificationQueue.status == status)
    if channel:
        q = q.filter(PreventiveCareNotificationQueue.channel == channel)

    total = q.count()
    items = (
        q.order_by(desc(PreventiveCareNotificationQueue.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "message": "preventive_care_notification_queue",
        "mode": "preventive_care_notification_queue_v1",
        "items": [_notification_payload(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/draft", response_model=dict, status_code=201)
def create_notification_queue_draft(
    data: NotificationDraftIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    reminder = _reminder_or_404(db, data.reminder_id, user)
    opt_out_snapshot = _client_opt_out_snapshot(db, _user_id(user), reminder)

    status = "blocked_opt_out" if opt_out_snapshot else "draft"
    item = PreventiveCareNotificationQueue(
        notification_id=f"pcn_{uuid4().hex}",
        reminder_id=reminder.reminder_id,
        owner_id=reminder.owner_id,
        case_id=reminder.case_id,
        channel=data.channel or "phone_call",
        status=status,
        scheduled_for=_parse_dt(data.scheduled_for),
        sent_at=None,
        manual_review_required=True,
        reviewed_by=data.reviewed_by,
        client_opt_out_snapshot=opt_out_snapshot,
        message_preview=data.message_preview or _default_message_preview(reminder),
        failure_code="client_opt_out" if opt_out_snapshot else None,
        failure_reason="client opted out; manual review required" if opt_out_snapshot else None,
        extra_data={
            "source": "preventive-care-notification-queue-v1",
            "note": data.note,
            "metadata": data.metadata or {},
            "auto_send": False,
            "sends_external_message": False,
        },
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "preventive_care_notification_draft_created",
        "mode": "preventive_care_notification_queue_v1",
        "notification": _notification_payload(item),
        "writes_database": True,
        "writes_notification_queue": True,
        "manual_review_required": True,
        "auto_send": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/{notification_id}/review", response_model=dict)
def review_notification_queue_item(
    notification_id: str,
    data: NotificationReviewIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = _notification_or_404(db, notification_id, user)
    if item.client_opt_out_snapshot:
        item.status = "blocked_opt_out"
        item.failure_code = "client_opt_out"
        item.failure_reason = "client opted out; cannot approve contact"
    else:
        item.status = "reviewed" if data.action == "approve_for_manual_contact" else "review_required"

    item.reviewed_by = data.reviewed_by
    item.manual_review_required = True
    item.extra_data = {
        **(item.extra_data or {}),
        "review_action": data.action,
        "review_note": data.note,
        "review_metadata": data.metadata or {},
        "auto_send": False,
        "sends_external_message": False,
    }
    item.updated_at = _now()

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "preventive_care_notification_reviewed",
        "mode": "preventive_care_notification_queue_v1",
        "notification": _notification_payload(item),
        "writes_database": True,
        "manual_review_required": True,
        "auto_send": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/{notification_id}/mark-contacted", response_model=dict)
def mark_notification_queue_contacted(
    notification_id: str,
    data: NotificationContactedIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = _notification_or_404(db, notification_id, user)
    if item.client_opt_out_snapshot:
        raise HTTPException(status_code=409, detail="client opted out; cannot mark contacted")

    item.status = "contacted_manually"
    item.sent_at = _now()
    item.reviewed_by = item.reviewed_by or data.contacted_by
    item.manual_review_required = True
    item.extra_data = {
        **(item.extra_data or {}),
        "contacted_by": data.contacted_by,
        "contact_result": data.contact_result,
        "contact_note": data.note,
        "contact_metadata": data.metadata or {},
        "manual_contact_only": True,
        "auto_send": False,
        "sends_external_message": False,
    }
    item.updated_at = _now()

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "preventive_care_notification_marked_contacted",
        "mode": "preventive_care_notification_queue_v1",
        "notification": _notification_payload(item),
        "writes_database": True,
        "manual_contact_only": True,
        "auto_send": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/{notification_id}/cancel", response_model=dict)
def cancel_notification_queue_item(
    notification_id: str,
    data: NotificationCancelIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = _notification_or_404(db, notification_id, user)
    item.status = "canceled"
    item.failure_code = "canceled"
    item.failure_reason = data.reason
    item.extra_data = {
        **(item.extra_data or {}),
        "canceled_by": data.canceled_by,
        "cancel_note": data.note,
        "auto_send": False,
        "sends_external_message": False,
    }
    item.updated_at = _now()

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "preventive_care_notification_canceled",
        "mode": "preventive_care_notification_queue_v1",
        "notification": _notification_payload(item),
        "writes_database": True,
        "auto_send": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }
