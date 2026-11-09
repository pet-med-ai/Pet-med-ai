"""Read-only pilot with a separate, least-privilege connection and v2 sessions."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import os
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v2", tags=["clinic read pilot"])
bearer = HTTPBearer(auto_error=False)
AUDIENCE = "pmai-clinic-read-v1"


def mode():
    return os.getenv("PMAI_MULTICLINIC_MODE", "off")


def secret():
    value = os.getenv("MULTICLINIC_TOKEN_SECRET", "")
    if len(value) < 32:
        raise HTTPException(503, "Clinic session signing key is not configured")
    return value


@lru_cache(maxsize=2)
def engine_for(url):
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql":
        raise HTTPException(503, "Clinic read pilot requires PostgreSQL")
    return create_engine(
        parsed.set(drivername="postgresql+psycopg2"),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
    )


def get_db():
    if mode() != "read_pilot":
        raise HTTPException(503, "Clinic read pilot is not enabled")
    url = os.getenv("MULTICLINIC_DATABASE_URL", "")
    if not url:
        raise HTTPException(503, "Clinic runtime database is not configured")
    with Session(engine_for(url)) as db:
        # Fail closed for accidentally supplied owner credentials or a partially installed policy.
        ready = db.execute(
            text("""SELECT current_user='pmai_scope_runtime'
          AND NOT r.rolsuper AND NOT r.rolbypassrls AND NOT r.rolcreaterole AND NOT r.rolinherit
          AND NOT r.rolcreatedb AND NOT r.rolreplication
          AND c.relrowsecurity AND c.relforcerowsecurity
          AND NOT has_any_column_privilege(current_user,'public.cases','SELECT')
          AND NOT has_database_privilege(current_user,current_database(),'CREATE')
          AND NOT has_schema_privilege(current_user,'public','CREATE')
          AND NOT EXISTS(SELECT FROM pg_database WHERE datname=current_database() AND datdba=r.oid)
          AND NOT EXISTS(SELECT FROM pg_class WHERE relowner=r.oid)
          AND NOT EXISTS(SELECT FROM pg_proc WHERE proowner=r.oid)
          AND NOT EXISTS(SELECT FROM pg_namespace WHERE nspowner=r.oid)
          AND NOT EXISTS(SELECT FROM pg_auth_members WHERE member=r.oid)
          FROM pg_roles r,pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE r.rolname=current_user AND n.nspname='public' AND c.relname='cases'""")
        ).scalar()
        if not ready:
            raise HTTPException(503, "Clinic runtime role or row policy is not ready")
        yield db
        # Read requests deliberately never commit; SET LOCAL cannot leak through the pool.


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


@router.post("/auth/login")
def login(body: Login, response: Response, db: Session = Depends(get_db)):
    key = secret()
    row = (
        db.execute(
            text("""SELECT id,hashed_password,token_version,status,principal_kind FROM users
                             WHERE email=:email"""),
            {"email": body.email.strip()},
        )
        .mappings()
        .first()
    )
    # Do not return a user/account-existence oracle. Bcrypt also handles a nonexistent account.
    digest = (
        row["hashed_password"]
        if row
        else "$2b$12$C6UzMDM.H6dfI/f/IKcEe.6f4ON2UXGj3nW2bWFgiWNeExFq2o6bS"
    )
    try:
        valid = bcrypt.verify(body.password, digest)
    except (ValueError, TypeError):
        valid = False
    if (
        not valid
        or not row
        or row["status"] != "active"
        or row["principal_kind"] != "human"
    ):
        raise HTTPException(401, "Incorrect credentials or inactive account")
    sid, now = str(uuid4()), datetime.now(timezone.utc)
    expires = now + timedelta(minutes=15)
    db.execute(
        text("""INSERT INTO auth_sessions(id,user_id,token_version,expires_at)
                       VALUES (:sid,:user,:tv,:expires)"""),
        {"sid": sid, "user": row["id"], "tv": row["token_version"], "expires": expires},
    )
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {
        "access_token": jwt.encode(
            {
                "sub": str(row["id"]),
                "sid": sid,
                "tv": row["token_version"],
                "ver": 2,
                "aud": AUDIENCE,
                "iss": AUDIENCE,
                "iat": now,
                "exp": expires,
            },
            key,
            algorithm="HS256",
        ),
        "token_type": "bearer",
        "expires_in": 900,
    }


def principal(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    try:
        if not credentials:
            raise ValueError()
        claims = jwt.decode(
            credentials.credentials,
            secret(),
            algorithms=["HS256"],
            audience=AUDIENCE,
            issuer=AUDIENCE,
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
        actor, sid = int(claims["sub"]), str(UUID(claims["sid"]))
        if claims.get("ver") != 2 or type(claims.get("tv")) is not int:
            raise ValueError()
    except (JWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "Session expired; log in again")
    row = db.execute(
        text("""SELECT s.id FROM auth_sessions s JOIN users u ON u.id=s.user_id
       WHERE s.id=:sid AND s.user_id=:actor AND s.token_version=:tv AND u.token_version=s.token_version
         AND s.revoked_at IS NULL AND s.expires_at>statement_timestamp()
         AND u.status='active' AND u.principal_kind='human'"""),
        {"sid": sid, "actor": actor, "tv": claims["tv"]},
    ).first()
    if not row:
        raise HTTPException(401, "Session expired; log in again")
    db.execute(
        text(
            "SELECT set_config('pmai.actor_id',:actor,true),set_config('pmai.session_id',:sid,true)"
        ),
        {"actor": str(actor), "sid": sid},
    )
    return {"id": actor, "sid": sid}


@router.post("/auth/logout", status_code=204)
def logout(actor=Depends(principal), db: Session = Depends(get_db)):
    db.execute(
        text("UPDATE auth_sessions SET revoked_at=statement_timestamp() WHERE id=:sid"),
        {"sid": actor["sid"]},
    )
    db.commit()
    return Response(status_code=204)


@router.get("/scopes")
def scopes(actor=Depends(principal), db: Session = Depends(get_db)):
    return {
        "items": [
            dict(row)
            for row in db.execute(
                text(
                    "SELECT * FROM pmai_scope.available_clinics() ORDER BY org_name,clinic_name,clinic_id"
                )
            ).mappings()
        ]
    }


def read_cases(db, org_id, clinic_id, projection, case_id=None, after=0, limit=50):
    if projection not in ("clinical", "demographics"):
        raise HTTPException(422, "Unknown projection")
    db.execute(
        text(
            "SELECT set_config('pmai.org_id',:org,true),set_config('pmai.clinic_id',:clinic,true)"
        ),
        {"org": str(org_id), "clinic": str(clinic_id)},
    )
    # View identifiers are closed constants, not interpolated caller input.
    view = "clinical_cases" if projection == "clinical" else "demographic_cases"
    condition = "id=:case_id" if case_id is not None else "id>:after"
    rows = (
        db.execute(
            text(
                f"SELECT * FROM pmai_scope.{view} WHERE org_id=:org AND clinic_id=:clinic AND {condition} ORDER BY id LIMIT :limit"
            ),
            {
                "org": str(org_id),
                "clinic": str(clinic_id),
                "case_id": case_id,
                "after": after,
                "limit": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    if case_id is not None:
        if not rows:
            raise HTTPException(404, "Case not found")
        return dict(rows[0])
    return {
        "items": [dict(row) for row in rows[:limit]],
        "next_after": rows[limit - 1]["id"] if len(rows) > limit else None,
    }


@router.get("/organizations/{org_id}/clinics/{clinic_id}/cases")
def case_list(
    org_id: UUID,
    clinic_id: UUID,
    projection: str = "clinical",
    after: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return read_cases(db, org_id, clinic_id, projection, after=after, limit=limit)


@router.get("/organizations/{org_id}/clinics/{clinic_id}/cases/{case_id}")
def case_detail(
    org_id: UUID,
    clinic_id: UUID,
    case_id: int,
    projection: str = "clinical",
    actor=Depends(principal),
    db: Session = Depends(get_db),
):
    return read_cases(db, org_id, clinic_id, projection, case_id=case_id)
