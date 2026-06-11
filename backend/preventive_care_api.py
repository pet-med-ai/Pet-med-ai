# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta
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
        Case,
        PreventiveCareClientPreference,
        PreventiveCareEvent,
        PreventiveCareReminder,
    )
    from backend.preventive_care_rules import (
        compute_preventive_care_reminders,
        load_preventive_care_rules,
    )
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import (
        Case,
        PreventiveCareClientPreference,
        PreventiveCareEvent,
        PreventiveCareReminder,
    )
    from preventive_care_rules import (
        compute_preventive_care_reminders,
        load_preventive_care_rules,
    )


router = APIRouter(prefix="/api/preventive-care", tags=["preventive-care"])


class PreventiveCareDryRunIn(BaseModel):
    case_id: Optional[int] = Field(default=None, ge=1)
    pet: Optional[Dict[str, Any]] = None
    as_of_date: Optional[str] = None
    include_active: bool = True


class PreventiveCareReminderCreateIn(BaseModel):
    case_id: Optional[int] = Field(default=None, ge=1)
    pet_id: Optional[str] = Field(default=None, max_length=64)
    pet_name: Optional[str] = Field(default=None, max_length=255)
    species: Optional[str] = Field(default=None, max_length=50)
    category: str = Field(..., min_length=1, max_length=100)
    rule_id: Optional[str] = Field(default=None, max_length=100)
    source_rule_id: Optional[str] = Field(default=None, max_length=100)
    status: str = Field(default="active", max_length=50)
    due_date: Optional[str] = None
    due_window_start: Optional[str] = None
    due_window_end: Optional[str] = None
    reminder_lead_days: Optional[int] = Field(default=None, ge=0)
    clinician_override: bool = False
    override_reason: Optional[str] = None
    client_opt_out: bool = False
    channel_preference: str = Field(default="in_app", max_length=50)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PreventiveCareCompleteIn(BaseModel):
    event_type: str = Field(default="preventive_care_completed", max_length=100)
    event_date: Optional[str] = None
    product_name: Optional[str] = Field(default=None, max_length=255)
    lot_number: Optional[str] = Field(default=None, max_length=100)
    next_due_date: Optional[str] = None
    clinician_id: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PreventiveCareSnoozeIn(BaseModel):
    due_date: str
    due_window_start: Optional[str] = None
    due_window_end: Optional[str] = None
    reason: Optional[str] = None
    note: Optional[str] = None


class PreventiveCareDismissIn(BaseModel):
    reason: Optional[str] = None
    note: Optional[str] = None


class PreventiveCareClientPreferenceIn(BaseModel):
    allow_in_app: bool = True
    allow_sms: bool = False
    allow_wechat: bool = False
    allow_email: bool = False
    opt_out_all: bool = False
    preferred_channel: str = Field(default="in_app", max_length=50)
    updated_by: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


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


def _case_or_404(db: Session, case_id: Optional[int], user) -> Optional[Case]:
    if not case_id:
        return None
    case = db.get(Case, int(case_id))
    if not case or getattr(case, "owner_id", None) != _user_id(user):
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _reminder_or_404(db: Session, reminder_id: str, user) -> PreventiveCareReminder:
    reminder = db.get(PreventiveCareReminder, reminder_id)
    if not reminder or int(reminder.owner_id) != _user_id(user):
        raise HTTPException(status_code=404, detail="preventive care reminder not found")
    return reminder


def _case_pet_payload(case: Case) -> Dict[str, Any]:
    return {
        "owner_id": getattr(case, "owner_id", None),
        "case_id": getattr(case, "id", None),
        "pet_name": getattr(case, "patient_name", None),
        "species": getattr(case, "species", None),
        "life_stage": "adult",
    }


