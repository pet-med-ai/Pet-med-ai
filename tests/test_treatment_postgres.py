"""Real PostgreSQL/API acceptance for the opt-in treatment store."""

import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from jose import jwt
import test_multiclinic_postgres as fixture
from test_multiclinic_postgres import ADMIN, KEY, ROOT
from treatment_store import api as treatment_api, service as store
from multiclinic import api

CONTENT = {
    "schema": "treatment-content-v1",
    "diagnoses": [{"label": "Synthetic diagnosis", "code_system": None, "code": None}],
    "assessment": "合成验收 café 🐾\n原文 {{literal}}; literal \\n remains",
    "treatment": {
        "goals": ["仅软件测试"],
        "management_text": "医生输入的合成治疗文本",
        "monitoring_text": "",
        "followup_text": "",
    },
    "linked_orders": [],
    "provenance": {"ai_generation_ids": [], "voice_transcript_revision_ids": []},
}


@unittest.skipUnless(ADMIN, "requires disposable PostgreSQL")
class TreatmentPostgresTests(unittest.TestCase):
    auth = fixture.ClinicPostgresTests.auth
    url = fixture.ClinicPostgresTests.url

    @classmethod
    def setUpClass(cls):
        fixture.ClinicPostgresTests.setUpClass.__func__(cls)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "alembic.ini",
                "upgrade",
                "mc02_treatment_store",
            ],
            cwd=ROOT / "backend",
            env={**os.environ, "DATABASE_URL": cls.admin_url},
            check=True,
            text=True,
        )
        with cls.owner.begin() as conn:
            conn.exec_driver_sql(
                (ROOT / "backend/treatment_store/policy.sql")
                .read_text()
                .replace("%", "%%")
            )
            for u in (1, 2, 7):
                conn.execute(
                    sa.text(
                        "INSERT INTO clinician_profiles(id,org_id,membership_id,display_name,credential_ref,status,verified_by) VALUES (:id,:o,:m,:name,'synthetic-credential','active',9)"
                    ),
                    {
                        "id": str(uuid4()),
                        "o": cls.o2 if u == 7 else cls.o1,
                        "m": cls.members[u],
                        "name": f"合成医生 {u}",
                    },
                )
            password = make_url(ADMIN).password
            if password:
                conn.execute(
                    sa.text("ALTER ROLE pmai_treatment_runtime PASSWORD :password"),
                    {"password": password},
                )
        cls.env.stop()
        cls.runtime.dispose()
        cls.runtime_url = (
            make_url(cls.admin_url)
            .set(username="pmai_treatment_runtime")
            .render_as_string(hide_password=False)
        )
        cls.runtime = sa.create_engine(cls.runtime_url)
        cls.env = patch.dict(
            os.environ,
            PMAI_MULTICLINIC_MODE="treatment_pilot",
            MULTICLINIC_DATABASE_URL=cls.runtime_url,
            MULTICLINIC_TOKEN_SECRET=KEY,
        )
        cls.env.start()
        cls.app.include_router(treatment_api.router)
        cls.next_case = 100

    @classmethod
    def tearDownClass(cls):
        fixture.ClinicPostgresTests.tearDownClass.__func__(cls)

    def setUp(self):
        fixture.ClinicPostgresTests.setUp(self)
        type(self).next_case += 1
        self.case = type(self).next_case
        with self.owner.begin() as conn:
            conn.exec_driver_sql("UPDATE clinician_profiles SET status='active'")
            conn.execute(
                sa.text(
                    "DELETE FROM role_bindings WHERE membership_id=:m AND clinic_id=:c"
                ),
                {"m": self.members[2], "c": self.c1},
            )
            conn.exec_driver_sql(
                "UPDATE organizations SET review_policy='self_allowed',required_signing_assurance='account_attestation'"
            )
            conn.execute(
                sa.text(
                    "INSERT INTO cases(id,owner_id,org_id,clinic_id,visibility,patient_name,species,chief_complaint,created_at) VALUES (:id,1,:o,:c,'clinic','合成犬','dog','合成验收',now())"
                ),
                {"id": self.case, "o": self.o1, "c": self.c1},
            )
        self.headers = self.auth()
        self.root = self.url(self.case)
        self.scope = {"org_id": self.o1, "clinic_id": self.c1, "case_id": self.case}

    def get(self, headers=None):
        r = self.client.get(self.root + "/treatment", headers=headers or self.headers)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def mutation(self, op, body, *, headers=None, key=None, pre=None, target=None):
        a = headers or self.headers
        g = self.get(a)
        suffix, method = {
            "draft.save": ("/draft", "patch"),
            "revision.freeze": ("/revisions", "post"),
            "review": (f"/revisions/{target}/reviews", "post"),
            "sign": (f"/revisions/{target}/signatures", "post"),
            "amend": ("/amendments", "post"),
            "revoke": (f"/signatures/{target}/revocations", "post"),
        }[op]
        h = {**a, "Idempotency-Key": key or uuid4().hex + uuid4().hex}
        if op == "draft.save" and not g["draft"]:
            h["If-None-Match"] = pre or "*"
        else:
            h["If-Match"] = pre or (
                g["draft_etag"] if op == "draft.save" else g["etag"]
            )
        return getattr(self.client, method)(
            self.root + "/treatment" + suffix, headers=h, json=body
        )

    def freeze(self, headers=None):
        r = self.mutation(
            "draft.save", {"content": copy.deepcopy(CONTENT)}, headers=headers
        )
        self.assertEqual(r.status_code, 201, r.text)
        g = self.get(headers)
        r = self.mutation(
            "revision.freeze",
            {
                "draft_version": g["draft"]["draft_version"],
                "expected_source_epoch": g["source_epoch"],
            },
            headers=headers,
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["revision_id"]

    def review(self, rid, headers=None):
        r = self.mutation(
            "review",
            {"decision": "approve", "reason": "已逐项核对合成记录"},
            target=rid,
            headers=headers,
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["review_id"]

    def challenge(self, rid, action="sign", sid=None, headers=None):
        g = self.get(headers)
        revision = next(r for r in g["revisions"] if r["id"] == rid)
        r = self.client.post(
            "/api/v2/auth/reauthenticate",
            headers=headers or self.headers,
            json={
                **self.scope,
                "revision_id": rid,
                "content_hash": revision["content_sha256"],
                "action": action,
                "target_signature_id": sid,
                "password": self.password,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["challenge_id"]

    def sign(self, rid, review, headers=None):
        g = self.get(headers)
        ch = self.challenge(rid, headers=headers)
        r = self.mutation(
            "sign",
            {
                "review_id": review,
                "content_hash": g["revisions"][0]["content_sha256"],
                "challenge_id": ch,
            },
            target=rid,
            headers=headers,
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["signature_id"]

    def test_01_roundtrip_immutable_signature_and_audit(self):
        rid = self.freeze()
        review = self.review(rid)
        sid = self.sign(rid, review)
        r = self.client.get(
            self.root + "/treatment/signatures/" + sid, headers=self.headers
        )
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertEqual(out["revision"]["content"], CONTENT)
        self.assertEqual(out["state"], "effective")
        self.assertEqual(out["audit"]["target_id"], sid)
        self.assertEqual(out["signature"]["assurance"], "account_attestation")
        self.assertEqual(
            store.sha256(out["revision"]["canonical_utf8"].encode()).hexdigest(),
            out["signature"]["content_hash"],
        )
        with self.assertRaises(sa.exc.DBAPIError), self.owner.begin() as conn:
            conn.execute(
                sa.text("DELETE FROM treatment_signatures WHERE id=:id"), {"id": sid}
            )
        with self.assertRaises(sa.exc.DBAPIError), self.owner.begin() as conn:
            conn.execute(sa.text("DELETE FROM cases WHERE id=:id"), {"id": self.case})

    def test_02_roles_scope_and_unported_workflows(self):
        for user in (2, 3, 4, 5, 6, 7, 9):
            a = self.auth(user)
            self.assertEqual(
                self.client.get(self.root + "/treatment", headers=a).status_code, 404
            )
        assistant = self.auth(8)
        rid = self.freeze(assistant)
        r = self.mutation(
            "review",
            {"decision": "approve", "reason": "test"},
            target=rid,
            headers=assistant,
        )
        self.assertEqual(r.status_code, 403, r.text)
        self.assertEqual(
            self.client.post("/api/cases", headers=self.headers, json={}).status_code,
            409,
        )
        with self.runtime.connect() as conn:
            for table in ("cases", "clinician_profiles", "diagnostic_reports"):
                with self.assertRaises(sa.exc.DBAPIError):
                    conn.exec_driver_sql("SELECT * FROM " + table)
                conn.rollback()
            self.assertEqual(
                conn.exec_driver_sql(
                    "SELECT count(*) FROM treatment_revisions"
                ).scalar(),
                0,
            )

    def test_03_duplicate_conflict_response_loss_recovery(self):
        key = uuid4().hex + uuid4().hex
        body = {"content": CONTENT}
        r = self.mutation("draft.save", body, key=key)
        self.assertEqual(r.status_code, 201, r.text)
        old = r.json()
        # Replay the ORIGINAL precondition, not a new version/key.
        headers = {**self.headers, "Idempotency-Key": key, "If-None-Match": "*"}
        repeat = self.client.patch(
            self.root + "/treatment/draft", headers=headers, json=body
        )
        self.assertEqual(repeat.json(), old)
        changed = copy.deepcopy(body)
        changed["content"]["assessment"] = "changed"
        self.assertEqual(
            self.client.patch(
                self.root + "/treatment/draft", headers=headers, json=changed
            ).status_code,
            409,
        )
        lookup = self.client.get(
            self.root + "/commands/" + key + "?operation=draft.save",
            headers=self.headers,
        )
        self.assertEqual(lookup.json(), old)
        self.assertEqual(self.get()["draft"]["draft_version"], 1)

    def test_04_source_changed_and_version_conflicts(self):
        rid = self.freeze()
        old = self.get()
        with self.owner.begin() as conn:
            conn.execute(
                sa.text("UPDATE cases SET history='changed' WHERE id=:id"),
                {"id": self.case},
            )
        r = self.mutation(
            "review", {"decision": "approve", "reason": "check"}, target=rid
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["code"], "SOURCE_CHANGED")
        r = self.mutation("draft.save", {"content": CONTENT}, pre='"draft:999"')
        self.assertEqual(r.status_code, 412)
        self.assertEqual(len(self.get()["reviews"]), 0)

    def test_05_reauth_session_hash_profile_and_certificate_policy(self):
        rid = self.freeze()
        review = self.review(rid)
        ch = self.challenge(rid)
        g = self.get()
        a = self.auth()  # Another session for the same actor cannot consume old proof.
        r = self.mutation(
            "sign",
            {
                "review_id": review,
                "content_hash": g["revisions"][0]["content_sha256"],
                "challenge_id": ch,
            },
            target=rid,
            headers=a,
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["code"], "CHALLENGE_INVALID")
        with self.owner.begin() as conn:
            conn.execute(
                sa.text(
                    "UPDATE organizations SET required_signing_assurance='certificate_signature',signing_policy_version=2 WHERE id=:id"
                ),
                {"id": self.o1},
            )
        r = self.mutation(
            "sign",
            {
                "review_id": review,
                "content_hash": g["revisions"][0]["content_sha256"],
                "challenge_id": ch,
            },
            target=rid,
        )
        self.assertEqual(r.json()["code"], "ASSURANCE_UNAVAILABLE")
        self.assertEqual(self.get()["signatures"], [])

    def test_06_amend_supersede_revoke_retains_history(self):
        rid = self.freeze()
        sid = self.sign(rid, self.review(rid))
        r = self.mutation("amend", {"base_signature_id": sid, "reason": "修订合成记录"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.get()["plan"]["active_signature_id"], sid)
        rid2 = self.freeze()
        sid2 = self.sign(rid2, self.review(rid2))
        self.assertEqual(
            self.client.get(
                self.root + "/treatment/signatures/" + sid, headers=self.headers
            ).json()["state"],
            "superseded",
        )
        ch = self.challenge(rid2, "revoke", sid2)
        r = self.mutation(
            "revoke", {"challenge_id": ch, "reason": "合成记录作废"}, target=sid2
        )
        self.assertEqual(r.status_code, 201, r.text)
        g = self.get()
        self.assertIsNone(g["plan"]["active_signature_id"])
        self.assertEqual(len(g["signatures"]), 2)
        self.assertEqual(
            self.client.get(
                self.root + "/treatment/signatures/" + sid2, headers=self.headers
            ).json()["state"],
            "revoked",
        )
        # A revoked amendment must not permanently strand the treatment plan.
        self.assertIsNone(g["draft"]["amendment_of"])
        self.assertEqual(g["draft"]["content"], CONTENT)
        rid3 = self.freeze()
        sid3 = self.sign(rid3, self.review(rid3))
        g = self.get()
        self.assertEqual(g["plan"]["active_signature_id"], sid3)
        self.assertEqual(len(g["signatures"]), 3)
        self.assertEqual(len(g["events"]), 2)

    def test_07_cancel_before_request_fences_late_worker(self):
        key = uuid4().hex + uuid4().hex
        body = {"content": CONTENT}
        h = store.command_hash({"id": 1}, self.scope, "draft.save", "draft", "*", body)
        r = self.client.post(
            self.root + "/commands/" + key + "/cancel",
            headers=self.headers,
            json={"operation": "draft.save", "request_hash": h, "reason": "停止原请求"},
        )
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(r.json()["state"], "cancelled")
        r = self.mutation("draft.save", body, key=key)
        self.assertEqual(r.json()["state"], "cancelled")
        self.assertIsNone(self.get()["draft"])

    def test_08_failed_atomic_signature_leaves_queryable_receipt(self):
        rid = self.freeze()
        review = self.review(rid)
        ch = self.challenge(rid)
        g = self.get()
        key = uuid4().hex + uuid4().hex
        original = store.insert

        def failing(db, table, data):
            if table == "treatment_signatures":
                raise RuntimeError("synthetic DB failure")
            return original(db, table, data)

        with patch.object(store, "insert", side_effect=failing), self.assertRaises(
            RuntimeError
        ):
            self.mutation(
                "sign",
                {
                    "review_id": review,
                    "content_hash": g["revisions"][0]["content_sha256"],
                    "challenge_id": ch,
                },
                target=rid,
                key=key,
            )
        r = self.client.get(
            self.root + "/commands/" + key + "?operation=sign", headers=self.headers
        )
        self.assertEqual(r.status_code, 202, r.text)
        self.assertEqual(r.json()["state"], "pending")
        g = self.get()
        self.assertEqual(g["signatures"], [])
        with self.owner.connect() as conn:
            self.assertEqual(
                conn.execute(
                    sa.text(
                        "SELECT count(*) FROM clinical_audit_events WHERE case_id=:id AND action='sign'"
                    ),
                    {"id": self.case},
                ).scalar(),
                0,
            )
            self.assertIsNone(
                conn.execute(
                    sa.text(
                        "SELECT consumed_by_command FROM signing_challenges WHERE id=:id"
                    ),
                    {"id": ch},
                ).scalar()
            )

    def test_09_two_person_requires_distinct_clinician(self):
        with self.owner.begin() as conn:
            conn.execute(
                sa.text(
                    "UPDATE organizations SET review_policy='two_person',signing_policy_version=2 WHERE id=:o"
                ),
                {"o": self.o1},
            )
            conn.execute(
                sa.text(
                    "INSERT INTO role_bindings(id,org_id,membership_id,scope_kind,clinic_id,role_code,granted_by) VALUES (:id,:o,:m,'clinic',:c,'veterinarian',9)"
                ),
                {"id": str(uuid4()), "o": self.o1, "m": self.members[2], "c": self.c1},
            )
        rid = self.freeze()
        review = self.review(rid)
        ch = self.challenge(rid)
        g = self.get()
        r = self.mutation(
            "sign",
            {
                "review_id": review,
                "content_hash": g["revisions"][0]["content_sha256"],
                "challenge_id": ch,
            },
            target=rid,
        )
        self.assertEqual(r.json()["code"], "SECOND_CLINICIAN_REQUIRED")
        sid = self.sign(rid, review, headers=self.auth(2))
        self.assertTrue(sid)

    def test_10_payload_provenance_and_identity_are_not_client_assertions(self):
        content = copy.deepcopy(CONTENT)
        content["provenance"]["ai_generation_ids"] = ["unported"]
        self.assertEqual(
            self.mutation("draft.save", {"content": content}).status_code, 422
        )
        content = copy.deepcopy(CONTENT)
        content["signer_id"] = 1
        self.assertEqual(
            self.mutation("draft.save", {"content": content}).status_code, 422
        )
        self.assertIsNone(self.get()["draft"])

    def test_11_concurrent_duplicate_only_one_command_and_revision(self):
        self.mutation("draft.save", {"content": CONTENT})
        g = self.get()
        body = {"draft_version": 1, "expected_source_epoch": g["source_epoch"]}
        key = uuid4().hex + uuid4().hex
        h = {**self.headers, "Idempotency-Key": key, "If-Match": g["etag"]}

        def request():
            return self.client.post(
                self.root + "/treatment/revisions", headers=h, json=body
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: request(), range(2)))
        self.assertTrue(
            all(r.status_code in (201, 202) for r in responses),
            [r.text for r in responses],
        )
        result = self.client.get(
            self.root + "/commands/" + key + "?operation=revision.freeze",
            headers=self.headers,
        )
        self.assertEqual(result.json()["state"], "committed")
        self.assertEqual(len(self.get()["revisions"]), 1)

    def test_12_expired_pending_cannot_commit_after_cancel(self):
        rid = self.freeze()
        review = self.review(rid)
        ch = self.challenge(rid)
        g = self.get()
        key = uuid4().hex + uuid4().hex
        body = {
            "review_id": review,
            "content_hash": g["revisions"][0]["content_sha256"],
            "challenge_id": ch,
        }
        pre = g["etag"]
        original = store.perform
        with patch.object(
            store,
            "perform",
            side_effect=RuntimeError("synthetic crash after reservation"),
        ), self.assertRaises(RuntimeError):
            self.mutation("sign", body, target=rid, key=key)
        pending = self.client.get(
            self.root + "/commands/" + key + "?operation=sign", headers=self.headers
        ).json()
        cancelled = self.client.post(
            self.root + "/commands/" + key + "/cancel",
            headers=self.headers,
            json={
                "operation": "sign",
                "request_hash": pending["request_hash"],
                "reason": "cancel hung worker",
            },
        )
        self.assertEqual(cancelled.json()["state"], "cancelled")
        claims = jwt.get_unverified_claims(self.headers["Authorization"].split()[1])
        actor = {"id": 1, "sid": claims["sid"]}
        with sa.orm.Session(self.runtime) as db:
            status, result = original(
                db,
                actor,
                self.scope,
                key,
                "sign",
                rid,
                pre,
                body,
                pending["request_hash"],
            )
        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(self.get()["signatures"], [])

    def test_13_explicit_read_grant_does_not_allow_drafts(self):
        with self.owner.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO case_access_grants(id,org_id,clinic_id,case_id,grantee_membership_id,permission,expires_at,granted_by,reason) VALUES (:id,:o,:c,:i,:m,'clinical.read',now()+interval '1 hour',9,'synthetic grant')"
                ),
                {
                    "id": str(uuid4()),
                    "o": self.o1,
                    "c": self.c1,
                    "i": self.case,
                    "m": self.members[2],
                },
            )
        a = self.auth(2)
        g = self.get(a)
        self.assertFalse(g["allowed_actions"]["edit"])
        self.assertEqual(
            self.mutation("draft.save", {"content": CONTENT}, headers=a).status_code,
            403,
        )

    def test_14_legacy_import_is_unsigned_audited_resumable_and_exact(self):
        from treatment_store.admin import import_legacy

        with self.owner.begin() as conn:
            conn.execute(
                sa.text("UPDATE cases SET treatment=:t,analysis=:a WHERE id=:id"),
                {
                    "id": self.case,
                    "t": CONTENT["assessment"],
                    "a": "historical analysis",
                },
            )
        args = {
            "org": self.o1,
            "clinic": self.c1,
            "case_id": self.case,
            "actor": 9,
            "key": uuid4().hex,
            "reason": "synthetic migration",
        }
        dry = import_legacy(self.owner, **args)
        self.assertIsNone(self.get()["plan"])
        result = import_legacy(
            self.owner, **args, apply=True, expected_sha256=dry["source_sha256"]
        )
        self.assertTrue(
            import_legacy(
                self.owner, **args, apply=True, expected_sha256=dry["source_sha256"]
            )["replayed"]
        )
        g = self.get()
        self.assertEqual(
            g["draft"]["content"]["treatment"]["management_text"], CONTENT["assessment"]
        )
        self.assertEqual(g["signatures"], [])
        r = self.mutation(
            "review",
            {"decision": "approve", "reason": "test"},
            target=result["revision_id"],
        )
        self.assertEqual(r.json()["code"], "LEGACY_UNSIGNED")

    def test_15_policy_install_repeat_and_reviewer_revocation(self):
        from treatment_store.admin import install_policy, configure

        install_policy(self.owner)
        rid = self.freeze()
        self.review(rid)
        configure(
            self.owner,
            org=self.o1,
            actor=9,
            membership=self.members[1],
            name="合成医生 1",
            credential="synthetic-credential",
            status="revoked",
            reason="synthetic revocation",
            key=uuid4().hex,
            apply=True,
        )
        self.assertFalse(self.get()["allowed_actions"]["sign"])
        r = self.client.post(
            "/api/v2/auth/reauthenticate",
            headers=self.headers,
            json={
                **self.scope,
                "revision_id": rid,
                "content_hash": self.get()["revisions"][0]["content_sha256"],
                "action": "sign",
                "target_signature_id": None,
                "password": self.password,
            },
        )
        self.assertEqual(r.status_code, 403)

    def test_16_saved_draft_change_invalidates_old_review_and_challenge(self):
        rid = self.freeze()
        review = self.review(rid)
        ch = self.challenge(rid)
        h = self.get()["revisions"][0]["content_sha256"]
        changed = copy.deepcopy(CONTENT)
        changed["assessment"] = "changed after review"
        self.assertEqual(
            self.mutation("draft.save", {"content": changed}).status_code, 201
        )
        r = self.mutation(
            "sign",
            {"review_id": review, "content_hash": h, "challenge_id": ch},
            target=rid,
        )
        self.assertEqual(r.json()["code"], "DRAFT_CHANGED")
        self.assertEqual(self.get()["signatures"], [])

    def test_17_diagnostic_source_change_invalidates_review(self):
        rid = self.freeze()
        previous = self.get()["source_epoch"]
        with self.owner.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO diagnostic_reports(case_id,report_type,source_type,status,ai_summary_status,title,created_at) VALUES (:id,'lab','manual','final','not_run','synthetic added report',now())"
                ),
                {"id": self.case},
            )
        self.assertGreater(self.get()["source_epoch"], previous)
        r = self.mutation(
            "review", {"decision": "approve", "reason": "check"}, target=rid
        )
        self.assertEqual(r.json()["code"], "SOURCE_CHANGED")

    def test_18_active_signature_pointer_cannot_be_silently_removed(self):
        rid = self.freeze()
        sid = self.sign(rid, self.review(rid))
        with self.assertRaises(sa.exc.DBAPIError), self.owner.begin() as conn:
            conn.execute(
                sa.text(
                    "UPDATE treatment_plans SET active_signature_id=NULL WHERE case_id=:id"
                ),
                {"id": self.case},
            )
        self.assertEqual(self.get()["plan"]["active_signature_id"], sid)

    def test_19_revocation_keeps_open_draft_but_invalidates_its_old_approval(self):
        rid = self.freeze()
        sid = self.sign(rid, self.review(rid))
        r = self.mutation("amend", {"base_signature_id": sid, "reason": "new draft"})
        self.assertEqual(r.status_code, 201, r.text)
        content = copy.deepcopy(CONTENT)
        content["assessment"] = "保留未签署修订的原文 café 🐾\n{{literal}}"
        r = self.mutation("draft.save", {"content": content})
        self.assertEqual(r.status_code, 201, r.text)
        before = self.get()
        r = self.mutation("revision.freeze", {
            "draft_version": before["draft"]["draft_version"],
            "expected_source_epoch": before["source_epoch"],
        })
        self.assertEqual(r.status_code, 201, r.text)
        pending_revision = r.json()["revision_id"]
        approval = self.review(pending_revision)
        proof = self.challenge(pending_revision)
        old_hash = self.get()["revisions"][0]["content_sha256"]
        revoke_proof = self.challenge(rid, "revoke", sid)
        r = self.mutation("revoke", {
            "challenge_id": revoke_proof, "reason": "撤回当前签署，保留新草稿"
        }, target=sid)
        self.assertEqual(r.status_code, 201, r.text)
        after = self.get()
        self.assertEqual(after["draft"]["content"], content)
        self.assertIsNone(after["draft"]["amendment_of"])
        self.assertEqual(after["draft"]["draft_version"], before["draft"]["draft_version"] + 1)
        self.assertIsNone(after["plan"]["active_signature_id"])
        r = self.mutation("sign", {
            "review_id": approval, "content_hash": old_hash, "challenge_id": proof,
        }, target=pending_revision)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(r.json()["code"], "DRAFT_CHANGED")
        r = self.mutation("revision.freeze", {
            "draft_version": after["draft"]["draft_version"],
            "expected_source_epoch": after["source_epoch"],
        })
        self.assertEqual(r.status_code, 201, r.text)
        fresh_revision = r.json()["revision_id"]
        fresh_signature = self.sign(fresh_revision, self.review(fresh_revision))
        self.assertEqual(self.get()["plan"]["active_signature_id"], fresh_signature)
        self.assertEqual(self.get()["draft"]["content"], content)
