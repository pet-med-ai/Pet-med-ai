# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import AutomatedReminderDeliveryTemplate
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import AutomatedReminderDeliveryTemplate


router = APIRouter(prefix="/api/automated-reminder-delivery/templates", tags=["automated-reminder-delivery-templates"])

PLACEHOLDER_RE = re.compile(r"{{\s*([A-Za-z0-9_.-]+)\s*}}")


class AutomatedReminderDeliveryTemplateCreateIn(BaseModel):
    template_key: str = Field(..., min_length=1, max_length=120)
    template_version: str = Field(default="v1", min_length=1, max_length=50)
    channel: str = Field(..., min_length=1, max_length=50)
    language: str = Field(default="zh-CN", max_length=20)
    category: str = Field(..., min_length=1, max_length=100)

    subject: Optional[str] = Field(default=None, max_length=255)
    body: str = Field(..., min_length=1)
    clinical_safety_text: Optional[str] = None
    opt_out_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AutomatedReminderDeliveryTemplateReviewIn(BaseModel):
    review_status: str = Field(..., min_length=1, max_length=50)
    reviewed_by: str = Field(..., min_length=1, max_length=100)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AutomatedReminderDeliveryTemplatePreviewIn(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


def _now() -> datetime:
    return datetime.utcnow()


def _require_user(user) -> int:
    value = getattr(user, "id", None)
    if value is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return int(value)


def _template_or_404(db: Session, template_id: int) -> AutomatedReminderDeliveryTemplate:
    template = db.get(AutomatedReminderDeliveryTemplate, int(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="automated reminder delivery template not found")
    return template


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


def _unreplaced_placeholders(*parts: str) -> list[str]:
    found = []
    for part in parts:
        found.extend(PLACEHOLDER_RE.findall(part or ""))
    return sorted(set(found))


def _hash_message(subject: str, body: str) -> str:
    return hashlib.sha256(f"{subject}\n{body}".encode("utf-8")).hexdigest()


def _template_payload(template: AutomatedReminderDeliveryTemplate) -> Dict[str, Any]:
    return {
        "id": template.id,
        "template_key": template.template_key,
        "template_version": template.template_version,
        "channel": template.channel,
        "language": template.language,
        "category": template.category,
        "subject": template.subject,
        "body": template.body,
        "clinical_safety_text": template.clinical_safety_text,
        "opt_out_text": template.opt_out_text,
        "review_status": template.review_status,
        "approved_by": template.approved_by,
        "approved_at": template.approved_at.isoformat() if template.approved_at else None,
        "metadata": template.extra_data,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.get("", response_model=dict)
def list_automated_reminder_delivery_templates(
    channel: Optional[str] = None,
    category: Optional[str] = None,
    review_status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_user(user)
    q = db.query(AutomatedReminderDeliveryTemplate)
    if channel:
        q = q.filter(AutomatedReminderDeliveryTemplate.channel == channel)
    if category:
        q = q.filter(AutomatedReminderDeliveryTemplate.category == category)
    if review_status:
        q = q.filter(AutomatedReminderDeliveryTemplate.review_status == review_status)

    total = q.count()
    items = (
        q.order_by(desc(AutomatedReminderDeliveryTemplate.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "message": "automated_reminder_delivery_templates",
        "mode": "automated_reminder_delivery_template_registry_v1",
        "items": [_template_payload(item) for item in items],
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


@router.post("", response_model=dict, status_code=201)
def create_automated_reminder_delivery_template(
    data: AutomatedReminderDeliveryTemplateCreateIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _require_user(user)
    template = AutomatedReminderDeliveryTemplate(
        template_key=data.template_key.strip(),
        template_version=data.template_version.strip(),
        channel=data.channel.strip(),
        language=data.language.strip() or "zh-CN",
        category=data.category.strip(),
        subject=data.subject,
        body=data.body,
        clinical_safety_text=data.clinical_safety_text,
        opt_out_text=data.opt_out_text,
        review_status="draft",
        approved_by=None,
        approved_at=None,
        extra_data={
            "source": "automated-reminder-delivery-template-registry-v1",
            "created_by_user_id": user_id,
            "metadata": data.metadata or {},
            "auto_send": False,
            "sends_external_message": False,
        },
        created_at=_now(),
        updated_at=_now(),
    )
    try:
        db.add(template)
        db.commit()
        db.refresh(template)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="template_key/template_version/channel already exists")

    return {
        "message": "automated_reminder_delivery_template_created",
        "mode": "automated_reminder_delivery_template_registry_v1",
        "template": _template_payload(template),
        "writes_database": True,
        "writes_template_registry": True,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.get("/{template_id}", response_model=dict)
def get_automated_reminder_delivery_template(
    template_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_user(user)
    template = _template_or_404(db, template_id)
    return {
        "message": "automated_reminder_delivery_template",
        "mode": "automated_reminder_delivery_template_registry_v1",
        "template": _template_payload(template),
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/{template_id}/render-preview", response_model=dict)
def render_automated_reminder_delivery_template_preview(
    template_id: int,
    data: AutomatedReminderDeliveryTemplatePreviewIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_user(user)
    template = _template_or_404(db, template_id)
    rendered_subject = _render_text(template.subject, data.context)
    rendered_body = _render_text(template.body, data.context)
    rendered_safety = _render_text(template.clinical_safety_text, data.context)
    rendered_opt_out = _render_text(template.opt_out_text, data.context)
    message_hash = _hash_message(rendered_subject, rendered_body)

    return {
        "message": "automated_reminder_delivery_template_render_preview",
        "mode": "automated_reminder_delivery_template_registry_v1",
        "template_id": template.id,
        "template_key": template.template_key,
        "template_version": template.template_version,
        "channel": template.channel,
        "rendered": {
            "subject": rendered_subject,
            "body": rendered_body,
            "clinical_safety_text": rendered_safety,
            "opt_out_text": rendered_opt_out,
            "message_hash": message_hash,
            "unreplaced_placeholders": _unreplaced_placeholders(rendered_subject, rendered_body, rendered_safety, rendered_opt_out),
        },
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/{template_id}/review", response_model=dict)
def review_automated_reminder_delivery_template(
    template_id: int,
    data: AutomatedReminderDeliveryTemplateReviewIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_user(user)
    template = _template_or_404(db, template_id)
    status = data.review_status.strip().lower()
    allowed = {"draft", "approved", "changes_requested", "rejected"}
    if status not in allowed:
        raise HTTPException(status_code=422, detail=f"review_status must be one of: {', '.join(sorted(allowed))}")

    if status == "approved":
        if not (template.clinical_safety_text or "").strip():
            raise HTTPException(status_code=422, detail="clinical_safety_text is required before approval")
        template.approved_by = data.reviewed_by.strip()
        template.approved_at = _now()
    else:
        template.approved_by = data.reviewed_by.strip()
        template.approved_at = None

    template.review_status = status
    template.updated_at = _now()
    template.extra_data = {
        **(template.extra_data or {}),
        "review_note": data.note,
        "review_metadata": data.metadata or {},
        "reviewed_by": data.reviewed_by,
        "auto_send": False,
        "sends_external_message": False,
    }

    db.add(template)
    db.commit()
    db.refresh(template)

    return {
        "message": "automated_reminder_delivery_template_reviewed",
        "mode": "automated_reminder_delivery_template_registry_v1",
        "template": _template_payload(template),
        "writes_database": True,
        "writes_template_registry": True,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/{template_id}/retire", response_model=dict)
def retire_automated_reminder_delivery_template(
    template_id: int,
    data: AutomatedReminderDeliveryTemplateReviewIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_user(user)
    template = _template_or_404(db, template_id)
    template.review_status = "retired"
    template.approved_at = None
    template.approved_by = data.reviewed_by.strip()
    template.updated_at = _now()
    template.extra_data = {
        **(template.extra_data or {}),
        "retire_note": data.note,
        "retire_metadata": data.metadata or {},
        "retired_by": data.reviewed_by,
        "auto_send": False,
        "sends_external_message": False,
    }

    db.add(template)
    db.commit()
    db.refresh(template)

    return {
        "message": "automated_reminder_delivery_template_retired",
        "mode": "automated_reminder_delivery_template_registry_v1",
        "template": _template_payload(template),
        "writes_database": True,
        "writes_template_registry": True,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }
