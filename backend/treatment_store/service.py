"""Atomic account attestations. No network calls and no prescription execution.

Lock order: organization, membership, case, plan, command, challenge. Unknown
results keep the original key. A committed receipt is re-readable, never retried.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import uuid4
from passlib.hash import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

TABLES = {
    "treatment_plans",
    "treatment_drafts",
    "treatment_revisions",
    "treatment_reviews",
    "treatment_signatures",
    "treatment_events",
    "signing_challenges",
    "clinical_audit_events",
    "command_receipts",
}
JSON_FIELDS = {
    "content",
    "source_manifest",
    "clinician_snapshot",
    "actor_snapshot",
    "result",
}
OPERATIONS = {"draft.save", "revision.freeze", "review", "sign", "amend", "revoke"}


class Problem(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


def canonical(value):
    # No normalization, template expansion or inferred clinical content.
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def one(db, sql, **params):
    row = db.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def rows(db, sql, **params):
    return [dict(r) for r in db.execute(text(sql), params).mappings()]


def insert(db, table, data):
    assert table in TABLES
    values = {
        k: (
            json.dumps(v, ensure_ascii=False, allow_nan=False)
            if k in JSON_FIELDS and v is not None
            else v
        )
        for k, v in data.items()
    }
    expressions = [
        f"CAST(:{k} AS jsonb)" if k in JSON_FIELDS else f":{k}" for k in data
    ]
    db.execute(
        text(
            f'INSERT INTO {table} ({",".join(data)}) VALUES ({",".join(expressions)})'
        ),
        values,
    )


def bind(db, actor, scope):
    db.execute(
        text(
            "SELECT set_config('pmai.actor_id',:actor,true),set_config('pmai.session_id',:sid,true),set_config('pmai.org_id',:org_id,true),set_config('pmai.clinic_id',:clinic_id,true)"
        ),
        {**scope, "actor": str(actor["id"]), "sid": actor["sid"]},
    )


def context(db, actor, scope, locking=False, writing=False, signing=False):
    bind(db, actor, scope)
    if db.execute(text("SELECT pmai_scope.actor_id()")).scalar() is None:
        raise Problem(401, "SESSION_EXPIRED")
    ctx = db.execute(
        text("SELECT pmai_treatment.context(:org_id,:clinic_id,:case_id,:locking)"),
        {**scope, "locking": locking},
    ).scalar()
    if not ctx:
        raise Problem(404, "CASE_NOT_FOUND")
    if (writing and not ctx["can_edit"]) or (signing and not ctx["can_sign"]):
        raise Problem(403, "CLINICAL_PERMISSION_REQUIRED")
    return ctx


def plan(db, scope, create=False):
    row = one(
        db,
        "SELECT * FROM treatment_plans WHERE org_id=:org_id AND clinic_id=:clinic_id AND case_id=:case_id FOR UPDATE",
        **scope,
    )
    if row is None and create:
        insert(db, "treatment_plans", {"id": str(uuid4()), **scope})
        return plan(db, scope)
    return row


def scope_row(p):
    return {key: p[key] for key in ("org_id", "clinic_id", "case_id")} | {
        "plan_id": p["id"]
    }


def etag(p):
    return f'"plan:{p["lock_version"] if p else 0}"'


def draft_etag(d):
    return f'"draft:{d["draft_version"] if d else 0}"'


def aggregate(db, actor, scope):
    ctx = context(db, actor, scope)
    p = one(
        db,
        "SELECT * FROM treatment_plans WHERE org_id=:org_id AND clinic_id=:clinic_id AND case_id=:case_id",
        **scope,
    )
    d = (
        one(db, "SELECT * FROM treatment_drafts WHERE plan_id=:p", p=p["id"])
        if p
        else None
    )
    revisions = (
        rows(
            db,
            "SELECT id,revision_no,draft_version,content,source_manifest,content_sha256,created_by,created_at,origin,amendment_of FROM treatment_revisions WHERE plan_id=:p ORDER BY revision_no DESC",
            p=p["id"],
        )
        if p
        else []
    )
    reviews = (
        rows(
            db,
            "SELECT * FROM treatment_reviews WHERE plan_id=:p ORDER BY reviewed_at",
            p=p["id"],
        )
        if p
        else []
    )
    signatures = (
        rows(
            db,
            "SELECT * FROM treatment_signatures WHERE plan_id=:p ORDER BY signed_at",
            p=p["id"],
        )
        if p
        else []
    )
    events = (
        rows(
            db,
            "SELECT * FROM treatment_events WHERE plan_id=:p ORDER BY created_at",
            p=p["id"],
        )
        if p
        else []
    )
    return {
        "actor_id": actor["id"],
        "scope": scope,
        "plan": p,
        "etag": etag(p),
        "draft_etag": draft_etag(d),
        "draft": d,
        "revisions": revisions,
        "reviews": reviews,
        "signatures": signatures,
        "events": events,
        "profile": ctx["profile"],
        "source_epoch": ctx["source"]["case"]["clinical_epoch"],
        "policy": ctx["source"]["policy"],
        "allowed_actions": {
            "edit": ctx["can_edit"],
            "review": ctx["can_sign"],
            "sign": ctx["can_sign"]
            and ctx["source"]["policy"]["required_assurance"] == "account_attestation",
        },
    }


def revision(db, p, rid):
    r = one(
        db,
        "SELECT * FROM treatment_revisions WHERE plan_id=:p AND id=:id",
        p=p["id"],
        id=rid,
    )
    if not r:
        raise Problem(404, "REVISION_NOT_FOUND")
    return r


def fresh(r, p, ctx, db):
    if str(p["head_revision_id"]) != str(r["id"]):
        raise Problem(409, "REVISION_SUPERSEDED")
    if r["origin"] != "clinical":
        raise Problem(409, "LEGACY_UNSIGNED")
    current_draft = one(
        db, "SELECT draft_version FROM treatment_drafts WHERE plan_id=:p", p=p["id"]
    )
    if not current_draft or current_draft["draft_version"] != r["draft_version"]:
        raise Problem(409, "DRAFT_CHANGED")
    if r["source_manifest"] != ctx["source"]:
        raise Problem(409, "SOURCE_CHANGED")


def signature(db, actor, scope, sid):
    context(db, actor, scope)
    s = one(
        db,
        "SELECT * FROM treatment_signatures WHERE org_id=:org_id AND clinic_id=:clinic_id AND case_id=:case_id AND id=:id",
        **scope,
        id=sid,
    )
    if not s:
        raise Problem(404, "SIGNATURE_NOT_FOUND")
    r = one(db, "SELECT * FROM treatment_revisions WHERE id=:id", id=s["revision_id"])
    r["canonical_utf8"] = bytes(r.pop("canonical_bytes")).decode("utf-8")
    e = one(db, "SELECT * FROM treatment_events WHERE signature_id=:id", id=sid)
    a = one(
        db, "SELECT * FROM clinical_audit_events WHERE id=:id", id=s["audit_event_id"]
    )
    return {
        "signature": s,
        "revision": r,
        "audit": a,
        "terminal_event": e,
        "state": e["event"] if e else "effective",
    }


def key_valid(key):
    if not key or not re.fullmatch("[0-9a-f]{64}", key):
        raise Problem(422, "INVALID_IDEMPOTENCY_KEY")


def command_hash(actor, scope, op, target, precondition, body):
    return digest(
        {
            "actor_id": actor["id"],
            "scope": scope,
            "operation": op,
            "target": target,
            "precondition": precondition,
            "body": body,
        }
    )


def receipt(db, scope, actor, key, operation, locking=False):
    return one(
        db,
        "SELECT * FROM command_receipts WHERE org_id=:org_id AND clinic_id=:clinic_id AND case_id=:case_id AND actor_id=:actor AND idempotency_key=:key AND operation=:op"
        + (" FOR UPDATE" if locking else ""),
        **scope,
        actor=actor["id"],
        key=key,
        op=operation,
    )


def receipt_result(r):
    if r["state"] == "pending":
        return 202, {
            "state": "pending",
            "request_hash": r["request_hash"],
            "operation": r["operation"],
            "idempotency_key": r["idempotency_key"],
        }
    return r["http_status"], {
        **(r["result"] or {}),
        "state": r["state"],
        "request_hash": r["request_hash"],
        "operation": r["operation"],
        "idempotency_key": r["idempotency_key"],
    }


def lookup(db, actor, scope, key, operation):
    key_valid(key)
    if operation not in OPERATIONS:
        raise Problem(422, "INVALID_OPERATION")
    context(db, actor, scope)
    r = receipt(db, scope, actor, key, operation)
    return (
        receipt_result(r)
        if r
        else (
            202,
            {"state": "not_observed", "idempotency_key": key, "operation": operation},
        )
    )


def finish(db, cmd, state, status, result, code=None):
    db.execute(
        text(
            "UPDATE command_receipts SET state=:state,http_status=:status,result=CAST(:result AS jsonb),error_code=:code,completed_at=clock_timestamp(),lease_until=NULL WHERE id=:id AND state='pending' AND attempt_version=:attempt"
        ),
        {
            "id": cmd["id"],
            "attempt": cmd["attempt_version"],
            "state": state,
            "status": status,
            "result": json.dumps(result, ensure_ascii=False),
            "code": code,
        },
    )


def audit(db, p, actor, cmd, ctx, action, target, payload_hash, reason):
    aid = str(uuid4())
    insert(
        db,
        "clinical_audit_events",
        {
            "id": aid,
            **scope_row(p),
            "actor_id": actor["id"],
            "session_id": actor["sid"],
            "action": action,
            "target_id": target,
            "command_id": cmd["id"],
            "payload_sha256": payload_hash,
            "policy_version": ctx["source"]["policy"]["version"],
            "actor_snapshot": ctx["profile"] or {"user_id": actor["id"]},
            "reason": reason,
        },
    )
    return aid


def challenge(db, actor, body):
    scope = {k: body[k] for k in ("org_id", "clinic_id", "case_id")}
    ctx = context(db, actor, scope, locking=True, writing=True, signing=True)
    p = plan(db, scope)
    if not p:
        raise Problem(404, "REVISION_NOT_FOUND")
    if ctx["source"]["policy"]["required_assurance"] != "account_attestation":
        raise Problem(409, "ASSURANCE_UNAVAILABLE")
    r = revision(db, p, body["revision_id"])
    if body["content_hash"] != r["content_sha256"]:
        raise Problem(409, "HASH_MISMATCH")
    if body["action"] == "sign":
        if body["target_signature_id"] is not None:
            raise Problem(422, "INVALID_CHALLENGE_TARGET")
        fresh(r, p, ctx, db)
    elif str(p["active_signature_id"]) != body["target_signature_id"] or not one(
        db,
        "SELECT id FROM treatment_signatures WHERE id=:id AND revision_id=:r",
        id=body["target_signature_id"],
        r=r["id"],
    ):
        raise Problem(409, "SIGNATURE_NOT_ACTIVE")
    user = one(db, "SELECT hashed_password FROM users WHERE id=:id", id=actor["id"])
    try:
        valid = bcrypt.verify(body["password"], user["hashed_password"])
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise Problem(401, "REAUTHENTICATION_FAILED")
    cid = str(uuid4())
    db.execute(
        text(
            "INSERT INTO signing_challenges(id,org_id,clinic_id,case_id,plan_id,revision_id,content_hash,action,target_signature_id,actor_id,session_id,method,verified_at,expires_at) VALUES (:id,:org_id,:clinic_id,:case_id,:plan_id,:revision_id,:content_hash,:action,:target_signature_id,:actor,:sid,'password',statement_timestamp(),statement_timestamp()+interval '5 minutes')"
        ),
        {
            **scope_row(p),
            **{
                k: body[k]
                for k in (
                    "revision_id",
                    "content_hash",
                    "action",
                    "target_signature_id",
                )
            },
            "id": cid,
            "actor": actor["id"],
            "sid": actor["sid"],
        },
    )
    db.commit()
    return {"challenge_id": cid, "expires_in": 300, "assurance": "account_attestation"}


def consume(db, p, actor, cmd, cid, r, action, target=None):
    ch = one(
        db,
        "SELECT *,expires_at>clock_timestamp() AS fresh FROM signing_challenges WHERE id=:id FOR UPDATE",
        id=cid,
    )
    if (
        not ch
        or not ch["fresh"]
        or ch["consumed_by_command"]
        or str(ch["plan_id"]) != str(p["id"])
        or str(ch["revision_id"]) != str(r["id"])
        or ch["content_hash"] != r["content_sha256"]
        or ch["action"] != action
        or str(ch["session_id"]) != actor["sid"]
        or ch["actor_id"] != actor["id"]
        or str(ch["target_signature_id"]) != str(target)
    ):
        raise Problem(409, "CHALLENGE_INVALID")
    db.execute(
        text("UPDATE signing_challenges SET consumed_by_command=:cmd WHERE id=:id"),
        {"cmd": cmd["id"], "id": cid},
    )


def execute(db, actor, scope, key, op, target, precondition, body):
    key_valid(key)
    if not precondition:
        raise Problem(428, "PRECONDITION_REQUIRED")
    request_hash = command_hash(actor, scope, op, target, precondition, body)
    context(
        db,
        actor,
        scope,
        locking=True,
        writing=True,
        signing=op in ("review", "sign", "revoke"),
    )
    p = plan(db, scope, create=True)
    old = receipt(db, scope, actor, key, op, True)
    if old:
        if old["request_hash"] != request_hash:
            raise Problem(409, "IDEMPOTENCY_CONFLICT")
        return receipt_result(old)
    cid = str(uuid4())
    try:
        db.execute(
            text(
                "INSERT INTO command_receipts(id,org_id,clinic_id,case_id,plan_id,actor_id,operation,idempotency_key,request_hash,state,lease_until) VALUES (:id,:org_id,:clinic_id,:case_id,:plan_id,:actor,:op,:key,:hash,'pending',clock_timestamp()+interval '60 seconds')"
            ),
            {
                **scope_row(p),
                "id": cid,
                "actor": actor["id"],
                "op": op,
                "key": key,
                "hash": request_hash,
            },
        )
        db.commit()  # The key survives a crash before the domain transaction starts.
    except IntegrityError:
        db.rollback()
        raise Problem(409, "IDEMPOTENCY_CONFLICT")
    return perform(db, actor, scope, key, op, target, precondition, body, request_hash)


def perform(db, actor, scope, key, op, target, precondition, body, request_hash):
    ctx = context(
        db,
        actor,
        scope,
        locking=True,
        writing=True,
        signing=op in ("review", "sign", "revoke"),
    )
    p = plan(db, scope)
    cmd = receipt(db, scope, actor, key, op, True)
    if not cmd or cmd["request_hash"] != request_hash:
        raise Problem(409, "IDEMPOTENCY_CONFLICT")
    if cmd["state"] != "pending":
        return receipt_result(cmd)
    if not db.execute(
        text("SELECT lease_until>clock_timestamp() FROM command_receipts WHERE id=:id"),
        {"id": cmd["id"]},
    ).scalar():
        finish(
            db,
            cmd,
            "failed",
            409,
            {"code": "COMMAND_LEASE_EXPIRED"},
            "COMMAND_LEASE_EXPIRED",
        )
        db.commit()
        return lookup(db, actor, scope, key, op)
    try:
        with db.begin_nested():
            result = mutate(db, actor, p, cmd, ctx, op, target, precondition, body)
            db.execute(
                text(
                    "UPDATE treatment_plans SET lock_version=lock_version+1 WHERE id=:id"
                ),
                {"id": p["id"]},
            )
            result["etag"] = f'"plan:{p["lock_version"]+1}"'
            if not db.execute(
                text(
                    "SELECT lease_until>clock_timestamp() FROM command_receipts WHERE id=:id"
                ),
                {"id": cmd["id"]},
            ).scalar():
                raise Problem(409, "COMMAND_LEASE_EXPIRED")
            finish(db, cmd, "committed", 201, result)
    except Problem as exc:
        finish(db, cmd, "failed", exc.status, {"code": exc.code}, exc.code)
    # Unexpected DB failures roll back facts and leave a queryable pending receipt.
    db.commit()
    return lookup(db, actor, scope, key, op)


def mutate(db, actor, p, cmd, ctx, op, target, precondition, body):
    s = scope_row(p)
    d = one(db, "SELECT * FROM treatment_drafts WHERE plan_id=:p", p=p["id"])
    if op == "draft.save":
        if precondition != ("*" if not d else draft_etag(d)):
            raise Problem(412, "VERSION_MISMATCH")
        if p["active_signature_id"] and (
            not d or str(d["amendment_of"]) != str(p["active_signature_id"])
        ):
            raise Problem(409, "AMENDMENT_REQUIRED")
        v = d["draft_version"] + 1 if d else 1
        if d:
            db.execute(
                text(
                    "UPDATE treatment_drafts SET content=CAST(:body AS jsonb),draft_version=:v,updated_by=:a,updated_at=clock_timestamp() WHERE plan_id=:p"
                ),
                {
                    "body": json.dumps(body["content"], ensure_ascii=False),
                    "v": v,
                    "a": actor["id"],
                    "p": p["id"],
                },
            )
        else:
            insert(
                db,
                "treatment_drafts",
                {
                    **s,
                    "base_revision_id": p["head_revision_id"],
                    "content": body["content"],
                    "draft_version": v,
                    "created_by": actor["id"],
                    "updated_by": actor["id"],
                },
            )
        aid = audit(
            db,
            p,
            actor,
            cmd,
            ctx,
            op,
            p["id"],
            digest(body["content"]),
            "Save treatment draft",
        )
        return {
            "plan_id": str(p["id"]),
            "draft_version": v,
            "draft_etag": f'"draft:{v}"',
            "audit_id": aid,
        }
    if precondition != etag(p):
        raise Problem(412, "VERSION_MISMATCH")
    if op == "revision.freeze":
        if not d or d["draft_version"] != body["draft_version"]:
            raise Problem(412, "VERSION_MISMATCH")
        if body["expected_source_epoch"] != ctx["source"]["case"]["clinical_epoch"]:
            raise Problem(409, "SOURCE_CHANGED")
        if (
            not d["content"]["diagnoses"]
            or not d["content"]["treatment"]["management_text"].strip()
        ):
            raise Problem(422, "INCOMPLETE_TREATMENT")
        if p["active_signature_id"] and str(d["amendment_of"]) != str(
            p["active_signature_id"]
        ):
            raise Problem(409, "AMENDMENT_REQUIRED")
        rid = str(uuid4())
        now = datetime.now(timezone.utc)
        envelope = {
            "schema": "pmai-treatment-revision-v1",
            "canonicalization": "pmai-canonical-json-v1",
            **{k: str(v) if k != "case_id" else v for k, v in s.items()},
            "revision_id": rid,
            "draft_version": d["draft_version"],
            "content": d["content"],
            "source_manifest": ctx["source"],
            "created_by": actor["id"],
            "created_at": now.isoformat().replace("+00:00", "Z"),
        }
        encoded = canonical(envelope)
        h = sha256(encoded).hexdigest()
        n = db.execute(
            text(
                "SELECT COALESCE(max(revision_no),0)+1 FROM treatment_revisions WHERE plan_id=:p"
            ),
            {"p": p["id"]},
        ).scalar()
        insert(
            db,
            "treatment_revisions",
            {
                "id": rid,
                **s,
                "revision_no": n,
                "draft_version": d["draft_version"],
                "predecessor_id": p["head_revision_id"],
                "amendment_of": d["amendment_of"],
                "schema_version": "treatment-content-v1",
                "content": d["content"],
                "source_manifest": ctx["source"],
                "canonical_bytes": encoded,
                "content_sha256": h,
                "created_by": actor["id"],
                "created_at": now,
                "origin": "clinical",
            },
        )
        db.execute(
            text("UPDATE treatment_plans SET head_revision_id=:r WHERE id=:p"),
            {"r": rid, "p": p["id"]},
        )
        audit(db, p, actor, cmd, ctx, op, rid, h, "Freeze exact treatment and sources")
        return {"revision_id": rid, "content_hash": h}
    if op == "review":
        r = revision(db, p, target)
        fresh(r, p, ctx, db)
        if one(
            db, "SELECT id FROM treatment_reviews WHERE revision_id=:id", id=r["id"]
        ):
            raise Problem(409, "ALREADY_REVIEWED")
        rid = str(uuid4())
        insert(
            db,
            "treatment_reviews",
            {
                "id": rid,
                **s,
                "revision_id": r["id"],
                "reviewed_hash": r["content_sha256"],
                "decision": body["decision"],
                "reviewer_id": actor["id"],
                "clinician_snapshot": ctx["profile"],
                "review_mode": ctx["source"]["policy"]["review_policy"],
                "reason": body["reason"],
            },
        )
        audit(db, p, actor, cmd, ctx, op, rid, r["content_sha256"], body["reason"])
        return {
            "review_id": rid,
            "revision_id": str(r["id"]),
            "decision": body["decision"],
        }
    if op == "sign":
        if ctx["source"]["policy"]["required_assurance"] != "account_attestation":
            raise Problem(409, "ASSURANCE_UNAVAILABLE")
        r = revision(db, p, target)
        fresh(r, p, ctx, db)
        if r["content_sha256"] != body["content_hash"]:
            raise Problem(409, "HASH_MISMATCH")
        review = one(
            db,
            "SELECT * FROM treatment_reviews WHERE revision_id=:r AND id=:id",
            r=r["id"],
            id=body["review_id"],
        )
        if not review or review["decision"] != "approve":
            raise Problem(409, "APPROVAL_REQUIRED")
        if not db.execute(
            text("SELECT pmai_treatment.reviewer_valid(:o,:c,:a,CAST(:p AS jsonb))"),
            {
                "o": p["org_id"],
                "c": p["clinic_id"],
                "a": review["reviewer_id"],
                "p": json.dumps(review["clinician_snapshot"]),
            },
        ).scalar():
            raise Problem(409, "REVIEWER_NO_LONGER_ELIGIBLE")
        if (
            ctx["source"]["policy"]["review_policy"] == "two_person"
            and review["reviewer_id"] == actor["id"]
        ):
            raise Problem(409, "SECOND_CLINICIAN_REQUIRED")
        if one(
            db, "SELECT id FROM treatment_signatures WHERE revision_id=:id", id=r["id"]
        ):
            raise Problem(409, "ALREADY_SIGNED")
        if str(r["amendment_of"]) != str(p["active_signature_id"]):
            raise Problem(409, "AMENDMENT_BASE_CHANGED")
        consume(db, p, actor, cmd, body["challenge_id"], r, "sign")
        sid = str(uuid4())
        aid = audit(
            db,
            p,
            actor,
            cmd,
            ctx,
            op,
            sid,
            r["content_sha256"],
            "Account attestation; not a certificate signature",
        )
        insert(
            db,
            "treatment_signatures",
            {
                "id": sid,
                **s,
                "revision_id": r["id"],
                "review_id": review["id"],
                "content_hash": r["content_sha256"],
                "signer_id": actor["id"],
                "clinician_snapshot": ctx["profile"],
                "assurance": "account_attestation",
                "challenge_id": body["challenge_id"],
                "audit_event_id": aid,
                "command_id": cmd["id"],
            },
        )
        if p["active_signature_id"]:
            insert(
                db,
                "treatment_events",
                {
                    "id": str(uuid4()),
                    **s,
                    "signature_id": p["active_signature_id"],
                    "event": "superseded",
                    "successor_signature_id": sid,
                    "reason": "Replaced by a newly signed amendment",
                    "actor_id": actor["id"],
                    "command_id": cmd["id"],
                },
            )
        db.execute(
            text("UPDATE treatment_plans SET active_signature_id=:s WHERE id=:p"),
            {"s": sid, "p": p["id"]},
        )
        return {
            "signature_id": sid,
            "revision_id": str(r["id"]),
            "assurance": "account_attestation",
        }
    if op == "amend":
        if str(p["active_signature_id"]) != body["base_signature_id"]:
            raise Problem(409, "SIGNATURE_NOT_ACTIVE")
        old = one(
            db,
            "SELECT * FROM treatment_signatures WHERE id=:id",
            id=body["base_signature_id"],
        )
        r = revision(db, p, old["revision_id"])
        # Preserve current drafts: opening another amendment must not overwrite edits.
        if d and str(d["amendment_of"]) == str(p["active_signature_id"]):
            raise Problem(409, "AMENDMENT_ALREADY_OPEN")
        v = d["draft_version"] + 1 if d else 1
        if d:
            db.execute(
                text(
                    "UPDATE treatment_drafts SET base_revision_id=:r,amendment_of=:s,content=CAST(:c AS jsonb),draft_version=:v,updated_by=:a,updated_at=clock_timestamp() WHERE plan_id=:p"
                ),
                {
                    "r": r["id"],
                    "s": old["id"],
                    "c": json.dumps(r["content"], ensure_ascii=False),
                    "v": v,
                    "a": actor["id"],
                    "p": p["id"],
                },
            )
        else:
            insert(
                db,
                "treatment_drafts",
                {
                    **s,
                    "base_revision_id": r["id"],
                    "amendment_of": old["id"],
                    "content": r["content"],
                    "draft_version": v,
                    "created_by": actor["id"],
                    "updated_by": actor["id"],
                },
            )
        audit(
            db, p, actor, cmd, ctx, op, old["id"], r["content_sha256"], body["reason"]
        )
        return {"draft_version": v, "base_signature_id": str(old["id"])}
    if op == "revoke":
        if str(p["active_signature_id"]) != target:
            raise Problem(409, "SIGNATURE_NOT_ACTIVE")
        old = one(db, "SELECT * FROM treatment_signatures WHERE id=:id", id=target)
        r = revision(db, p, old["revision_id"])
        consume(db, p, actor, cmd, body["challenge_id"], r, "revoke", target)
        eid = str(uuid4())
        audit(db, p, actor, cmd, ctx, op, eid, r["content_sha256"], body["reason"])
        insert(
            db,
            "treatment_events",
            {
                "id": eid,
                **s,
                "signature_id": target,
                "event": "revoked",
                "reason": body["reason"],
                "actor_id": actor["id"],
                "command_id": cmd["id"],
            },
        )
        db.execute(
            text("UPDATE treatment_plans SET active_signature_id=NULL WHERE id=:p"),
            {"p": p["id"]},
        )
        # Keep any open draft verbatim, but detach it from the now-terminal
        # signature. A new draft version fences its old approval/challenge and
        # permits a freshly frozen, reviewed and authenticated replacement.
        if d:
            db.execute(
                text(
                    "UPDATE treatment_drafts SET amendment_of=NULL,draft_version=draft_version+1,updated_by=:a,updated_at=clock_timestamp() WHERE plan_id=:p"
                ),
                {"a": actor["id"], "p": p["id"]},
            )
        return {"signature_id": target, "event_id": eid}
    raise Problem(422, "INVALID_OPERATION")


def cancel(db, actor, scope, key, body):
    key_valid(key)
    ctx = context(db, actor, scope, locking=True, writing=True)
    p = plan(db, scope, create=True)
    r = receipt(db, scope, actor, key, body["operation"], True)
    if r and r["request_hash"] != body["request_hash"]:
        raise Problem(409, "IDEMPOTENCY_CONFLICT")
    if r and r["state"] != "pending":
        return receipt_result(r)
    if not r:
        cid = str(uuid4())
        try:
            insert(
                db,
                "command_receipts",
                {
                    "id": cid,
                    **scope_row(p),
                    "actor_id": actor["id"],
                    "operation": body["operation"],
                    "idempotency_key": key,
                    "request_hash": body["request_hash"],
                    "state": "cancelled",
                    "http_status": 409,
                    "result": {"code": "COMMAND_CANCELLED"},
                    "error_code": "COMMAND_CANCELLED",
                    "completed_at": datetime.now(timezone.utc),
                },
            )
        except IntegrityError:
            db.rollback()
            raise Problem(409, "IDEMPOTENCY_CONFLICT")
        r = receipt(db, scope, actor, key, body["operation"])
    else:
        finish(
            db, r, "cancelled", 409, {"code": "COMMAND_CANCELLED"}, "COMMAND_CANCELLED"
        )
    audit(db, p, actor, r, ctx, "cancel", r["id"], r["request_hash"], body["reason"])
    db.commit()
    return lookup(db, actor, scope, key, body["operation"])