def _reminder_payload(reminder: PreventiveCareReminder) -> Dict[str, Any]:
    return {
        "reminder_id": reminder.reminder_id,
        "owner_id": reminder.owner_id,
        "case_id": reminder.case_id,
        "pet_id": reminder.pet_id,
        "pet_name": reminder.pet_name,
        "species": reminder.species,
        "category": reminder.category,
        "rule_id": reminder.rule_id,
        "source_rule_id": reminder.source_rule_id,
        "status": reminder.status,
        "due_date": reminder.due_date.isoformat() if reminder.due_date else None,
        "due_window_start": reminder.due_window_start.isoformat() if reminder.due_window_start else None,
        "due_window_end": reminder.due_window_end.isoformat() if reminder.due_window_end else None,
        "reminder_lead_days": reminder.reminder_lead_days,
        "last_completed_at": reminder.last_completed_at.isoformat() if reminder.last_completed_at else None,
        "next_due_date": reminder.next_due_date.isoformat() if reminder.next_due_date else None,
        "clinician_override": reminder.clinician_override,
        "override_reason": reminder.override_reason,
        "client_opt_out": reminder.client_opt_out,
        "channel_preference": reminder.channel_preference,
        "note": reminder.note,
        "metadata": reminder.extra_data,
        "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
        "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


def _preference_payload(pref: PreventiveCareClientPreference) -> Dict[str, Any]:
    return {
        "id": pref.id,
        "owner_id": pref.owner_id,
        "allow_in_app": pref.allow_in_app,
        "allow_sms": pref.allow_sms,
        "allow_wechat": pref.allow_wechat,
        "allow_email": pref.allow_email,
        "opt_out_all": pref.opt_out_all,
        "preferred_channel": pref.preferred_channel,
        "updated_by": pref.updated_by,
        "note": pref.note,
        "metadata": pref.extra_data,
        "created_at": pref.created_at.isoformat() if pref.created_at else None,
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
        "sends_external_message": False,
    }


@router.get("/rules", response_model=dict)
def list_preventive_care_rules(
    species: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rules = load_preventive_care_rules()
    items = []
    for rule in rules:
        if species and rule.species not in {species, "dog_cat"}:
            continue
        if category and rule.category != category:
            continue
        items.append({
            "rule_id": rule.rule_id,
            "species": rule.species,
            "life_stage": rule.life_stage,
            "category": rule.category,
            "trigger_basis": rule.trigger_basis,
            "interval_days": rule.interval_days,
            "due_window_days": rule.due_window_days,
            "lead_days": rule.lead_days,
            "requires_clinician_confirmation": rule.requires_clinician_confirmation,
            "requires_client_consent": rule.requires_client_consent,
            "allow_auto_send": False,
            "recommended_stage": rule.recommended_stage,
            "source_note": rule.source_note,
            "notes": rule.notes,
        })

    return {
        "message": "preventive_care_rules",
        "mode": "preventive_care_reminder_api_v1",
        "items": items,
        "total": len(items),
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/dry-run", response_model=dict)
def preventive_care_dry_run(
    data: PreventiveCareDryRunIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    case = _case_or_404(db, data.case_id, user)
    pet = dict(data.pet or {})
    if case:
        merged = _case_pet_payload(case)
        merged.update({key: value for key, value in pet.items() if value not in (None, "")})
        pet = merged

    if not pet:
        raise HTTPException(status_code=422, detail="pet payload or case_id is required")

    pet["owner_id"] = pet.get("owner_id") or _user_id(user)
    report = compute_preventive_care_reminders(
        pet,
        as_of=data.as_of_date,
        include_active=data.include_active,
    )
    return report


@router.get("/reminders", response_model=dict)
def list_preventive_care_reminders(
    status: Optional[str] = None,
    category: Optional[str] = None,
    case_id: Optional[int] = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(PreventiveCareReminder).filter(PreventiveCareReminder.owner_id == _user_id(user))
    if status:
        q = q.filter(PreventiveCareReminder.status == status)
    if category:
        q = q.filter(PreventiveCareReminder.category == category)
    if case_id:
        _case_or_404(db, case_id, user)
        q = q.filter(PreventiveCareReminder.case_id == int(case_id))

    total = q.count()
    reminders = (
        q.order_by(desc(PreventiveCareReminder.due_date), desc(PreventiveCareReminder.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "message": "preventive_care_reminders",
        "mode": "preventive_care_reminder_api_v1",
        "items": [_reminder_payload(item) for item in reminders],
        "total": total,
        "page": page,
        "page_size": page_size,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/reminders", response_model=dict, status_code=201)
def create_preventive_care_reminder(
    data: PreventiveCareReminderCreateIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    case = _case_or_404(db, data.case_id, user)

    pet_name = (data.pet_name or (getattr(case, "patient_name", None) if case else "") or "").strip()
    species = (data.species or (getattr(case, "species", None) if case else "") or "").strip()
    if not pet_name:
        raise HTTPException(status_code=422, detail="pet_name is required when case_id is not provided")
    if not species:
        raise HTTPException(status_code=422, detail="species is required when case_id is not provided")

    due_date = _parse_dt(data.due_date)
    due_window_start = _parse_dt(data.due_window_start) or (due_date - timedelta(days=7) if due_date else None)
    due_window_end = _parse_dt(data.due_window_end) or (due_date + timedelta(days=14) if due_date else None)

    reminder = PreventiveCareReminder(
        reminder_id=f"pcr_{uuid4().hex}",
        owner_id=_user_id(user),
        case_id=int(data.case_id) if data.case_id else None,
        pet_id=data.pet_id,
        pet_name=pet_name,
        species=species,
        category=data.category,
        rule_id=data.rule_id,
        source_rule_id=data.source_rule_id or data.rule_id,
        status=data.status,
        due_date=due_date,
        due_window_start=due_window_start,
        due_window_end=due_window_end,
        reminder_lead_days=data.reminder_lead_days,
        clinician_override=data.clinician_override,
        override_reason=data.override_reason,
        client_opt_out=data.client_opt_out,
        channel_preference=data.channel_preference or "in_app",
        note=data.note,
        extra_data=data.metadata,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return {
        "message": "preventive_care_reminder_created",
        "mode": "preventive_care_reminder_api_v1",
        "reminder": _reminder_payload(reminder),
        "writes_database": True,
        "writes_preventive_care_reminders": True,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/reminders/{reminder_id}/complete", response_model=dict)
def complete_preventive_care_reminder(
    reminder_id: str,
    data: PreventiveCareCompleteIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    reminder = _reminder_or_404(db, reminder_id, user)
    now = _now()
    event_date = _parse_dt(data.event_date) or now
    next_due_date = _parse_dt(data.next_due_date)

    reminder.status = "completed"
    reminder.last_completed_at = event_date
    reminder.next_due_date = next_due_date
    reminder.updated_at = now

    event = PreventiveCareEvent(
        event_id=f"pce_{uuid4().hex}",
        reminder_id=reminder.reminder_id,
        owner_id=reminder.owner_id,
        case_id=reminder.case_id,
        pet_id=reminder.pet_id,
        event_type=data.event_type,
        category=reminder.category,
        event_date=event_date,
        product_name=data.product_name,
        lot_number=data.lot_number,
        next_due_date=next_due_date,
        clinician_id=data.clinician_id,
        note=data.note,
        extra_data=data.metadata,
        created_at=now,
    )
    db.add(reminder)
    db.add(event)
    db.commit()
    db.refresh(reminder)
    db.refresh(event)

    return {
        "message": "preventive_care_reminder_completed",
        "mode": "preventive_care_reminder_api_v1",
        "reminder": _reminder_payload(reminder),
        "event": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "next_due_date": event.next_due_date.isoformat() if event.next_due_date else None,
        },
        "writes_database": True,
        "writes_preventive_care_events": True,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/reminders/{reminder_id}/snooze", response_model=dict)
def snooze_preventive_care_reminder(
    reminder_id: str,
    data: PreventiveCareSnoozeIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    reminder = _reminder_or_404(db, reminder_id, user)
    due_date = _parse_dt(data.due_date)
    if not due_date:
        raise HTTPException(status_code=422, detail="due_date is required")

    reminder.status = "snoozed"
    reminder.due_date = due_date
    reminder.due_window_start = _parse_dt(data.due_window_start) or due_date
    reminder.due_window_end = _parse_dt(data.due_window_end) or due_date + timedelta(days=14)
    reminder.override_reason = data.reason or reminder.override_reason
    reminder.note = data.note or reminder.note
    reminder.updated_at = _now()

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return {
        "message": "preventive_care_reminder_snoozed",
        "mode": "preventive_care_reminder_api_v1",
        "reminder": _reminder_payload(reminder),
        "writes_database": True,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/reminders/{reminder_id}/dismiss", response_model=dict)
def dismiss_preventive_care_reminder(
    reminder_id: str,
    data: PreventiveCareDismissIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    reminder = _reminder_or_404(db, reminder_id, user)
    reminder.status = "dismissed"
    reminder.override_reason = data.reason or reminder.override_reason
    reminder.note = data.note or reminder.note
    reminder.updated_at = _now()

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return {
        "message": "preventive_care_reminder_dismissed",
        "mode": "preventive_care_reminder_api_v1",
        "reminder": _reminder_payload(reminder),
        "writes_database": True,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.post("/reminders/{reminder_id}/disable", response_model=dict)
def disable_preventive_care_reminder(
    reminder_id: str,
    data: PreventiveCareDismissIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    reminder = _reminder_or_404(db, reminder_id, user)
    reminder.status = "disabled"
    reminder.client_opt_out = True
    reminder.override_reason = data.reason or reminder.override_reason
    reminder.note = data.note or reminder.note
    reminder.updated_at = _now()

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return {
        "message": "preventive_care_reminder_disabled",
        "mode": "preventive_care_reminder_api_v1",
        "reminder": _reminder_payload(reminder),
        "writes_database": True,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.get("/client-preferences", response_model=dict)
def get_preventive_care_client_preferences(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    pref = (
        db.query(PreventiveCareClientPreference)
        .filter(PreventiveCareClientPreference.owner_id == _user_id(user))
        .first()
    )
    return {
        "message": "preventive_care_client_preferences",
        "mode": "preventive_care_reminder_api_v1",
        "preferences": _preference_payload(pref) if pref else None,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }


@router.put("/client-preferences", response_model=dict)
def upsert_preventive_care_client_preferences(
    data: PreventiveCareClientPreferenceIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    pref = (
        db.query(PreventiveCareClientPreference)
        .filter(PreventiveCareClientPreference.owner_id == _user_id(user))
        .first()
    )
    if not pref:
        pref = PreventiveCareClientPreference(
            owner_id=_user_id(user),
            created_at=_now(),
        )

    pref.allow_in_app = data.allow_in_app
    pref.allow_sms = data.allow_sms
    pref.allow_wechat = data.allow_wechat
    pref.allow_email = data.allow_email
    pref.opt_out_all = data.opt_out_all
    pref.preferred_channel = data.preferred_channel
    pref.updated_by = data.updated_by
    pref.note = data.note
    pref.extra_data = data.metadata
    pref.updated_at = _now()

    db.add(pref)
    db.commit()
    db.refresh(pref)

    return {
        "message": "preventive_care_client_preferences_saved",
        "mode": "preventive_care_reminder_api_v1",
        "preferences": _preference_payload(pref),
        "writes_database": True,
        "writes_client_preferences": True,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }
