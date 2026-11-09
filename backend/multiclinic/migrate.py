"""Explicit mapping backfill. An administrator runs this outside the web process."""

from datetime import datetime
import hashlib
import json
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator
import sqlalchemy as sa


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Organization(Strict):
    id: UUID
    name: str = Field(min_length=1, max_length=200)


class Clinic(Strict):
    id: UUID
    org_id: UUID
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    timezone: str = "Asia/Shanghai"

    @field_validator("timezone")
    @classmethod
    def timezone_valid(cls, value):
        ZoneInfo(value)
        return value


class Membership(Strict):
    id: UUID
    org_id: UUID
    user_id: int = Field(gt=0)


class Binding(Strict):
    id: UUID
    org_id: UUID
    membership_id: UUID
    clinic_id: UUID | None = None
    scope_kind: str
    role_code: str
    granted_by: int = Field(gt=0)
    valid_until: datetime | None = None

    @field_validator("valid_until")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("Role expiry requires an explicit timezone")
        return value


class Mapping(Strict):
    case_id: int = Field(gt=0)
    expected_owner_id: int = Field(gt=0)
    org_id: UUID
    clinic_id: UUID


class Manifest(Strict):
    migration_key: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    operator_user_id: int = Field(gt=0)
    reason: str = Field(min_length=1)
    organizations: list[Organization]
    clinics: list[Clinic]
    memberships: list[Membership]
    role_bindings: list[Binding]
    cases: list[Mapping]


