# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter
from datetime import datetime
from math import ceil
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

try:
    from backend.auth_jwt import get_current_user
except ModuleNotFoundError:
    from auth_jwt import get_current_user


router = APIRouter(prefix="/api/migrations", tags=["migrations"])

MAX_MOCK_RECORDS = 1000
MAX_DRY_RUN_RECORDS = 5000
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_SAMPLE_LIMIT = 5

ALLOWED_SPECIES = {
    "dog", "cat", "rabbit", "bird", "avian", "reptile", "turtle", "snake",
    "lizard", "amphibian", "ferret", "rodent", "guinea_pig", "hamster",
    "chinchilla", "rat", "mouse", "hedgehog", "sugar_glider", "fish", "other",
}

CASE_CREATE_FIELDS = [
    "patient_name",
    "species",
    "sex",
    "age_info",
    "breed",
    "weight",
    "coat_color",
    "owner_name",
    "owner_phone",
    "chief_complaint",
    "history",
    "exam_findings",
]


class LegacyCaseImportMockIn(BaseModel):
    # API mock for legacy case import JSONL records.
    batch_id: Optional[str] = None
    records: List[Dict[str, Any]] = Field(default_factory=list)
    validate_only: bool = True


class LegacyCaseImportDryRunOptions(BaseModel):
    chunk_size: int = DEFAULT_CHUNK_SIZE
    sample_limit: int = DEFAULT_SAMPLE_LIMIT
    include_items: bool = True


class LegacyCaseImportDryRunIn(BaseModel):
    # V2 dry-run report. This still never writes to DB or calls /api/cases.
    batch_id: Optional[str] = None
    records: List[Dict[str, Any]] = Field(default_factory=list)
    validate_only: bool = True
    options: LegacyCaseImportDryRunOptions = Field(default_factory=LegacyCaseImportDryRunOptions)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _error(field: str, code: str, reason: str, suggestion: str = "") -> Dict[str, str]:
    return {
        "field": field,
        "error_code": code,
        "error_reason": reason,
        "suggestion": suggestion,
    }


def _warning(field: str, code: str, reason: str, suggestion: str = "") -> Dict[str, str]:
    return {
        "field": field,
        "warning_code": code,
        "warning_reason": reason,
        "suggestion": suggestion,
    }


def _case_create_errors(case_create: Dict[str, Any]) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []

    for field in ("patient_name", "species", "chief_complaint"):
        if not _text(case_create.get(field)):
            errors.append(_error(
                f"case_create.{field}",
                "required",
                f"case_create.{field} is required.",
                f"Populate {field} before real import.",
            ))

    species = _text(case_create.get("species")).lower()
    if species and species not in ALLOWED_SPECIES:
        errors.append(_error(
            "case_create.species",
            "invalid_species",
            f"Unsupported species: {species}",
            "Map species to Pet-Med-AI internal values before import.",
        ))

    history = _text(case_create.get("history"))
    if history and len(history) > 20000:
        errors.append(_error(
            "case_create.history",
            "too_long",
            "history is too long for dry-run import preview.",
            "Split or shorten legacy history before import.",
        ))

    chief = _text(case_create.get("chief_complaint"))
    if chief and len(chief) > 5000:
        errors.append(_error(
            "case_create.chief_complaint",
            "too_long",
            "chief_complaint is unexpectedly long.",
            "Move long legacy notes to history and keep chief complaint concise.",
        ))

    return errors


def _case_create_warnings(case_create: Dict[str, Any]) -> List[Dict[str, str]]:
    warnings: List[Dict[str, str]] = []

    for field in ("history", "exam_findings"):
        if not _text(case_create.get(field)):
            warnings.append(_warning(
                f"case_create.{field}",
                "optional_missing",
                f"case_create.{field} is empty.",
                "This is allowed in dry-run, but review whether legacy data should populate it.",
            ))

    for field in ("weight", "owner_name", "owner_phone", "breed"):
        if not _text(case_create.get(field)):
            warnings.append(_warning(
                f"case_create.{field}",
                "optional_missing",
                f"case_create.{field} is empty.",
                "Optional field is blank; acceptable if legacy data does not contain it.",
            ))

    return warnings


