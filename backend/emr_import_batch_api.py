# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import AuditLog, EmrImportBatch, EmrImportBatchReceipt, WebhookInbox
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import AuditLog, EmrImportBatch, EmrImportBatchReceipt, WebhookInbox


router = APIRouter(prefix="/api/emr/import-batches", tags=["emr-import-batches"])

MAX_RECEIPTS_PER_BATCH = 500
READY_STATUS = "ready_for_import"
BATCH_STATUS_DRAFT = "draft"
BATCH_STATUS_FROZEN = "frozen"


class EmrImportBatchPlanIn(BaseModel):
    """Create a real-import candidate batch from reviewed EMR webhook receipts.

    V1 is a planning gate only. It writes only emr_import_batches,
    emr_import_batch_receipts and one audit_log row. It never creates or updates
    Case records.
    """

    batch_id: Optional[str] = Field(default=None, max_length=64)
    source_system: str = Field(default="emr", min_length=1, max_length=100)
    receipt_ids: List[str] = Field(default_factory=list)
    status_filter: str = Field(default=READY_STATUS, max_length=50)
    max_receipts: int = Field(default=100, ge=1, le=MAX_RECEIPTS_PER_BATCH)
    freeze: bool = True
    created_by: str = Field(..., min_length=1, max_length=100)
    clinical_signoff_id: Optional[str] = Field(default=None, max_length=100)
    rollback_snapshot_id: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _dt(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _new_batch_id() -> str:
    return "emr_batch_" + uuid4().hex[:24]


def _receipt_summary(item: WebhookInbox) -> Dict[str, Any]:
    return {
        "receipt_id": item.receipt_id,
        "status": item.status,
        "dry_run": bool(item.dry_run),
        "external_case_id": item.external_case_id,
        "external_encounter_id": item.external_encounter_id,
        "idempotency_key": item.idempotency_key,
        "payload_hash": item.payload_hash,
        "received_at": _dt(item.received_at),
        "has_mapped_case_preview": isinstance(item.mapped_case_preview, dict) and bool(item.mapped_case_preview),
    }


def _batch_summary(item: EmrImportBatch) -> Dict[str, Any]:
    return {
        "batch_id": item.batch_id,
        "source_system": item.source_system,
        "status": item.status,
        "receipt_count": item.receipt_count,
        "ready_for_import_count": item.ready_for_import_count,
        "rejected_count": item.rejected_count,
        "review_action_count": item.review_action_count,
        "clinical_signoff_id": item.clinical_signoff_id,
        "rollback_snapshot_id": item.rollback_snapshot_id,
        "frozen_at": _dt(item.frozen_at),
        "approved_at": _dt(item.approved_at),
        "started_at": _dt(item.started_at),
        "completed_at": _dt(item.completed_at),
        "created_by": item.created_by,
        "approved_by": item.approved_by,
        "note": item.note,
        "metadata": item.extra_data or {},
        "created_at": _dt(item.created_at),
        "updated_at": _dt(item.updated_at),
    }


def _get_receipts_for_plan(db: Session, data: EmrImportBatchPlanIn) -> List[WebhookInbox]:
    query = db.query(WebhookInbox).filter(WebhookInbox.dry_run.is_(True))

    if data.receipt_ids:
        normalized_ids = [_text(item) for item in data.receipt_ids if _text(item)]
        if not normalized_ids:
            raise HTTPException(status_code=422, detail="receipt_ids cannot be blank")
        if len(normalized_ids) > data.max_receipts:
            raise HTTPException(status_code=422, detail="receipt_ids exceeds max_receipts")
        rows = query.filter(WebhookInbox.receipt_id.in_(normalized_ids)).all()
        found = {row.receipt_id for row in rows}
        missing = [item for item in normalized_ids if item not in found]
        if missing:
            raise HTTPException(status_code=404, detail={"missing_receipt_ids": missing})
        by_id = {row.receipt_id: row for row in rows}
        return [by_id[item] for item in normalized_ids]

    status_filter = _text(data.status_filter) or READY_STATUS
    return (
        query.filter(WebhookInbox.status == status_filter)
        .order_by(WebhookInbox.received_at.asc(), WebhookInbox.created_at.asc())
        .limit(data.max_receipts)
        .all()
    )


def _assert_receipts_ready(receipts: List[WebhookInbox]) -> None:
    if not receipts:
        raise HTTPException(status_code=422, detail="No reviewed receipts are available for batch planning")

    not_ready = [item.receipt_id for item in receipts if item.status != READY_STATUS]
    if not_ready:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "All receipts must be ready_for_import before planning a real-import batch",
                "not_ready_receipt_ids": not_ready,
            },
        )


def _assert_not_already_batched(db: Session, receipt_ids: List[str]) -> None:
    existing = (
        db.query(EmrImportBatchReceipt)
        .filter(EmrImportBatchReceipt.receipt_id.in_(receipt_ids))
        .all()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "One or more receipts are already linked to an import batch",
                "already_batched": [
                    {"receipt_id": row.receipt_id, "batch_id": row.batch_id}
                    for row in existing
                ],
            },
        )


