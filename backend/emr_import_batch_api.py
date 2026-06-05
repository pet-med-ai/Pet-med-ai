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
    from backend.feature_flags import assert_feature_enabled, is_feature_enabled
    from backend.models import AuditLog, Case, EmrImportBatch, EmrImportBatchReceipt, EmrImportExecutionRun, EmrImportExecutionItemResult, WebhookInbox
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from feature_flags import assert_feature_enabled, is_feature_enabled
    from models import AuditLog, Case, EmrImportBatch, EmrImportBatchReceipt, EmrImportExecutionRun, EmrImportExecutionItemResult, WebhookInbox


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


class EmrImportExecutionDryRunIn(BaseModel):
    """Generate import diff / rollback plan for a frozen EMR import batch.

    This endpoint is strictly dry-run. It does not create/update Case records,
    does not mutate batch state, and does not download attachments.
    """

    operator_id: str = Field(..., min_length=1, max_length=100)
    clinical_signoff_id: Optional[str] = Field(default=None, max_length=100)
    rollback_snapshot_id: Optional[str] = Field(default=None, max_length=100)
    include_payload_preview: bool = False
    max_items: int = Field(default=100, ge=1, le=500)
    note: Optional[str] = None


class EmrImportClinicalApprovalIn(BaseModel):
    """Clinical approval gate for a planned EMR import batch.

    V1 is still a safety gate only. It may update emr_import_batches and append
    one audit_log row, but it never executes real Case import.
    """

    operator_id: str = Field(..., min_length=1, max_length=100)
    clinical_signoff_id: str = Field(..., min_length=1, max_length=100)
    rollback_snapshot_id: str = Field(..., min_length=1, max_length=100)
    approval_action: str = Field(default="approve", min_length=1, max_length=50)
    note: Optional[str] = None
    request_id: Optional[str] = Field(default=None, max_length=100)
    metadata: Optional[Dict[str, Any]] = None
    max_items: int = Field(default=500, ge=1, le=500)


class EmrImportExecuteIn(BaseModel):
    """Skeleton payload for a future real EMR import execution endpoint.

    V1 is deliberately dry-run protected. Even with clinical approval, this
    endpoint refuses to execute real Case writes. It exists only to prove the
    final safety gate and API contract.
    """

    operator_id: str = Field(..., min_length=1, max_length=100)
    clinical_signoff_id: str = Field(..., min_length=1, max_length=100)
    rollback_snapshot_id: str = Field(..., min_length=1, max_length=100)
    dry_run_ack: bool = Field(default=False)
    create_only_ack: bool = Field(default=False)
    execution_confirmation: str = Field(default="", max_length=100)
    request_id: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    max_items: int = Field(default=500, ge=1, le=500)


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


APPROVAL_ACTION_TO_STATUS = {
    "approve": "approved",
    "clinical_signed": "clinical_signed",
    "needs_fix": "needs_fix",
    "reject": "approval_rejected",
    "rejected": "approval_rejected",
}

APPROVAL_ALLOWED_BATCH_STATUSES = {"frozen", "clinical_signed", "approved"}


def _approval_status(action: str) -> str:
    key = _text(action).lower()
    if key not in APPROVAL_ACTION_TO_STATUS:
        raise HTTPException(
            status_code=422,
            detail="approval_action must be one of: approve, clinical_signed, needs_fix, reject, rejected",
        )
    return APPROVAL_ACTION_TO_STATUS[key]


def _append_clinical_approval_audit(
    db: Session,
    *,
    batch: EmrImportBatch,
    operator_id: str,
    approval_action: str,
    status_before: str,
    status_after: str,
    data: EmrImportClinicalApprovalIn,
    quality_gate: Dict[str, Any],
) -> AuditLog:
    audit = AuditLog(
        request_id=_text(data.request_id) or f"emr-import-clinical-approval-{batch.batch_id}",
        patient_token=batch.source_system,
        clinician_id=operator_id,
        model_version=None,
        confidence=None,
        suggested_action=f"Clinical approval gate for EMR import batch {batch.batch_id}",
        action_taken=approval_action,
        override_reason="Clinical Go/No-Go approval before any real EMR import execution",
        note=_text(data.note) or None,
        case_id=None,
        session_uid=None,
        event_type="emr_import_clinical_approval",
        source="pet-med-ai",
        extra_data={
            "batch_id": batch.batch_id,
            "source_system": batch.source_system,
            "clinical_signoff_id": data.clinical_signoff_id,
            "rollback_snapshot_id": data.rollback_snapshot_id,
            "status_before": status_before,
            "status_after": status_after,
            "approval_action": approval_action,
            "quality_gate": quality_gate,
            "metadata": data.metadata or {},
            "writes_case_database": False,
            "creates_case": False,
            "updates_case": False,
            "executes_real_import": False,
        },
    )
    db.add(audit)
    return audit


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


