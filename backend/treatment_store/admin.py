"""Offline, audited administration. Nothing runs on application startup."""

from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text
from .service import canonical, digest, insert, one


def check_target(conn):
    if conn.dialect.name != "postgresql":
        raise ValueError("Explicit PostgreSQL target required")
    if conn.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalars().all() != ["mc02_treatment_store"]:
        raise ValueError(
            "Expected mc02_treatment_store; never stamp an unknown database"
        )


def administrator(conn, org, actor):
    check_target(conn)
    if not one(
        conn,
        "SELECT id FROM organizations WHERE id=:o AND status='active' FOR UPDATE",
        o=org,
    ):
        raise ValueError("Organization unavailable")
    valid = one(
        conn,
        """SELECT m.id FROM org_memberships m JOIN users u ON u.id=m.user_id JOIN role_bindings b ON b.org_id=m.org_id AND b.membership_id=m.id
      WHERE m.org_id=:o AND m.user_id=:a AND m.status='active' AND u.status='active' AND u.principal_kind='human'
      AND b.scope_kind='org' AND b.role_code='org_admin' AND b.revoked_at IS NULL AND b.valid_from<=now()
      AND (b.valid_until IS NULL OR b.valid_until>now())""",
        o=org,
        a=actor,
    )
    if not valid:
        raise ValueError("Active organization administrator required")


def admin_audit(conn, org, actor, action, target, before, after, reason, key):
    if not reason.strip():
        raise ValueError("Reason required")
    old = one(
        conn,
        "SELECT * FROM access_audit_events WHERE org_id=:o AND request_key=:key",
        o=org,
        key=key,
    )
    if old:
        if (
            old["action"] != action
            or old["target_id"] != str(target)
            or old["after_permissions"] != after
            or old["actor_id"] != actor
            or old["reason"] != reason
        ):
            raise ValueError("Request key conflict")
        return False
    conn.execute(
        text(
            """INSERT INTO access_audit_events(id,org_id,actor_id,request_key,action,target_type,target_id,before_permissions,after_permissions,reason)
     VALUES (:id,:o,:a,:key,:action,'treatment_administration',:target,CAST(:before AS jsonb),CAST(:after AS jsonb),:reason)"""
        ),
        {
            "id": str(uuid4()),
            "o": org,
            "a": actor,
            "key": key,
            "action": action,
            "target": str(target),
            "before": json.dumps(before, default=str),
            "after": json.dumps(after, default=str),
            "reason": reason,
        },
    )
    return True


def configure(
    engine,
    *,
    org,
    actor,
    membership=None,
    name=None,
    credential=None,
    status="active",
    review_policy=None,
    assurance=None,
    reason,
    key,
    apply=False
):
    with engine.begin() as conn:
        administrator(conn, org, actor)
        if membership:
            member = one(
                conn,
                "SELECT * FROM org_memberships WHERE org_id=:o AND id=:m FOR UPDATE",
                o=org,
                m=membership,
            )
            if not member:
                raise ValueError("Membership is outside this organization")
            if not name or not credential:
                raise ValueError(
                    "Verified display name and credential reference required"
                )
            old = one(
                conn,
                "SELECT * FROM clinician_profiles WHERE org_id=:o AND membership_id=:m",
                o=org,
                m=membership,
            )
            after = {
                "membership_id": membership,
                "display_name": name,
                "credential_ref": credential,
                "status": status,
            }
            action = "clinician_profile.configure"
            target = membership
        else:
            if review_policy not in ("self_allowed", "two_person") or assurance not in (
                "account_attestation",
                "certificate_signature",
            ):
                raise ValueError("Unknown policy")
            old = one(conn, "SELECT * FROM organizations WHERE id=:o", o=org)
            after = {
                "review_policy": review_policy,
                "required_signing_assurance": assurance,
            }
            action = "signing_policy.configure"
            target = org
        if not apply:
            return {"dry_run": True, "action": action, "target": target, "after": after}
        if not admin_audit(conn, org, actor, action, target, old, after, reason, key):
            return {"replayed": True}
        if membership:
            conn.execute(
                text(
                    """INSERT INTO clinician_profiles(id,org_id,membership_id,display_name,credential_ref,status,verified_by)
             VALUES (:id,:o,:membership_id,:display_name,:credential_ref,:status,:a)
             ON CONFLICT(org_id,membership_id) DO UPDATE SET display_name=excluded.display_name,credential_ref=excluded.credential_ref,status=excluded.status,verified_by=excluded.verified_by,verified_at=now()"""
                ),
                {"id": str(uuid4()), "o": org, "a": actor, **after},
            )
        else:
            conn.execute(
                text(
                    "UPDATE organizations SET review_policy=:review_policy,required_signing_assurance=:required_signing_assurance WHERE id=:o"
                ),
                {"o": org, **after},
            )
        return {"applied": True, "action": action, "target": target}


