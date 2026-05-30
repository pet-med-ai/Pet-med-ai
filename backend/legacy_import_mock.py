# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

try:
    from backend.auth_jwt import get_current_user
except ModuleNotFoundError:
    from auth_jwt import get_current_user


router = APIRouter(prefix="/api/migrations", tags=["migrations"])

MAX_MOCK_RECORDS = 1000


class LegacyCaseImportMockIn(BaseModel):
    # API mock for legacy case import JSONL records.
    batch_id: Optional[str] = None
    records: List[Dict[str, Any]] = Field(default_factory=list)
    validate_only: bool = True


def _text(value: Any) -> str:
    return str(value or "").strip()


def _case_create_errors(case_create: Dict[str, Any]) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []

    for field in ("patient_name", "species", "chief_complaint"):
        if not _text(case_create.get(field)):
            errors.append({
                "field": f"case_create.{field}",
                "error_code": "required",
                "error_reason": f"case_create.{field} is required.",
            })

    history = _text(case_create.get("history"))
    if history and len(history) > 20000:
        errors.append({
            "field": "case_create.history",
            "error_code": "too_long",
            "error_reason": "history is too long for mock import preview.",
        })

    return errors


def _record_errors(record: Dict[str, Any], seen_keys: Set[str]) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []

    if record.get("operation") != "case_create":
        errors.append({
            "field": "operation",
            "error_code": "unsupported_operation",
            "error_reason": "Only operation=case_create is supported by V1 mock.",
        })

    if record.get("dry_run") is not True:
        errors.append({
            "field": "dry_run",
            "error_code": "not_dry_run",
            "error_reason": "Mock import requires dry_run=true records.",
        })

    idempotency_key = _text(record.get("idempotency_key"))
    if not idempotency_key:
        errors.append({
            "field": "idempotency_key",
            "error_code": "required",
            "error_reason": "idempotency_key is required.",
        })
    elif idempotency_key in seen_keys:
        errors.append({
            "field": "idempotency_key",
            "error_code": "duplicate_in_batch",
            "error_reason": "idempotency_key appears more than once in this mock batch.",
        })
    else:
        seen_keys.add(idempotency_key)

    case_create = record.get("case_create")
    if not isinstance(case_create, dict):
        errors.append({
            "field": "case_create",
            "error_code": "required",
            "error_reason": "case_create object is required.",
        })
    else:
        errors.extend(_case_create_errors(case_create))

    return errors


def _preview_case_create(case_create: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "patient_name": case_create.get("patient_name"),
        "species": case_create.get("species"),
        "breed": case_create.get("breed"),
        "weight": case_create.get("weight"),
        "chief_complaint": case_create.get("chief_complaint"),
        "has_history": bool(_text(case_create.get("history"))),
        "has_exam_findings": bool(_text(case_create.get("exam_findings"))),
    }


@router.post("/legacy-cases/mock", response_model=dict)
def legacy_cases_import_mock(
    data: LegacyCaseImportMockIn,
    user=Depends(get_current_user),
):
    records = data.records or []
    if not records:
        raise HTTPException(status_code=400, detail="records is required")
    if len(records) > MAX_MOCK_RECORDS:
        raise HTTPException(status_code=400, detail=f"records cannot exceed {MAX_MOCK_RECORDS} per mock batch")

    seen_keys: Set[str] = set()
    items: List[Dict[str, Any]] = []
    all_errors: List[Dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        legacy_case_id = _text(record.get("legacy_case_id") or (record.get("legacy") or {}).get("case_id"))
        idempotency_key = _text(record.get("idempotency_key"))
        record_errors = _record_errors(record, seen_keys)

        if record_errors:
            item = {
                "index": index,
                "status": "rejected",
                "legacy_case_id": legacy_case_id,
                "idempotency_key": idempotency_key,
                "errors": record_errors,
            }
            all_errors.append(item)
        else:
            case_create = record.get("case_create") or {}
            item = {
                "index": index,
                "status": "accepted",
                "legacy_case_id": legacy_case_id,
                "idempotency_key": idempotency_key,
                "operation": "case_create",
                "case_create_preview": _preview_case_create(case_create),
            }

        items.append(item)

    accepted = sum(1 for item in items if item.get("status") == "accepted")
    rejected = len(items) - accepted

    return {
        "message": "mocked",
        "mode": "api_mock",
        "batch_id": data.batch_id or f"mock-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "dry_run": True,
        "validate_only": True,
        "writes_database": False,
        "calls_case_create_api": False,
        "user_id": getattr(user, "id", None),
        "received": len(records),
        "accepted": accepted,
        "rejected": rejected,
        "items": items,
        "errors": all_errors,
    }
