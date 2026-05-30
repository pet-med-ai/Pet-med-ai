# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import Case, ImagingStudy, ImagingBilling, FollowUp, QaAudit
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import Case, ImagingStudy, ImagingBilling, FollowUp, QaAudit


router = APIRouter(prefix="/api/kpi", tags=["kpi"])

DEFAULT_DAYS = 30

CASE_COMPLETENESS_CHECKS = [
    "patient_name",
    "species",
    "chief_complaint",
    "weight",
    "exam_findings",
    "analysis",
    "care_plan",
]

DUPLICATE_TAGS = {
    "duplicate",
    "repeat",
    "repeated",
    "no_value",
    "no_diagnostic_value",
    "重复",
    "复拍",
    "无新增诊断价值",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _parse_datetime(value: Optional[str], *, is_end: bool = False) -> Optional[datetime]:
    raw = _text(value)
    if not raw:
        return None

    try:
        if len(raw) == 10:
            base = datetime.strptime(raw, "%Y-%m-%d")
            return base + timedelta(days=1) if is_end else base

        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {'end' if is_end else 'start'} datetime: {raw}. Use YYYY-MM-DD or ISO 8601.",
        ) from exc


def _date_window(start: Optional[str], end: Optional[str]) -> Tuple[datetime, datetime]:
    end_dt = _parse_datetime(end, is_end=True) or datetime.utcnow()
    start_dt = _parse_datetime(start, is_end=False) or (end_dt - timedelta(days=DEFAULT_DAYS))

    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="start must be earlier than end")

    return start_dt, end_dt


def _period_payload(start_dt: datetime, end_dt: datetime) -> Dict[str, str]:
    return {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "timezone_note": "Datetime values are evaluated as stored by SQLAlchemy; ISO inputs with timezone are normalized to UTC-naive for comparison.",
    }


