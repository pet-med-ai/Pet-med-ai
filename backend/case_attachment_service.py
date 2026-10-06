"""Case attachment lifecycle on existing Case JSON and append-only AuditLog."""
from contextlib import contextmanager
from datetime import datetime
import json
import re
import time

from sqlalchemy import text
from db import SessionLocal
from models import Case, AuditLog
from case_attachment_store import Store, AttachmentError, SCHEMA, TTL, digest, validate_file

SOURCE = "case-attachments-cw-b6"
MAX_CASE_BYTES = 100 * 1024 * 1024
MAX_CASE_FILES = 20
META_FIELDS = {"title", "kind", "taken_at", "reported_at", "source", "note"}


def request_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise AttachmentError("invalid_request_id", 422)
    return value


def stage_id(uid, cid, rid):
    return digest([SOURCE, str(uid), cid, request_id(rid)])


def known(item):
    return isinstance(item, dict) and item.get("schema") == SCHEMA


def public(item):
    fields = {"id", "name", "mime", "size", "sha256", "state", "metadata", "confirmed_at", "confirmed_by", "changed_at", "withdrawal_reason", "uploaded_at", "uploaded_by"}
    return {k: v for k, v in item.items() if k in fields}


def case_token(case):
    return digest({"owner": case.owner_id, "id": case.id, "patient": case.patient_name, "species": case.species,
                   "updated": str(case.updated_at), "deleted": str(case.deleted_at), "attachments": case.attachments})


def case_view(case):
    return {"case_id": case.id, "patient_name": case.patient_name, "species": case.species, "case_token": case_token(case)}


@contextmanager
def transaction(uid, cid, factory=SessionLocal):
    # Always own a fresh transaction: auth dependency may already have a read txn.
    with factory() as db:
        if db.get_bind().dialect.name == "sqlite": db.execute(text("BEGIN IMMEDIATE"))
        case = db.query(Case).filter_by(id=cid, owner_id=uid).with_for_update().first()
        if case is None or case.deleted_at is not None: raise AttachmentError("case_not_found", 404)
        if case.attachments is not None and not isinstance(case.attachments, list):
            raise AttachmentError("legacy_attachment_data_needs_review")
        yield db, case


def ledger_id(uid, cid, rid):
    return digest([SOURCE, "operation", str(uid), cid, request_id(rid)])


def audit(db, uid, cid, rid, action, fingerprint, result, **extra):
    row = AuditLog(log_id=ledger_id(uid, cid, rid), request_id=rid, clinician_id=str(uid),
                   case_id=cid, event_type="attachment_" + action, action_taken=action, source=SOURCE,
                   extra_data={"fingerprint": fingerprint, "result": result, **extra})
    db.add(row)
    return row


def replay(db, uid, cid, rid, fingerprint=None):
    row = db.get(AuditLog, ledger_id(uid, cid, rid))
    if row and (row.source != SOURCE or (fingerprint is not None and row.extra_data.get("fingerprint") != fingerprint)):
        raise AttachmentError("request_payload_changed")
    return row.extra_data if row else None


def protected_ids(db):
    return {a["id"] for (items,) in db.query(Case.attachments).all() for a in (items if isinstance(items, list) else []) if known(a)}


def find(case, aid, active=False):
    value = next((a for a in (case.attachments or []) if known(a) and a.get("id") == aid), None)
    if value is None or (active and value.get("state") != "active"):
        raise AttachmentError("attachment_not_found", 404)
    return value


def listing(uid, cid):
    store = Store()
    with store.locked(), transaction(uid, cid) as (db, case):
        store.cleanup(protected_ids(db))
        return {**case_view(case), "items": [public(a) for a in (case.attachments or []) if known(a)],
                "legacy_count": sum(not known(a) for a in (case.attachments or [])),
                "limits": {"file_bytes": 10 * 1024 * 1024, "case_bytes": MAX_CASE_BYTES, "case_files": MAX_CASE_FILES}}


