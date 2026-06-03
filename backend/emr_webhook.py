# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

try:
    from backend.db import get_db
    from backend.models import WebhookInbox
except ModuleNotFoundError:
    from db import get_db
    from models import WebhookInbox


router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

DEFAULT_DRY_RUN_SECRET = "petmed-emr-webhook-dry-run-secret-v1"
WINDOW_SECONDS = 300
MAX_BODY_BYTES = 512 * 1024

SPECIES_NORMALIZATION = {
    "canine": "dog",
    "feline": "cat",
    "avian": "bird",
    "mouse": "rodent",
    "mice": "rodent",
    "rat": "rodent",
    "hamster": "rodent",
    "guinea pig": "guinea_pig",
    "guinea-pig": "guinea_pig",
    "guinea_pig": "guinea_pig",
    "sugar glider": "sugar_glider",
    "sugar-glider": "sugar_glider",
}

ALLOWED_SPECIES = {
    "dog", "cat", "rabbit", "bird", "reptile", "turtle", "snake", "lizard",
    "amphibian", "ferret", "rodent", "guinea_pig", "hamster", "chinchilla",
    "rat", "mouse", "hedgehog", "sugar_glider", "fish", "other",
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


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _active_secrets() -> List[str]:
    env_secret = _text(os.getenv("PMAI_WEBHOOK_SECRET"))
    # Dry-run endpoint also accepts the deterministic smoke secret so that local
    # and Render smoke can run before a real EMR secret is configured.
    values = [env_secret, DEFAULT_DRY_RUN_SECRET]
    deduped: List[str] = []
    for item in values:
        if item and item not in deduped:
            deduped.append(item)
    return deduped


def _parse_timestamp(value: str) -> datetime:
    raw = _text(value)
    if not raw:
        raise HTTPException(status_code=400, detail="missing X-PMAI-Timestamp")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bad timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _assert_timestamp_window(timestamp: str) -> None:
    parsed = _parse_timestamp(timestamp)
    delta = abs((_utc_now() - parsed).total_seconds())
    if delta > WINDOW_SECONDS:
        raise HTTPException(status_code=401, detail="timestamp outside allowed window")


def _payload_hash(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def _signature_hash(signature: str) -> str:
    return hashlib.sha256(_text(signature).encode("utf-8")).hexdigest()


def _verify_signature(timestamp: str, raw_body: bytes, signature: str) -> bool:
    raw_signature = _text(signature)
    if not raw_signature.startswith("sha256="):
        return False

    signed = timestamp.encode("utf-8") + b"." + raw_body
    for secret in _active_secrets():
        digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        if hmac.compare_digest(raw_signature, f"sha256={digest}"):
            return True
    return False


def _receipt_for(idempotency_key: str, payload_digest: str) -> str:
    digest = hashlib.sha256(f"{idempotency_key}|{payload_digest}".encode("utf-8")).hexdigest()
    return "rcpt_" + digest[:24]


def _normalize_species(value: Any) -> str:
    raw = _text(value).lower().replace("-", "_").replace(" ", "_")
    raw = SPECIES_NORMALIZATION.get(raw, raw)
    return raw if raw in ALLOWED_SPECIES else (raw or "other")


def _format_weight(value: Any) -> Optional[str]:
    text = _text(value)
    if not text:
        return None
    return text if text.lower().endswith("kg") else f"{text}kg"


def _format_age_or_dob(pet: Dict[str, Any]) -> Optional[str]:
    age = _text(pet.get("age") or pet.get("age_info"))
    if age:
        return age
    dob = _text(pet.get("dob") or pet.get("date_of_birth"))
    return f"DOB {dob}" if dob else None


def _join_items(items: Any) -> str:
    if not isinstance(items, list) or not items:
        return "未记录"
    values: List[str] = []
    for item in items:
        if isinstance(item, dict):
            name = _text(item.get("name") or item.get("code") or item.get("id"))
            dose = _text(item.get("dose"))
            route = _text(item.get("route"))
            freq = _text(item.get("freq") or item.get("frequency"))
            parts = [part for part in [name, dose, route, freq] if part]
            values.append(" ".join(parts) if parts else json.dumps(item, ensure_ascii=False))
        else:
            values.append(_text(item))
    return "；".join(value for value in values if value) or "未记录"


def _validation_error(field: str, code: str, reason: str, suggestion: str) -> Dict[str, str]:
    return {
        "field": field,
        "error_code": code,
        "error_reason": reason,
        "suggestion": suggestion,
    }


def _validation_warning(field: str, code: str, reason: str, suggestion: str) -> Dict[str, str]:
    return {
        "field": field,
        "warning_code": code,
        "warning_reason": reason,
        "suggestion": suggestion,
    }


def _validate_payload(payload: Dict[str, Any]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    if not _text(payload.get("case_id")):
        errors.append(_validation_error(
            "case_id",
            "required",
            "case_id is required for EMR dry-run mapping.",
            "Send a stable EMR case_id.",
        ))

    pet = payload.get("pet") if isinstance(payload.get("pet"), dict) else {}
    if not _text(pet.get("name")):
        errors.append(_validation_error(
            "pet.name",
            "required",
            "pet.name is required.",
            "Send pet.name so the mapped Case has patient_name.",
        ))
    if not _text(pet.get("species")):
        errors.append(_validation_error(
            "pet.species",
            "required",
            "pet.species is required.",
            "Map species to dog/cat/rabbit/bird/reptile/ferret/rodent/other.",
        ))

    encounter = payload.get("encounter") if isinstance(payload.get("encounter"), dict) else {}
    if not _text(encounter.get("chief_complaint")):
        warnings.append(_validation_warning(
            "encounter.chief_complaint",
            "optional_missing",
            "chief_complaint is empty.",
            "Send chief_complaint when possible for a useful Case preview.",
        ))

    attachments = payload.get("attachments")
    if attachments is not None and not isinstance(attachments, list):
        errors.append(_validation_error(
            "attachments",
            "invalid_type",
            "attachments must be a list when present.",
            "Use an array of objects with presigned_url.",
        ))

    return errors, warnings


def build_case_create_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map EMR webhook payload to the current Pet-Med-AI CaseCreate shape."""

    pet = payload.get("pet") if isinstance(payload.get("pet"), dict) else {}
    owner = payload.get("owner") if isinstance(payload.get("owner"), dict) else {}
    encounter = payload.get("encounter") if isinstance(payload.get("encounter"), dict) else {}
    clinician = payload.get("clinician") if isinstance(payload.get("clinician"), dict) else {}
    timestamps = payload.get("timestamps") if isinstance(payload.get("timestamps"), dict) else {}
    vitals = encounter.get("vitals") if isinstance(encounter.get("vitals"), dict) else {}

    species = _normalize_species(pet.get("species"))
    weight_value = vitals.get("weight_kg") if vitals.get("weight_kg") is not None else pet.get("weight_kg")
    weight = _format_weight(weight_value)
    diagnosis_codes = encounter.get("diagnosis_codes") if isinstance(encounter.get("diagnosis_codes"), list) else []
    procedures = encounter.get("procedures") if isinstance(encounter.get("procedures"), list) else []
    meds = encounter.get("meds") if isinstance(encounter.get("meds"), list) else []
    attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []

    chief = _text(encounter.get("chief_complaint")) or f"EMR 同步病例：{_text(payload.get('case_id')) or '未记录'}"

    history_lines = [
        "【EMR Webhook Case 映射 dry-run】",
        f"EMR case_id：{_text(payload.get('case_id')) or '未记录'}",
        f"encounter_id：{_text(encounter.get('encounter_id')) or '未记录'}",
        f"EMR 状态：{_text(encounter.get('status')) or '未记录'}",
        f"医生：{_text(clinician.get('name')) or '未记录'} / {_text(clinician.get('id')) or '未记录'}",
        f"诊断码：{', '.join(str(x) for x in diagnosis_codes) if diagnosis_codes else '未记录'}",
        f"操作/检查：{', '.join(str(x) for x in procedures) if procedures else '未记录'}",
        f"用药摘要：{_join_items(meds)}",
        f"EMR 创建时间：{_text(timestamps.get('created_at')) or '未记录'}",
        f"EMR 更新时间：{_text(timestamps.get('updated_at')) or '未记录'}",
        "说明：本记录由 EMR → Case 映射 dry-run 生成，未创建 Pet-Med-AI 病例。",
    ]

    exam_lines = [
        "【EMR Webhook 体征/附件摘要】",
        f"体温：{vitals.get('temp_c', '未记录')}",
        f"心率：{vitals.get('hr', '未记录')}",
        f"呼吸：{vitals.get('rr', '未记录')}",
        f"体重：{weight or '未记录'}",
        f"BCS：{vitals.get('bcs', '未记录')}",
        f"附件条目数：{len(attachments)}",
        "说明：dry-run V1 只生成映射预览，不下载附件、不创建病例。",
    ]

    payload_out = {
        "patient_name": _text(pet.get("name")) or "未命名病例",
        "species": species,
        "sex": _text(pet.get("sex")) or None,
        "age_info": _format_age_or_dob(pet),
        "breed": _text(pet.get("breed")) or None,
        "weight": weight,
        "coat_color": _text(pet.get("coat_color")) or None,
        "owner_name": _text(owner.get("name")) or None,
        "owner_phone": _text(owner.get("phone")) or None,
        "chief_complaint": chief,
        "history": "\n".join(history_lines),
        "exam_findings": "\n".join(exam_lines),
    }
    return {field: payload_out.get(field) for field in CASE_CREATE_FIELDS}


def _mapping_quality(case_create: Dict[str, Any]) -> Dict[str, Any]:
    required = ["patient_name", "species", "chief_complaint"]
    recommended = ["weight", "owner_name", "owner_phone", "history", "exam_findings"]
    missing_required = [field for field in required if not _text(case_create.get(field))]
    missing_recommended = [field for field in recommended if not _text(case_create.get(field))]
    coverage_fields = required + recommended
    non_empty = sum(1 for field in coverage_fields if _text(case_create.get(field)))
    return {
        "required_fields": required,
        "recommended_fields": recommended,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "field_coverage": {
            "non_empty": non_empty,
            "total": len(coverage_fields),
            "ratio": round(non_empty / len(coverage_fields), 4) if coverage_fields else 0.0,
        },
        "ready_for_case_create_preview": not missing_required,
    }


def _extract_external_ids(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    encounter = payload.get("encounter") if isinstance(payload.get("encounter"), dict) else {}
    return _text(payload.get("case_id")) or None, _text(encounter.get("encounter_id")) or None


def _safe_payload_for_storage(payload: Dict[str, Any]) -> Dict[str, Any]:
    # V1 keeps the original JSON payload for traceability. It does not fetch or expand attachments.
    return payload


def _load_signed_payload(
    *,
    request_body: bytes,
    timestamp: str,
    signature: str,
) -> Tuple[Dict[str, Any], str, str]:
    if len(request_body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="webhook payload too large for dry-run")

    _assert_timestamp_window(timestamp)

    if not _verify_signature(timestamp, request_body, signature):
        raise HTTPException(status_code=401, detail="bad signature")

    try:
        payload = json.loads(request_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be a JSON object")

    return payload, _payload_hash(request_body), _signature_hash(signature)


def _receipt_response_base(
    *,
    message: str,
    mode: str,
    status: str,
    receipt_id: str,
    idempotency_key: str,
    payload_digest: str,
    receipt_persisted: bool,
    duplicate: bool,
) -> Dict[str, Any]:
    return {
        "message": message,
        "mode": mode,
        "status": status,
        "receipt_id": receipt_id,
        "idempotency_key": idempotency_key,
        "payload_hash": payload_digest,
        "generated_at": _now_iso(),
        "dry_run": True,
        "writes_webhook_inbox": True,
        "writes_case_database": False,
        "creates_case": False,
        "updates_case": False,
        "downloads_attachments": False,
        "receipt_persisted": receipt_persisted,
        "duplicate": duplicate,
    }


def _existing_receipt_response(existing: WebhookInbox, payload_digest: str, mode: str, message: str) -> Dict[str, Any]:
    warnings: List[Dict[str, str]] = []
    if existing.payload_hash != payload_digest:
        warnings.append(_validation_warning(
            "Idempotency-Key",
            "duplicate_key_different_payload",
            "Same Idempotency-Key already exists with a different payload hash.",
            "Keep a stable key per event and do not reuse it across different events.",
        ))

    case_preview = existing.mapped_case_preview if isinstance(existing.mapped_case_preview, dict) else {}
    response = _receipt_response_base(
        message=message,
        mode=mode,
        status="duplicate",
        receipt_id=existing.receipt_id,
        idempotency_key=existing.idempotency_key,
        payload_digest=payload_digest,
        receipt_persisted=True,
        duplicate=True,
    )
    response.update({
        "validation": {
            "accepted": existing.status == "accepted",
            "errors": existing.validation_errors or [],
            "warnings": warnings or existing.validation_warnings or [],
        },
        "mapped_case_preview": case_preview,
        "mapping": {
            "case_create": case_preview,
            "quality": _mapping_quality(case_preview) if case_preview else {},
        },
        "import_plan": {
            "target_operation": "case_create_preview",
            "can_promote_to_real_import": False,
            "reason": "This is a duplicate dry-run receipt; V1 never creates Case records.",
            "next_gate": "EMR real ingestion must be implemented as a separate audited workflow.",
        },
    })
    return response


def _persist_receipt(
    db: Session,
    *,
    receipt_id: str,
    payload: Dict[str, Any],
    idempotency_key: str,
    payload_digest: str,
    signature_digest: str,
    status: str,
    errors: List[Dict[str, str]],
    warnings: List[Dict[str, str]],
    case_preview: Dict[str, Any],
) -> WebhookInbox:
    external_case_id, external_encounter_id = _extract_external_ids(payload)
    obj = WebhookInbox(
        receipt_id=receipt_id,
        source="emr",
        event_type="case.mapping.dry_run",
        idempotency_key=idempotency_key,
        payload_hash=payload_digest,
        signature_hash=signature_digest,
        external_case_id=external_case_id,
        external_encounter_id=external_encounter_id,
        case_id=None,
        status=status,
        dry_run=True,
        validation_errors=errors or None,
        validation_warnings=warnings or None,
        mapped_case_preview=case_preview or None,
        payload=_safe_payload_for_storage(payload),
        error_code=(errors[0].get("error_code") if errors else None),
        error_message=(errors[0].get("error_reason") if errors else None),
        received_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(WebhookInbox).filter(WebhookInbox.idempotency_key == idempotency_key).first()
        if existing:
            return existing
        raise
    db.refresh(obj)
    return obj


async def _handle_emr_dry_run(
    *,
    request: Request,
    db: Session,
    timestamp: Optional[str],
    signature: Optional[str],
    idempotency_key: Optional[str],
    mode: str,
    message: str,
) -> Dict[str, Any]:
    ts = _text(timestamp)
    sig = _text(signature)
    idem = _text(idempotency_key)

    if not ts or not sig or not idem:
        raise HTTPException(status_code=400, detail="missing required webhook headers")

    raw_body = await request.body()
    payload, digest, sig_digest = _load_signed_payload(
        request_body=raw_body,
        timestamp=ts,
        signature=sig,
    )

    existing = db.query(WebhookInbox).filter(WebhookInbox.idempotency_key == idem).first()
    if existing:
        return _existing_receipt_response(existing, digest, mode, message)

    errors, warnings = _validate_payload(payload)
    case_preview = build_case_create_preview(payload)
    quality = _mapping_quality(case_preview)
    status = "accepted" if not errors and quality.get("ready_for_case_create_preview") else "rejected"
    receipt_id = _receipt_for(idem, digest)

    obj = _persist_receipt(
        db,
        receipt_id=receipt_id,
        payload=payload,
        idempotency_key=idem,
        payload_digest=digest,
        signature_digest=sig_digest,
        status=status,
        errors=errors,
        warnings=warnings,
        case_preview=case_preview,
    )

    # A race may return an existing object with a different receipt_id; treat it as duplicate.
    if obj.receipt_id != receipt_id:
        return _existing_receipt_response(obj, digest, mode, message)

    response = _receipt_response_base(
        message=message,
        mode=mode,
        status=status,
        receipt_id=obj.receipt_id,
        idempotency_key=idem,
        payload_digest=digest,
        receipt_persisted=True,
        duplicate=False,
    )
    response.update({
        "signature": {
            "algorithm": "HMAC-SHA256",
            "timestamp_window_seconds": WINDOW_SECONDS,
            "verified": True,
        },
        "validation": {
            "accepted": status == "accepted",
            "errors": errors,
            "warnings": warnings,
        },
        "mapped_case_preview": case_preview,
        "mapping": {
            "case_create": case_preview,
            "case_create_fields": CASE_CREATE_FIELDS,
            "quality": quality,
        },
        "import_plan": {
            "target_operation": "case_create_preview",
            "can_promote_to_real_import": False,
            "reason": "EMR → Case mapping dry-run V1 never creates or updates Pet-Med-AI Case records.",
            "next_gate": "EMR real ingestion requires a separate audited implementation and rollback plan.",
        },
    })
    return response


@router.post("/emr/dry-run", response_model=dict, status_code=202)
async def emr_webhook_dry_run(
    request: Request,
    db: Session = Depends(get_db),
    x_pmai_timestamp: Optional[str] = Header(default=None, alias="X-PMAI-Timestamp"),
    x_pmai_signature: Optional[str] = Header(default=None, alias="X-PMAI-Signature"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """
    Receive, validate, and persist an EMR webhook receipt in dry-run mode.

    Safety boundary:
    - writes webhook_inbox receipt only
    - does not write Case
    - does not create ConsultSession
    - does not download attachments
    - does not write audit_log yet
    """

    response = await _handle_emr_dry_run(
        request=request,
        db=db,
        timestamp=x_pmai_timestamp,
        signature=x_pmai_signature,
        idempotency_key=idempotency_key,
        mode="emr_webhook_dry_run",
        message="emr_webhook_dry_run",
    )
    return JSONResponse(status_code=202, content=response)


@router.post("/emr/case-mapping/dry-run", response_model=dict, status_code=202)
async def emr_case_mapping_dry_run(
    request: Request,
    db: Session = Depends(get_db),
    x_pmai_timestamp: Optional[str] = Header(default=None, alias="X-PMAI-Timestamp"),
    x_pmai_signature: Optional[str] = Header(default=None, alias="X-PMAI-Signature"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """
    Full EMR -> CaseCreate mapping dry-run.

    It persists a webhook_inbox receipt and returns a CaseCreate preview plus import plan.
    It still never creates or updates Case records.
    """

    response = await _handle_emr_dry_run(
        request=request,
        db=db,
        timestamp=x_pmai_timestamp,
        signature=x_pmai_signature,
        idempotency_key=idempotency_key,
        mode="case_mapping_dry_run",
        message="emr_case_mapping_dry_run",
    )
    return JSONResponse(status_code=202, content=response)