def _case_snapshot(case: Optional[Case]) -> Optional[Dict[str, Any]]:
    if case is None:
        return None
    return {
        "case_id": case.id,
        "patient_name": case.patient_name,
        "species": case.species,
        "chief_complaint": case.chief_complaint,
        "weight": case.weight,
        "owner_name": case.owner_name,
        "owner_phone": case.owner_phone,
        "created_at": _dt(case.created_at),
        "updated_at": _dt(case.updated_at),
    }


def _field_diff(existing: Optional[Case], case_create: Dict[str, Any]) -> Dict[str, Any]:
    if existing is None:
        return {
            "operation": "case_create_preview",
            "changed_fields": list(case_create.keys()),
            "changes": [
                {
                    "field": field,
                    "before": None,
                    "after": case_create.get(field),
                }
                for field in sorted(case_create.keys())
                if case_create.get(field) not in (None, "")
            ],
        }

    fields = [
        "patient_name",
        "species",
        "weight",
        "owner_name",
        "owner_phone",
        "chief_complaint",
        "history",
        "exam_findings",
    ]
    changes = []
    for field in fields:
        before = getattr(existing, field, None)
        after = case_create.get(field)
        if (before or "") != (after or ""):
            changes.append({
                "field": field,
                "before": before,
                "after": after,
            })
    return {
        "operation": "case_update_preview",
        "changed_fields": [item["field"] for item in changes],
        "changes": changes,
    }


def _execution_item(
    *,
    link: EmrImportBatchReceipt,
    receipt: Optional[WebhookInbox],
    existing_case: Optional[Case],
    include_payload_preview: bool,
) -> Dict[str, Any]:
    blocked_reasons = []
    if receipt is None:
        blocked_reasons.append("webhook receipt missing")
        case_create: Dict[str, Any] = {}
    else:
        if receipt.status != READY_STATUS:
            blocked_reasons.append(f"receipt status is {receipt.status}; expected {READY_STATUS}")
        if not bool(receipt.dry_run):
            blocked_reasons.append("receipt is not dry_run")
        if not isinstance(receipt.mapped_case_preview, dict) or not receipt.mapped_case_preview:
            blocked_reasons.append("mapped_case_preview missing")
        case_create = receipt.mapped_case_preview if isinstance(receipt.mapped_case_preview, dict) else {}

    if not bool(link.ready_for_import):
        blocked_reasons.append("batch link is not marked ready_for_import")
    if link.review_status != READY_STATUS:
        blocked_reasons.append(f"batch link review_status is {link.review_status}; expected {READY_STATUS}")

    for field in ("patient_name", "species", "chief_complaint"):
        if not _text(case_create.get(field)):
            blocked_reasons.append(f"case_create.{field} missing")

    operation = "case_update_preview" if existing_case else "case_create_preview"
    diff = _field_diff(existing_case, case_create)

    item = {
        "receipt_id": link.receipt_id,
        "external_case_id": link.external_case_id,
        "external_encounter_id": link.external_encounter_id,
        "operation": operation,
        "case_id": getattr(existing_case, "id", None),
        "ready_for_import": bool(link.ready_for_import) and not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "case_create_preview": case_create,
        "existing_case_snapshot": _case_snapshot(existing_case),
        "field_diff": diff,
    }
    if include_payload_preview and receipt is not None:
        item["payload_preview"] = receipt.payload or {}
    return item


