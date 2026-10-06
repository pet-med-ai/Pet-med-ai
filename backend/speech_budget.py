"""CW-B5 fixed batch ledger in append-only AuditLog. No automatic initialization."""
import hashlib
import json

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from db import SessionLocal
from models import AuditLog
from speech_transcription import SpeechError, ensure_development

BATCH = "CW-B5-20261006"
SOURCE = "speech-cw-b5"
LIMIT = 100
POLICY = {"batch": BATCH, "max_attempts": 100, "max_fen": 100, "fen_per_attempt": 1, "price_cny_per_1000": "3.20"}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def key(kind, request_id=""):
    return digest([BATCH, kind, request_id])


def row(kind, request_id, clinician, metadata, **kw):
    return AuditLog(log_id=key(kind, request_id), request_id=request_id or BATCH,
                    clinician_id=str(clinician), event_type="speech_" + kind,
                    action_taken=kind, source=SOURCE, extra_data=metadata, **kw)


def initialize_ledger(factory=SessionLocal):
    """Offline, explicit one-time action on an isolated test database only."""
    ensure_development()
    with factory() as db:
        if db.query(AuditLog).filter(AuditLog.source == SOURCE).first():
            raise SpeechError("ledger_already_exists", 409)
        db.add(row("anchor", "", "system", POLICY))
        db.commit()


def _locked(db):
    if db.get_bind().dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    anchor = db.query(AuditLog).filter_by(log_id=key("anchor")).with_for_update().first()
    if anchor is None or anchor.extra_data != POLICY:
        raise SpeechError("ledger_missing_or_invalid")
    entries = db.query(AuditLog).filter_by(source=SOURCE, event_type="speech_reserve").all()
    slots = sorted((r.extra_data or {}).get("slot", -1) for r in entries)
    if slots != list(range(1, len(entries) + 1)) or len(entries) > LIMIT or any((r.extra_data or {}).get("fen") != 1 or r.log_id != key("reserve", r.request_id) for r in entries):
        raise SpeechError("ledger_missing_or_invalid")
    return entries


def reserve(request_id, clinician, binding, audio_hash, duration, factory=SessionLocal):
    """Reserve and commit BEFORE egress. Anchor lock serializes every process."""
    try:
        with factory() as db:
            entries = _locked(db)
            if db.get(AuditLog, key("reserve", request_id)):
                raise SpeechError("request_already_reserved", 409)
            if len(entries) >= LIMIT:
                raise SpeechError("batch_budget_exhausted", 429)
            db.add(row("reserve", request_id, clinician,
                       {"slot": len(entries) + 1, "fen": 1, "binding": digest(binding),
                        "audio_sha256": audio_hash, "seconds": duration}, session_uid=binding["session_id"]))
            db.commit()
            return len(entries) + 1
    except SQLAlchemyError:
        raise SpeechError("ledger_write_failed") from None


def finish(request_id, clinician, state, *, transcript_hash=None, factory=SessionLocal):
    with factory() as db:
        if db.get(AuditLog, key("reserve", request_id)) is None:
            raise SpeechError("ledger_missing_or_invalid")
        db.add(row("result", request_id, clinician, {"state": state, "transcript_hash": transcript_hash}))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise SpeechError("request_already_finished", 409) from None


def status(request_id, clinician, factory=SessionLocal):
    with factory() as db:
        claim = db.get(AuditLog, key("reserve", request_id))
        if claim is None or claim.clinician_id != str(clinician):
            raise SpeechError("request_not_found", 404)
        result = db.get(AuditLog, key("result", request_id))
        return {"request_id": request_id, "state": result.extra_data["state"] if result else "reserved_result_unknown", "reserved_fen": 1,
                "retry_allowed": False}  # No transcript recovery or re-egress.


def budget_status(factory=SessionLocal):
    try:
        with factory() as db:
            entries = _locked(db)
            return {"batch": BATCH, "attempts": len(entries), "reserved_fen": len(entries), "limit": LIMIT}
    except SQLAlchemyError:
        raise SpeechError("ledger_unavailable") from None
