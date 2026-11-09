"""Treatment pilot API; the old dry-run endpoints remain unmodified and gated."""

from uuid import UUID
from fastapi import APIRouter, Depends, Header, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from multiclinic.api import get_db, principal, mode
from . import schemas as s, service as store


def enabled():
    if mode() != "treatment_pilot":
        from fastapi import HTTPException

        raise HTTPException(503, "Treatment pilot is not enabled")


router = APIRouter(
    prefix="/api/v2",
    tags=["treatment account attestation"],
    dependencies=[Depends(enabled)],
)
P = "/organizations/{org_id}/clinics/{clinic_id}/cases/{case_id}"


def scope(org_id, clinic_id, case_id):
    return {"org_id": str(org_id), "clinic_id": str(clinic_id), "case_id": case_id}


def call(db, fn, *args):
    try:
        result = fn(db, *args)
        status, body = result if isinstance(result, tuple) else (200, result)
        return JSONResponse(
            jsonable_encoder(body),
            status_code=status,
            headers={
                "Cache-Control": "no-store",
                **({"ETag": body["etag"]} if "etag" in body else {}),
            },
        )
    except store.Problem as exc:
        db.rollback()
        return JSONResponse(
            {"code": exc.code},
            status_code=exc.status,
            headers={"Cache-Control": "no-store"},
        )


@router.get(P + "/treatment")
def read(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(db, store.aggregate, actor, scope(org_id, clinic_id, case_id))


@router.post("/auth/reauthenticate")
def reauthenticate(
    body: s.Reauthenticate, actor=Depends(principal), db: Session = Depends(get_db)
):
    return call(db, store.challenge, actor, body.model_dump())


@router.get(P + "/treatment/signatures/{signature_id}")
def signature(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    signature_id: UUID,
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(
        db, store.signature, actor, scope(org_id, clinic_id, case_id), str(signature_id)
    )


@router.get(P + "/commands/{key}")
def lookup(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    key: str,
    operation: str,
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(
        db, store.lookup, actor, scope(org_id, clinic_id, case_id), key, operation
    )


@router.post(P + "/commands/{key}/cancel")
def cancel(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    key: str,
    body: s.Cancel,
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(
        db,
        store.cancel,
        actor,
        scope(org_id, clinic_id, case_id),
        key,
        body.model_dump(),
    )


@router.patch(P + "/treatment/draft")
def draft(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    body: s.Draft,
    idempotency_key: str = Header(default=""),
    if_match: str = Header(default=""),
    if_none_match: str = Header(default=""),
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    pre = (
        if_match
        if not if_none_match
        else "*" if if_none_match == "*" and not if_match else "invalid"
    )
    return call(
        db,
        store.execute,
        actor,
        scope(org_id, clinic_id, case_id),
        idempotency_key,
        "draft.save",
        "draft",
        pre,
        body.model_dump(),
    )


@router.post(P + "/treatment/revisions")
def freeze(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    body: s.Freeze,
    idempotency_key: str = Header(default=""),
    if_match: str = Header(default=""),
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(
        db,
        store.execute,
        actor,
        scope(org_id, clinic_id, case_id),
        idempotency_key,
        "revision.freeze",
        "revisions",
        if_match,
        body.model_dump(),
    )


@router.post(P + "/treatment/revisions/{revision_id}/reviews")
def review(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    revision_id: UUID,
    body: s.Review,
    idempotency_key: str = Header(default=""),
    if_match: str = Header(default=""),
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(
        db,
        store.execute,
        actor,
        scope(org_id, clinic_id, case_id),
        idempotency_key,
        "review",
        str(revision_id),
        if_match,
        body.model_dump(),
    )


@router.post(P + "/treatment/revisions/{revision_id}/signatures")
def sign(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    revision_id: UUID,
    body: s.Sign,
    idempotency_key: str = Header(default=""),
    if_match: str = Header(default=""),
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(
        db,
        store.execute,
        actor,
        scope(org_id, clinic_id, case_id),
        idempotency_key,
        "sign",
        str(revision_id),
        if_match,
        body.model_dump(),
    )


@router.post(P + "/treatment/amendments")
def amend(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    body: s.Amend,
    idempotency_key: str = Header(default=""),
    if_match: str = Header(default=""),
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(
        db,
        store.execute,
        actor,
        scope(org_id, clinic_id, case_id),
        idempotency_key,
        "amend",
        "amendments",
        if_match,
        body.model_dump(),
    )


@router.post(P + "/treatment/signatures/{signature_id}/revocations")
def revoke(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    signature_id: UUID,
    body: s.Revoke,
    idempotency_key: str = Header(default=""),
    if_match: str = Header(default=""),
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return call(
        db,
        store.execute,
        actor,
        scope(org_id, clinic_id, case_id),
        idempotency_key,
        "revoke",
        str(signature_id),
        if_match,
        body.model_dump(),
    )
