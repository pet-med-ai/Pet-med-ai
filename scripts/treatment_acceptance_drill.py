"""Independent pre/post migration backup and restore rehearsal on fresh clusters."""
import copy
import json
from pathlib import Path
import secrets
import time

from fastapi.testclient import TestClient
import sqlalchemy as sa

from treatment_acceptance_support import (
    Cluster, CONTENT, TEXT, backup, check, expand_and_seed, fingerprint,
    make_api, restore, seed_legacy, set_policy, source_change, write_json,
)


class Flow:
    def __init__(self, client, fixture, case=101, user=1):
        self.client, self.f, self.case, self.user = client, fixture, case, user
        self.scope = {"org_id": fixture["org"], "clinic_id": fixture["clinic"], "case_id": case}
        self.root = f'/api/v2/organizations/{fixture["org"]}/clinics/{fixture["clinic"]}/cases/{case}'
        account = next(a for a in fixture["accounts"] if a["id"] == user)
        response = client.post("/api/v2/auth/login", json={"email": account["email"], "password": fixture["password"]})
        check(response.status_code == 200, "Synthetic login: " + response.text)
        self.auth = {"Authorization": "Bearer " + response.json()["access_token"]}

    def get(self):
        r = self.client.get(self.root + "/treatment", headers=self.auth)
        check(r.status_code == 200, r.text)
        return r.json()

    def mutate(self, op, body, target=None, expected=201):
        g = self.get()
        suffix, method = {
            "draft.save": ("/draft", "PATCH"), "revision.freeze": ("/revisions", "POST"),
            "review": (f"/revisions/{target}/reviews", "POST"), "sign": (f"/revisions/{target}/signatures", "POST"),
            "amend": ("/amendments", "POST"), "revoke": (f"/signatures/{target}/revocations", "POST"),
        }[op]
        headers = {**self.auth, "Idempotency-Key": secrets.token_hex(32)}
        if op == "draft.save" and not g["draft"]:
            headers["If-None-Match"] = "*"
        else:
            headers["If-Match"] = g["draft_etag"] if op == "draft.save" else g["etag"]
        r = self.client.request(method, self.root + "/treatment" + suffix, headers=headers, json=body)
        check(r.status_code == expected, f"{op}: {r.status_code} {r.text}")
        return r.json()

    def freeze(self, content=None):
        self.mutate("draft.save", {"content": content or CONTENT})
        g = self.get()
        return self.mutate("revision.freeze", {"draft_version": g["draft"]["draft_version"], "expected_source_epoch": g["source_epoch"]})["revision_id"]

    def review(self, rid):
        return self.mutate("review", {"decision": "approve", "reason": "逐字核对合成原文"}, rid)["review_id"]

    def proof(self, rid, action="sign", signature=None):
        revision = next(r for r in self.get()["revisions"] if r["id"] == rid)
        r = self.client.post("/api/v2/auth/reauthenticate", headers=self.auth, json={**self.scope, "revision_id": rid, "content_hash": revision["content_sha256"], "action": action, "target_signature_id": signature, "password": self.f["password"]})
        check(r.status_code == 200, r.text)
        return r.json()["challenge_id"], revision["content_sha256"]

    def sign(self, rid, review, expected=201):
        proof, hash_value = self.proof(rid)
        return self.mutate("sign", {"review_id": review, "challenge_id": proof, "content_hash": hash_value}, rid, expected)