def _round_ratio(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _case_query(db: Session, user: Any, start_dt: datetime, end_dt: datetime):
    query = db.query(Case).filter(
        Case.owner_id == getattr(user, "id", None),
        Case.created_at >= start_dt,
        Case.created_at < end_dt,
    )
    if hasattr(Case, "deleted_at"):
        query = query.filter(Case.deleted_at.is_(None))
    return query


def _case_missing_fields(case: Case) -> List[str]:
    missing: List[str] = []
    for field in CASE_COMPLETENESS_CHECKS:
        if field == "care_plan":
            value = _text(getattr(case, "treatment", "")) or _text(getattr(case, "prognosis", ""))
        else:
            value = _text(getattr(case, field, ""))
        if not value:
            missing.append(field)
    return missing


def build_case_kpi(
    db: Session,
    user: Any,
    start_dt: datetime,
    end_dt: datetime,
    *,
    include_samples: bool = True,
) -> Dict[str, Any]:
    cases = _case_query(db, user, start_dt, end_dt).all()
    total = len(cases)

    complete = 0
    missing_counter: Counter = Counter()
    incomplete_samples: List[Dict[str, Any]] = []

    for item in cases:
        missing = _case_missing_fields(item)
        if not missing:
            complete += 1
        else:
            for field in missing:
                missing_counter[field] += 1
            if include_samples and len(incomplete_samples) < 20:
                incomplete_samples.append({
                    "case_id": item.id,
                    "patient_name": item.patient_name,
                    "species": item.species,
                    "missing_fields": missing,
                })

    return {
        "message": "kpi_cases",
        "period": _period_payload(start_dt, end_dt),
        "metrics": {
            "case_completeness": {
                "total_cases": total,
                "complete_cases": complete,
                "incomplete_cases": total - complete,
                "rate": _round_ratio(complete, total),
                "threshold": 0.95,
                "required_fields_v1": CASE_COMPLETENESS_CHECKS,
                "missing_by_field": dict(sorted(missing_counter.items())),
                "incomplete_samples": incomplete_samples if include_samples else [],
                "v1_note": "Current V1 completeness uses existing Pet-Med-AI Case fields. Temperature, allergy, invoice and closed_at require later data-model phases.",
            },
            "average_time_to_close": {
                "avg_hours": None,
                "closed_cases": 0,
                "threshold_outpatient_hours": 6,
                "threshold_inpatient_hours": 72,
                "status": "unavailable",
                "v1_note": "Case model does not yet include closed_at/status required for true time-to-close.",
            },
        },
    }


def _owned_imaging_studies(db: Session, user: Any, start_dt: datetime, end_dt: datetime) -> List[ImagingStudy]:
    return (
        db.query(ImagingStudy)
        .join(Case, ImagingStudy.case_id == Case.id)
        .filter(
            Case.owner_id == getattr(user, "id", None),
            ImagingStudy.taken_at >= start_dt,
            ImagingStudy.taken_at < end_dt,
        )
        .all()
    )


def _owned_imaging_billing(db: Session, user: Any, start_dt: datetime, end_dt: datetime) -> List[ImagingBilling]:
    return (
        db.query(ImagingBilling)
        .join(Case, ImagingBilling.case_id == Case.id)
        .filter(
            Case.owner_id == getattr(user, "id", None),
            ImagingBilling.bill_date >= start_dt,
            ImagingBilling.bill_date < end_dt,
        )
        .all()
    )


def build_imaging_kpi(
    db: Session,
    user: Any,
    start_dt: datetime,
    end_dt: datetime,
    *,
    include_samples: bool = True,
) -> Dict[str, Any]:
    studies = _owned_imaging_studies(db, user, start_dt, end_dt)
    unplanned = [item for item in studies if not bool(item.is_planned_review)]

    groups: Dict[Tuple[Any, str, str], List[ImagingStudy]] = defaultdict(list)
    for item in unplanned:
        key = (
            item.case_id,
            _text(item.modality).lower(),
            _text(item.body_part).lower() or "unknown",
        )
        groups[key].append(item)

    repeat_groups = [
        (key, rows)
        for key, rows in groups.items()
        if len(rows) > 1
    ]

    repeat_anomalies = []
    if include_samples:
        for key, rows in sorted(repeat_groups, key=lambda pair: len(pair[1]), reverse=True)[:20]:
            case_id, modality, body_part = key
            repeat_anomalies.append({
                "case_id": case_id,
                "modality": modality,
                "body_part": body_part,
                "count": len(rows),
                "first_taken_at": min(row.taken_at for row in rows).isoformat(),
                "last_taken_at": max(row.taken_at for row in rows).isoformat(),
            })

    billings = _owned_imaging_billing(db, user, start_dt, end_dt)
    total_fee = sum(float(item.fee or 0.0) for item in billings)
    duplicate_fee = sum(
        float(item.fee or 0.0)
        for item in billings
        if _text(item.tag).lower() in DUPLICATE_TAGS
    )

    return {
        "message": "kpi_imaging",
        "period": _period_payload(start_dt, end_dt),
        "metrics": {
            "repeat_imaging": {
                "study_count": len(studies),
                "unplanned_study_count": len(unplanned),
                "group_count": len(groups),
                "repeat_group_count": len(repeat_groups),
                "rate": _round_ratio(len(repeat_groups), len(groups)),
                "threshold": 0.08,
                "anomalies": repeat_anomalies,
            },
            "duplicate_imaging_share": {
                "billing_rows": len(billings),
                "total_fee": round(total_fee, 2),
                "duplicate_fee": round(duplicate_fee, 2),
                "share": _round_ratio(duplicate_fee, total_fee),
                "threshold": 0.05,
            },
        },
    }


def _owned_followups(db: Session, user: Any, start_dt: datetime, end_dt: datetime) -> List[FollowUp]:
    return (
        db.query(FollowUp)
        .join(Case, FollowUp.case_id == Case.id)
        .filter(
            Case.owner_id == getattr(user, "id", None),
            FollowUp.due_date >= start_dt,
            FollowUp.due_date < end_dt,
        )
        .all()
    )


def build_followup_kpi(
    db: Session,
    user: Any,
    start_dt: datetime,
    end_dt: datetime,
    *,
    include_samples: bool = True,
) -> Dict[str, Any]:
    rows = _owned_followups(db, user, start_dt, end_dt)

    bands = Counter({
        "same_day": 0,
        "within_1_day": 0,
        "within_2_days": 0,
        "overdue_or_missing": 0,
    })
    on_time = 0
    overdue_samples = []

    for item in rows:
        if item.done_at is None:
            bands["overdue_or_missing"] += 1
            if include_samples and len(overdue_samples) < 20:
                overdue_samples.append({
                    "case_id": item.case_id,
                    "due_date": item.due_date.isoformat(),
                    "done_at": None,
                    "owner": item.owner,
                    "status": item.status,
                })
            continue

        delta_days = (item.done_at.date() - item.due_date.date()).days
        if delta_days == 0:
            bands["same_day"] += 1
        if abs(delta_days) <= 1:
            bands["within_1_day"] += 1
            on_time += 1
        elif abs(delta_days) <= 2:
            bands["within_2_days"] += 1
        else:
            bands["overdue_or_missing"] += 1
            if include_samples and len(overdue_samples) < 20:
                overdue_samples.append({
                    "case_id": item.case_id,
                    "due_date": item.due_date.isoformat(),
                    "done_at": item.done_at.isoformat(),
                    "owner": item.owner,
                    "status": item.status,
                })

    return {
        "message": "kpi_followups",
        "period": _period_payload(start_dt, end_dt),
        "metrics": {
            "followup_compliance": {
                "due_total": len(rows),
                "done_within_due_plus_minus_1_day": on_time,
                "rate": _round_ratio(on_time, len(rows)),
                "threshold": 0.85,
                "bands": dict(bands),
                "overdue_samples": overdue_samples,
            }
        },
    }


def _owned_qa_audits(db: Session, user: Any, start_dt: datetime, end_dt: datetime) -> List[QaAudit]:
    return (
        db.query(QaAudit)
        .join(Case, QaAudit.case_id == Case.id)
        .filter(
            Case.owner_id == getattr(user, "id", None),
            QaAudit.created_at >= start_dt,
            QaAudit.created_at < end_dt,
        )
        .all()
    )


def build_qa_kpi(
    db: Session,
    user: Any,
    start_dt: datetime,
    end_dt: datetime,
    *,
    include_samples: bool = True,
) -> Dict[str, Any]:
    cases = _case_query(db, user, start_dt, end_dt).all()
    audits = _owned_qa_audits(db, user, start_dt, end_dt)

    audited_case_ids = {item.case_id for item in audits}
    severity_counts = Counter(_text(item.severity).lower() or "unspecified" for item in audits)
    status_counts = Counter(_text(item.status).lower() or "unspecified" for item in audits)

    samples = []
    if include_samples:
        for item in audits[:20]:
            samples.append({
                "case_id": item.case_id,
                "audit_type": item.audit_type,
                "severity": item.severity,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })

    return {
        "message": "kpi_qa",
        "period": _period_payload(start_dt, end_dt),
        "metrics": {
            "qa_audit_coverage": {
                "total_cases": len(cases),
                "audited_cases": len(audited_case_ids),
                "audit_rows": len(audits),
                "rate": _round_ratio(len(audited_case_ids), len(cases)),
                "threshold": 0.15,
                "severity_counts": dict(sorted(severity_counts.items())),
                "status_counts": dict(sorted(status_counts.items())),
                "samples": samples,
            }
        },
    }


def build_dashboard_kpi(
    db: Session,
    user: Any,
    start_dt: datetime,
    end_dt: datetime,
) -> Dict[str, Any]:
    cases = build_case_kpi(db, user, start_dt, end_dt, include_samples=True)
    imaging = build_imaging_kpi(db, user, start_dt, end_dt, include_samples=True)
    followups = build_followup_kpi(db, user, start_dt, end_dt, include_samples=True)
    qa = build_qa_kpi(db, user, start_dt, end_dt, include_samples=True)

    case_metrics = cases["metrics"]
    imaging_metrics = imaging["metrics"]
    followup_metrics = followups["metrics"]
    qa_metrics = qa["metrics"]

    return {
        "message": "kpi_dashboard",
        "period": _period_payload(start_dt, end_dt),
        "cards": {
            "case_completeness": {
                "label": "病例字段完整度率",
                "value": case_metrics["case_completeness"]["rate"],
                "threshold": case_metrics["case_completeness"]["threshold"],
                "direction": "higher_is_better",
            },
            "repeat_imaging_rate": {
                "label": "影像复拍率",
                "value": imaging_metrics["repeat_imaging"]["rate"],
                "threshold": imaging_metrics["repeat_imaging"]["threshold"],
                "direction": "lower_is_better",
            },
            "followup_compliance": {
                "label": "回访合规率",
                "value": followup_metrics["followup_compliance"]["rate"],
                "threshold": followup_metrics["followup_compliance"]["threshold"],
                "direction": "higher_is_better",
            },
            "average_time_to_close_hours": {
                "label": "平均结案时长",
                "value": case_metrics["average_time_to_close"]["avg_hours"],
                "threshold": case_metrics["average_time_to_close"]["threshold_outpatient_hours"],
                "direction": "lower_is_better",
                "status": case_metrics["average_time_to_close"]["status"],
            },
            "duplicate_imaging_share": {
                "label": "重复影像占比",
                "value": imaging_metrics["duplicate_imaging_share"]["share"],
                "threshold": imaging_metrics["duplicate_imaging_share"]["threshold"],
                "direction": "lower_is_better",
            },
            "qa_audit_coverage": {
                "label": "QA 审计覆盖率",
                "value": qa_metrics["qa_audit_coverage"]["rate"],
                "threshold": qa_metrics["qa_audit_coverage"]["threshold"],
                "direction": "higher_is_better",
            },
        },
        "sections": {
            "cases": cases,
            "imaging": imaging,
            "followups": followups,
            "qa": qa,
        },
    }


@router.get("/cases", response_model=dict)
def kpi_cases(
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    start_dt, end_dt = _date_window(start, end)
    return build_case_kpi(db, user, start_dt, end_dt)


@router.get("/imaging", response_model=dict)
def kpi_imaging(
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    start_dt, end_dt = _date_window(start, end)
    return build_imaging_kpi(db, user, start_dt, end_dt)


@router.get("/followups", response_model=dict)
def kpi_followups(
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    start_dt, end_dt = _date_window(start, end)
    return build_followup_kpi(db, user, start_dt, end_dt)


@router.get("/qa", response_model=dict)
def kpi_qa(
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    start_dt, end_dt = _date_window(start, end)
    return build_qa_kpi(db, user, start_dt, end_dt)


@router.get("/dashboard", response_model=dict)
def kpi_dashboard(
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    start_dt, end_dt = _date_window(start, end)
    return build_dashboard_kpi(db, user, start_dt, end_dt)
