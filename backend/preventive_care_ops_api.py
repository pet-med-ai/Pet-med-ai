# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import (
        PreventiveCareClientPreference,
        PreventiveCareEvent,
        PreventiveCareNotificationQueue,
        PreventiveCareReminder,
    )
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import (
        PreventiveCareClientPreference,
        PreventiveCareEvent,
        PreventiveCareNotificationQueue,
        PreventiveCareReminder,
    )


router = APIRouter(prefix="/api/preventive-care/ops", tags=["preventive-care-ops"])


def _user_id(user) -> int:
    return int(getattr(user, "id"))


def _count_by(items: List[Any], attr: str) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for item in items:
        key = str(getattr(item, attr, None) or "unknown")
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _iso(value) -> str | None:
    return value.isoformat() if value else None


@router.get("/summary", response_model=dict)
def preventive_care_ops_summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Preventive Care Reminder Ops Dashboard V1.

    Authenticated, user-scoped, read-only operational summary.
    Does not create reminders, send messages, or mutate Case records.
    """
    owner_id = _user_id(user)
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    tomorrow_start = today_start + timedelta(days=1)

    reminders = (
        db.query(PreventiveCareReminder)
        .filter(PreventiveCareReminder.owner_id == owner_id)
        .all()
    )
    queue_items = (
        db.query(PreventiveCareNotificationQueue)
        .filter(PreventiveCareNotificationQueue.owner_id == owner_id)
        .all()
    )
    prefs = (
        db.query(PreventiveCareClientPreference)
        .filter(PreventiveCareClientPreference.owner_id == owner_id)
        .all()
    )
    recent_events = (
        db.query(PreventiveCareEvent)
        .filter(
            PreventiveCareEvent.owner_id == owner_id,
            PreventiveCareEvent.created_at >= now - timedelta(days=30),
        )
        .all()
    )

    due_today = [
        item for item in reminders
        if item.due_date and today_start <= item.due_date < tomorrow_start
    ]
    overdue = [
        item for item in reminders
        if item.due_date and item.due_date < today_start and item.status not in {"completed", "dismissed", "disabled"}
    ]
    due_soon = [
        item for item in reminders
        if item.status == "due_soon"
    ]
    open_reminders = [
        item for item in reminders
        if item.status not in {"completed", "dismissed", "disabled"}
    ]
    queue_needs_review = [
        item for item in queue_items
        if item.status in {"draft", "review_required"} or item.manual_review_required
    ]
    queue_blocked_opt_out = [
        item for item in queue_items
        if item.status == "blocked_opt_out" or item.client_opt_out_snapshot
    ]
    queue_contacted = [
        item for item in queue_items
        if item.status == "contacted_manually"
    ]

    attention_count = (
        len(overdue)
        + len(due_today)
        + len(queue_needs_review)
        + len(queue_blocked_opt_out)
    )

    return {
        "message": "preventive_care_ops_summary",
        "mode": "preventive_care_reminder_ops_dashboard_v1",
        "owner_id": owner_id,
        "generated_at": now.isoformat() + "Z",
        "reminders": {
            "total": len(reminders),
            "open": len(open_reminders),
            "due_today": len(due_today),
            "due_soon": len(due_soon),
            "overdue": len(overdue),
            "by_status": _count_by(reminders, "status"),
            "by_category": _count_by(reminders, "category"),
        },
        "notification_queue": {
            "total": len(queue_items),
            "needs_review": len(queue_needs_review),
            "blocked_opt_out": len(queue_blocked_opt_out),
            "contacted_manually": len(queue_contacted),
            "by_status": _count_by(queue_items, "status"),
            "by_channel": _count_by(queue_items, "channel"),
        },
        "client_preferences": {
            "total": len(prefs),
            "opt_out_all": sum(1 for item in prefs if item.opt_out_all),
            "allow_sms": sum(1 for item in prefs if item.allow_sms),
            "allow_wechat": sum(1 for item in prefs if item.allow_wechat),
            "allow_email": sum(1 for item in prefs if item.allow_email),
        },
        "events": {
            "recent_30d_total": len(recent_events),
            "recent_30d_by_type": _count_by(recent_events, "event_type"),
        },
        "attention": {
            "count": attention_count,
            "needs_attention": attention_count > 0,
            "reasons": {
                "overdue_reminders": len(overdue),
                "due_today_reminders": len(due_today),
                "queue_needs_review": len(queue_needs_review),
                "queue_blocked_opt_out": len(queue_blocked_opt_out),
            },
        },
        "latest": {
            "overdue_reminder_ids": [item.reminder_id for item in overdue[:5]],
            "queue_needs_review_ids": [item.notification_id for item in queue_needs_review[:5]],
            "queue_blocked_opt_out_ids": [item.notification_id for item in queue_blocked_opt_out[:5]],
        },
        "safety": {
            "read_only": True,
            "writes_database": False,
            "creates_case": False,
            "updates_case": False,
            "auto_send": False,
            "sends_external_message": False,
            "executes_real_import": False,
            "manual_review_required": True,
        },
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "auto_send": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }
