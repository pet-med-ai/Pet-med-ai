# backend/models.py
from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    Boolean,
    Float,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # 删除用户时，级联删除其病例（与你原来保持一致）
    cases: Mapped[List["Case"]] = relationship(
        back_populates="owner",
        cascade="all, delete",
        passive_deletes=True,
    )


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    patient_name: Mapped[str] = mapped_column(String(255), index=True)
    species: Mapped[str] = mapped_column(String(50), default="dog")   # dog/cat/other
    sex: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    age_info: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "4y", "6m"
    breed: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weight: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    coat_color: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 主诉/病史/检查
    chief_complaint: Mapped[str] = mapped_column(Text)
    history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exam_findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 结果/计划
    analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prognosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # （可选）附件，与你前端 /api/files 返回的结构兼容：[{id,url,name,type,size}, ...]
    attachments: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    # ⭐ 软删除标记（前端“撤销”用）
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    owner: Mapped["User"] = relationship(back_populates="cases")

    # 可选：组合索引，常见查询更快
    __table_args__ = (
        Index("ix_cases_patient_species", "patient_name", "species"),
    )

class ConsultSession(Base):
    """
    动态问诊会话 V1：
    - 保存初始主诉、追问回答数组、最近一次 AI 返回结果。
    - 可绑定 owner_id 做用户隔离，可绑定 case_id 追溯已保存病例。
    - session_uid 给前端持有，避免暴露自增 ID。
    """
    __tablename__ = "consult_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    case_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    answers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    __table_args__ = (
        Index("ix_consult_sessions_created_at", "created_at"),
    )


class ImagingStudy(Base):
    """
    KPI / diagnostics V1:
    Imaging metadata only. It stores study/report/viewer references and quality tags,
    not raw DICOM image files.
    """
    __tablename__ = "imaging_studies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    modality: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    body_part: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    is_planned_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    report_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    viewer_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_imaging_studies_case_modality_part_time", "case_id", "modality", "body_part", "taken_at"),
    )


class ImagingBilling(Base):
    """
    KPI V1 billing-side imaging summary.
    Used for duplicate imaging share; does not replace the clinic billing system.
    """
    __tablename__ = "imaging_billing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    imaging_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("imaging_studies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    bill_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_imaging_billing_case_bill_date", "case_id", "bill_date"),
    )


class FollowUp(Base):
    """
    KPI V1 follow-up plan/result table.
    Used for follow-up compliance dashboards.
    """
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    done_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    channel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="due", nullable=False, index=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    __table_args__ = (
        Index("ix_followups_case_due_date", "case_id", "due_date"),
        Index("ix_followups_status_due_date", "status", "due_date"),
    )


class QaAudit(Base):
    """
    KPI V1 QA audit sampling table.
    Used for QA audit coverage and follow-up action tracking.
    """
    __tablename__ = "qa_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    auditor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    audit_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_qa_audit_case_created_at", "case_id", "created_at"),
    )

class AuditLog(Base):
    """
    Compliance / audit V1 append-only log.

    Intended for AI recommendation review, EMR webhook receipts, KB patch review,
    and later clinical override workflows. The application should only append rows;
    no update/delete API should be provided.
    """
    __tablename__ = "audit_log"

    log_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    patient_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    clinician_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    suggested_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_taken: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    case_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_uid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), default="ai_review", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), default="pet-med-ai", nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_log_request_created_at", "request_id", "created_at"),
        Index("ix_audit_log_clinician_created_at", "clinician_id", "created_at"),
    )

class WebhookInbox(Base):
    """
    EMR / external webhook inbox V1.

    This table persists inbound webhook receipt metadata for idempotency,
    traceability, dry-run validation reports, and later async processing.
    It does not create Case records by itself.
    """
    __tablename__ = "webhook_inbox"

    receipt_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"rcpt_{uuid4().hex}")

    source: Mapped[str] = mapped_column(String(100), default="emr", nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), default="case.upsert", nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    signature_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    external_case_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    external_encounter_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    case_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(50), default="received", nullable=False, index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    validation_errors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    validation_warnings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    mapped_case_preview: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    __table_args__ = (
        Index("ux_webhook_inbox_idempotency_key", "idempotency_key", unique=True),
        Index("ix_webhook_inbox_source_received", "source", "received_at"),
        Index("ix_webhook_inbox_status_received", "status", "received_at"),
        Index("ix_webhook_inbox_external_case", "external_case_id", "external_encounter_id"),
    )

class EmrImportBatch(Base):
    """
    EMR real import batch V1.

    This table tracks a frozen, reviewed batch of webhook receipts before any
    future real Case import implementation. It does not create Case records by
    itself.
    """
    __tablename__ = "emr_import_batches"

    batch_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"emr_batch_{uuid4().hex}")
    source_system: Mapped[str] = mapped_column(String(100), default="emr", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)

    receipt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ready_for_import_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_action_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    clinical_signoff_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    rollback_snapshot_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    frozen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    __table_args__ = (
        Index("ix_emr_import_batches_status_created", "status", "created_at"),
        Index("ix_emr_import_batches_source_status", "source_system", "status"),
    )


class EmrImportBatchReceipt(Base):
    """
    Link table between EMR real import batches and webhook_inbox receipts.

    V1 stores selection and review snapshots only. It does not execute the import.
    """
    __tablename__ = "emr_import_batch_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("emr_import_batches.batch_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("webhook_inbox.receipt_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    review_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    ready_for_import: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    external_case_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    external_encounter_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ux_emr_import_batch_receipt", "batch_id", "receipt_id", unique=True),
        Index("ix_emr_import_batch_receipts_ready", "batch_id", "ready_for_import"),
    )

class EmrImportExecutionRun(Base):
    """
    EMR real import execution result V1.

    This table records a future real-import execution run for a previously
    approved EMR import batch. The model is result tracking only; it does not
    execute imports by itself.
    """
    __tablename__ = "emr_import_execution_runs"

    execution_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"emr_exec_{uuid4().hex}")
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("emr_import_batches.batch_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_system: Mapped[str] = mapped_column(String(100), default="emr", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="planned", nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(100), default="real_import_execution_result", nullable=False)

    operator_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    clinical_signoff_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    rollback_snapshot_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    approval_audit_log_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("audit_log.log_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    receipt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rolled_back_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    __table_args__ = (
        Index("ix_emr_import_execution_runs_batch_status", "batch_id", "status"),
        Index("ix_emr_import_execution_runs_source_created", "source_system", "created_at"),
    )


class EmrImportExecutionItemResult(Base):
    """
    Per-receipt execution result V1.

    Each row records what happened, or would be recorded, for one webhook_inbox
    receipt inside a future real-import execution run. It supports tracking
    created_case_id, failure reasons, and rollback status without changing the
    Case table model in this phase.
    """
    __tablename__ = "emr_import_execution_item_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("emr_import_execution_runs.execution_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("emr_import_batches.batch_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receipt_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("webhook_inbox.receipt_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    external_case_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    external_encounter_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    operation: Mapped[str] = mapped_column(String(50), default="case_create", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)

    created_case_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_case_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    failure_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rollback_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    rollback_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    case_diff: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    __table_args__ = (
        Index("ux_emr_import_execution_item_receipt", "execution_id", "receipt_id", unique=True),
        Index("ix_emr_import_execution_items_batch_status", "batch_id", "status"),
        Index("ix_emr_import_execution_items_failure", "failure_code", "status"),
        Index("ix_emr_import_execution_items_created_case", "created_case_id", "status"),
    )

