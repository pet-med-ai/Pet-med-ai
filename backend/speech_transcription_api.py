"""Authenticated, synthetic-only development route and atomic history provenance."""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session
from db import SessionLocal
from models import AuditLog, Case, ConsultSession
from auth_jwt import get_current_user
import speech_budget as budget
import speech_transcription as provider

router = APIRouter(prefix="/api/speech", tags=["speech"])


def get_db():
    with SessionLocal() as db:
        yield db


class Binding(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str = Field(min_length=1, max_length=64)
    case_id: int | None = None
    patient_name: str = Field(min_length=1, max_length=255)
    species: str = Field(min_length=1, max_length=50)
    session_version: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft_version: str = Field(pattern=r"^[a-f0-9]{64}$")


class TranscriptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    binding: Binding
    synthetic_only: Literal[True]
    audio_base64: str = Field(max_length=2800000)


class VoiceConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    receipt: str = Field(min_length=20, max_length=4000)
    original_text: str = Field(min_length=1, max_length=4000)
    edited_text: str = Field(min_length=1, max_length=4000)
    reviewed: Literal[True]


def fail(error):
    raise HTTPException(error.status, detail=error.code) from None


def owned(db, sid, user):
    session = db.query(ConsultSession).filter_by(session_uid=sid, owner_id=user.id).first()
    if session is None:
        raise HTTPException(404, "问诊不存在")
    case = None
    if session.case_id:
        case = db.query(Case).filter_by(id=session.case_id, owner_id=user.id).first()
        if case is None or getattr(case, "deleted_at", None):
            raise HTTPException(404, "病例不存在")
    return session, case


def session_version(session, case=None):
    return budget.digest([session.session_uid, session.case_id, str(session.updated_at), session.answers, session.result,
                          str(case.updated_at) if case else None])


def signing_key():
    secret = os.getenv("SECRET_KEY", "")
    if len(secret) < 16:
        raise provider.SpeechError("receipt_signing_unavailable")
    return secret.encode()


def issue_receipt(request_id, user_id, binding, transcript, origin_binding=None):
    data = {"id": request_id, "user": user_id, "binding": binding, "sha256": budget.digest(transcript),
            "origin_binding": origin_binding or budget.digest(binding),
            "provider": provider.PROVIDER, "expires": int(time.time()) + 8 * 3600}
    body = base64.urlsafe_b64encode(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()).decode()
    return body + "." + hmac.new(signing_key(), body.encode(), hashlib.sha256).hexdigest()


def parse_receipt(receipt):
    try:
        body, signature = receipt.rsplit(".", 1)
        if not hmac.compare_digest(signature, hmac.new(signing_key(), body.encode(), hashlib.sha256).hexdigest()):
            raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(body))
        if data["expires"] < time.time():
            raise ValueError()
        return data
    except (ValueError, KeyError, TypeError):
        raise HTTPException(409, "语音来源已失效，请重新核对") from None


@router.get("/availability")
def availability(user=Depends(get_current_user)):
    try:
        provider.ensure_enabled()
        signing_key()
        meter = budget.budget_status()
        return {"enabled": meter["attempts"] < budget.LIMIT, "synthetic_only": True, **meter}
    except provider.SpeechError as error:
        return {"enabled": False, "reason": error.code, "synthetic_only": True}