def _record_errors(record: Dict[str, Any], seen_keys: Set[str]) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []

    if record.get("operation") != "case_create":
        errors.append(_error(
            "operation",
            "unsupported_operation",
            "Only operation=case_create is supported by dry-run V2.",
            "Use operation=case_create for legacy case payloads.",
        ))

    if record.get("dry_run") is not True:
        errors.append(_error(
            "dry_run",
            "not_dry_run",
            "Dry-run import requires dry_run=true records.",
            "Regenerate JSONL from scripts/legacy_cases_to_case_payloads.py.",
        ))

    idempotency_key = _text(record.get("idempotency_key"))
    if not idempotency_key:
        errors.append(_error(
            "idempotency_key",
            "required",
            "idempotency_key is required.",
            "Generate idempotency_key from stable legacy case identifiers.",
        ))
    elif idempotency_key in seen_keys:
        errors.append(_error(
            "idempotency_key",
            "duplicate_in_batch",
            "idempotency_key appears more than once in this dry-run batch.",
            "Deduplicate the JSONL batch before real import.",
        ))
    else:
        seen_keys.add(idempotency_key)

    case_create = record.get("case_create")
    if not isinstance(case_create, dict):
        errors.append(_error(
            "case_create",
            "required",
            "case_create object is required.",
            "Generate payload using scripts/legacy_cases_to_case_payloads.py.",
        ))
    else:
        errors.extend(_case_create_errors(case_create))

    return errors


def _record_warnings(record: Dict[str, Any]) -> List[Dict[str, str]]:
    case_create = record.get("case_create")
    if not isinstance(case_create, dict):
        return []
    return _case_create_warnings(case_create)


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


def _field_coverage(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    coverage: Dict[str, Dict[str, Any]] = {}
    total = len(records)
    for field in CASE_CREATE_FIELDS:
        non_empty = 0
        for record in records:
            case_create = record.get("case_create") or {}
            if isinstance(case_create, dict) and _text(case_create.get(field)):
                non_empty += 1
        coverage[field] = {
            "non_empty": non_empty,
            "total": total,
            "ratio": round(non_empty / total, 4) if total else 0.0,
        }
    return coverage


def _counter_to_sorted_dict(counter: Counter) -> Dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0]))


def _safe_positive_int(value: Any, default: int, minimum: int = 1, maximum: int = 10000) -> int:
    try:
        number = int(value)
    except Exception:
        return default
    return max(minimum, min(maximum, number))


