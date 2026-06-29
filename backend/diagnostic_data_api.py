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


try:
    from backend.lab_result_parser import parse_lab_result_fixture, lab_parser_safety_flags
except ModuleNotFoundError:
    from lab_result_parser import parse_lab_result_fixture, lab_parser_safety_flags

try:
    from backend.imaging_metadata_parser import (
        IMAGING_METADATA_DRY_RUN_MODE,
        parse_imaging_metadata_fixture,
    )
except ModuleNotFoundError:
    from imaging_metadata_parser import (
        IMAGING_METADATA_DRY_RUN_MODE,
        parse_imaging_metadata_fixture,
    )

try:
    from backend.ai_lab_abnormal_summary import (
        AI_LAB_ABNORMAL_SUMMARY_MODE,
        ai_lab_abnormal_summary_safety_flags,
        build_ai_lab_abnormal_summary,
    )
except ModuleNotFoundError:
    from ai_lab_abnormal_summary import (
        AI_LAB_ABNORMAL_SUMMARY_MODE,
        ai_lab_abnormal_summary_safety_flags,
        build_ai_lab_abnormal_summary,
    )

try:
    from backend.ai_imaging_report_summary import (
        AI_IMAGING_REPORT_SUMMARY_MODE,
        ai_imaging_report_summary_safety_flags,
        build_ai_imaging_report_summary,
    )
except ModuleNotFoundError:
    from ai_imaging_report_summary import (
        AI_IMAGING_REPORT_SUMMARY_MODE,
        ai_imaging_report_summary_safety_flags,
        build_ai_imaging_report_summary,
    )



try:
    from backend.drug_dose_safety_framework import (
        DRUG_DOSE_SAFETY_FRAMEWORK_MODE,
        build_drug_dose_safety_framework,
        drug_dose_safety_framework_flags,
    )
except ModuleNotFoundError:
    from drug_dose_safety_framework import (
        DRUG_DOSE_SAFETY_FRAMEWORK_MODE,
        build_drug_dose_safety_framework,
        drug_dose_safety_framework_flags,
    )


try:
    from backend.drug_dose_knowledge_base import (
        DRUG_DOSE_KNOWLEDGE_BASE_MODE,
        drug_dose_knowledge_base_flags,
        get_drug_dose_monograph,
        list_drug_dose_monographs,
        review_drug_dose_knowledge_base,
    )
except ModuleNotFoundError:
    from drug_dose_knowledge_base import (
        DRUG_DOSE_KNOWLEDGE_BASE_MODE,
        drug_dose_knowledge_base_flags,
        get_drug_dose_monograph,
        list_drug_dose_monographs,
        review_drug_dose_knowledge_base,
    )

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


def _safe_fixture_path(prefix: str, fixture_id: str) -> Path:
    if "/" in fixture_id or "\\" in fixture_id or ".." in fixture_id:
        raise HTTPException(status_code=400, detail="invalid fixture_id")
    if not fixture_id.startswith(prefix):
        raise HTTPException(status_code=400, detail=f"fixture_id must start with {prefix}")
    return FIXTURE_DIR / f"{fixture_id}.json"


@router.get("/dry-run/lab-results/fixtures", response_model=dict)
def list_lab_result_dry_run_fixtures(
    user=Depends(get_current_user),
):
    fixture_ids = []
    if FIXTURE_DIR.exists():
        fixture_ids = sorted(path.stem for path in FIXTURE_DIR.glob("lab_result_*.json"))

    safety = _safety_flags(dry_run=True)
    parser_safety = lab_parser_safety_flags()
    return {
        "message": "lab_result_dry_run_fixtures",
        "mode": "lab_result_dry_run_fixture_parser_v1",
        "fixture_ids": fixture_ids,
        "total": len(fixture_ids),
        "safety": {**safety, **parser_safety},
        **safety,
        **parser_safety,
    }


@router.get("/dry-run/lab-results/fixtures/{fixture_id}", response_model=dict)
def get_lab_result_dry_run_fixture(
    fixture_id: str,
    user=Depends(get_current_user),
):
    fixture_path = _safe_fixture_path("lab_result_", fixture_id)
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail="lab result dry-run fixture not found")

    try:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to load lab result fixture: {exc}") from exc

    safety = _safety_flags(dry_run=True)
    parser_safety = lab_parser_safety_flags()
    return {
        "message": "lab_result_dry_run_fixture",
        "mode": "lab_result_dry_run_fixture_parser_v1",
        "fixture_id": fixture_id,
        "fixture": fixture,
        "safety": {**safety, **parser_safety},
        **safety,
        **parser_safety,
    }