def build_execution_dry_run_report(
    *,
    db: Session,
    batch: EmrImportBatch,
    data: EmrImportExecutionDryRunIn,
) -> Dict[str, Any]:
    links = (
        db.query(EmrImportBatchReceipt)
        .filter(EmrImportBatchReceipt.batch_id == batch.batch_id)
        .order_by(EmrImportBatchReceipt.created_at.asc(), EmrImportBatchReceipt.id.asc())
        .limit(data.max_items)
        .all()
    )
    if not links:
        raise HTTPException(status_code=422, detail="batch has no receipts to dry-run")

    receipt_ids = [link.receipt_id for link in links]
    receipts = (
        db.query(WebhookInbox)
        .filter(WebhookInbox.receipt_id.in_(receipt_ids))
        .all()
    )
    receipt_by_id = {item.receipt_id: item for item in receipts}

    case_ids = [
        item.case_id
        for item in receipts
        if item.case_id is not None
    ]
    cases = db.query(Case).filter(Case.id.in_(case_ids)).all() if case_ids else []
    case_by_id = {item.id: item for item in cases}

    items = []
    for link in links:
        receipt = receipt_by_id.get(link.receipt_id)
        existing_case = case_by_id.get(receipt.case_id) if receipt and receipt.case_id is not None else None
        items.append(_execution_item(
            link=link,
            receipt=receipt,
            existing_case=existing_case,
            include_payload_preview=bool(data.include_payload_preview),
        ))

    would_create_count = sum(1 for item in items if item.get("operation") == "case_create_preview" and not item.get("blocked_reasons"))
    would_update_count = sum(1 for item in items if item.get("operation") == "case_update_preview" and not item.get("blocked_reasons"))
    blocked_items = [
        {
            "receipt_id": item.get("receipt_id"),
            "blocked_reasons": item.get("blocked_reasons") or [],
        }
        for item in items
        if item.get("blocked_reasons")
    ]
    blocked_count = len(blocked_items)
    has_snapshot = bool(_text(data.rollback_snapshot_id or batch.rollback_snapshot_id))
    has_signoff = bool(_text(data.clinical_signoff_id or batch.clinical_signoff_id))
    ready_for_execution_review = blocked_count == 0 and has_snapshot and has_signoff and batch.status in {"frozen", "clinical_signed", "approved"}

    return {
        "message": "emr_import_execution_dry_run",
        "mode": "execution_dry_run",
        "batch": _batch_summary(batch),
        "operator_id": _text(data.operator_id),
        "review_only": True,
        "dry_run": True,
        "writes_database": False,
        "writes_case_database": False,
        "creates_case": False,
        "updates_case": False,
        "downloads_attachments": False,
        "executes_real_import": False,
        "can_execute_import": False,
        "ready_for_execution_review": ready_for_execution_review,
        "safety": {
            "writes_database": False,
            "writes_case_database": False,
            "creates_case": False,
            "updates_case": False,
            "downloads_attachments": False,
            "executes_real_import": False,
            "can_execute_import": False,
        },
        "quality_gate": {
            "passed": ready_for_execution_review,
            "batch_status_allowed": batch.status in {"frozen", "clinical_signed", "approved"},
            "has_clinical_signoff": has_signoff,
            "has_rollback_snapshot": has_snapshot,
            "blocked_count": blocked_count,
            "blocked_items": blocked_items,
        },
        "import_diff": {
            "summary": {
                "receipt_count": len(items),
                "would_create_count": would_create_count,
                "would_update_count": would_update_count,
                "blocked_count": blocked_count,
            },
            "items": items,
        },
        "rollback_plan": {
            "snapshot_required": True,
            "rollback_snapshot_id": _text(data.rollback_snapshot_id or batch.rollback_snapshot_id) or None,
            "batch_id": batch.batch_id,
            "receipt_ids": receipt_ids,
            "case_ids_to_restore": sorted({item.get("case_id") for item in items if item.get("case_id")}),
            "steps": [
                "Take database snapshot before any real import execution.",
                "Record batch_id, receipt_ids and execution operator.",
                "If real import fails, stop execution, restore snapshot or reverse inserted cases by import marker.",
                "Run smoke test and clinical spot check after rollback.",
            ],
        },
        "next_gate": "A separate audited real import execution API is required before writing Case records.",
    }