@router.get("/context/{session_id}")
def context(session_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    session, case = owned(db, session_id, user)
    return {"session_id": session_id, "case_id": session.case_id, "session_version": session_version(session, case),
            "patient_name": case.patient_name if case else None, "species": case.species if case else None}


@router.get("/requests/{request_id}")
def request_status(request_id: str, user=Depends(get_current_user)):
    try:
        return budget.status(request_id, user.id)
    except provider.SpeechError as error:
        fail(error)


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirmation: VoiceConfirmation
    binding: Binding


@router.post("/review")
def review(data: ReviewIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Doctor re-review after local edits/restore, without another ASR call."""
    entry = data.confirmation
    receipt = parse_receipt(entry.receipt)
    binding = data.binding.model_dump()
    old = receipt["binding"]
    session, case = owned(db, binding["session_id"], user)
    claim = db.get(AuditLog, budget.key("reserve", receipt["id"]))
    result = db.get(AuditLog, budget.key("result", receipt["id"]))
    if (receipt["user"] != user.id or any(old[k] != binding[k] for k in ("session_id", "case_id", "patient_name", "species"))
            or binding["case_id"] != session.case_id or binding["session_version"] != session_version(session, case)
            or (case and (case.patient_name != binding["patient_name"] or case.species != binding["species"]))
            or receipt["sha256"] != budget.digest(entry.original_text)
            or claim is None or claim.clinician_id != str(user.id) or claim.extra_data["binding"] != receipt["origin_binding"]
            or result is None or result.extra_data != {"state": "recognized", "transcript_hash": receipt["sha256"]}
            or db.get(AuditLog, budget.key("confirm", receipt["id"])) is not None):
        raise HTTPException(409, "语音来源不属于当前病例或已保存，不能重新绑定")
    return {"receipt": issue_receipt(receipt["id"], user.id, binding, entry.original_text, receipt["origin_binding"])}


@router.post("/transcribe")
async def transcribe(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    audio = payload = data = None
    reserved = False
    try:
        provider.ensure_enabled()
        signing_key()
        # Read bounded JSON directly: UploadFile can spool recordings to disk.
        payload = bytearray()
        async with asyncio.timeout(15):
            async for part in request.stream():
                if len(payload) + len(part) > 2810000:
                    raise provider.SpeechError("audio_size", 413)
                payload.extend(part)
        try:
            data = TranscriptionIn.model_validate_json(payload)
            audio = base64.b64decode(data.audio_base64, validate=True)
        except (ValidationError, ValueError):
            raise provider.SpeechError("invalid_audio_request", 422) from None
        payload = None
        duration = provider.validate_wav(audio)
        binding = data.binding.model_dump()
        session, case = owned(db, binding["session_id"], user)
        if (binding["case_id"] != session.case_id or binding["session_version"] != session_version(session, case)
                or (case and (binding["patient_name"] != case.patient_name or binding["species"] != case.species))):
            raise provider.SpeechError("context_changed", 409)
        budget.reserve(data.request_id, user.id, binding, hashlib.sha256(audio).hexdigest(), duration)
        reserved = True
        result = await provider.recognize(audio, data.request_id)
        budget.finish(data.request_id, user.id, "recognized", transcript_hash=budget.digest(result["text"]))
        reserved = False
        return {"request_id": data.request_id, "text": result["text"], "provider": provider.PROVIDER,
                "receipt": issue_receipt(data.request_id, user.id, binding, result["text"]),
                "binding": binding, "reserved_fen": 1}
    except (TimeoutError, asyncio.CancelledError):
        if reserved:
            budget.finish(data.request_id, user.id, "result_unknown")
        raise HTTPException(504, "speech_request_timeout_unknown") from None
    except provider.SpeechError as error:
        if reserved:
            budget.finish(data.request_id, user.id, error.code)
        fail(error)
    finally:
        # No body/error logging. Unknown exit leaves the reservation spent.
        audio = payload = data = None


def validate_confirmations(db, items, session, user, patient_name, species, history, case=None):
    verified = []
    ids = set()
    for item in items:
        entry = item.model_dump() if isinstance(item, VoiceConfirmation) else VoiceConfirmation.model_validate(item).model_dump()
        receipt = parse_receipt(entry["receipt"])
        binding = receipt["binding"]
        rid = receipt["id"]
        claim, result = db.get(AuditLog, budget.key("reserve", rid)), db.get(AuditLog, budget.key("result", rid))
        if (rid in ids or receipt["user"] != user.id or receipt["provider"] != provider.PROVIDER
                or binding["session_id"] != session.session_uid or binding["case_id"] != session.case_id
                or binding["patient_name"] != patient_name or binding["species"] != species
                or binding["session_version"] != session_version(session, case)
                or receipt["sha256"] != budget.digest(entry["original_text"])
                or not entry["edited_text"].strip() or entry["edited_text"] not in history
                or claim is None or claim.clinician_id != str(user.id) or claim.extra_data["binding"] != receipt["origin_binding"]
                or result is None or result.extra_data != {"state": "recognized", "transcript_hash": receipt["sha256"]}
                or db.get(AuditLog, budget.key("confirm", rid)) is not None):
            raise HTTPException(409, "语音来源、病例或内容已改变，请重新核对")
        ids.add(rid)
        verified.append({"request_id": rid, "original_text": entry["original_text"], "edited_text": entry["edited_text"],
                         "provider": provider.PROVIDER, "binding": binding})
    return verified


def append_confirmation_audits(db, verified, user, case_id, session_id):
    # Caller commits alongside the case. A deterministic primary key also stops
    # a replay racing an older SQLite snapshot; a losing transaction rolls back.
    for entry in verified:
        db.add(budget.row("confirm", entry["request_id"], user.id,
                          {**entry, "confirmed_at": datetime.utcnow().isoformat() + "Z"},
                          case_id=case_id, session_uid=session_id))


def bind_confirmation_preview(snapshot, items):
    if not items:
        return snapshot
    confirmations = [item.model_dump() for item in items]
    return {**snapshot, "voice_confirmations": confirmations,
            "preview_token": budget.digest([snapshot["preview_token"], confirmations])}
