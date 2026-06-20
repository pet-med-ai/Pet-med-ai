# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import Case, DiagnosticReport, Observation, ImagingStudy
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import Case, DiagnosticReport, Observation, ImagingStudy


router = APIRouter(prefix="/api/diagnostic-data", tags=["diagnostic-data"])

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "docs" / "clinical_data" / "fixtures"
MODE = "diagnostic_data_readonly_api_dry_run_fixtures_v1"


def _user_id(user: Any) -> int:
    value = getattr(user, "id", None)
    if value is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return int(value)


def _safety_flags(*, dry_run: bool = False) -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": bool(dry_run),
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "downloads_attachments": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
    }


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _metadata(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _owned_case_or_404(db: Session, case_id: int, user: Any) -> Case:
    case = db.get(Case, int(case_id))
    if not case or int(getattr(case, "owner_id", -1)) != _user_id(user):
        raise HTTPException(status_code=404, detail="Case not found")
    if getattr(case, "deleted_at", None) is not None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _page(page: int, page_size: int) -> Tuple[int, int]:
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, min(int(page_size or 20), 100))
    return safe_page, safe_page_size


def _case_payload(case: Case) -> Dict[str, Any]:
    return {
        "case_id": case.id,
        "patient_name": case.patient_name,
        "species": case.species,
        "created_at": _iso(case.created_at),
        "updated_at": _iso(case.updated_at),
    }


def _diagnostic_report_payload(report: DiagnosticReport) -> Dict[str, Any]:
    return {
        "report_id": report.id,
        "case_id": report.case_id,
        "report_type": report.report_type,
        "source_type": report.source_type,
        "source_system": report.source_system,
        "source_report_id": report.source_report_id,
        "status": report.status,
        "title": report.title,
        "report_text": report.report_text,
        "abnormal_summary": report.abnormal_summary,
        "ai_summary": report.ai_summary,
        "ai_summary_status": report.ai_summary_status,
        "ordering_clinician": report.ordering_clinician,
        "reviewed_by": report.reviewed_by,
        "reviewed_at": _iso(report.reviewed_at),
        "attachment_ref": report.attachment_ref,
        "metadata": _metadata(report.metadata_json),
        "created_at": _iso(report.created_at),
        "updated_at": _iso(report.updated_at),
    }


def _observation_payload(item: Observation) -> Dict[str, Any]:
    return {
        "observation_id": item.id,
        "case_id": item.case_id,
        "diagnostic_report_id": item.diagnostic_report_id,
        "code": item.code,
        "display_name": item.display_name,
        "value_text": item.value_text,
        "value_numeric": item.value_numeric,
        "value_type": item.value_type,
        "unit": item.unit,
        "reference_low": item.reference_low,
        "reference_high": item.reference_high,
        "reference_text": item.reference_text,
        "abnormal_flag": item.abnormal_flag,
        "interpretation": item.interpretation,
        "specimen_type": item.specimen_type,
        "collected_at": _iso(item.collected_at),
        "observed_at": _iso(item.observed_at),
        "source_type": item.source_type,
        "review_status": item.review_status,
        "metadata": _metadata(item.metadata_json),
        "created_at": _iso(item.created_at),
        "updated_at": _iso(item.updated_at),
    }


def _imaging_study_payload(item: ImagingStudy) -> Dict[str, Any]:
    return {
        "imaging_study_id": item.id,
        "case_id": item.case_id,
        "modality": item.modality,
        "body_part": item.body_part,
        "taken_at": _iso(item.taken_at),
        "is_planned_review": item.is_planned_review,
        "tag": item.tag,
        "report_url": item.report_url,
        "viewer_url": item.viewer_url,
        "thumbnail_url": item.thumbnail_url,
        "metadata": _metadata(item.extra_data),
        "study_uid": item.study_uid,
        "accession_number": item.accession_number,
        "source_type": item.source_type,
        "source_system": item.source_system,
        "report_text": item.report_text,
        "abnormal_flag": item.abnormal_flag,
        "ai_summary": item.ai_summary,
        "ai_summary_status": item.ai_summary_status,
        "review_status": item.review_status,
        "reviewed_by": item.reviewed_by,
        "reviewed_at": _iso(item.reviewed_at),
        "attachment_ref": item.attachment_ref,
        "created_at": _iso(item.created_at),
        "updated_at": _iso(item.updated_at),
    }


def _report_query_for_case(db: Session, case_id: int):
    return db.query(DiagnosticReport).filter(DiagnosticReport.case_id == int(case_id))


def _observation_query_for_case(db: Session, case_id: int):
    return db.query(Observation).filter(Observation.case_id == int(case_id))


def _imaging_query_for_case(db: Session, case_id: int):
    return db.query(ImagingStudy).filter(ImagingStudy.case_id == int(case_id))