def exercise(cluster, fixture):
    owner = cluster.engine()
    runtime = cluster.url(user="pmai_treatment_runtime")
    app = make_api(runtime, secrets.token_urlsafe(48))
    with TestClient(app) as client:
        flow = Flow(client, fixture)
        rid = flow.freeze()
        first = flow.sign(rid, flow.review(rid))
        flow.mutate("amend", {"base_signature_id": first["signature_id"], "reason": "合成修订"})
        edited = copy.deepcopy(CONTENT)
        edited["assessment"] += "\n修订二"
        rid2 = flow.freeze(edited)
        second = flow.sign(rid2, flow.review(rid2))
        proof, _ = flow.proof(rid2, "revoke", second["signature_id"])
        flow.mutate("revoke", {"challenge_id": proof, "reason": "合成作废"}, second["signature_id"])
        check(flow.get()["draft"]["content"] == edited, "Revocation lost exact draft")
        rid3 = flow.freeze(edited)
        third = flow.sign(rid3, flow.review(rid3))
        # Query the original successful request under a NEW same-account session.
        relogged = Flow(client, fixture)
        recovered = client.get(flow.root + "/commands/" + third["idempotency_key"] + "?operation=sign", headers=relogged.auth)
        check(recovered.status_code == 201 and recovered.json() == third, "Original receipt recovery differs")
        check(len(relogged.get()["signatures"]) == 3, "Recovery duplicated signature")
        key = secrets.token_hex(32)
        cancelled = client.post(flow.root + "/commands/" + key + "/cancel", headers=relogged.auth, json={"operation": "draft.save", "request_hash": "a" * 64, "reason": "合成取消墓碑"})
        check(cancelled.status_code == 409 and cancelled.json()["state"] == "cancelled", cancelled.text)
        # A real diagnostic-report insertion must invalidate the older freeze.
        changed = Flow(client, fixture, case=108)
        old = changed.freeze()
        source_change(owner, 108)
        rejection = changed.mutate("review", {"decision": "approve", "reason": "旧来源不能通过"}, old, 409)
        check(rejection["code"] == "SOURCE_CHANGED", "Diagnostic source was not invalidated")
        set_policy(owner, fixture, "two_person")
        dual = Flow(client, fixture, case=107)
        dr = dual.freeze()
        review = dual.review(dr)
        rejected = dual.sign(dr, review, 409)
        check(rejected["code"] == "SECOND_CLINICIAN_REQUIRED", "Two-person rule not enforced")
        other = Flow(client, fixture, case=107, user=2)
        dual_signed = other.sign(dr, review)
        expected = [{"case": 101, "id": first["signature_id"], "state": "superseded", "content": CONTENT}, {"case": 101, "id": second["signature_id"], "state": "revoked", "content": edited}, {"case": 101, "id": third["signature_id"], "state": "effective", "content": edited}, {"case": 107, "id": dual_signed["signature_id"], "state": "effective", "content": CONTENT}]
        evidence = {"signatures": expected, "receipt": third, "cancel_key": key, "cancel_receipt": cancelled.json()}
    return evidence