def checksum(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _insert_once(conn, table, values):
    current = (
        conn.execute(sa.select(table).where(table.c.id == values["id"]))
        .mappings()
        .first()
    )
    if current:
        if any(current[key] != value for key, value in values.items()):
            raise ValueError(
                f"Existing {table.name} row differs from approved mapping: {values['id']}"
            )
        return
    conn.execute(table.insert().values(**values))


def backfill(engine, raw_manifest, *, apply=False, batch_size=200):
    manifest = Manifest.model_validate(raw_manifest)
    if batch_size < 1 or batch_size > 2000:
        raise ValueError("batch_size must be 1..2000")
    ids = [row.case_id for row in manifest.cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case mapping")
    if any(
        row.granted_by != manifest.operator_user_id for row in manifest.role_bindings
    ):
        raise ValueError("Binding grantor must be the recorded migration operator")
    mapping_hash = checksum(manifest.model_dump(mode="json"))
    meta = sa.MetaData()
    with engine.connect() as conn:
        if conn.dialect.name != "postgresql":
            raise ValueError("Backfill validation requires PostgreSQL")
        head = (
            conn.execute(sa.text("SELECT version_num FROM alembic_version"))
            .scalars()
            .all()
        )
        if head != ["mc01_scope_expand"]:
            raise ValueError(
                "Expected mc01_scope_expand; do not stamp or guess a different migration head"
            )
        meta.reflect(
            conn,
            only=[
                "organizations",
                "clinics",
                "org_memberships",
                "role_bindings",
                "users",
                "cases",
                "patients",
                "migration_batches",
                "access_audit_events",
            ],
        )
        conn.rollback()
        # Session advisory lock covers every batch; release even after validation failure.
        conn.execute(
            sa.text("SELECT pg_advisory_lock(hashtextextended(:key,0))"),
            {"key": manifest.migration_key},
        )
        conn.commit()
        try:
            batches = meta.tables["migration_batches"]
            prior = (
                conn.execute(
                    sa.select(batches).where(
                        batches.c.migration_key == manifest.migration_key
                    )
                )
                .mappings()
                .all()
            )
            if any(row["mapping_sha256"] != mapping_hash for row in prior):
                raise ValueError(
                    "Mapping changed for this migration key; resume only the exact approved manifest"
                )
            conn.rollback()
            with conn.begin():
                if not conn.execute(
                    sa.select(meta.tables["users"].c.id).where(
                        meta.tables["users"].c.id == manifest.operator_user_id
                    )
                ).first():
                    raise ValueError("Operator user does not exist")
                for name, rows in (
                    ("organizations", manifest.organizations),
                    ("clinics", manifest.clinics),
                    ("org_memberships", manifest.memberships),
                    ("role_bindings", manifest.role_bindings),
                ):
                    for row in rows:
                        _insert_once(conn, meta.tables[name], row.model_dump())
                # Validate all associations before any applied batch; roll back bootstrap on a bad manifest.
                for row in manifest.cases:
                    case = (
                        conn.execute(
                            sa.select(meta.tables["cases"]).where(
                                meta.tables["cases"].c.id == row.case_id
                            )
                        )
                        .mappings()
                        .first()
                    )
                    if not case or case["owner_id"] != row.expected_owner_id:
                        raise ValueError(f"Case owner mismatch: {row.case_id}")
                    clinic = conn.execute(
                        sa.select(meta.tables["clinics"].c.id).where(
                            meta.tables["clinics"].c.id == row.clinic_id,
                            meta.tables["clinics"].c.org_id == row.org_id,
                        )
                    ).first()
                    if not clinic:
                        raise ValueError(f"Clinic/org mismatch: {row.case_id}")
                    if case["org_id"] is not None and (
                        str(case["org_id"]) != str(row.org_id)
                        or str(case["clinic_id"]) != str(row.clinic_id)
                    ):
                        raise ValueError(
                            f"Refusing to move an already scoped case: {row.case_id}"
                        )
                if not prior:
                    for org_id in sorted(
                        {str(row.id) for row in manifest.organizations}
                    ):
                        conn.execute(
                            meta.tables["access_audit_events"]
                            .insert()
                            .values(
                                id=uuid4(),
                                org_id=UUID(org_id),
                                actor_id=manifest.operator_user_id,
                                request_key=checksum([mapping_hash, org_id]),
                                action="scope.bootstrap",
                                target_type="manifest",
                                target_id=mapping_hash,
                                before_permissions={},
                                after_permissions=manifest.model_dump(mode="json"),
                                reason=manifest.reason,
                            )
                        )
                    conn.execute(
                        batches.insert().values(
                            id=uuid4(),
                            migration_key=manifest.migration_key,
                            batch_no=0,
                            mapping_sha256=mapping_hash,
                            counts={"bootstrap": 1, "batch_size": batch_size},
                            content_checksums={},
                            status="committed",
                        )
                    )
                elif (
                    next(row for row in prior if row["batch_no"] == 0)["counts"][
                        "batch_size"
                    ]
                    != batch_size
                ):
                    raise ValueError("Resume must use the same batch size")
                if not apply:
                    conn.rollback()
            completed = {row["batch_no"] for row in prior}
            if apply:
                ordered = sorted(manifest.cases, key=lambda row: row.case_id)
                for start in range(0, len(ordered), batch_size):
                    number = start // batch_size + 1
                    if number in completed:
                        continue
                    with conn.begin():
                        digest = {}
                        for row in ordered[start : start + batch_size]:
                            cases = meta.tables["cases"]
                            current = dict(
                                conn.execute(
                                    sa.select(cases)
                                    .where(cases.c.id == row.case_id)
                                    .with_for_update()
                                )
                                .mappings()
                                .one()
                            )
                            if current["owner_id"] != row.expected_owner_id:
                                raise ValueError(
                                    f"Case changed during backfill: {row.case_id}"
                                )
                            if current["org_id"] is not None and (
                                str(current["org_id"]) != str(row.org_id)
                                or str(current["clinic_id"]) != str(row.clinic_id)
                            ):
                                raise ValueError(
                                    f"Scope changed during backfill: {row.case_id}"
                                )
                            if current["org_id"] is not None:
                                raise ValueError(
                                    f"Case already mapped without this batch checkpoint: {row.case_id}"
                                )
                            patient_id = uuid5(
                                NAMESPACE_URL,
                                f"pmai:{row.org_id}:legacy-case:{row.case_id}",
                            )
                            # Never merge animals by name or phone number.
                            _insert_once(
                                conn,
                                meta.tables["patients"],
                                dict(
                                    id=patient_id,
                                    org_id=row.org_id,
                                    patient_no=f"legacy-case-{row.case_id}",
                                    name=current["patient_name"],
                                    species=current["species"],
                                ),
                            )
                            preserve = {
                                key: value
                                for key, value in current.items()
                                if key not in ("org_id", "clinic_id", "patient_id")
                            }
                            conn.execute(
                                cases.update()
                                .where(cases.c.id == row.case_id)
                                .values(
                                    org_id=row.org_id,
                                    clinic_id=row.clinic_id,
                                    patient_id=patient_id,
                                )
                            )
                            after = dict(
                                conn.execute(
                                    sa.select(cases).where(cases.c.id == row.case_id)
                                )
                                .mappings()
                                .one()
                            )
                            if checksum(preserve) != checksum(
                                {key: after[key] for key in preserve}
                            ):
                                raise ValueError(
                                    "Backfill changed legacy clinical content"
                                )
                            digest[str(row.case_id)] = checksum(preserve)
                        conn.execute(
                            batches.insert().values(
                                id=uuid4(),
                                migration_key=manifest.migration_key,
                                batch_no=number,
                                last_entity_id=ordered[
                                    min(start + batch_size, len(ordered)) - 1
                                ].case_id,
                                mapping_sha256=mapping_hash,
                                counts={"cases": len(digest)},
                                content_checksums=digest,
                                status="committed",
                            )
                        )
            return {
                "applied": apply,
                "mapping_sha256": mapping_hash,
                "planned_cases": len(ids),
                "previous_batches": len(prior),
            }
        finally:
            conn.rollback()
            conn.execute(
                sa.text("SELECT pg_advisory_unlock(hashtextextended(:key,0))"),
                {"key": manifest.migration_key},
            )
            conn.commit()


def revoke_membership(engine, *, org_id, membership_id, actor_id, reason, request_key):
    if (
        not reason.strip()
        or len(request_key) != 64
        or any(c not in "0123456789abcdef" for c in request_key)
    ):
        raise ValueError(
            "Reason and a 64-character hexadecimal request key are required"
        )
    with engine.begin() as conn:
        org = conn.execute(
            sa.text(
                "SELECT id FROM organizations WHERE id=:org AND status='active' FOR UPDATE"
            ),
            {"org": str(UUID(org_id))},
        ).first()
        if not org:
            raise ValueError("Active organization not found")
        allowed = conn.execute(
            sa.text("""SELECT m.id FROM org_memberships m JOIN role_bindings b
          ON b.org_id=m.org_id AND b.membership_id=m.id JOIN users u ON u.id=m.user_id
          WHERE m.org_id=:org AND m.user_id=:actor AND m.status='active' AND u.status='active'
          AND u.principal_kind='human' AND b.role_code='org_admin' AND b.scope_kind='org'
          AND b.revoked_at IS NULL AND b.valid_from<=statement_timestamp()
          AND (b.valid_until IS NULL OR b.valid_until>statement_timestamp())"""),
            {"org": org_id, "actor": actor_id},
        ).first()
        if not allowed:
            raise ValueError("Actor is not an active organization administrator")
        prior = (
            conn.execute(
                sa.text(
                    "SELECT target_id,actor_id,reason,action FROM access_audit_events WHERE org_id=:org AND request_key=:key"
                ),
                {"org": org_id, "key": request_key},
            )
            .mappings()
            .first()
        )
        if prior:
            if dict(prior) != dict(
                target_id=str(UUID(membership_id)),
                actor_id=actor_id,
                reason=reason,
                action="membership.revoke",
            ):
                raise ValueError("Request key already used for a different command")
            return {"replayed": True}
        target = (
            conn.execute(
                sa.text(
                    "SELECT id,status FROM org_memberships WHERE org_id=:org AND id=:id FOR UPDATE"
                ),
                {"org": org_id, "id": str(UUID(membership_id))},
            )
            .mappings()
            .first()
        )
        if not target:
            raise ValueError("Member not found")
        conn.execute(
            sa.text(
                "UPDATE org_memberships SET status='revoked',authz_version=authz_version+1 WHERE id=:id"
            ),
            {"id": membership_id},
        )
        conn.execute(
            sa.text("UPDATE organizations SET authz_epoch=authz_epoch+1 WHERE id=:id"),
            {"id": org_id},
        )
        conn.execute(
            sa.text("""INSERT INTO access_audit_events(id,org_id,actor_id,request_key,action,target_type,target_id,before_permissions,after_permissions,reason)
          VALUES (:id,:org,:actor,:key,'membership.revoke','membership',:target,CAST(:before AS json),CAST(:after AS json),:reason)"""),
            {
                "id": str(uuid4()),
                "org": org_id,
                "actor": actor_id,
                "key": request_key,
                "target": membership_id,
                "before": json.dumps({"status": target["status"]}),
                "after": json.dumps({"status": "revoked"}),
                "reason": reason,
            },
        )
        return {"replayed": False}