@router.get("/cases/{case_id}/summary", response_model=dict)
def get_diagnostic_data_case_summary(
    case_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    case = _owned_case_or_404(db, case_id, user)

    reports = (
        _report_query_for_case(db, case.id)
        .order_by(DiagnosticReport.created_at.desc(), DiagnosticReport.id.desc())
        .limit(100)
        .all()
    )
    observations = (
        _observation_query_for_case(db, case.id)
        .order_by(Observation.created_at.desc(), Observation.id.desc())
        .limit(200)
        .all()
    )
    imaging_studies = (
        _imaging_query_for_case(db, case.id)
        .order_by(ImagingStudy.taken_at.desc(), ImagingStudy.id.desc())
        .limit(100)
        .all()
    )

    safety = _safety_flags()
    return {
        "message": "diagnostic_data_case_summary",
        "mode": MODE,
        "case": _case_payload(case),
        "counts": {
            "reports": len(reports),
            "observations": len(observations),
            "imaging_studies": len(imaging_studies),
        },
        "reports": [_diagnostic_report_payload(item) for item in reports],
        "observations": [_observation_payload(item) for item in observations],
        "imaging_studies": [_imaging_study_payload(item) for item in imaging_studies],
        "safety": safety,
        **safety,
    }


@router.get("/cases/{case_id}/reports", response_model=dict)
def list_diagnostic_reports(
    case_id: int,
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    case = _owned_case_or_404(db, case_id, user)
    safe_page, safe_page_size = _page(page, page_size)

    query = _report_query_for_case(db, case.id)
    if report_type:
        query = query.filter(DiagnosticReport.report_type == report_type)
    if status:
        query = query.filter(DiagnosticReport.status == status)

    total = query.count()
    reports = (
        query.order_by(DiagnosticReport.created_at.desc(), DiagnosticReport.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    safety = _safety_flags()
    return {
        "message": "diagnostic_reports",
        "mode": MODE,
        "case": _case_payload(case),
        "items": [_diagnostic_report_payload(item) for item in reports],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "safety": safety,
        **safety,
    }


@router.get("/reports/{report_id}", response_model=dict)
def get_diagnostic_report(
    report_id: int,
    include_observations: bool = True,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = (
        db.query(DiagnosticReport)
        .join(Case, DiagnosticReport.case_id == Case.id)
        .filter(
            DiagnosticReport.id == int(report_id),
            Case.owner_id == _user_id(user),
        )
    )
    report = query.first()
    if not report:
        raise HTTPException(status_code=404, detail="Diagnostic report not found")

    observations: List[Observation] = []
    if include_observations:
        observations = (
            db.query(Observation)
            .filter(Observation.diagnostic_report_id == report.id)
            .order_by(Observation.created_at.desc(), Observation.id.desc())
            .all()
        )

    safety = _safety_flags()
    return {
        "message": "diagnostic_report",
        "mode": MODE,
        "report": _diagnostic_report_payload(report),
        "observations": [_observation_payload(item) for item in observations],
        "safety": safety,
        **safety,
    }


@router.get("/cases/{case_id}/observations", response_model=dict)
def list_observations(
    case_id: int,
    code: Optional[str] = None,
    abnormal_only: bool = False,
    review_status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    case = _owned_case_or_404(db, case_id, user)
    safe_page, safe_page_size = _page(page, page_size)

    query = _observation_query_for_case(db, case.id)
    if code:
        query = query.filter(Observation.code == code)
    if review_status:
        query = query.filter(Observation.review_status == review_status)
    if abnormal_only:
        query = query.filter(Observation.abnormal_flag.isnot(None), Observation.abnormal_flag != "")

    total = query.count()
    observations = (
        query.order_by(Observation.created_at.desc(), Observation.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    safety = _safety_flags()
    return {
        "message": "diagnostic_observations",
        "mode": MODE,
        "case": _case_payload(case),
        "items": [_observation_payload(item) for item in observations],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "safety": safety,
        **safety,
    }


@router.get("/cases/{case_id}/imaging-studies", response_model=dict)
def list_imaging_studies(
    case_id: int,
    modality: Optional[str] = None,
    abnormal_flag: Optional[str] = None,
    review_status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    case = _owned_case_or_404(db, case_id, user)
    safe_page, safe_page_size = _page(page, page_size)

    query = _imaging_query_for_case(db, case.id)
    if modality:
        query = query.filter(ImagingStudy.modality == modality)
    if abnormal_flag:
        query = query.filter(ImagingStudy.abnormal_flag == abnormal_flag)
    if review_status:
        query = query.filter(ImagingStudy.review_status == review_status)

    total = query.count()
    studies = (
        query.order_by(ImagingStudy.taken_at.desc(), ImagingStudy.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    safety = _safety_flags()
    return {
        "message": "diagnostic_imaging_studies",
        "mode": MODE,
        "case": _case_payload(case),
        "items": [_imaging_study_payload(item) for item in studies],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "safety": safety,
        **safety,
    }


@router.get("/dry-run/fixtures", response_model=dict)
def list_diagnostic_dry_run_fixtures(
    user=Depends(get_current_user),
):
    fixture_ids = []
    if FIXTURE_DIR.exists():
        fixture_ids = sorted(path.stem for path in FIXTURE_DIR.glob("diagnostic_data_*.json"))

    safety = _safety_flags(dry_run=True)
    return {
        "message": "diagnostic_data_dry_run_fixtures",
        "mode": MODE,
        "fixture_ids": fixture_ids,
        "total": len(fixture_ids),
        "safety": safety,
        **safety,
    }


@router.get("/dry-run/fixtures/{fixture_id}", response_model=dict)
def get_diagnostic_dry_run_fixture(
    fixture_id: str,
    user=Depends(get_current_user),
):
    if "/" in fixture_id or "\\" in fixture_id or ".." in fixture_id:
        raise HTTPException(status_code=400, detail="invalid fixture_id")

    fixture_path = FIXTURE_DIR / f"{fixture_id}.json"
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail="diagnostic dry-run fixture not found")

    try:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to load diagnostic fixture: {exc}") from exc

    safety = _safety_flags(dry_run=True)
    return {
        "message": "diagnostic_data_dry_run_fixture",
        "mode": MODE,
        "fixture_id": fixture_id,
        "fixture": fixture,
        "safety": safety,
        **safety,
    }
