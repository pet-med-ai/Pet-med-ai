# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_FLAGS = {
    "ENABLE_PREVENTIVE_AUTO_DELIVERY": False,
    "ENABLE_PREVENTIVE_SMS_DELIVERY": False,
    "ENABLE_PREVENTIVE_WECHAT_DELIVERY": False,
    "ENABLE_PREVENTIVE_EMAIL_DELIVERY": False,
    "ENABLE_PREVENTIVE_DELIVERY_DRY_RUN": True,
    "ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL": True,
}

CHANNEL_FLAG_MAP = {
    "sms": "ENABLE_PREVENTIVE_SMS_DELIVERY",
    "wechat": "ENABLE_PREVENTIVE_WECHAT_DELIVERY",
    "email": "ENABLE_PREVENTIVE_EMAIL_DELIVERY",
}

CHANNEL_PERMISSION_MAP = {
    "sms": "allow_sms",
    "wechat": "allow_wechat",
    "email": "allow_email",
    "in_app": "allow_in_app",
}


@dataclass(frozen=True)
class EligibilityBlocker:
    reason: str
    detail: str
    severity: str = "block"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _flags(payload: Dict[str, Any]) -> Dict[str, bool]:
    merged = dict(DEFAULT_FLAGS)
    for key, value in _dict(payload.get("feature_flags")).items():
        if key in merged:
            merged[key] = _truthy(value)
    return merged


def _channel(payload: Dict[str, Any]) -> str:
    return str(payload.get("channel") or "sms").strip().lower()


def _is_outside_send_window(payload: Dict[str, Any]) -> bool:
    quiet = _dict(payload.get("quiet_hours"))
    if not _truthy(quiet.get("enabled", True)):
        return False

    # A simple dry-run design rule: send_window_start <= local_hour < send_window_end.
    local_hour = quiet.get("local_hour")
    if local_hour is None:
        text = str(quiet.get("local_time") or "").strip()
        try:
            local_hour = datetime.fromisoformat(text).hour if text else None
        except Exception:
            local_hour = None

    if local_hour is None:
        return False

    start = _int(quiet.get("send_window_start_hour", 9), 9)
    end = _int(quiet.get("send_window_end_hour", 18), 18)
    hour = _int(local_hour, 0)

    if start < end:
        return not (start <= hour < end)
    # Overnight window, uncommon but supported.
    return not (hour >= start or hour < end)


def _rate_limit_blocker(payload: Dict[str, Any]) -> Optional[EligibilityBlocker]:
    rate = _dict(payload.get("rate_limits"))
    if _truthy(rate.get("duplicate_within_cooldown")):
        return EligibilityBlocker("blocked_rate_limit", "duplicate reminder within cooldown window")

    if _int(rate.get("owner_daily_sent_count"), 0) >= _int(rate.get("owner_daily_cap"), 1):
        return EligibilityBlocker("blocked_rate_limit", "owner daily cap reached")

    if _int(rate.get("owner_weekly_sent_count"), 0) >= _int(rate.get("owner_weekly_cap"), 3):
        return EligibilityBlocker("blocked_rate_limit", "owner weekly cap reached")

    if _int(rate.get("global_hourly_sent_count"), 0) >= _int(rate.get("global_hourly_cap"), 100):
        return EligibilityBlocker("blocked_rate_limit", "global hourly cap reached")

    return None