@router.post("/{batch_id}/clinical-approval", response_model=dict)
def approve_emr_real_import_batch(
    batch_id: str,
    data: EmrImportClinicalApprovalIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Apply clinical approval / Go-No-Go decision to a planned EMR batch.

    Safety boundary:
    - writes emr_import_batches approval fields / status
    - appends one audit_log row
    - does not create or update Case
    - does not download attachments
    - does not execute real import
    """

    batch = db.get(EmrImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="EMR import batch not found")

    if batch.status not in APPROVAL_ALLOWED_BATCH_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="batch must be frozen, clinical_signed or approved before clinical approval",
        )

    operator_id = _text(data.operator_id)
    clinical_signoff_id = _text(data.clinical_signoff_id)
    rollback_snapshot_id = _text(data.rollback_snapshot_id)
    approval_action = _text(data.approval_action).lower() or "approve"
    status_after = _approval_status(approval_action)

    if not operator_id:
        raise HTTPException(status_code=422, detail="operator_id is required")
    if not clinical_signoff_id:
        raise HTTPException(status_code=422, detail="clinical_signoff_id is required")
    if not rollback_snapshot_id:
        raise HTTPException(status_code=422, detail="rollback_snapshot_id is required")

    if status_after in {"needs_fix", "approval_rejected"} and len(_text(data.note)) < 10:
        raise HTTPException(
            status_code=422,
            detail="note must be at least 10 characters for needs_fix/rejected approvals",
        )

    dry_run_data = EmrImportExecutionDryRunIn(
        operator_id=operator_id,
        clinical_signoff_id=clinical_signoff_id,
        rollback_snapshot_id=rollback_snapshot_id,
        include_payload_preview=False,
        max_items=data.max_items,
        note=data.note,
    )
    dry_run_report = build_execution_dry_run_report(db=db, batch=batch, data=dry_run_data)
    quality_gate = dry_run_report.get("quality_gate") or {}

    if status_after in {"approved", "clinical_signed"} and not bool(quality_gate.get("passed")):
        raise HTTPException(
            status_code=422,
            detail={
                "message": "execution dry-run quality gate must pass before clinical approval",
                "quality_gate": quality_gate,
            },
        )

    now = datetime.utcnow()
    status_before = batch.status
    batch.status = status_after
    batch.clinical_signoff_id = clinical_signoff_id
    batch.rollback_snapshot_id = rollback_snapshot_id
    if status_after in {"approved", "clinical_signed"}:
        batch.approved_at = now
        batch.approved_by = operator_id
    batch.updated_at = now

    existing_meta = batch.extra_data if isinstance(batch.extra_data, dict) else {}
    batch.extra_data = {
        **existing_meta,
        "clinical_approval": {
            "operator_id": operator_id,
            "clinical_signoff_id": clinical_signoff_id,
            "rollback_snapshot_id": rollback_snapshot_id,
            "approval_action": approval_action,
            "status_before": status_before,
            "status_after": status_after,
            "approved_at": now.isoformat(),
            "quality_gate_passed": bool(quality_gate.get("passed")),
            "metadata": data.metadata or {},
        },
    }

    audit = _append_clinical_approval_audit(
        db,
        batch=batch,
        operator_id=operator_id,
        approval_action=approval_action,
        status_before=status_before,
        status_after=status_after,
        data=data,
        quality_gate=quality_gate,
    )

    db.add(batch)
    db.add(audit)
    db.commit()
    db.refresh(batch)
    db.refresh(audit)

    return {
        "message": "emr_import_clinical_approval",
        "mode": "clinical_approval_api",
        "batch": _batch_summary(batch),
        "status_before": status_before,
        "status_after": batch.status,
        "approval_action": approval_action,
        "clinical_signoff_id": batch.clinical_signoff_id,
        "rollback_snapshot_id": batch.rollback_snapshot_id,
        "approved_by": batch.approved_by,
        "audit_log_id": audit.log_id,
        "quality_gate": quality_gate,
        "import_diff_summary": (dry_run_report.get("import_diff") or {}).get("summary") or {},
        "writes_emr_import_batches": True,
        "writes_audit_log": True,
        "writes_case_database": False,
        "creates_case": False,
        "updates_case": False,
        "downloads_attachments": False,
        "executes_real_import": False,
        "can_execute_import": False,
        "next_gate": "A separate real import execution API is required before writing Case records.",
    }



CREATE_ONLY_PILOT_MAX_RECEIPTS = 5
REAL_IMPORT_ALLOWED_BATCH_STATUSES = {"approved", "clinical_signed"}
REAL_IMPORT_CONFIRMATION = "I_UNDERSTAND_THIS_WILL_CREATE_CASES"


def _assert_execute_feature_gates() -> Dict[str, bool]:
    assert_feature_enabled("ENABLE_EMR_REAL_IMPORT")

    enabled_blockers: List[str] = []
    if is_feature_enabled("ENABLE_EMR_IMPORT_CASE_UPDATE"):
        enabled_blockers.append("ENABLE_EMR_IMPORT_CASE_UPDATE")
    if is_feature_enabled("ENABLE_EMR_ATTACHMENT_DOWNLOAD"):
        enabled_blockers.append("ENABLE_EMR_ATTACHMENT_DOWNLOAD")
    if is_feature_enabled("ENABLE_PRESCRIPTION_STRUCTURED_WRITE"):
        enabled_blockers.append("ENABLE_PRESCRIPTION_STRUCTURED_WRITE")
    if is_feature_enabled("ENABLE_DEVICE_REAL_INGEST"):
        enabled_blockers.append("ENABLE_DEVICE_REAL_INGEST")
    if is_feature_enabled("ENABLE_BILLING_REAL_WRITE"):
        enabled_blockers.append("ENABLE_BILLING_REAL_WRITE")
    if is_feature_enabled("ENABLE_CASE_DELETE_IMPORT"):
        enabled_blockers.append("ENABLE_CASE_DELETE_IMPORT")

    if enabled_blockers:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "unsafe feature flags enabled for create-only EMR import",
                "enabled_blockers": enabled_blockers,
            },
        )

    return {
        "ENABLE_EMR_REAL_IMPORT": True,
        "ENABLE_EMR_IMPORT_CASE_UPDATE": False,
        "ENABLE_EMR_ATTACHMENT_DOWNLOAD": False,
        "ENABLE_PRESCRIPTION_STRUCTURED_WRITE": False,
        "ENABLE_DEVICE_REAL_INGEST": False,
        "ENABLE_BILLING_REAL_WRITE": False,
        "ENABLE_CASE_DELETE_IMPORT": False,
    }

def _case_payload_from_preview(case_create: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "patient_name": _text(case_create.get("patient_name")) or "未命名病例",
        "species": _text(case_create.get("species")) or "other",
        "sex": _text(case_create.get("sex")) or None,
        "age_info": _text(case_create.get("age_info")) or None,
        "breed": _text(case_create.get("breed")) or None,
        "weight": _text(case_create.get("weight")) or None,
        "coat_color": _text(case_create.get("coat_color")) or None,
        "owner_name": _text(case_create.get("owner_name")) or None,
        "owner_phone": _text(case_create.get("owner_phone")) or None,
        "chief_complaint": _text(case_create.get("chief_complaint")) or "EMR 导入病例",
        "history": _text(case_create.get("history")) or None,
        "exam_findings": _text(case_create.get("exam_findings")) or None,
        "analysis": "【EMR real import create-only pilot】由人工批准的 EMR receipt 创建；请临床复核。",
        "treatment": None,
        "prognosis": None,
        "attachments": None,
    }


def _required_case_fields_missing(case_create: Dict[str, Any]) -> List[str]:
    return [
        field for field in ("patient_name", "species", "chief_complaint")
        if not _text(case_create.get(field))
    ]


def _duplicate_reason_for_create(db: Session, receipt: WebhookInbox, case_create: Dict[str, Any]) -> Optional[str]:
    previous_success = (
        db.query(EmrImportExecutionItemResult)
        .filter(EmrImportExecutionItemResult.receipt_id == receipt.receipt_id)
        .filter(EmrImportExecutionItemResult.status == "created")
        .first()
    )
    if previous_success:
        return f"receipt already executed successfully in execution {previous_success.execution_id}"

    if _text(receipt.external_case_id):
        previous_external = (
            db.query(EmrImportExecutionItemResult)
            .filter(EmrImportExecutionItemResult.external_case_id == _text(receipt.external_case_id))
            .filter(EmrImportExecutionItemResult.status == "created")
            .first()
        )
        if previous_external:
            return f"external_case_id already imported in execution {previous_external.execution_id}"

    patient_name = _text(case_create.get("patient_name"))
    species = _text(case_create.get("species"))
    owner_phone = _text(case_create.get("owner_phone"))
    if patient_name and species and owner_phone:
        existing_case = (
            db.query(Case)
            .filter(Case.patient_name == patient_name)
            .filter(Case.species == species)
            .filter(Case.owner_phone == owner_phone)
            .first()
        )
        if existing_case:
            return f"possible duplicate Case already exists: {existing_case.id}"

    return None


def _create_execution_audit(
    db: Session,
    *,
    execution: EmrImportExecutionRun,
    batch: EmrImportBatch,
    operator_id: str,
    data: EmrImportExecuteIn,
    dry_run_summary: Dict[str, Any],
    feature_flags: Dict[str, bool],
) -> AuditLog:
    audit = AuditLog(
        request_id=_text(data.request_id) or f"emr-import-execute-{execution.execution_id}",
        patient_token=batch.source_system,
        clinician_id=operator_id,
        model_version=None,
        confidence=None,
        suggested_action=f"Execute EMR create-only import pilot for batch {batch.batch_id}",
        action_taken=execution.status,
        override_reason="Feature-flag protected create-only EMR import pilot",
        note=_text(data.note) or None,
        case_id=None,
        session_uid=None,
        event_type="emr_import_execute_create_only",
        source="pet-med-ai",
        extra_data={
            "execution_id": execution.execution_id,
            "batch_id": batch.batch_id,
            "source_system": batch.source_system,
            "clinical_signoff_id": data.clinical_signoff_id,
            "rollback_snapshot_id": data.rollback_snapshot_id,
            "receipt_count": execution.receipt_count,
            "created_count": execution.created_count,
            "skipped_count": execution.skipped_count,
            "failed_count": execution.failed_count,
            "dry_run_summary": dry_run_summary,
            "feature_flags": feature_flags,
            "metadata": data.metadata or {},
            "create_only": True,
            "updates_case": False,
            "downloads_attachments": False,
            "executes_real_import": True,
        },
    )
    db.add(audit)
    return audit


@router.post("/{batch_id}/execute", response_model=dict, status_code=201)
def execute_emr_real_import_create_only_pilot(
    batch_id: str,
    data: EmrImportExecuteIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Feature-flag protected create-only EMR real import pilot."""

    feature_flags = _assert_execute_feature_gates()

    batch = db.get(EmrImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="EMR import batch not found")

    operator_id = _text(data.operator_id)
    clinical_signoff_id = _text(data.clinical_signoff_id)
    rollback_snapshot_id = _text(data.rollback_snapshot_id)

    if not operator_id:
        raise HTTPException(status_code=422, detail="operator_id is required")
    if not clinical_signoff_id:
        raise HTTPException(status_code=422, detail="clinical_signoff_id is required")
    if not rollback_snapshot_id:
        raise HTTPException(status_code=422, detail="rollback_snapshot_id is required")
    if not bool(data.dry_run_ack):
        raise HTTPException(status_code=422, detail="dry_run_ack must be true before real create-only pilot")
    if not bool(getattr(data, "create_only_ack", False)):
        raise HTTPException(status_code=422, detail="create_only_ack must be true before real create-only pilot")
    if _text(data.execution_confirmation) != REAL_IMPORT_CONFIRMATION:
        raise HTTPException(
            status_code=422,
            detail=f"execution_confirmation must be {REAL_IMPORT_CONFIRMATION}",
        )

    if batch.status not in REAL_IMPORT_ALLOWED_BATCH_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="batch must be approved or clinical_signed before real create-only execution",
        )

    if clinical_signoff_id != _text(batch.clinical_signoff_id):
        raise HTTPException(status_code=422, detail="clinical_signoff_id must match approved batch")
    if rollback_snapshot_id != _text(batch.rollback_snapshot_id):
        raise HTTPException(status_code=422, detail="rollback_snapshot_id must match approved batch")
    if int(batch.receipt_count or 0) > CREATE_ONLY_PILOT_MAX_RECEIPTS:
        raise HTTPException(
            status_code=422,
            detail=f"batch receipt_count exceeds create-only pilot limit {CREATE_ONLY_PILOT_MAX_RECEIPTS}",
        )

    dry_run_data = EmrImportExecutionDryRunIn(
        operator_id=operator_id,
        clinical_signoff_id=clinical_signoff_id,
        rollback_snapshot_id=rollback_snapshot_id,
        include_payload_preview=False,
        max_items=min(data.max_items, CREATE_ONLY_PILOT_MAX_RECEIPTS),
        note=data.note,
    )
    dry_run_report = build_execution_dry_run_report(db=db, batch=batch, data=dry_run_data)
    quality_gate = dry_run_report.get("quality_gate") or {}
    if not bool(quality_gate.get("passed")):
        raise HTTPException(
            status_code=422,
            detail={
                "message": "execution dry-run quality gate must pass before real create-only pilot",
                "quality_gate": quality_gate,
            },
        )

    dry_run_items = ((dry_run_report.get("import_diff") or {}).get("items") or [])
    non_create = [
        item.get("receipt_id") for item in dry_run_items
        if item.get("operation") != "case_create_preview"
    ]
    if non_create:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "create-only pilot blocks non-create operations",
                "non_create_receipt_ids": non_create,
            },
        )

    blocked = [
        {"receipt_id": item.get("receipt_id"), "blocked_reasons": item.get("blocked_reasons") or []}
        for item in dry_run_items
        if item.get("blocked_reasons")
    ]
    if blocked:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "execution dry-run contains blocked items",
                "blocked_items": blocked,
            },
        )

    links = (
        db.query(EmrImportBatchReceipt)
        .filter(EmrImportBatchReceipt.batch_id == batch.batch_id)
        .order_by(EmrImportBatchReceipt.created_at.asc(), EmrImportBatchReceipt.id.asc())
        .limit(CREATE_ONLY_PILOT_MAX_RECEIPTS)
        .all()
    )
    if not links:
        raise HTTPException(status_code=422, detail="batch has no receipts to execute")

    receipt_ids = [link.receipt_id for link in links]
    receipts = (
        db.query(WebhookInbox)
        .filter(WebhookInbox.receipt_id.in_(receipt_ids))
        .all()
    )
    receipt_by_id = {item.receipt_id: item for item in receipts}

    now = datetime.utcnow()
    execution = EmrImportExecutionRun(
        execution_id="emr_exec_" + uuid4().hex[:24],
        batch_id=batch.batch_id,
        source_system=batch.source_system,
        status="running",
        mode="create_only_pilot_v1",
        operator_id=operator_id,
        clinical_signoff_id=clinical_signoff_id,
        rollback_snapshot_id=rollback_snapshot_id,
        approval_audit_log_id=None,
        receipt_count=len(links),
        created_count=0,
        updated_count=0,
        skipped_count=0,
        failed_count=0,
        rolled_back_count=0,
        started_at=now,
        created_by=operator_id,
        note=_text(data.note) or None,
        extra_data={
            "feature_flags": feature_flags,
            "quality_gate": quality_gate,
            "dry_run_summary": (dry_run_report.get("import_diff") or {}).get("summary") or {},
            "create_only": True,
            "pilot_limit": CREATE_ONLY_PILOT_MAX_RECEIPTS,
            "metadata": data.metadata or {},
        },
    )
    db.add(execution)
    db.flush()

    created_cases = []

    for link in links:
        receipt = receipt_by_id.get(link.receipt_id)
        started_at = datetime.utcnow()
        status = "skipped"
        failure_code = None
        failure_reason = None
        created_case_id = None
        case_diff: Dict[str, Any] = {}

        try:
            if receipt is None:
                failure_code = "receipt_missing"
                failure_reason = "Linked webhook_inbox receipt is missing."
            elif receipt.status != READY_STATUS:
                failure_code = "receipt_not_ready"
                failure_reason = f"Receipt status is {receipt.status}; expected {READY_STATUS}."
            elif receipt.case_id is not None:
                failure_code = "case_update_blocked"
                failure_reason = f"Receipt points to existing Case {receipt.case_id}; create-only pilot blocks updates."
            elif not bool(link.ready_for_import):
                failure_code = "batch_link_not_ready"
                failure_reason = "Batch link is not marked ready_for_import."
            elif link.review_status != READY_STATUS:
                failure_code = "review_status_not_ready"
                failure_reason = f"Batch link review_status is {link.review_status}; expected {READY_STATUS}."
            else:
                case_create = receipt.mapped_case_preview if isinstance(receipt.mapped_case_preview, dict) else {}
                missing_fields = _required_case_fields_missing(case_create)
                if missing_fields:
                    failure_code = "required_fields_missing"
                    failure_reason = "Missing required fields: " + ", ".join(missing_fields)
                else:
                    duplicate_reason = _duplicate_reason_for_create(db, receipt, case_create)
                    if duplicate_reason:
                        failure_code = "duplicate_blocked"
                        failure_reason = duplicate_reason
                    else:
                        payload = _case_payload_from_preview(case_create)
                        case = Case(owner_id=getattr(user, "id", None), **payload)
                        db.add(case)
                        db.flush()
                        created_case_id = case.id
                        status = "created"
                        case_diff = {
                            "operation": "case_create",
                            "created_fields": sorted(payload.keys()),
                            "source": "emr_import_create_only_pilot_v1",
                        }
                        created_cases.append({
                            "case_id": case.id,
                            "receipt_id": receipt.receipt_id,
                            "external_case_id": receipt.external_case_id,
                        })
        except Exception as exc:
            status = "failed"
            failure_code = "create_exception"
            failure_reason = str(exc)[:1000]

        if status == "created":
            execution.created_count += 1
        elif status == "failed":
            execution.failed_count += 1
        else:
            execution.skipped_count += 1

        result = EmrImportExecutionItemResult(
            execution_id=execution.execution_id,
            batch_id=batch.batch_id,
            receipt_id=link.receipt_id,
            external_case_id=link.external_case_id,
            external_encounter_id=link.external_encounter_id,
            idempotency_key=getattr(receipt, "idempotency_key", None) if receipt else None,
            payload_hash=getattr(receipt, "payload_hash", None) if receipt else None,
            operation="case_create",
            status=status,
            created_case_id=created_case_id,
            target_case_id=None,
            failure_code=failure_code,
            failure_reason=failure_reason,
            rollback_status="not_required" if status != "created" else "pending_if_needed",
            rollback_note=None,
            case_diff=case_diff or None,
            result_payload={
                "receipt_id": link.receipt_id,
                "status": status,
                "created_case_id": created_case_id,
                "failure_code": failure_code,
                "failure_reason": failure_reason,
            },
            extra_data={
                "create_only": True,
                "source": "emr_import_execute_api_v1",
            },
            started_at=started_at,
            completed_at=datetime.utcnow(),
        )
        db.add(result)

    execution.status = "completed" if execution.failed_count == 0 else "completed_with_failures"
    execution.completed_at = datetime.utcnow()
    execution.updated_at = datetime.utcnow()

    batch.status = "completed" if execution.failed_count == 0 else "failed"
    batch.started_at = execution.started_at
    batch.completed_at = execution.completed_at
    batch.updated_at = datetime.utcnow()
    existing_meta = batch.extra_data if isinstance(batch.extra_data, dict) else {}
    batch.extra_data = {
        **existing_meta,
        "last_execution": {
            "execution_id": execution.execution_id,
            "operator_id": operator_id,
            "created_count": execution.created_count,
            "skipped_count": execution.skipped_count,
            "failed_count": execution.failed_count,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "feature_flags": feature_flags,
        },
    }

    audit = _create_execution_audit(
        db,
        execution=execution,
        batch=batch,
        operator_id=operator_id,
        data=data,
        dry_run_summary=(dry_run_report.get("import_diff") or {}).get("summary") or {},
        feature_flags=feature_flags,
    )
    db.add(batch)
    db.add(execution)
    db.add(audit)
    db.commit()
    db.refresh(execution)
    db.refresh(audit)

    return {
        "message": "emr_real_import_execute_create_only_pilot",
        "mode": "create_only_pilot_v1",
        "execution_id": execution.execution_id,
        "batch_id": batch.batch_id,
        "status": execution.status,
        "audit_log_id": audit.log_id,
        "created_cases": created_cases,
        "summary": {
            "receipt_count": execution.receipt_count,
            "created_count": execution.created_count,
            "updated_count": execution.updated_count,
            "skipped_count": execution.skipped_count,
            "failed_count": execution.failed_count,
        },
        "feature_flags": feature_flags,
        "writes_database": True,
        "writes_case_database": True,
        "writes_audit_log": True,
        "writes_execution_results": True,
        "creates_case": execution.created_count > 0,
        "updates_case": False,
        "downloads_attachments": False,
        "executes_real_import": True,
        "can_execute_import": False,
        "create_only": True,
        "pilot_limit": CREATE_ONLY_PILOT_MAX_RECEIPTS,
        "rollback_snapshot_id": rollback_snapshot_id,
        "clinical_signoff_id": clinical_signoff_id,
        "post_execution_required": [
            "run smoke immediately",
            "100 percent clinical spot-check for created cases",
            "record Go / pause / rollback decision",
        ],
    }


@router.post("/{batch_id}/execution-dry-run", response_model=dict)
def dry_run_emr_real_import_execution(
    batch_id: str,
    data: EmrImportExecutionDryRunIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Generate import diff and rollback plan for a planned EMR import batch.

    V1 is a dry-run only:
    - reads emr_import_batches and linked webhook_inbox receipts
    - returns would-create / would-update diff
    - returns rollback plan
    - does not mutate database
    - does not create/update Case
    """

    batch = db.get(EmrImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="EMR import batch not found")

    if batch.status not in {"frozen", "clinical_signed", "approved"}:
        raise HTTPException(
            status_code=422,
            detail="batch must be frozen, clinical_signed or approved before execution dry-run",
        )

    return build_execution_dry_run_report(db=db, batch=batch, data=data)


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
