# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/api/system", tags=["system"])

TRUE_VALUES = {"1", "true", "yes", "y", "on", "enabled"}
FALSE_VALUES = {"0", "false", "no", "n", "off", "disabled", ""}


FEATURE_FLAG_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "ENABLE_EMR_REAL_IMPORT": {
        "label": "Allow real EMR import execution",
        "default": False,
        "risk": "P0",
        "category": "emr_import",
        "reason": "Would allow future Case writes from EMR import execution.",
    },
    "ENABLE_EMR_IMPORT_CASE_UPDATE": {
        "label": "Allow EMR import to update existing Case records",
        "default": False,
        "risk": "P0",
        "category": "emr_import",
        "reason": "Could overwrite clinical records; disabled until update policy is designed.",
    },
    "ENABLE_EMR_ATTACHMENT_DOWNLOAD": {
        "label": "Allow EMR import to download external attachments",
        "default": False,
        "risk": "P0",
        "category": "attachments",
        "reason": "External file ingestion requires storage, malware, PHI and rollback controls.",
    },
    "ENABLE_PREVENTIVE_AUTO_DELIVERY": {
        "label": "Allow automated preventive reminder delivery",
        "default": False,
        "risk": "P0",
        "category": "automated_delivery",
        "reason": "Commercial V1 allows manual contact only; real automated outbound delivery is out of scope.",
    },
    "ENABLE_PREVENTIVE_SMS_DELIVERY": {
        "label": "Allow automated preventive SMS delivery",
        "default": False,
        "risk": "P0",
        "category": "automated_delivery",
        "reason": "Commercial V1 has no real SMS provider and no automatic outbound sending approval.",
    },
    "ENABLE_PREVENTIVE_WECHAT_DELIVERY": {
        "label": "Allow automated preventive WeChat delivery",
        "default": False,
        "risk": "P0",
        "category": "automated_delivery",
        "reason": "Commercial V1 has no real WeChat provider and no automatic outbound sending approval.",
    },
    "ENABLE_PREVENTIVE_EMAIL_DELIVERY": {
        "label": "Allow automated preventive email delivery",
        "default": False,
        "risk": "P0",
        "category": "automated_delivery",
        "reason": "Commercial V1 has no real email provider and no automatic outbound sending approval.",
    },
    "ENABLE_PRESCRIPTION_STRUCTURED_WRITE": {
        "label": "Allow structured prescription / medication order writes",
        "default": False,
        "risk": "P0",
        "category": "clinical_orders",
        "reason": "Medication order writes require separate clinical safety review.",
    },
    "ENABLE_DEVICE_REAL_INGEST": {
        "label": "Allow hospital device real ingest",
        "default": False,
        "risk": "P0",
        "category": "device_integration",
        "reason": "Device data should stay in mock/dry-run until interfaces are validated.",
    },
    "ENABLE_BILLING_REAL_WRITE": {
        "label": "Allow billing / invoice writes",
        "default": False,
        "risk": "P0",
        "category": "billing",
        "reason": "Financial writes require separate reconciliation and rollback policy.",
    },
    "ENABLE_KB_PRODUCTION_PATCH": {
        "label": "Allow production knowledge-base patch promotion",
        "default": False,
        "risk": "P1",
        "category": "knowledge_base",
        "reason": "Clinical KB updates require schema validation and clinician review.",
    },
    "ENABLE_CASE_DELETE_IMPORT": {
        "label": "Allow imported data to delete Case records",
        "default": False,
        "risk": "P0",
        "category": "data_integrity",
        "reason": "Imported data must never delete clinical records in V1.",
    },
}


def _parse_bool(raw: str | None, default: bool = False) -> bool:
    value = str(raw if raw is not None else "").strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    return bool(default)


def is_feature_enabled(name: str) -> bool:
    if name not in FEATURE_FLAG_DEFINITIONS:
        raise KeyError(f"Unknown feature flag: {name}")
    default = bool(FEATURE_FLAG_DEFINITIONS[name].get("default", False))
    return _parse_bool(os.getenv(name), default=default)


def assert_feature_enabled(name: str) -> None:
    if not is_feature_enabled(name):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "feature flag disabled",
                "feature_flag": name,
                "enabled": False,
            },
        )


def _flag_payload(name: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    enabled = is_feature_enabled(name)
    return {
        "name": name,
        "enabled": enabled,
        "default": bool(meta.get("default", False)),
        "risk": meta.get("risk"),
        "category": meta.get("category"),
        "label": meta.get("label"),
        "reason": meta.get("reason"),
        "env_var": name,
    }


def _all_flags() -> Dict[str, Dict[str, Any]]:
    return {
        name: _flag_payload(name, meta)
        for name, meta in FEATURE_FLAG_DEFINITIONS.items()
    }


def dangerous_enabled_flags() -> list[str]:
    flags = _all_flags()
    return [
        name for name, payload in flags.items()
        if bool(payload.get("enabled")) and str(payload.get("risk")) in {"P0", "P1"}
    ]


@router.get("/feature-flags", response_model=dict)
def system_feature_flags():
    """
    Read-only feature flag status endpoint.

    This endpoint exposes boolean safety gates only. It does not expose secrets or
    raw environment values, and it never mutates database state.
    """

    flags = _all_flags()
    dangerous = dangerous_enabled_flags()

    return {
        "message": "system_feature_flags",
        "mode": "safety_gate_status",
        "flags": flags,
        "dangerous_features_enabled": dangerous,
        "all_dangerous_features_disabled": len(dangerous) == 0,
        "real_import_enabled": bool(flags["ENABLE_EMR_REAL_IMPORT"]["enabled"]),
        "case_update_import_enabled": bool(flags["ENABLE_EMR_IMPORT_CASE_UPDATE"]["enabled"]),
        "attachment_download_enabled": bool(flags["ENABLE_EMR_ATTACHMENT_DOWNLOAD"]["enabled"]),
        "preventive_auto_delivery_enabled": bool(flags["ENABLE_PREVENTIVE_AUTO_DELIVERY"]["enabled"]),
        "preventive_sms_delivery_enabled": bool(flags["ENABLE_PREVENTIVE_SMS_DELIVERY"]["enabled"]),
        "preventive_wechat_delivery_enabled": bool(flags["ENABLE_PREVENTIVE_WECHAT_DELIVERY"]["enabled"]),
        "preventive_email_delivery_enabled": bool(flags["ENABLE_PREVENTIVE_EMAIL_DELIVERY"]["enabled"]),
        "device_real_ingest_enabled": bool(flags["ENABLE_DEVICE_REAL_INGEST"]["enabled"]),
        "writes_database": False,
        "exposes_secret_values": False,
        "safety_note": (
            "High-risk capabilities default to disabled. Enabling a flag only "
            "removes the runtime block; clinical approval, rollback and smoke "
            "requirements still apply."
        ),
    }
