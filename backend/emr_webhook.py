# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import time
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
IDEMPOTENCY_CACHE_SECONDS = 15 * 60

# Kept only as a best-effort short-lived cache for compatibility, but receipt
# persistence V1 uses the webhook_inbox table as the source of truth.
_IDEMPOTENCY_CACHE: Dict[str, Dict[str, Any]] = {}


def _text(value: Any) -> str:
    return str(value or "").strip()


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


def _cleanup_idempotency_cache() -> None:
    now = time.time()
    stale = [
        key for key, value in _IDEMPOTENCY_CACHE.items()
        if now - float(value.get("created_monotonic") or 0) > IDEMPOTENCY_CACHE_SECONDS
    ]
    for key in stale:
        _IDEMPOTENCY_CACHE.pop(key, None)


def _receipt_for(idempotency_key: str, payload_digest: str) -> str:
    digest = hashlib.sha256(f"{idempotency_key}|{payload_digest}".encode("utf-8")).hexdigest()
    return "rcpt_" + digest[:24]


def _signature_hash(signature: str) -> str:
    return hashlib.sha256(_text(signature).encode("utf-8")).hexdigest()


def _external_ids(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    encounter = payload.get("encounter") if isinstance(payload.get("encounter"), dict) else {}
    return _text(payload.get("case_id")) or None, _text(encounter.get("encounter_id")) or None


def _first_error_code(errors: List[Dict[str, str]]) -> Optional[str]:
    if not errors:
        return None
    return _text(errors[0].get("error_code")) or "validation_error"


def _first_error_message(errors: List[Dict[str, str]]) -> Optional[str]:
    if not errors:
        return None
    return _text(errors[0].get("error_reason")) or "Webhook validation failed."


def _duplicate_response(existing: WebhookInbox, idem: str, digest: str) -> JSONResponse:
    warnings: List[Dict[str, str]] = []
    if existing.payload_hash != digest:
        warnings.append({
            "field": "Idempotency-Key",
            "warning_code": "duplicate_key_different_payload",
            "warning_reason": "Same Idempotency-Key was reused with a different payload hash.",
            "suggestion": "Keep a stable key per event and do not reuse it across different events.",
        })

    stored_warnings = existing.validation_warnings if isinstance(existing.validation_warnings, list) else []
    return JSONResponse(
        status_code=202,
        content={
            "message": "emr_webhook_dry_run",
            "status": "duplicate",
            "stored_status": existing.status,
            "receipt_id": existing.receipt_id,
            "idempotency_key": idem,
            "payload_hash": digest,
            "stored_payload_hash": existing.payload_hash,
            "dry_run": True,
            "writes_database": True,
            "writes_webhook_inbox": True,
            "writes_case_database": False,
            "creates_case": False,
            "downloads_attachments": False,
            "receipt_persisted": True,
            "mapped_case_preview": existing.mapped_case_preview or None,
            "validation": {
                "accepted": existing.status == "accepted",
                "errors": existing.validation_errors or [],
                "warnings": stored_warnings + warnings,
            },
            "warnings": warnings,
            "next_gate": "EMR -> Case mapping dry-run before any real case ingestion.",
        },
    )


def _save_webhook_inbox_record(
    *,
    db: Session,
    receipt_id: str,
    idem: str,
    digest: str,
    signature: str,
    payload: Dict[str, Any],
    errors: List[Dict[str, str]],
    warnings: List[Dict[str, str]],
    case_preview: Dict[str, Any],
    status: str,
) -> WebhookInbox:
    external_case_id, external_encounter_id = _external_ids(payload)
    obj = WebhookInbox(
        receipt_id=receipt_id,
        source="emr",
        event_type="case.upsert",
        idempotency_key=idem,
        payload_hash=digest,
        signature_hash=_signature_hash(signature),
        external_case_id=external_case_id,
        external_encounter_id=external_encounter_id,
        status=status,
        dry_run=True,
        validation_errors=errors or None,
        validation_warnings=warnings or None,
        mapped_case_preview=case_preview or None,
        payload=payload,
        error_code=_first_error_code(errors),
        error_message=_first_error_message(errors),
        received_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _validate_payload(payload: Dict[str, Any]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    if not _text(payload.get("case_id")):
        errors.append({
            "field": "case_id",
            "error_code": "required",
            "error_reason": "case_id is required for EMR dry-run mapping.",
            "suggestion": "Send a stable EMR case_id.",
        })

    pet = payload.get("pet") if isinstance(payload.get("pet"), dict) else {}
    if not _text(pet.get("name")):
        errors.append({
            "field": "pet.name",
            "error_code": "required",
            "error_reason": "pet.name is required.",
            "suggestion": "Send pet.name so the mapped Case has patient_name.",
        })
    if not _text(pet.get("species")):
        errors.append({
            "field": "pet.species",
            "error_code": "required",
            "error_reason": "pet.species is required.",
            "suggestion": "Map species to dog/cat/rabbit/bird/reptile/ferret/rodent/other.",
        })

    encounter = payload.get("encounter") if isinstance(payload.get("encounter"), dict) else {}
    if not _text(encounter.get("chief_complaint")):
        warnings.append({
            "field": "encounter.chief_complaint",
            "warning_code": "optional_missing",
            "warning_reason": "chief_complaint is empty.",
            "suggestion": "Send chief_complaint when possible for a useful Case preview.",
        })

    attachments = payload.get("attachments")
    if attachments is not None and not isinstance(attachments, list):
        errors.append({
            "field": "attachments",
            "error_code": "invalid_type",
            "error_reason": "attachments must be a list when present.",
            "suggestion": "Use an array of objects with presigned_url.",
        })

    return errors, warnings


def _map_case_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    pet = payload.get("pet") if isinstance(payload.get("pet"), dict) else {}
    owner = payload.get("owner") if isinstance(payload.get("owner"), dict) else {}
    encounter = payload.get("encounter") if isinstance(payload.get("encounter"), dict) else {}
    clinician = payload.get("clinician") if isinstance(payload.get("clinician"), dict) else {}
    timestamps = payload.get("timestamps") if isinstance(payload.get("timestamps"), dict) else {}
    vitals = encounter.get("vitals") if isinstance(encounter.get("vitals"), dict) else {}

    species = _text(pet.get("species")).lower() or "other"
    weight_value = vitals.get("weight_kg") if vitals.get("weight_kg") is not None else pet.get("weight_kg")
    weight = f"{weight_value}kg" if weight_value not in (None, "") else None

    diagnosis_codes = encounter.get("diagnosis_codes") if isinstance(encounter.get("diagnosis_codes"), list) else []
    procedures = encounter.get("procedures") if isinstance(encounter.get("procedures"), list) else []
    meds = encounter.get("meds") if isinstance(encounter.get("meds"), list) else []
    attachments = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []

    chief = _text(encounter.get("chief_complaint")) or f"EMR 同步病例：{_text(payload.get('case_id'))}"

    history_lines = [
        "【EMR Webhook dry-run 映射预览】",
        f"EMR case_id：{_text(payload.get('case_id')) or '未记录'}",
        f"encounter_id：{_text(encounter.get('encounter_id')) or '未记录'}",
        f"EMR 状态：{_text(encounter.get('status')) or '未记录'}",
        f"医生：{_text(clinician.get('name')) or '未记录'} / {_text(clinician.get('id')) or '未记录'}",
        f"诊断码：{', '.join(str(x) for x in diagnosis_codes) if diagnosis_codes else '未记录'}",
        f"操作/检查：{', '.join(str(x) for x in procedures) if procedures else '未记录'}",
        f"EMR 创建时间：{_text(timestamps.get('created_at')) or '未记录'}",
        f"EMR 更新时间：{_text(timestamps.get('updated_at')) or '未记录'}",
    ]

    exam_lines = [
        "【EMR Webhook dry-run 体征/附件摘要】",
        f"体温：{vitals.get('temp_c', '未记录')}",
        f"心率：{vitals.get('hr', '未记录')}",
        f"呼吸：{vitals.get('rr', '未记录')}",
        f"体重：{weight or '未记录'}",
        f"BCS：{vitals.get('bcs', '未记录')}",
        f"用药条目数：{len(meds)}",
        f"附件条目数：{len(attachments)}",
        "说明：dry-run V1 只生成映射预览，不下载附件、不创建病例。",
    ]

    return {
        "patient_name": _text(pet.get("name")) or "未命名病例",
        "species": species,
        "sex": None,
        "age_info": None,
        "breed": None,
        "weight": weight,
        "coat_color": None,
        "owner_name": _text(owner.get("name")) or None,
        "owner_phone": _text(owner.get("phone")) or None,
        "chief_complaint": chief,
        "history": "\n".join(history_lines),
        "exam_findings": "\n".join(exam_lines),
    }


@router.post("/emr/dry-run", response_model=dict, status_code=202)
async def emr_webhook_dry_run(
    request: Request,
    x_pmai_timestamp: Optional[str] = Header(default=None, alias="X-PMAI-Timestamp"),
    x_pmai_signature: Optional[str] = Header(default=None, alias="X-PMAI-Signature"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """
    Receive and validate an EMR webhook in dry-run mode.

    Safety boundary:
    - persists a webhook_inbox receipt for traceability and idempotency
    - does not write Case
    - does not create ConsultSession
    - does not download attachments
    - does not write audit_log yet
    """

    timestamp = _text(x_pmai_timestamp)
    signature = _text(x_pmai_signature)
    idem = _text(idempotency_key)

    if not timestamp or not signature or not idem:
        raise HTTPException(status_code=400, detail="missing required webhook headers")

    _assert_timestamp_window(timestamp)

    raw_body = await request.body()
    if len(raw_body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="webhook payload too large for dry-run")

    if not _verify_signature(timestamp, raw_body, signature):
        raise HTTPException(status_code=401, detail="bad signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be a JSON object")

    _cleanup_idempotency_cache()
    digest = _payload_hash(raw_body)

    existing = db.query(WebhookInbox).filter(WebhookInbox.idempotency_key == idem).first()
    if existing:
        return _duplicate_response(existing, idem, digest)

    errors, warnings = _validate_payload(payload)
    case_preview = _map_case_preview(payload)
    receipt_id = _receipt_for(idem, digest)

    status = "accepted" if not errors else "rejected"

    try:
        inbox = _save_webhook_inbox_record(
            db=db,
            receipt_id=receipt_id,
            idem=idem,
            digest=digest,
            signature=signature,
            payload=payload,
            errors=errors,
            warnings=warnings,
            case_preview=case_preview,
            status=status,
        )
    except IntegrityError:
        db.rollback()
        existing = db.query(WebhookInbox).filter(WebhookInbox.idempotency_key == idem).first()
        if existing:
            return _duplicate_response(existing, idem, digest)
        raise

    _IDEMPOTENCY_CACHE[idem] = {
        "receipt_id": receipt_id,
        "payload_hash": digest,
        "created_monotonic": time.time(),
    }

    return {
        "message": "emr_webhook_dry_run",
        "status": status,
        "receipt_id": receipt_id,
        "idempotency_key": idem,
        "payload_hash": digest,
        "generated_at": _now_iso(),
        "dry_run": True,
        "writes_database": True,
        "writes_webhook_inbox": True,
        "writes_case_database": False,
        "creates_case": False,
        "downloads_attachments": False,
        "receipt_persisted": True,
        "webhook_inbox": {
            "receipt_id": inbox.receipt_id,
            "status": inbox.status,
            "external_case_id": inbox.external_case_id,
            "external_encounter_id": inbox.external_encounter_id,
            "received_at": inbox.received_at.isoformat() if inbox.received_at else None,
            "processed_at": inbox.processed_at.isoformat() if inbox.processed_at else None,
        },
        "signature": {
            "algorithm": "HMAC-SHA256",
            "timestamp_window_seconds": WINDOW_SECONDS,
            "verified": True,
        },
        "validation": {
            "accepted": not errors,
            "errors": errors,
            "warnings": warnings,
        },
        "mapped_case_preview": case_preview,
        "next_gate": "EMR Webhook inbox/receipt model V1 before any real ingestion.",
    }