@router.post("/dry-run/lab-results/parse", response_model=dict)
def parse_lab_result_dry_run(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be a JSON object")

    case_payload = None
    case_id = payload.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        case_payload = _case_payload(case)
        case_id = case.id
    else:
        case_id = None

    fixture_id = payload.get("fixture_id")
    fixture = payload.get("fixture")
    if fixture_id:
        fixture_path = _safe_fixture_path("lab_result_", str(fixture_id))
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail="lab result dry-run fixture not found")
        try:
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"failed to load lab result fixture: {exc}") from exc

    if not isinstance(fixture, dict):
        raise HTTPException(status_code=422, detail="fixture_id or fixture object is required")

    try:
        parsed = parse_lab_result_fixture(fixture, case_id=case_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    parser_safety = lab_parser_safety_flags()
    return {
        "message": "lab_result_dry_run_parsed",
        "mode": "lab_result_dry_run_fixture_parser_v1",
        "fixture_id": parsed.get("fixture_id") or fixture_id,
        "case": case_payload,
        "report_preview": parsed["report_preview"],
        "observations_preview": parsed["observations_preview"],
        "abnormal_observations": parsed["abnormal_observations"],
        "quality_gate": parsed["quality_gate"],
        "safety": {**safety, **parser_safety},
        **safety,
        **parser_safety,
    }

@router.post("/dry-run/lab-results/abnormal-summary", response_model=dict)
def summarize_lab_result_abnormalities_dry_run(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be a JSON object")

    case_payload = None
    case_id = payload.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        case_payload = _case_payload(case)
        case_id = case.id
    else:
        case_id = None

    fixture_id = payload.get("fixture_id")
    fixture = payload.get("fixture")
    parsed_lab_result = payload.get("parsed_lab_result") or payload.get("parsed")

    if fixture_id:
        fixture_path = _safe_fixture_path("lab_result_", str(fixture_id))
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail="lab result dry-run fixture not found")
        try:
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"failed to load lab result fixture: {exc}") from exc

    if parsed_lab_result is None:
        if not isinstance(fixture, dict):
            raise HTTPException(status_code=422, detail="fixture_id, fixture object, or parsed_lab_result is required")
        try:
            parsed_lab_result = parse_lab_result_fixture(fixture, case_id=case_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    elif not isinstance(parsed_lab_result, dict):
        raise HTTPException(status_code=422, detail="parsed_lab_result must be a JSON object")

    try:
        summary = build_ai_lab_abnormal_summary(
            parsed_lab_result,
            case_id=case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    summary_safety = ai_lab_abnormal_summary_safety_flags()
    combined_safety = {**safety, **summary_safety}

    return {
        "message": "ai_lab_abnormal_summary_dry_run",
        "mode": AI_LAB_ABNORMAL_SUMMARY_MODE,
        "fixture_id": summary.get("fixture_id") or fixture_id,
        "case": case_payload,
        "summary": summary["summary"],
        "abnormal_findings": summary["abnormal_findings"],
        "review_recommendations": summary["review_recommendations"],
        "quality_gate": summary["quality_gate"],
        "safety": combined_safety,
        **combined_safety,
    }


@router.get("/dry-run/imaging-metadata/fixtures", response_model=dict)
def list_imaging_metadata_dry_run_fixtures(
    user=Depends(get_current_user),
):
    fixture_ids = []
    if FIXTURE_DIR.exists():
        fixture_ids = sorted(path.stem for path in FIXTURE_DIR.glob("imaging_metadata_*.json"))

    safety = _safety_flags(dry_run=True)
    return {
        "message": "imaging_metadata_dry_run_fixtures",
        "mode": IMAGING_METADATA_DRY_RUN_MODE,
        "fixture_ids": fixture_ids,
        "total": len(fixture_ids),
        "safety": safety,
        **safety,
    }


@router.get("/dry-run/imaging-metadata/fixtures/{fixture_id}", response_model=dict)
def get_imaging_metadata_dry_run_fixture(
    fixture_id: str,
    user=Depends(get_current_user),
):
    if "/" in fixture_id or "\\" in fixture_id or ".." in fixture_id:
        raise HTTPException(status_code=400, detail="invalid fixture_id")

    fixture_path = FIXTURE_DIR / f"{fixture_id}.json"
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail="imaging metadata dry-run fixture not found")

    try:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to load imaging metadata fixture: {exc}") from exc

    safety = _safety_flags(dry_run=True)
    return {
        "message": "imaging_metadata_dry_run_fixture",
        "mode": IMAGING_METADATA_DRY_RUN_MODE,
        "fixture_id": fixture_id,
        "fixture": fixture,
        "safety": safety,
        **safety,
    }


@router.post("/dry-run/imaging-metadata/parse", response_model=dict)
def parse_imaging_metadata_dry_run_fixture(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    fixture_id = str(data.get("fixture_id") or "").strip()
    fixture_payload = data.get("fixture") or data.get("payload")

    if fixture_id:
        if "/" in fixture_id or "\\" in fixture_id or ".." in fixture_id:
            raise HTTPException(status_code=400, detail="invalid fixture_id")
        fixture_path = FIXTURE_DIR / f"{fixture_id}.json"
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail="imaging metadata dry-run fixture not found")
        try:
            fixture_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"failed to load imaging metadata fixture: {exc}") from exc

    if not isinstance(fixture_payload, dict):
        raise HTTPException(status_code=422, detail="fixture_id or fixture payload is required")

    case_payload = None
    case_id = data.get("case_id") or fixture_payload.get("case_id")
    parsed_case_id = None
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        parsed = parse_imaging_metadata_fixture(fixture_payload, case_id=parsed_case_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    return {
        "message": "imaging_metadata_dry_run_parse",
        "mode": IMAGING_METADATA_DRY_RUN_MODE,
        "fixture_id": fixture_id or parsed.get("fixture_id"),
        "case": case_payload,
        **parsed,
        "safety": {**parsed.get("safety", {}), **safety},
        **safety,
        "creates_imaging_study": False,
        "queries_pacs": False,
    }

@router.post("/dry-run/imaging-metadata/report-summary", response_model=dict)
def summarize_imaging_metadata_dry_run_report(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    fixture_id = str(data.get("fixture_id") or "").strip()
    fixture_payload = data.get("fixture") or data.get("payload")

    if fixture_id:
        if "/" in fixture_id or "\\" in fixture_id or ".." in fixture_id:
            raise HTTPException(status_code=400, detail="invalid fixture_id")
        fixture_path = FIXTURE_DIR / f"{fixture_id}.json"
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail="imaging metadata dry-run fixture not found")
        try:
            fixture_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"failed to load imaging metadata fixture: {exc}") from exc

    if not isinstance(fixture_payload, dict):
        raise HTTPException(status_code=422, detail="fixture_id or fixture payload is required")

    case_payload = None
    case_id = data.get("case_id") or fixture_payload.get("case_id")
    parsed_case_id = None
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        parsed = parse_imaging_metadata_fixture(fixture_payload, case_id=parsed_case_id)
        summary = build_ai_imaging_report_summary(
            parsed,
            case_id=parsed_case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    summary_safety = ai_imaging_report_summary_safety_flags()
    return {
        "message": "ai_imaging_report_summary_dry_run",
        "mode": AI_IMAGING_REPORT_SUMMARY_MODE,
        "fixture_id": fixture_id or parsed.get("fixture_id"),
        "case": case_payload,
        "parsed_imaging_metadata": parsed,
        **summary,
        "safety": {**safety, **summary_safety},
        **safety,
        **summary_safety,
    }

try:
    from backend.treatment_recommendation_boundary import (
        TREATMENT_RECOMMENDATION_BOUNDARY_MODE,
        build_treatment_recommendation_boundary,
        treatment_boundary_safety_flags,
    )
except ModuleNotFoundError:
    from treatment_recommendation_boundary import (
        TREATMENT_RECOMMENDATION_BOUNDARY_MODE,
        build_treatment_recommendation_boundary,
        treatment_boundary_safety_flags,
    )


@router.post("/dry-run/treatment-boundary/check", response_model=dict)
def check_treatment_recommendation_boundary(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    case_payload = None
    parsed_case_id = None
    case_id = data.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        boundary = build_treatment_recommendation_boundary(
            data,
            case_id=parsed_case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    boundary_safety = treatment_boundary_safety_flags()
    return {
        "message": "treatment_recommendation_boundary_checked",
        "mode": TREATMENT_RECOMMENDATION_BOUNDARY_MODE,
        "case": case_payload,
        **boundary,
        "safety": {**safety, **boundary_safety},
        **safety,
        **boundary_safety,
    }

@router.post("/dry-run/drug-dose-safety/check", response_model=dict)
def check_drug_dose_safety_framework(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    case_payload = None
    parsed_case_id = None
    case_id = data.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        framework = build_drug_dose_safety_framework(
            data,
            case_id=parsed_case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    framework_safety = drug_dose_safety_framework_flags()
    return {
        "message": "drug_dose_safety_framework_checked",
        "mode": DRUG_DOSE_SAFETY_FRAMEWORK_MODE,
        "case": case_payload,
        **framework,
        "safety": {**safety, **framework_safety},
        **safety,
        **framework_safety,
    }


@router.get("/dry-run/drug-dose-kb/monographs", response_model=dict)
def list_drug_dose_knowledge_base_monographs(
    user=Depends(get_current_user),
):
    safety = _safety_flags(dry_run=True)
    kb_safety = drug_dose_knowledge_base_flags()
    items = list_drug_dose_monographs()
    return {
        "message": "drug_dose_knowledge_base_monographs",
        "mode": DRUG_DOSE_KNOWLEDGE_BASE_MODE,
        "items": items,
        "total": len(items),
        "safety": {**safety, **kb_safety},
        **safety,
        **kb_safety,
    }


@router.get("/dry-run/drug-dose-kb/monographs/{drug_key}", response_model=dict)
def get_drug_dose_knowledge_base_monograph(
    drug_key: str,
    user=Depends(get_current_user),
):
    monograph = get_drug_dose_monograph(drug_key)
    if monograph is None:
        raise HTTPException(status_code=404, detail="drug dose monograph not found")

    safety = _safety_flags(dry_run=True)
    kb_safety = drug_dose_knowledge_base_flags()
    return {
        "message": "drug_dose_knowledge_base_monograph",
        "mode": DRUG_DOSE_KNOWLEDGE_BASE_MODE,
        "drug_key": drug_key,
        "monograph": monograph,
        "safety": {**safety, **kb_safety},
        **safety,
        **kb_safety,
    }


@router.post("/dry-run/drug-dose-kb/review", response_model=dict)
def review_drug_dose_knowledge_base_endpoint(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    case_payload = None
    parsed_case_id = None
    case_id = data.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        review = review_drug_dose_knowledge_base(
            data,
            case_id=parsed_case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    kb_safety = drug_dose_knowledge_base_flags()
    return {
        "message": "drug_dose_knowledge_base_reviewed",
        "mode": DRUG_DOSE_KNOWLEDGE_BASE_MODE,
        "case": case_payload,
        **review,
        "safety": {**safety, **kb_safety},
        **safety,
        **kb_safety,
    }


@router.post("/dry-run/clinician-review/diagnostic-summaries/check", response_model=dict)
def check_clinician_review_workflow_for_diagnostic_summaries(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.clinician_review_workflow import (
            CLINICIAN_REVIEW_WORKFLOW_MODE,
            build_clinician_review_workflow,
            clinician_review_workflow_safety_flags,
        )
    except ModuleNotFoundError:
        from clinician_review_workflow import (
            CLINICIAN_REVIEW_WORKFLOW_MODE,
            build_clinician_review_workflow,
            clinician_review_workflow_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    case_payload = None
    parsed_case_id = None
    case_id = data.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        workflow = build_clinician_review_workflow(
            data,
            case_id=parsed_case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    workflow_safety = clinician_review_workflow_safety_flags()
    return {
        "message": "clinician_review_workflow_checked",
        "mode": CLINICIAN_REVIEW_WORKFLOW_MODE,
        "case": case_payload,
        **workflow,
        "safety": {**safety, **workflow_safety},
        **safety,
        **workflow_safety,
    }

# --- Diagnostic Assistance Problem List V1 endpoint: start ---
@router.post("/dry-run/problem-list/build", response_model=dict)
def build_diagnostic_assistance_problem_list_dry_run(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.diagnostic_problem_list import (
            DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_MODE,
            build_diagnostic_assistance_problem_list,
            diagnostic_problem_list_safety_flags,
        )
    except ModuleNotFoundError:
        from diagnostic_problem_list import (
            DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_MODE,
            build_diagnostic_assistance_problem_list,
            diagnostic_problem_list_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    case_payload = None
    parsed_case_id = None
    case_id = data.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        problem_list = build_diagnostic_assistance_problem_list(
            data,
            case_id=parsed_case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    problem_safety = diagnostic_problem_list_safety_flags()
    return {
        "message": "diagnostic_assistance_problem_list_built",
        "mode": DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_MODE,
        "case": case_payload,
        **problem_list,
        "safety": {**safety, **problem_safety},
        **safety,
        **problem_safety,
    }
# --- Diagnostic Assistance Problem List V1 endpoint: end ---

# --- Differential Diagnosis Candidates V1 endpoint: start ---
@router.post("/dry-run/differential-diagnosis/candidates/build", response_model=dict)
def build_differential_diagnosis_candidates_dry_run(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.differential_diagnosis_candidates import (
            DIFFERENTIAL_DIAGNOSIS_CANDIDATES_MODE,
            build_differential_diagnosis_candidates,
            differential_diagnosis_candidates_safety_flags,
        )
    except ModuleNotFoundError:
        from differential_diagnosis_candidates import (
            DIFFERENTIAL_DIAGNOSIS_CANDIDATES_MODE,
            build_differential_diagnosis_candidates,
            differential_diagnosis_candidates_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    case_payload = None
    parsed_case_id = None
    case_id = data.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        candidates = build_differential_diagnosis_candidates(
            data,
            case_id=parsed_case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    candidate_safety = differential_diagnosis_candidates_safety_flags()
    return {
        "message": "differential_diagnosis_candidates_built",
        "mode": DIFFERENTIAL_DIAGNOSIS_CANDIDATES_MODE,
        "case": case_payload,
        **candidates,
        "safety": {**safety, **candidate_safety},
        **safety,
        **candidate_safety,
    }
# --- Differential Diagnosis Candidates V1 endpoint: end ---

# --- Diagnostic Reasoning Evidence Trace V1 endpoint: start ---
@router.post("/dry-run/diagnostic-reasoning/evidence-trace/build", response_model=dict)
def build_diagnostic_reasoning_evidence_trace_dry_run(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.diagnostic_reasoning_evidence_trace import (
            DIAGNOSTIC_REASONING_EVIDENCE_TRACE_MODE,
            build_diagnostic_reasoning_evidence_trace,
            diagnostic_reasoning_evidence_trace_safety_flags,
        )
    except ModuleNotFoundError:
        from diagnostic_reasoning_evidence_trace import (
            DIAGNOSTIC_REASONING_EVIDENCE_TRACE_MODE,
            build_diagnostic_reasoning_evidence_trace,
            diagnostic_reasoning_evidence_trace_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    case_payload = None
    parsed_case_id = None
    case_id = data.get("case_id")
    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        parsed_case_id = int(case.id)
        case_payload = _case_payload(case)

    try:
        trace = build_diagnostic_reasoning_evidence_trace(
            data,
            case_id=parsed_case_id,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=True)
    trace_safety = diagnostic_reasoning_evidence_trace_safety_flags()
    return {
        "message": "diagnostic_reasoning_evidence_trace_built",
        "mode": DIAGNOSTIC_REASONING_EVIDENCE_TRACE_MODE,
        "case": case_payload,
        **trace,
        "safety": {**safety, **trace_safety},
        **safety,
        **trace_safety,
    }
# --- Diagnostic Reasoning Evidence Trace V1 endpoint: end ---


# --- Clinician Review Persistence V1 endpoint: start ---
@router.post("/clinician-review/persistence/apply", response_model=dict)
def apply_clinician_review_persistence(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.clinician_review_persistence import (
            CLINICIAN_REVIEW_PERSISTENCE_MODE,
            build_clinician_review_persistence_plan,
            clinician_review_persistence_safety_flags,
        )
    except ModuleNotFoundError:
        from clinician_review_persistence import (
            CLINICIAN_REVIEW_PERSISTENCE_MODE,
            build_clinician_review_persistence_plan,
            clinician_review_persistence_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    case_id = data.get("case_id")
    if case_id in (None, ""):
        raise HTTPException(status_code=422, detail="case_id is required")

    case = _owned_case_or_404(db, int(case_id), user)
    case_payload = _case_payload(case)

    try:
        plan = build_clinician_review_persistence_plan(
            data,
            case_id=int(case.id),
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    dry_run = bool(plan.get("dry_run"))
    reviewed_by = str(plan.get("persistence", {}).get("reviewed_by") or "").strip()
    review_items = list(plan.get("review_items") or [])

    def snapshot_report(target: DiagnosticReport) -> Dict[str, Any]:
        return {
            "target_type": "diagnostic_report",
            "target_id": int(target.id),
            "case_id": int(target.case_id),
            "status": target.status,
            "reviewed_by": target.reviewed_by,
            "reviewed_at": _iso(target.reviewed_at),
            "ai_summary_status": target.ai_summary_status,
        }

    targets = []
    for item in review_items:
        if item.get("target_type") != "diagnostic_report":
            raise HTTPException(
                status_code=422,
                detail="Clinician Review Persistence V1 only supports diagnostic_report targets",
            )
        target_id = int(item.get("target_id"))
        target = db.get(DiagnosticReport, target_id)
        if target is None or int(target.case_id) != int(case.id):
            raise HTTPException(status_code=404, detail="review target not found")
        targets.append((item, target, snapshot_report(target)))

    now = datetime.utcnow()
    persisted_count = 0
    item_results: List[Dict[str, Any]] = []

    if not dry_run:
        for item, target, _before in targets:
            target.status = item["review_status"]
            target.reviewed_by = reviewed_by
            target.reviewed_at = now
            persisted_count += 1

        if persisted_count:
            db.commit()
            for _, target, _ in targets:
                db.refresh(target)

    for item, target, before in targets:
        after = snapshot_report(target)
        if dry_run:
            after = dict(before)
            after.update({
                "status": item["review_status"],
                "reviewed_by": reviewed_by,
                "reviewed_at": "DRY_RUN_PREVIEW",
            })

        item_results.append({
            "target_type": "diagnostic_report",
            "target_id": item["target_id"],
            "review_status": item["review_status"],
            "note_present": bool(item.get("note")),
            "source_preview_id": item.get("source_preview_id"),
            "persisted": bool(not dry_run),
            "before": before,
            "after": after,
            "allowed_persisted_fields": item.get("allowed_persisted_fields") or [],
        })

    api_safety = clinician_review_persistence_safety_flags(
        dry_run=dry_run,
        writes_database=(not dry_run and persisted_count > 0),
        item_count=persisted_count if not dry_run else len(review_items),
    )
    wrote_report_status = bool(not dry_run and persisted_count > 0)
    api_safety.update({
        "updates_diagnostic_report": wrote_report_status,
        "writes_diagnostic_report": wrote_report_status,
        "writes_diagnostic_report_status_only": wrote_report_status,
        "updates_observation": False,
        "writes_observation_review_status_only": False,
        "updates_imaging_study": False,
        "writes_imaging_study_review_status_only": False,
    })

    persistence_result = {
        "decision": "review_status_persisted" if persisted_count else plan.get("persistence", {}).get("decision"),
        "dry_run": dry_run,
        "reviewed_by": reviewed_by,
        "reviewed_at": _iso(now) if (not dry_run and persisted_count) else None,
        "requested_item_count": len(review_items),
        "persisted_item_count": persisted_count,
        "items": item_results,
        "review_status_persistence_only": True,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
    }

    quality_gate = dict(plan.get("quality_gate") or {})
    quality_gate.update({
        "status": "PASS",
        "persisted_item_count": persisted_count,
        "writes_database": bool(api_safety.get("writes_database")),
        "writes_audit_log": False,
        "persists_reasoning_trace": False,
        "updates_observation": False,
        "updates_imaging_study": False,
    })

    return {
        "message": "clinician_review_persistence_applied",
        "mode": CLINICIAN_REVIEW_PERSISTENCE_MODE,
        "case": case_payload,
        "persistence": plan.get("persistence"),
        "persistence_result": persistence_result,
        "review_items": review_items,
        "blocked_actions": plan.get("blocked_actions") or [],
        "quality_gate": quality_gate,
        "safety": api_safety,
        **api_safety,
    }
# --- Clinician Review Persistence V1 endpoint: end ---


# --- Clinical QA Dashboard V2 endpoint: start ---
@router.get("/clinical-qa-dashboard/v2/summary", response_model=dict)
def get_clinical_qa_dashboard_v2_summary(
    case_id: Optional[int] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.clinical_qa_dashboard import (
            CLINICAL_QA_DASHBOARD_MODE,
            build_clinical_qa_dashboard,
            clinical_qa_dashboard_safety_flags,
        )
    except ModuleNotFoundError:
        from clinical_qa_dashboard import (
            CLINICAL_QA_DASHBOARD_MODE,
            build_clinical_qa_dashboard,
            clinical_qa_dashboard_safety_flags,
        )

    try:
        from backend.models import AuditLog
    except ModuleNotFoundError:
        from models import AuditLog

    owner_id = _user_id(user)
    case_context = None

    if case_id not in (None, ""):
        case = _owned_case_or_404(db, int(case_id), user)
        case_rows = [case]
        case_context = _case_payload(case)
    else:
        case_rows = (
            db.query(Case)
            .filter(Case.owner_id == owner_id, Case.deleted_at.is_(None))
            .order_by(Case.updated_at.desc(), Case.id.desc())
            .limit(int(limit))
            .all()
        )

    case_ids = [int(item.id) for item in case_rows]
    reports = []
    observations = []
    imaging_studies = []
    audit_logs = []

    if case_ids:
        reports = (
            db.query(DiagnosticReport)
            .filter(DiagnosticReport.case_id.in_(case_ids))
            .order_by(DiagnosticReport.updated_at.desc(), DiagnosticReport.id.desc())
            .limit(1000)
            .all()
        )
        observations = (
            db.query(Observation)
            .filter(Observation.case_id.in_(case_ids))
            .order_by(Observation.updated_at.desc(), Observation.id.desc())
            .limit(2000)
            .all()
        )
        imaging_studies = (
            db.query(ImagingStudy)
            .filter(ImagingStudy.case_id.in_(case_ids))
            .order_by(ImagingStudy.updated_at.desc(), ImagingStudy.id.desc())
            .limit(1000)
            .all()
        )
        audit_logs = (
            db.query(AuditLog)
            .filter(AuditLog.case_id.in_(case_ids))
            .order_by(AuditLog.created_at.desc())
            .limit(1000)
            .all()
        )

    dashboard_payload = {
        "cases": [_case_payload(item) for item in case_rows],
        "diagnostic_reports": [
            {
                "report_id": int(item.id),
                "case_id": int(item.case_id),
                "report_type": item.report_type,
                "source_type": item.source_type,
                "status": item.status,
                "title": item.title,
                "ai_summary_status": item.ai_summary_status,
                "has_ai_summary": bool(item.ai_summary),
                "reviewed_by": item.reviewed_by,
                "reviewed_at": _iso(item.reviewed_at),
                "updated_at": _iso(item.updated_at),
            }
            for item in reports
        ],
        "observations": [
            {
                "observation_id": int(item.id),
                "case_id": int(item.case_id),
                "diagnostic_report_id": int(item.diagnostic_report_id),
                "code": item.code,
                "display_name": item.display_name,
                "abnormal_flag": item.abnormal_flag,
                "review_status": item.review_status,
                "updated_at": _iso(item.updated_at),
            }
            for item in observations
        ],
        "imaging_studies": [
            {
                "imaging_study_id": int(item.id),
                "case_id": int(item.case_id),
                "modality": item.modality,
                "body_part": item.body_part,
                "abnormal_flag": item.abnormal_flag,
                "review_status": item.review_status,
                "reviewed_by": item.reviewed_by,
                "reviewed_at": _iso(item.reviewed_at),
                "updated_at": _iso(item.updated_at),
            }
            for item in imaging_studies
        ],
        "audit_logs": [
            {
                "log_id": item.log_id,
                "case_id": item.case_id,
                "event_type": item.event_type,
                "source": item.source,
                "created_at": _iso(item.created_at),
            }
            for item in audit_logs
        ],
    }

    try:
        dashboard = build_clinical_qa_dashboard(dashboard_payload, case_context=case_context)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safety = _safety_flags(dry_run=False)
    qa_safety = clinical_qa_dashboard_safety_flags()
    combined_safety = {**safety, **qa_safety}
    return {
        "message": "clinical_qa_dashboard_v2_summary",
        "mode": CLINICAL_QA_DASHBOARD_MODE,
        "case": case_context,
        "scope": {
            "case_id": int(case_id) if case_id not in (None, "") else None,
            "case_count": len(case_rows),
            "limit": int(limit),
            "owner_scoped": True,
        },
        **dashboard,
        "safety": combined_safety,
        **combined_safety,
    }
# --- Clinical QA Dashboard V2 endpoint: end ---

# --- DiagnosticReport AI Summary Persistence V1 endpoint: start ---
@router.post("/diagnostic-reports/{report_id}/ai-summary/persistence/apply", response_model=dict)
def apply_diagnosticreport_ai_summary_persistence_endpoint(
    report_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.diagnostic_report_ai_summary_persistence import (
            DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_MODE,
            apply_diagnosticreport_ai_summary_persistence,
            diagnosticreport_ai_summary_persistence_safety_flags,
        )
    except ModuleNotFoundError:
        from diagnostic_report_ai_summary_persistence import (
            DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_MODE,
            apply_diagnosticreport_ai_summary_persistence,
            diagnosticreport_ai_summary_persistence_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    report = db.get(DiagnosticReport, int(report_id))
    if report is None:
        raise HTTPException(status_code=404, detail="Diagnostic report not found")

    case = _owned_case_or_404(db, int(report.case_id), user)
    raw_case_id = data.get("case_id")
    if raw_case_id not in (None, "") and int(raw_case_id) != int(case.id):
        raise HTTPException(status_code=422, detail="case_id does not match diagnostic report")

    case_payload = _case_payload(case)
    report_context = {
        "report_id": int(report.id),
        "case_id": int(report.case_id),
        "report_type": getattr(report, "report_type", None),
        "source_type": getattr(report, "source_type", None),
        "status": getattr(report, "status", None),
        "ai_summary_status": getattr(report, "ai_summary_status", None),
    }

    try:
        persistence = apply_diagnosticreport_ai_summary_persistence(
            db=db,
            report=report,
            payload=data,
            report_context=report_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    api_safety = diagnosticreport_ai_summary_persistence_safety_flags(
        dry_run=bool(persistence.get("dry_run")),
        writes_database=bool(persistence.get("writes_database")),
    )
    api_safety.update(persistence.get("safety") or {})

    return {
        "message": "diagnosticreport_ai_summary_persistence_applied",
        "mode": DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_MODE,
        "case": case_payload,
        "report": report_context,
        **persistence,
        "safety": api_safety,
        **api_safety,
    }
# --- DiagnosticReport AI Summary Persistence V1 endpoint: end ---

# --- Observation Abnormal Flag Review V1 endpoint: start ---
@router.post("/observations/{observation_id}/abnormal-flag/review/apply", response_model=dict)
def apply_observation_abnormal_flag_review_endpoint(
    observation_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.observation_abnormal_flag_review import (
            OBSERVATION_ABNORMAL_FLAG_REVIEW_MODE,
            apply_observation_abnormal_flag_review,
            observation_abnormal_flag_review_safety_flags,
        )
    except ModuleNotFoundError:
        from observation_abnormal_flag_review import (
            OBSERVATION_ABNORMAL_FLAG_REVIEW_MODE,
            apply_observation_abnormal_flag_review,
            observation_abnormal_flag_review_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    observation = db.get(Observation, int(observation_id))
    if observation is None:
        raise HTTPException(status_code=404, detail="Observation not found")

    case = _owned_case_or_404(db, int(observation.case_id), user)
    raw_case_id = data.get("case_id")
    if raw_case_id not in (None, "") and int(raw_case_id) != int(case.id):
        raise HTTPException(status_code=422, detail="case_id does not match observation")

    observation_context = {
        "observation_id": int(observation.id),
        "case_id": int(observation.case_id),
        "diagnostic_report_id": getattr(observation, "diagnostic_report_id", None),
        "code": getattr(observation, "code", None),
        "display_name": getattr(observation, "display_name", None),
        "abnormal_flag": getattr(observation, "abnormal_flag", None),
        "review_status": getattr(observation, "review_status", None),
    }

    try:
        review = apply_observation_abnormal_flag_review(
            db=db,
            observation=observation,
            payload=data,
            observation_context=observation_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    api_safety = observation_abnormal_flag_review_safety_flags(
        dry_run=bool(review.get("dry_run")),
        writes_database=bool(review.get("writes_database")),
    )
    api_safety.update(review.get("safety") or {})

    return {
        "message": "observation_abnormal_flag_review_applied",
        "mode": OBSERVATION_ABNORMAL_FLAG_REVIEW_MODE,
        "case": _case_payload(case),
        "observation": observation_context,
        **review,
        "safety": api_safety,
        **api_safety,
    }
# --- Observation Abnormal Flag Review V1 endpoint: end ---

# --- ImagingStudy Review Workflow V1 endpoint: start ---
@router.post("/imaging-studies/{imaging_study_id}/review-workflow/apply", response_model=dict)
def apply_imagingstudy_review_workflow_endpoint(
    imaging_study_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.imagingstudy_review_workflow import (
            IMAGINGSTUDY_REVIEW_WORKFLOW_MODE,
            apply_imagingstudy_review_workflow,
            imagingstudy_review_workflow_safety_flags,
        )
    except ModuleNotFoundError:
        from imagingstudy_review_workflow import (
            IMAGINGSTUDY_REVIEW_WORKFLOW_MODE,
            apply_imagingstudy_review_workflow,
            imagingstudy_review_workflow_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    imaging_study = db.get(ImagingStudy, int(imaging_study_id))
    if imaging_study is None:
        raise HTTPException(status_code=404, detail="Imaging study not found")

    case = _owned_case_or_404(db, int(imaging_study.case_id), user)
    raw_case_id = data.get("case_id")
    if raw_case_id not in (None, "") and int(raw_case_id) != int(case.id):
        raise HTTPException(status_code=422, detail="case_id does not match imaging study")

    imaging_context = {
        "imaging_study_id": int(imaging_study.id),
        "case_id": int(imaging_study.case_id),
        "modality": getattr(imaging_study, "modality", None),
        "body_part": getattr(imaging_study, "body_part", None),
        "study_uid": getattr(imaging_study, "study_uid", None),
        "accession_number": getattr(imaging_study, "accession_number", None),
        "abnormal_flag": getattr(imaging_study, "abnormal_flag", None),
        "review_status": getattr(imaging_study, "review_status", None),
        "reviewed_by": getattr(imaging_study, "reviewed_by", None),
        "ai_summary_status": getattr(imaging_study, "ai_summary_status", None),
    }

    try:
        review = apply_imagingstudy_review_workflow(
            db=db,
            imaging_study=imaging_study,
            payload=data,
            imaging_context=imaging_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    api_safety = imagingstudy_review_workflow_safety_flags(
        dry_run=bool(review.get("dry_run")),
        writes_database=bool(review.get("writes_database")),
    )
    api_safety.update(review.get("safety") or {})

    return {
        "message": "imagingstudy_review_workflow_applied",
        "mode": IMAGINGSTUDY_REVIEW_WORKFLOW_MODE,
        "case": _case_payload(case),
        "imaging_study": imaging_context,
        **review,
        "safety": api_safety,
        **api_safety,
    }
# --- ImagingStudy Review Workflow V1 endpoint: end ---


# --- Confirmed Diagnosis Treatment Framework Draft V1 endpoint: start ---
@router.post("/dry-run/confirmed-diagnosis/treatment-framework/build", response_model=dict)
def build_confirmed_diagnosis_treatment_framework_dry_run(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        from backend.confirmed_diagnosis_treatment_framework import (
            CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_MODE,
            build_confirmed_diagnosis_treatment_framework,
            confirmed_diagnosis_treatment_framework_safety_flags,
        )
    except ModuleNotFoundError:
        from confirmed_diagnosis_treatment_framework import (
            CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_MODE,
            build_confirmed_diagnosis_treatment_framework,
            confirmed_diagnosis_treatment_framework_safety_flags,
        )

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="request body must be an object")

    raw_case_id = data.get("case_id")
    if raw_case_id in (None, ""):
        raise HTTPException(status_code=422, detail="case_id is required")
    try:
        case = _owned_case_or_404(db, int(raw_case_id), user)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="case_id must be an integer") from exc

    case_payload = _case_payload(case)
    payload = dict(data)
    payload["case_id"] = int(case.id)

    try:
        framework = build_confirmed_diagnosis_treatment_framework(
            payload,
            case_context=case_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    api_safety = _safety_flags(dry_run=True)
    framework_safety = confirmed_diagnosis_treatment_framework_safety_flags()
    combined_safety = {**api_safety, **framework_safety}
    return {
        "message": "confirmed_diagnosis_treatment_framework_built",
        "mode": CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_MODE,
        "case": case_payload,
        **framework,
        "safety": combined_safety,
        **combined_safety,
    }
# --- Confirmed Diagnosis Treatment Framework Draft V1 endpoint: end ---
