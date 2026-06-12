# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import re
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
    from backend.automated_reminder_delivery_eligibility import evaluate_delivery_eligibility
    from backend.models import (
        AutomatedReminderDeliveryAttempt,
        AutomatedReminderDeliveryTemplate,
        PreventiveCareClientPreference,
        PreventiveCareNotificationQueue,
        PreventiveCareReminder,
    )
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from automated_reminder_delivery_eligibility import evaluate_delivery_eligibility
    from models import (
        AutomatedReminderDeliveryAttempt,
        AutomatedReminderDeliveryTemplate,
        PreventiveCareClientPreference,
        PreventiveCareNotificationQueue,
        PreventiveCareReminder,
    )


router = APIRouter(prefix="/api/automated-reminder-delivery", tags=["automated-reminder-delivery-dry-run"])

PLACEHOLDER_RE = re.compile(r"{{\s*([A-Za-z0-9_.-]+)\s*}}")


class AutomatedReminderDeliveryDryRunIn(BaseModel):
    reminder_id: str = Field(..., min_length=1, max_length=64)
    notification_id: Optional[str] = Field(default=None, max_length=64)
    template_id: int = Field(..., ge=1)
    channel: str = Field(default="sms", max_length=50)

    context: Dict[str, Any] = Field(default_factory=dict)
    destination_exists: bool = True
    contact_destination_hash: Optional[str] = Field(default=None, max_length=128)

    feature_flags: Dict[str, Any] = Field(default_factory=dict)
    rate_limits: Dict[str, Any] = Field(default_factory=dict)
    quiet_hours: Dict[str, Any] = Field(default_factory=dict)
    suppression: Dict[str, Any] = Field(default_factory=dict)
    provider: Dict[str, Any] = Field(default_factory=dict)

    manual_approval_required: bool = True
    save_attempt: bool = True
    metadata: Optional[Dict[str, Any]] = None


class AutomatedReminderDeliveryAttemptCancelIn(BaseModel):
    canceled_by: str = Field(..., min_length=1, max_length=100)
    reason: Optional[str] = None
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def _now() -> datetime:
    return datetime.utcnow()


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


def _notification_or_404(
    db: Session,
    notification_id: Optional[str],
    user,
) -> Optional[PreventiveCareNotificationQueue]:
    if not notification_id:
        return None
    item = db.get(PreventiveCareNotificationQueue, notification_id)
    if not item or int(item.owner_id) != _user_id(user):
        raise HTTPException(status_code=404, detail="preventive care notification queue item not found")
    return item