def upload(uid, cid, rid, expected, data, name, mime):
    info = validate_file(data, name, mime)
    key = stage_id(uid, cid, rid)
    fingerprint = digest({"info": info, "case_token": expected})
    store = Store()
    with store.locked(), transaction(uid, cid) as (db, case):
        prior = replay(db, uid, cid, rid, fingerprint)
        if prior:
            return _upload_status(store, case, uid, key, prior)
        if case_token(case) != expected: raise AttachmentError("case_changed_review_again")
        store.cleanup(protected_ids(db))
        duplicate = next((a for a in (case.attachments or []) if known(a) and a.get("state") == "active" and a.get("sha256") == info["sha256"]), None)
        if duplicate:
            result = {"state": "already_attached", "attachment": public(duplicate)}
        else:
            active = [a for a in (case.attachments or []) if known(a) and a.get("state") == "active"]
            if len(active) >= MAX_CASE_FILES or sum(a["size"] for a in active) + info["size"] > MAX_CASE_BYTES:
                raise AttachmentError("case_attachment_limit", 413)
            if store.path(key, ".json").exists():
                item = store.metadata(key)
                if item.get("fingerprint") != fingerprint or item.get("state") != "pending":
                    raise AttachmentError("request_payload_changed")
                store.verified(item)
                if time.time() - item["created_at"] >= TTL: raise AttachmentError("upload_expired")
            else:
                if key in protected_ids(db): raise AttachmentError("attachment_metadata_invalid")
                item = {**info, "schema": SCHEMA, "id": key, "owner": uid, "case_id": cid,
                        "created_at": time.time(), "uploaded_at": datetime.utcnow().isoformat() + "Z", "uploaded_by": str(uid), "state": "pending", "case_token": expected, "fingerprint": fingerprint}
                store.write(key, ".blob", data)
                store.write_metadata(item)
            result = {"state": "pending", "attachment": public(item), "expires_at": item["created_at"] + TTL}
        audit(db, uid, cid, rid, "upload", fingerprint, result)
        db.commit()
        return {**result, **case_view(case)}


def _upload_status(store, case, uid, key, prior):
    confirmed = next((a for a in (case.attachments or []) if known(a) and a["id"] == key), None)
    if confirmed: return {"state": confirmed["state"], "attachment": public(confirmed), **case_view(case)}
    result = prior["result"]
    if result["state"] == "already_attached":
        return {"state": "already_attached", "attachment": public(find(case, result["attachment"]["id"])), **case_view(case)}
    if time.time() >= result["expires_at"]: return {"state": "expired", **case_view(case)}
    item = store.metadata(key)
    if item["owner"] != uid or item["case_id"] != case.id: raise AttachmentError("attachment_not_found", 404)
    if item["state"] == "cancelled": return {"state": "cancelled", **case_view(case)}
    if time.time() - item["created_at"] >= TTL: raise AttachmentError("upload_expired")
    store.verified(item)
    return {**result, **case_view(case)}


def upload_status(uid, cid, rid):
    store = Store()
    with store.locked(), transaction(uid, cid) as (db, case):
        prior = replay(db, uid, cid, rid)
        if prior is None: return {"state": "not_committed", **case_view(case)}
        return _upload_status(store, case, uid, stage_id(uid, cid, rid), prior)


def cancel(uid, cid, rid):
    store = Store()
    with store.locked(), transaction(uid, cid) as (db, case):
        key = stage_id(uid, cid, rid)
        if any(known(a) and a["id"] == key for a in (case.attachments or [])):
            return {"state": "already_attached"}
        prior = replay(db, uid, cid, rid)
        if prior is None: return {"state": "not_committed"}
        if prior["result"]["state"] == "already_attached": return {"state": "already_attached"}
        item = store.metadata(key)
        item["state"] = "cancelled"
        store.write_metadata(item)
        store.path(key, ".blob").unlink(missing_ok=True)
        return {"state": "cancelled"}


def metadata(value):
    if not isinstance(value, dict) or set(value) != META_FIELDS:
        raise AttachmentError("invalid_attachment_metadata", 422)
    limits = {"title": 150, "kind": 20, "taken_at": 40, "reported_at": 40, "source": 150, "note": 1000}
    if any(not isinstance(v, str) or len(v) > limits[k] or "\x00" in v for k, v in value.items()):
        raise AttachmentError("invalid_attachment_metadata", 422)
    if not value["title"].strip() or value["kind"] not in {"lab", "dr", "ultrasound", "other"}:
        raise AttachmentError("invalid_attachment_metadata", 422)
    for key in ("taken_at", "reported_at"):
        if value[key]:
            try:
                parsed = datetime.fromisoformat(value[key].replace("Z", "+00:00"))
                if parsed.tzinfo is None: raise ValueError()
            except ValueError: raise AttachmentError("invalid_attachment_date", 422) from None
    return value.copy()