def _append_planning_audit(
    db: Session,
    *,
    batch: EmrImportBatch,
    receipts: List[WebhookInbox],
    created_by: str,
    note: Optional[str],
) -> AuditLog:
    audit = AuditLog(
        request_id=f"emr-import-batch-plan-{batch.batch_id}",
        patient_token=batch.source_system,
        clinician_id=created_by,
        model_version=None,
        confidence=None,
        suggested_action=f"Plan EMR real import candidate batch {batch.batch_id}",
        action_taken="frozen" if batch.status == BATCH_STATUS_FROZEN else "draft",
        override_reason="Go/No-Go planning gate before real import",
        note=note,
        case_id=None,
        session_uid=None,
        event_type="emr_import_batch_planning",
        source="pet-med-ai",
        extra_data={
            "batch_id": batch.batch_id,
            "source_system": batch.source_system,
            "receipt_ids": [item.receipt_id for item in receipts],
            "receipt_count": len(receipts),
            "status": batch.status,
            "writes_case_database": False,
            "creates_case": False,
        },
    )
    db.add(audit)
    return audit


@router.post("/plan", response_model=dict, status_code=201)
def plan_emr_real_import_batch(
    data: EmrImportBatchPlanIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a frozen/draft planning batch from reviewed EMR webhook receipts.

    Safety boundary:
    - writes emr_import_batches
    - writes emr_import_batch_receipts
    - writes audit_log
    - does not create/update Case
    - does not download attachments
    - does not execute real import
    """

    batch_id = _text(data.batch_id) or _new_batch_id()
    if db.get(EmrImportBatch, batch_id):
        raise HTTPException(status_code=409, detail="batch_id already exists")

    created_by = _text(data.created_by)
    if not created_by:
        raise HTTPException(status_code=422, detail="created_by is required")

    receipts = _get_receipts_for_plan(db, data)
    _assert_receipts_ready(receipts)
    _assert_not_already_batched(db, [item.receipt_id for item in receipts])

    now = datetime.utcnow()
    batch_status = BATCH_STATUS_FROZEN if data.freeze else BATCH_STATUS_DRAFT
    ready_count = sum(1 for item in receipts if item.status == READY_STATUS)
    rejected_count = sum(1 for item in receipts if item.status != READY_STATUS)

    batch = EmrImportBatch(
        batch_id=batch_id,
        source_system=_text(data.source_system) or "emr",
        status=batch_status,
        receipt_count=len(receipts),
        ready_for_import_count=ready_count,
        rejected_count=rejected_count,
        review_action_count=len(receipts),
        clinical_signoff_id=_text(data.clinical_signoff_id) or None,
        rollback_snapshot_id=_text(data.rollback_snapshot_id) or None,
        frozen_at=now if data.freeze else None,
        created_by=created_by,
        note=_text(data.note) or None,
        extra_data=data.metadata or None,
    )
    db.add(batch)

    for receipt in receipts:
        link = EmrImportBatchReceipt(
            batch_id=batch.batch_id,
            receipt_id=receipt.receipt_id,
            review_status=receipt.status,
            ready_for_import=receipt.status == READY_STATUS,
            external_case_id=receipt.external_case_id,
            external_encounter_id=receipt.external_encounter_id,
            note="Included by EMR real import batch planning API V1",
            extra_data={
                "idempotency_key": receipt.idempotency_key,
                "payload_hash": receipt.payload_hash,
            },
        )
        db.add(link)

    audit = _append_planning_audit(
        db,
        batch=batch,
        receipts=receipts,
        created_by=created_by,
        note=_text(data.note) or None,
    )

    db.commit()
    db.refresh(batch)
    db.refresh(audit)

    return {
        "message": "emr_import_batch_planned",
        "mode": "planning_api",
        "batch": _batch_summary(batch),
        "receipts": [_receipt_summary(item) for item in receipts],
        "audit_log_id": audit.log_id,
        "writes_emr_import_batches": True,
        "writes_emr_import_batch_receipts": True,
        "writes_audit_log": True,
        "writes_case_database": False,
        "creates_case": False,
        "updates_case": False,
        "downloads_attachments": False,
        "executes_real_import": False,
        "can_execute_import": False,
        "next_gate": "Clinical signoff, rollback snapshot and a separate real import execution API are required.",
    }


@router.get("", response_model=dict)
def list_emr_import_batches(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = None,
    source_system: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(EmrImportBatch)
    if status:
        query = query.filter(EmrImportBatch.status == status.strip())
    if source_system:
        query = query.filter(EmrImportBatch.source_system == source_system.strip())

    total = query.count()
    items = (
        query.order_by(EmrImportBatch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "message": "emr_import_batches",
        "mode": "planning_api",
        "review_only": True,
        "writes_database": False,
        "creates_case": False,
        "items": [_batch_summary(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{batch_id}", response_model=dict)
def get_emr_import_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    batch = db.get(EmrImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="EMR import batch not found")

    links = (
        db.query(EmrImportBatchReceipt)
        .filter(EmrImportBatchReceipt.batch_id == batch.batch_id)
        .order_by(EmrImportBatchReceipt.created_at.asc(), EmrImportBatchReceipt.id.asc())
        .all()
    )
    return {
        "message": "emr_import_batch",
        "mode": "planning_api",
        "review_only": True,
        "writes_database": False,
        "creates_case": False,
        "batch": _batch_summary(batch),
        "receipts": [
            {
                "id": link.id,
                "batch_id": link.batch_id,
                "receipt_id": link.receipt_id,
                "review_status": link.review_status,
                "ready_for_import": bool(link.ready_for_import),
                "external_case_id": link.external_case_id,
                "external_encounter_id": link.external_encounter_id,
                "note": link.note,
                "metadata": link.extra_data or {},
                "created_at": _dt(link.created_at),
            }
            for link in links
        ],
        "safety": {
            "writes_case_database": False,
            "creates_case": False,
            "updates_case": False,
            "downloads_attachments": False,
            "executes_real_import": False,
        },
    }