def build_dry_run_report(
    *,
    records: List[Dict[str, Any]],
    batch_id: Optional[str],
    mode: str,
    message: str,
    max_records: int,
    options: Optional[LegacyCaseImportDryRunOptions] = None,
    include_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not records:
        raise HTTPException(status_code=400, detail="records is required")
    if len(records) > max_records:
        raise HTTPException(status_code=400, detail=f"records cannot exceed {max_records} per dry-run batch")

    options = options or LegacyCaseImportDryRunOptions()
    chunk_size = _safe_positive_int(options.chunk_size, DEFAULT_CHUNK_SIZE, 1, max_records)
    sample_limit = _safe_positive_int(options.sample_limit, DEFAULT_SAMPLE_LIMIT, 0, 100)
    include_items = bool(options.include_items)

    seen_keys: Set[str] = set()
    items: List[Dict[str, Any]] = []
    all_errors: List[Dict[str, Any]] = []
    all_warnings: List[Dict[str, Any]] = []
    accepted_records: List[Dict[str, Any]] = []

    species_counts: Counter = Counter()
    operation_counts: Counter = Counter()
    legacy_status_counts: Counter = Counter()
    rejected_by_code: Counter = Counter()
    warnings_by_code: Counter = Counter()

    for index, record in enumerate(records, start=1):
        legacy = record.get("legacy") if isinstance(record.get("legacy"), dict) else {}
        legacy_case_id = _text(record.get("legacy_case_id") or legacy.get("case_id"))
        idempotency_key = _text(record.get("idempotency_key"))
        operation_counts[_text(record.get("operation")) or "unknown"] += 1
        if legacy.get("status") is not None:
            legacy_status_counts[_text(legacy.get("status")) or "blank"] += 1

        record_errors = _record_errors(record, seen_keys)
        record_warnings = _record_warnings(record)

        case_create = record.get("case_create") if isinstance(record.get("case_create"), dict) else {}
        species_counts[_text(case_create.get("species")).lower() or "unknown"] += 1

        for err in record_errors:
            rejected_by_code[err.get("error_code") or "unknown"] += 1
        for warn in record_warnings:
            warnings_by_code[warn.get("warning_code") or "unknown"] += 1

        if record_errors:
            item = {
                "index": index,
                "status": "rejected",
                "legacy_case_id": legacy_case_id,
                "idempotency_key": idempotency_key,
                "errors": record_errors,
                "warnings": record_warnings,
            }
            all_errors.append(item)
        else:
            accepted_records.append(record)
            item = {
                "index": index,
                "status": "accepted",
                "legacy_case_id": legacy_case_id,
                "idempotency_key": idempotency_key,
                "operation": "case_create",
                "case_create_preview": _preview_case_create(case_create),
                "warnings": record_warnings,
            }

        if record_warnings:
            all_warnings.append({
                "index": index,
                "legacy_case_id": legacy_case_id,
                "idempotency_key": idempotency_key,
                "warnings": record_warnings,
            })

        items.append(item)

    accepted = len(accepted_records)
    rejected = len(records) - accepted
    chunks = ceil(accepted / chunk_size) if accepted else 0
    ready_for_import = rejected == 0

    report: Dict[str, Any] = {
        "message": message,
        "mode": mode,
        "batch_id": batch_id or f"dry-run-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "generated_at": _now_iso(),
        "dry_run": True,
        "validate_only": True,
        "writes_database": False,
        "calls_case_create_api": False,
        "user_id": include_user_id,
        "received": len(records),
        "accepted": accepted,
        "rejected": rejected,
        "ready_for_import": ready_for_import,
        "summary": {
            "received": len(records),
            "accepted": accepted,
            "rejected": rejected,
            "error_count": sum(len(item.get("errors") or []) for item in all_errors),
            "warning_count": sum(len(item.get("warnings") or []) for item in all_warnings),
            "species_counts": _counter_to_sorted_dict(species_counts),
            "operation_counts": _counter_to_sorted_dict(operation_counts),
            "legacy_status_counts": _counter_to_sorted_dict(legacy_status_counts),
            "rejected_by_code": _counter_to_sorted_dict(rejected_by_code),
            "warnings_by_code": _counter_to_sorted_dict(warnings_by_code),
        },
        "quality": {
            "field_coverage": _field_coverage(accepted_records),
            "idempotency_keys": {
                "unique_seen": len(seen_keys),
                "duplicates_in_batch": int(rejected_by_code.get("duplicate_in_batch", 0)),
            },
        },
        "import_plan": {
            "target_operation": "case_create",
            "chunk_size": chunk_size,
            "chunks": chunks,
            "accepted_records": accepted,
            "can_promote_to_real_import": False,
            "reason": "V2 is an API dry-run report only; it never writes database records.",
            "next_gate": "clinical pilot sign-off and a separate real-import implementation.",
        },
        "sample_payloads": [
            {
                "index": item["index"],
                "legacy_case_id": item.get("legacy_case_id"),
                "idempotency_key": item.get("idempotency_key"),
                "case_create": records[item["index"] - 1].get("case_create"),
            }
            for item in items
            if item.get("status") == "accepted"
        ][:sample_limit],
        "errors": all_errors,
        "warnings": all_warnings,
    }

    if include_items:
        report["items"] = items

    return report


@router.post("/legacy-cases/mock", response_model=dict)
def legacy_cases_import_mock(
    data: LegacyCaseImportMockIn,
    user=Depends(get_current_user),
):
    report = build_dry_run_report(
        records=data.records or [],
        batch_id=data.batch_id,
        mode="api_mock",
        message="mocked",
        max_records=MAX_MOCK_RECORDS,
        options=LegacyCaseImportDryRunOptions(sample_limit=3, include_items=True),
        include_user_id=getattr(user, "id", None),
    )

    # Keep the V1 contract stable for existing smoke checks.
    return {
        "message": "mocked",
        "mode": "api_mock",
        "batch_id": report["batch_id"],
        "dry_run": True,
        "validate_only": True,
        "writes_database": False,
        "calls_case_create_api": False,
        "user_id": report.get("user_id"),
        "received": report["received"],
        "accepted": report["accepted"],
        "rejected": report["rejected"],
        "items": report.get("items") or [],
        "errors": report.get("errors") or [],
        "summary": report.get("summary") or {},
        "ready_for_import": report.get("ready_for_import"),
    }


@router.post("/legacy-cases/dry-run", response_model=dict)
def legacy_cases_import_dry_run(
    data: LegacyCaseImportDryRunIn,
    user=Depends(get_current_user),
):
    return build_dry_run_report(
        records=data.records or [],
        batch_id=data.batch_id,
        mode="api_dry_run",
        message="dry_run_report",
        max_records=MAX_DRY_RUN_RECORDS,
        options=data.options,
        include_user_id=getattr(user, "id", None),
    )