def _preview(store, db, case, uid, body):
    if case_token(case) != body["expected_case_token"]: raise AttachmentError("case_changed_review_again")
    aid, operation = body["attachment_id"], body["operation"]
    request_id(body["request_id"])
    if operation == "confirm":
        item = store.metadata(aid)
        if item["owner"] != uid or item["case_id"] != case.id: raise AttachmentError("attachment_not_found", 404)
        if item["state"] != "pending" or time.time() - item["created_at"] >= TTL: raise AttachmentError("upload_expired")
        if item["case_token"] != case_token(case): raise AttachmentError("case_changed_upload_again")
        uploaded = db.query(AuditLog).filter_by(source=SOURCE, case_id=case.id, event_type="attachment_upload").all()
        if not any(r.extra_data.get("result", {}).get("attachment", {}).get("id") == aid for r in uploaded):
            raise AttachmentError("upload_not_committed")
        store.verified(item)
        active = [a for a in (case.attachments or []) if known(a) and a.get("state") == "active"]
        if any(a["sha256"] == item["sha256"] for a in active): raise AttachmentError("duplicate_attachment")
        if len(active) >= MAX_CASE_FILES or sum(a["size"] for a in active) + item["size"] > MAX_CASE_BYTES:
            raise AttachmentError("case_attachment_limit", 413)
    else:
        item = find(case, aid, active=True)
    if operation in {"confirm", "update"}:
        proposed = {**item, "metadata": metadata(body["metadata"])}
    elif operation == "withdraw":
        if not body["reason"].strip(): raise AttachmentError("withdrawal_reason_required", 422)
        proposed = {**item, "withdrawal_reason": body["reason"], "state": "withdrawn"}
    else: raise AttachmentError("invalid_operation", 422)
    return {**case_view(case), "before": public(item), "proposed": public(proposed),
            "preview_token": digest({"body": body, "owner": uid, "case": case_view(case), "before": public(item)}), "operation": operation}


def preview(uid, cid, body):
    store = Store()
    with store.locked(), transaction(uid, cid) as (db, case):
        return _preview(store, db, case, uid, body)


def commit(uid, cid, body, token):
    store = Store()
    fingerprint = digest({"body": body, "token": token})
    with store.locked(), transaction(uid, cid) as (db, case):
        prior = replay(db, uid, cid, body["request_id"], fingerprint)
        if prior: return {**prior["result"], "attachment": public(find(case, body["attachment_id"])), **case_view(case)}
        review = _preview(store, db, case, uid, body)
        if review["preview_token"] != token: raise AttachmentError("review_changed")
        item = {**review["proposed"], "schema": SCHEMA, "changed_at": datetime.utcnow().isoformat() + "Z"}
        if body["operation"] == "confirm":
            item.update(state="active", confirmed_at=item["changed_at"], confirmed_by=str(uid))
            case.attachments = [*(case.attachments or []), item]
        else:
            case.attachments = [item if known(a) and a["id"] == item["id"] else a for a in case.attachments or []]
        case.updated_at = datetime.utcnow()
        result = {"state": "committed", "attachment": public(item)}
        audit(db, uid, cid, body["request_id"], body["operation"], fingerprint, result,
              before=review["before"], after=public(item), reason=body["reason"])
        db.commit()
        return {**result, **case_view(case)}


def operation_status(uid, cid, rid):
    store = Store()
    with store.locked(), transaction(uid, cid) as (db, case):
        prior = replay(db, uid, cid, rid)
        result = dict(prior["result"]) if prior else {"state": "not_committed"}
        if result.get("state") == "committed":
            result["attachment"] = public(find(case, result["attachment"]["id"]))
        return {**result, **case_view(case)}


def download(uid, cid, aid, rid, preview_image=False):
    store = Store()
    with store.locked(), transaction(uid, cid) as (db, case):
        item = find(case, aid, active=True)
        if preview_image and item["mime"] not in {"image/png", "image/jpeg"}: raise AttachmentError("image_preview_only", 422)
        data = store.verified(item)
        fingerprint = digest([aid, "preview" if preview_image else "download"])
        if replay(db, uid, cid, rid, fingerprint) is None:
            audit(db, uid, cid, rid, "preview" if preview_image else "download", fingerprint,
                  {"state": "authorized", "attachment_id": aid}, sha256=item["sha256"], size=item["size"])
            db.commit()
        return data, public(item)