def verify_restored(cluster, fixture, evidence):
    owner = cluster.engine()
    runtime_url = cluster.url(user="pmai_treatment_runtime")
    runtime = cluster.engine(user="pmai_treatment_runtime")
    app = make_api(runtime_url, secrets.token_urlsafe(48))
    with TestClient(app) as client:
        a = Flow(client, fixture)
        for entry in evidence["signatures"]:
            path = a.root.replace("/cases/101", f'/cases/{entry["case"]}') + "/treatment/signatures/" + entry["id"]
            response = client.get(path, headers=a.auth)
            check(response.status_code == 200, response.text)
            body = response.json()
            check(body["state"] == entry["state"] and body["revision"]["content"] == entry["content"], "Restored exact content/status mismatch")
            check(body["audit"]["target_id"] == entry["id"], "Restored audit binding mismatch")
        receipt = evidence["receipt"]
        r = client.get(a.root + "/commands/" + receipt["idempotency_key"] + "?operation=sign", headers=a.auth)
        check(r.json() == receipt, "Restored original request receipt differs")
        r = client.get(a.root + "/commands/" + evidence["cancel_key"] + "?operation=draft.save", headers=a.auth)
        check(r.json() == evidence["cancel_receipt"], "Cancellation tombstone not restored")
        for user in (4, 5, 6, 7):
            denied = Flow(client, fixture, user=user)
            check(client.get(denied.root + "/treatment", headers=denied.auth).status_code == 404, f"Restored clinical leak for user {user}")
        front = Flow(client, fixture, user=4)
        demographics = client.get(front.root + "?projection=demographics", headers=front.auth)
        check(demographics.status_code == 200 and "treatment" not in demographics.json(), "Restored frontdesk projection leaked")
        remote = Flow(client, fixture, user=6, case=102)
        check(not any(remote.get()["allowed_actions"].values()), "Restored cross-clinic grant is writable")
        legacy = Flow(client, fixture, case=104).get()
        check(not legacy["signatures"] and not legacy["reviews"] and legacy["revisions"][0]["origin"] == "legacy_import", "Unsigned import became signed")
        check(legacy["draft"]["content"]["treatment"]["management_text"] == TEXT, "Legacy UTF-8 text changed")
    with runtime.connect() as conn:
        check(conn.exec_driver_sql("SELECT count(*) FROM treatment_signatures").scalar() == 0, "Unset context bypassed RLS")
        conn.rollback()
        try:
            conn.exec_driver_sql("SELECT * FROM cases")
        except sa.exc.DBAPIError:
            conn.rollback()
        else:
            raise RuntimeError("Runtime can read raw legacy table")
    with owner.connect() as conn:
        for statement in ("UPDATE users SET status='invalid' WHERE id=1", "UPDATE cases SET visibility='invalid' WHERE id=101"):
            try:
                conn.exec_driver_sql(statement)
            except sa.exc.IntegrityError as exc:
                check(exc.orig.pgcode == "23514", "Expected CHECK constraint rejection")
                conn.rollback()
            else:
                conn.rollback()
                raise RuntimeError("Restored CHECK constraint not enforced")
        try:
            conn.exec_driver_sql("UPDATE treatment_signatures SET assurance=assurance")
        except sa.exc.DBAPIError:
            conn.rollback()
        else:
            conn.rollback()
            raise RuntimeError("Restored signature history is mutable")
    return {"independent_signature_readbacks": len(evidence["signatures"]), "exact_utf8_text": True, "original_receipt": True, "cancel_tombstone": True, "unsigned_import": True, "rls_and_roles": True, "immutable_history": True, "check_constraints_enforced": True}


def run_drill(state, pg_bin, candidate):
    state = Path(state)
    result = {"candidate": candidate, "synthetic_only": True, "manual_safari_result": "PENDING", "acceptance": "NOT_CLOSED", "status": "RUNNING", "cleanup": False}
    write_json(state / "drill-receipt.json", result)
    started = time.monotonic()
    try:
        with Cluster(state / "source", pg_bin) as source:
            fixture = seed_legacy(source)
            pre = fingerprint(source.engine())
            result["pre_migration_backup"] = backup(source, state / "before-migration.dump")
            with Cluster(state / "restore-pre", pg_bin, "pmai_restore_bootstrap") as target:
                restore(target, state / "before-migration.dump")
                check(fingerprint(target.engine()) == pre, "Pre-migration restore fingerprint differs")
                result["pre_migration_restore"] = {"fingerprint_match": True, "tables": len(pre["tables"]), "schema": "0009_diag_data"}
            result["migration"] = expand_and_seed(source, fixture)
            evidence = exercise(source, fixture)
            before = fingerprint(source.engine())
            result["post_migration_backup"] = backup(source, state / "after-signing.dump")
            with Cluster(state / "restore-post", pg_bin, "pmai_restore_bootstrap") as target:
                restore(target, state / "after-signing.dump")
                restored = fingerprint(target.engine())
                write_json(state / "source-fingerprint.json", before)
                write_json(state / "restored-fingerprint.json", restored)
                check(restored == before, "Post-signing restore fingerprint differs")
                result["post_migration_restore"] = {"fingerprint_match": True, "tables": len(before["tables"]), "schema": "mc02_treatment_store", "verification": verify_restored(target, fixture, evidence)}
            result["status"] = "PASS"
    except BaseException as exc:
        result["status"] = "FAILED"
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        result["cleanup"] = all(not (state / n).exists() for n in ("source", "restore-pre", "restore-post"))
        result["seconds"] = round(time.monotonic() - started, 2)
        write_json(state / "drill-receipt.json", result)
    return result