def collect_delivery_blockers(payload: Dict[str, Any]) -> List[EligibilityBlocker]:
    flags = _flags(payload)
    channel = _channel(payload)
    owner = _dict(payload.get("owner"))
    consent = _dict(owner.get("consent"))
    reminder = _dict(payload.get("reminder"))
    queue = _dict(payload.get("notification_queue"))
    template = _dict(payload.get("template"))
    destination = _dict(payload.get("destination"))
    provider = _dict(payload.get("provider"))
    suppression = _dict(payload.get("suppression"))

    blockers: List[EligibilityBlocker] = []

    if _truthy(owner.get("opt_out_all")) or _truthy(consent.get("opt_out_all")):
        blockers.append(EligibilityBlocker("blocked_opt_out", "owner has opt_out_all=true"))

    if _truthy(reminder.get("client_opt_out")) or _truthy(queue.get("client_opt_out_snapshot")):
        blockers.append(EligibilityBlocker("blocked_opt_out", "reminder or queue has client opt-out snapshot"))

    permission_key = CHANNEL_PERMISSION_MAP.get(channel)
    if permission_key and not _truthy(consent.get(permission_key)):
        blockers.append(EligibilityBlocker("blocked_missing_consent", f"channel permission is false or missing: {permission_key}"))

    if not str(consent.get("consent_source") or "").strip():
        blockers.append(EligibilityBlocker("blocked_missing_consent", "consent source missing"))

    if not _truthy(destination.get("exists")):
        blockers.append(EligibilityBlocker("blocked_missing_channel", "contact destination missing"))

    manual_approval_required = _truthy(payload.get("manual_approval_required", True)) or flags["ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL"]
    queue_reviewed = str(queue.get("status") or "").strip().lower() in {"reviewed", "approved_for_send"} or bool(str(queue.get("reviewed_by") or "").strip())
    if manual_approval_required and not queue_reviewed:
        blockers.append(EligibilityBlocker("manual_review_required", "queue item has not been manually reviewed"))

    if str(template.get("review_status") or "").strip().lower() != "approved":
        blockers.append(EligibilityBlocker("blocked_unapproved_template", "message template is not approved"))

    rate_blocker = _rate_limit_blocker(payload)
    if rate_blocker:
        blockers.append(rate_blocker)

    if _is_outside_send_window(payload):
        blockers.append(EligibilityBlocker("blocked_quiet_hours", "current local time is outside send window"))

    if _truthy(suppression.get("active")):
        blockers.append(EligibilityBlocker("blocked_suppression", str(suppression.get("reason") or "active suppression rule")))

    if not flags["ENABLE_PREVENTIVE_AUTO_DELIVERY"]:
        blockers.append(EligibilityBlocker("blocked_kill_switch", "ENABLE_PREVENTIVE_AUTO_DELIVERY=false"))

    channel_flag = CHANNEL_FLAG_MAP.get(channel)
    if channel_flag and not flags[channel_flag]:
        blockers.append(EligibilityBlocker("blocked_channel_disabled", f"{channel_flag}=false"))

    if channel in CHANNEL_FLAG_MAP and not _truthy(provider.get("credentials_available")):
        blockers.append(EligibilityBlocker("blocked_provider_credentials", "provider credentials unavailable"))

    return blockers


def evaluate_delivery_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    flags = _flags(payload)
    channel = _channel(payload)
    dry_run_requested = _truthy(payload.get("dry_run", True)) or flags["ENABLE_PREVENTIVE_DELIVERY_DRY_RUN"]
    blockers = collect_delivery_blockers(payload)

    eligible_for_live_send = not blockers
    eligible_for_dry_run = True
    first_blocker = blockers[0].reason if blockers else None

    if dry_run_requested:
        state = "dry_run_only"
    elif eligible_for_live_send:
        state = "queued"
    else:
        state = first_blocker or "blocked"

    return {
        "message": "automated_reminder_delivery_eligibility_dry_run",
        "mode": "automated_reminder_delivery_eligibility_engine_dry_run_v1",
        "scenario_id": payload.get("scenario_id"),
        "channel": channel,
        "state": state,
        "eligible_for_dry_run": eligible_for_dry_run,
        "eligible_for_live_send": eligible_for_live_send,
        "first_blocked_reason": first_blocker,
        "blocked_reasons": [
            {"reason": item.reason, "detail": item.detail, "severity": item.severity}
            for item in blockers
        ],
        "feature_flags": flags,
        "dry_run": True,
        "auto_send": False,
        "sends_external_message": False,
        "manual_review_required": True,
        "creates_case": False,
        "updates_case": False,
        "executes_real_import": False,
        "writes_database": False,
    }


def evaluate_delivery_scenarios(payload: Dict[str, Any]) -> Dict[str, Any]:
    base = deepcopy(_dict(payload.get("base")))
    scenarios = payload.get("scenarios") if isinstance(payload.get("scenarios"), list) else []
    results = []

    for scenario in scenarios:
        scenario_payload = deepcopy(base)
        scenario_payload.update(_dict(scenario.get("patch")))
        scenario_payload["scenario_id"] = scenario.get("scenario_id")
        results.append(evaluate_delivery_eligibility(scenario_payload))

    by_reason: Dict[str, int] = {}
    for item in results:
        reason = item.get("first_blocked_reason") or "eligible"
        by_reason[reason] = by_reason.get(reason, 0) + 1

    return {
        "message": "automated_reminder_delivery_eligibility_scenarios",
        "mode": "automated_reminder_delivery_eligibility_engine_dry_run_v1",
        "total": len(results),
        "by_first_blocked_reason": dict(sorted(by_reason.items())),
        "results": results,
        "dry_run": True,
        "auto_send": False,
        "sends_external_message": False,
        "manual_review_required": True,
        "creates_case": False,
        "updates_case": False,
        "executes_real_import": False,
        "writes_database": False,
    }