def _template_or_404(db: Session, template_id: int) -> AutomatedReminderDeliveryTemplate:
    template = db.get(AutomatedReminderDeliveryTemplate, int(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="automated reminder delivery template not found")
    return template


def _attempt_or_404(db: Session, delivery_id: str, user) -> AutomatedReminderDeliveryAttempt:
    attempt = db.get(AutomatedReminderDeliveryAttempt, delivery_id)
    if not attempt or int(attempt.owner_id) != _user_id(user):
        raise HTTPException(status_code=404, detail="automated reminder delivery attempt not found")
    return attempt


def _client_preferences(db: Session, owner_id: int) -> Optional[PreventiveCareClientPreference]:
    return (
        db.query(PreventiveCareClientPreference)
        .filter(PreventiveCareClientPreference.owner_id == owner_id)
        .first()
    )


def _render_text(text: Optional[str], context: Dict[str, Any]) -> str:
    if not text:
        return ""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = context.get(key)
        if value is None:
            return match.group(0)
        return str(value)

    return PLACEHOLDER_RE.sub(repl, text)


def _message_hash(subject: str, body: str, safety: str, opt_out: str) -> str:
    return hashlib.sha256(f"{subject}\n{body}\n{safety}\n{opt_out}".encode("utf-8")).hexdigest()


def _attempt_payload(attempt: AutomatedReminderDeliveryAttempt) -> Dict[str, Any]:
    return {
        "delivery_id": attempt.delivery_id,
        "owner_id": attempt.owner_id,
        "reminder_id": attempt.reminder_id,
        "notification_id": attempt.notification_id,
        "channel": attempt.channel,
        "template_key": attempt.template_key,
        "template_version": attempt.template_version,
        "eligibility_result": attempt.eligibility_result,
        "blocked_reason": attempt.blocked_reason,
        "status": attempt.status,
        "manual_review_required": attempt.manual_review_required,
        "approved_by": attempt.approved_by,
        "approved_at": attempt.approved_at.isoformat() if attempt.approved_at else None,
        "dry_run": attempt.dry_run,
        "auto_send": attempt.auto_send,
        "sends_external_message": attempt.sends_external_message,
        "consent_snapshot": attempt.consent_snapshot,
        "opt_out_snapshot": attempt.opt_out_snapshot,
        "contact_destination_hash": attempt.contact_destination_hash,
        "message_hash": attempt.message_hash,
        "provider_name": attempt.provider_name,
        "provider_message_id": attempt.provider_message_id,
        "attempt_count": attempt.attempt_count,
        "last_error": attempt.last_error,
        "queued_at": attempt.queued_at.isoformat() if attempt.queued_at else None,
        "sent_at": attempt.sent_at.isoformat() if attempt.sent_at else None,
        "delivered_at": attempt.delivered_at.isoformat() if attempt.delivered_at else None,
        "failed_at": attempt.failed_at.isoformat() if attempt.failed_at else None,
        "canceled_at": attempt.canceled_at.isoformat() if attempt.canceled_at else None,
        "metadata": attempt.extra_data,
        "created_at": attempt.created_at.isoformat() if attempt.created_at else None,
        "updated_at": attempt.updated_at.isoformat() if attempt.updated_at else None,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


def _build_consent_snapshot(pref: Optional[PreventiveCareClientPreference]) -> Dict[str, Any]:
    if not pref:
        return {
            "allow_in_app": True,
            "allow_sms": False,
            "allow_wechat": False,
            "allow_email": False,
            "opt_out_all": False,
            "preferred_channel": "in_app",
            "consent_source": "",
        }
    return {
        "allow_in_app": bool(pref.allow_in_app),
        "allow_sms": bool(pref.allow_sms),
        "allow_wechat": bool(pref.allow_wechat),
        "allow_email": bool(pref.allow_email),
        "opt_out_all": bool(pref.opt_out_all),
        "preferred_channel": pref.preferred_channel,
        "consent_source": (pref.extra_data or {}).get("consent_source") or "preventive_care_client_preferences",
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
    }


def _default_flags(overrides: Dict[str, Any]) -> Dict[str, Any]:
    flags = {
        "ENABLE_PREVENTIVE_AUTO_DELIVERY": False,
        "ENABLE_PREVENTIVE_SMS_DELIVERY": False,
        "ENABLE_PREVENTIVE_WECHAT_DELIVERY": False,
        "ENABLE_PREVENTIVE_EMAIL_DELIVERY": False,
        "ENABLE_PREVENTIVE_DELIVERY_DRY_RUN": True,
        "ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL": True,
    }
    flags.update(overrides or {})
    return flags


def _eligibility_payload(
    *,
    data: AutomatedReminderDeliveryDryRunIn,
    reminder: PreventiveCareReminder,
    notification: Optional[PreventiveCareNotificationQueue],
    template: AutomatedReminderDeliveryTemplate,
    pref: Optional[PreventiveCareClientPreference],
) -> Dict[str, Any]:
    consent = _build_consent_snapshot(pref)
    notification_payload = {
        "notification_id": notification.notification_id,
        "status": notification.status,
        "reviewed_by": notification.reviewed_by,
        "client_opt_out_snapshot": notification.client_opt_out_snapshot,
    } if notification else {
        "notification_id": data.notification_id,
        "status": "missing",
        "reviewed_by": "",
        "client_opt_out_snapshot": False,
    }

    provider = {
        "name": data.provider.get("name") or "dry_run_provider",
        "credentials_available": bool(data.provider.get("credentials_available", False)),
    }

    return {
        "dry_run": True,
        "channel": data.channel,
        "feature_flags": _default_flags(data.feature_flags),
        "owner": {
            "owner_id": reminder.owner_id,
            "opt_out_all": consent.get("opt_out_all", False),
            "consent": consent,
        },
        "reminder": {
            "reminder_id": reminder.reminder_id,
            "owner_id": reminder.owner_id,
            "category": reminder.category,
            "client_opt_out": reminder.client_opt_out,
        },
        "notification_queue": notification_payload,
        "template": {
            "template_key": template.template_key,
            "template_version": template.template_version,
            "review_status": template.review_status,
            "approved_by": template.approved_by,
        },
        "destination": {
            "exists": bool(data.destination_exists),
            "contact_destination_hash": data.contact_destination_hash,
        },
        "provider": provider,
        "rate_limits": data.rate_limits or {},
        "quiet_hours": data.quiet_hours or {},
        "suppression": data.suppression or {},
        "manual_approval_required": data.manual_approval_required,
    }


@router.post("/dry-run", response_model=dict, status_code=201)
def create_automated_reminder_delivery_dry_run(
    data: AutomatedReminderDeliveryDryRunIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    reminder = _reminder_or_404(db, data.reminder_id, user)
    notification = _notification_or_404(db, data.notification_id, user)
    template = _template_or_404(db, data.template_id)
    pref = _client_preferences(db, reminder.owner_id)

    rendered_subject = _render_text(template.subject, data.context)
    rendered_body = _render_text(template.body, data.context)
    rendered_safety = _render_text(template.clinical_safety_text, data.context)
    rendered_opt_out = _render_text(template.opt_out_text, data.context)
    rendered_hash = _message_hash(rendered_subject, rendered_body, rendered_safety, rendered_opt_out)

    eligibility_payload = _eligibility_payload(
        data=data,
        reminder=reminder,
        notification=notification,
        template=template,
        pref=pref,
    )
    eligibility = evaluate_delivery_eligibility(eligibility_payload)

    attempt = None
    if data.save_attempt:
        now = _now()
        status = "dry_run_only"
        attempt = AutomatedReminderDeliveryAttempt(
            delivery_id=f"ard_{uuid4().hex}",
            owner_id=reminder.owner_id,
            reminder_id=reminder.reminder_id,
            notification_id=notification.notification_id if notification else None,
            channel=data.channel,
            template_key=template.template_key,
            template_version=template.template_version,
            eligibility_result="eligible" if eligibility.get("eligible_for_live_send") else "blocked",
            blocked_reason=eligibility.get("first_blocked_reason"),
            status=status,
            manual_review_required=True,
            approved_by=None,
            approved_at=None,
            dry_run=True,
            auto_send=False,
            sends_external_message=False,
            consent_snapshot=eligibility_payload["owner"]["consent"],
            opt_out_snapshot={
                "owner_opt_out_all": eligibility_payload["owner"].get("opt_out_all"),
                "reminder_client_opt_out": reminder.client_opt_out,
                "queue_client_opt_out_snapshot": notification.client_opt_out_snapshot if notification else False,
            },
            contact_destination_hash=data.contact_destination_hash,
            message_hash=rendered_hash,
            provider_name=(data.provider or {}).get("name") or "dry_run_provider",
            provider_message_id=None,
            attempt_count=0,
            last_error=None,
            queued_at=None,
            sent_at=None,
            delivered_at=None,
            failed_at=None,
            canceled_at=None,
            extra_data={
                "source": "automated-reminder-delivery-api-dry-run-v1",
                "eligibility": eligibility,
                "rendered": {
                    "subject": rendered_subject,
                    "body": rendered_body,
                    "clinical_safety_text": rendered_safety,
                    "opt_out_text": rendered_opt_out,
                },
                "metadata": data.metadata or {},
                "dry_run": True,
                "auto_send": False,
                "sends_external_message": False,
            },
            created_at=now,
            updated_at=now,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

    return {
        "message": "automated_reminder_delivery_dry_run_created",
        "mode": "automated_reminder_delivery_api_dry_run_v1",
        "eligibility": eligibility,
        "rendered": {
            "subject": rendered_subject,
            "body": rendered_body,
            "clinical_safety_text": rendered_safety,
            "opt_out_text": rendered_opt_out,
            "message_hash": rendered_hash,
        },
        "attempt": _attempt_payload(attempt) if attempt else None,
        "writes_database": bool(data.save_attempt),
        "writes_delivery_attempt": bool(data.save_attempt),
        "dry_run": True,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.get("/attempts", response_model=dict)
def list_automated_reminder_delivery_attempts(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    owner_id = _user_id(user)
    q = db.query(AutomatedReminderDeliveryAttempt).filter(AutomatedReminderDeliveryAttempt.owner_id == owner_id)
    if status:
        q = q.filter(AutomatedReminderDeliveryAttempt.status == status)
    if channel:
        q = q.filter(AutomatedReminderDeliveryAttempt.channel == channel)

    total = q.count()
    items = (
        q.order_by(desc(AutomatedReminderDeliveryAttempt.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "message": "automated_reminder_delivery_attempts",
        "mode": "automated_reminder_delivery_api_dry_run_v1",
        "items": [_attempt_payload(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.get("/attempts/{delivery_id}", response_model=dict)
def get_automated_reminder_delivery_attempt(
    delivery_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    attempt = _attempt_or_404(db, delivery_id, user)
    return {
        "message": "automated_reminder_delivery_attempt",
        "mode": "automated_reminder_delivery_api_dry_run_v1",
        "attempt": _attempt_payload(attempt),
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/attempts/{delivery_id}/cancel", response_model=dict)
def cancel_automated_reminder_delivery_attempt(
    delivery_id: str,
    data: AutomatedReminderDeliveryAttemptCancelIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    attempt = _attempt_or_404(db, delivery_id, user)
    attempt.status = "canceled"
    attempt.canceled_at = _now()
    attempt.updated_at = _now()
    attempt.last_error = data.reason or attempt.last_error
    attempt.extra_data = {
        **(attempt.extra_data or {}),
        "canceled_by": data.canceled_by,
        "cancel_reason": data.reason,
        "cancel_note": data.note,
        "cancel_metadata": data.metadata or {},
        "auto_send": False,
        "sends_external_message": False,
    }
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "message": "automated_reminder_delivery_attempt_canceled",
        "mode": "automated_reminder_delivery_api_dry_run_v1",
        "attempt": _attempt_payload(attempt),
        "writes_database": True,
        "writes_delivery_attempt": True,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }
