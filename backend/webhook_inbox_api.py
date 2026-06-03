# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import WebhookInbox
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import WebhookInbox


router = APIRouter(prefix="/api/webhooks/emr", tags=["webhooks"])

MAX_PAGE_SIZE = 100


def _dt(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _count_items(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def _boolish(value: Optional[bool]) -> Optional[bool]:
    if value is None:
        return None
    return bool(value)


def _summary(item: WebhookInbox) -> Dict[str, Any]:
    return {
        "receipt_id": item.receipt_id,
        "source": item.source,
        "event_type": item.event_type,
        "idempotency_key": item.idempotency_key,
        "payload_hash": item.payload_hash,
        "signature_hash": item.signature_hash,
        "external_case_id": item.external_case_id,
        "external_encounter_id": item.external_encounter_id,
        "case_id": item.case_id,
        "status": item.status,
        "dry_run": bool(item.dry_run),
        "validation_error_count": _count_items(item.validation_errors),
        "validation_warning_count": _count_items(item.validation_warnings),
        "has_mapped_case_preview": isinstance(item.mapped_case_preview, dict) and bool(item.mapped_case_preview),
        "error_code": item.error_code,
        "received_at": _dt(item.received_at),
        "processed_at": _dt(item.processed_at),
        "created_at": _dt(item.created_at),
        "updated_at": _dt(item.updated_at),
    }


def _detail(item: WebhookInbox, *, include_payload: bool) -> Dict[str, Any]:
    data = _summary(item)
    data.update({
        "validation_errors": item.validation_errors or [],
        "validation_warnings": item.validation_warnings or [],
        "mapped_case_preview": item.mapped_case_preview or {},
        "error_message": item.error_message,
        "payload_omitted": not include_payload,
    })
    if include_payload:
        data["payload"] = item.payload or {}
    return data


def _apply_filters(
    query,
    *,
    status: Optional[str],
    dry_run: Optional[bool],
    idempotency_key: Optional[str],
    external_case_id: Optional[str],
    receipt_id: Optional[str],
):
    if status:
        query = query.filter(WebhookInbox.status == status.strip())
    if dry_run is not None:
        query = query.filter(WebhookInbox.dry_run.is_(bool(dry_run)))
    if idempotency_key:
        query = query.filter(WebhookInbox.idempotency_key == idempotency_key.strip())
    if external_case_id:
        query = query.filter(WebhookInbox.external_case_id == external_case_id.strip())
    if receipt_id:
        query = query.filter(WebhookInbox.receipt_id == receipt_id.strip())
    return query


@router.get("/inbox", response_model=dict)
def list_webhook_inbox_receipts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
    status: Optional[str] = None,
    dry_run: Optional[bool] = None,
    idempotency_key: Optional[str] = None,
    external_case_id: Optional[str] = None,
    receipt_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Review EMR webhook inbox receipts.

    V1 is read-only and authenticated. It does not mutate webhook_inbox,
    create cases, download attachments, or enqueue real ingestion.
    """

    query = db.query(WebhookInbox)
    query = _apply_filters(
        query,
        status=status,
        dry_run=_boolish(dry_run),
        idempotency_key=idempotency_key,
        external_case_id=external_case_id,
        receipt_id=receipt_id,
    )

    total = query.count()
    items = (
        query.order_by(WebhookInbox.received_at.desc(), WebhookInbox.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "message": "webhook_inbox_receipts",
        "mode": "review_api",
        "review_only": True,
        "writes_database": False,
        "creates_case": False,
        "downloads_attachments": False,
        "user_id": getattr(user, "id", None),
        "items": [_summary(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "filters": {
            "status": status,
            "dry_run": dry_run,
            "idempotency_key": idempotency_key,
            "external_case_id": external_case_id,
            "receipt_id": receipt_id,
        },
    }


@router.get("/inbox/{receipt_id}", response_model=dict)
def get_webhook_inbox_receipt(
    receipt_id: str,
    include_payload: bool = Query(default=False),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Read a single EMR webhook inbox receipt.

    Payload is omitted by default to reduce accidental exposure of external EMR
    content. Use include_payload=true only for controlled troubleshooting.
    """

    item = db.get(WebhookInbox, receipt_id)
    if not item:
        raise HTTPException(status_code=404, detail="Webhook receipt not found")

    return {
        "message": "webhook_inbox_receipt",
        "mode": "review_api",
        "review_only": True,
        "writes_database": False,
        "creates_case": False,
        "downloads_attachments": False,
        "user_id": getattr(user, "id", None),
        "receipt": _detail(item, include_payload=include_payload),
    }