def import_legacy(
    engine,
    *,
    org,
    clinic,
    case_id,
    actor,
    expected_sha256=None,
    key,
    reason,
    apply=False
):
    """One explicitly mapped case per transaction; safe to resume using the same key.

    Historical preview/review fields never become a clinical approval or signature.
    """
    with engine.begin() as conn:
        administrator(conn, org, actor)
        case = one(
            conn,
            "SELECT * FROM cases WHERE org_id=:o AND clinic_id=:c AND id=:i AND deleted_at IS NULL FOR UPDATE",
            o=org,
            c=clinic,
            i=case_id,
        )
        if not case:
            raise ValueError("Explicitly scoped case not found")
        original = {"treatment": case["treatment"], "analysis": case["analysis"]}
        checksum = digest(original)
        if not apply:
            return {
                "dry_run": True,
                "case_id": case_id,
                "source_sha256": checksum,
                "origin": "legacy_import",
                "signatures_created": 0,
            }
        if checksum != expected_sha256:
            raise ValueError("Source checksum changed; repeat dry run and review")
        old = one(
            conn,
            "SELECT * FROM access_audit_events WHERE org_id=:o AND request_key=:k",
            o=org,
            k=key,
        )
        after = {
            "source_sha256": checksum,
            "origin": "legacy_import",
            "signatures_created": 0,
        }
        if old:
            admin_audit(
                conn,
                org,
                actor,
                "treatment.legacy_import",
                case_id,
                None,
                after,
                reason,
                key,
            )
            return {"replayed": True, **after}
        if one(
            conn,
            "SELECT id FROM treatment_plans WHERE org_id=:o AND clinic_id=:c AND case_id=:i",
            o=org,
            c=clinic,
            i=case_id,
        ):
            raise ValueError("Treatment plan already exists; do not overwrite it")
        p, r = str(uuid4()), str(uuid4())
        now = datetime.now(timezone.utc)
        scope = {"org_id": org, "clinic_id": clinic, "case_id": case_id}
        content = {
            "schema": "treatment-content-v1",
            "diagnoses": [],
            "assessment": original["analysis"] or "",
            "treatment": {
                "goals": [],
                "management_text": original["treatment"] or "",
                "monitoring_text": "",
                "followup_text": "",
            },
            "linked_orders": [],
            "provenance": {
                "ai_generation_ids": [],
                "voice_transcript_revision_ids": [],
            },
        }
        source = {
            "legacy_case_id": case_id,
            "legacy_source_sha256": checksum,
            "original_fields": original,
            "trust": "unsigned_legacy_text",
        }
        envelope = {
            "schema": "pmai-treatment-revision-v1",
            "canonicalization": "pmai-canonical-json-v1",
            **scope,
            "plan_id": p,
            "revision_id": r,
            "draft_version": 1,
            "content": content,
            "source_manifest": source,
            "created_by": actor,
            "created_at": now.isoformat().replace("+00:00", "Z"),
        }
        insert(conn, "treatment_plans", {"id": p, **scope})
        insert(
            conn,
            "treatment_revisions",
            {
                "id": r,
                **scope,
                "plan_id": p,
                "revision_no": 1,
                "draft_version": 1,
                "schema_version": "treatment-content-v1",
                "content": content,
                "source_manifest": source,
                "canonical_bytes": canonical(envelope),
                "content_sha256": digest(envelope),
                "created_by": actor,
                "created_at": now,
                "origin": "legacy_import",
            },
        )
        insert(
            conn,
            "treatment_drafts",
            {
                **scope,
                "plan_id": p,
                "base_revision_id": r,
                "content": content,
                "draft_version": 1,
                "created_by": actor,
                "updated_by": actor,
            },
        )
        conn.execute(
            text("UPDATE treatment_plans SET head_revision_id=:r WHERE id=:p"),
            {"r": r, "p": p},
        )
        admin_audit(
            conn,
            org,
            actor,
            "treatment.legacy_import",
            case_id,
            None,
            after,
            reason,
            key,
        )
        return {"applied": True, "revision_id": r, **after}


def install_policy(engine):
    with engine.begin() as conn:
        check_target(conn)
        conn.exec_driver_sql(
            (Path(__file__).with_name("policy.sql")).read_text().replace("%", "%%")
        )
    return {"installed": True, "service_enabled": False}
