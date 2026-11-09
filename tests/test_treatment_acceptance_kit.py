"""Boundary checks for the fresh-target acceptance tooling (not old PR72 replay)."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from treatment_acceptance import Controls, hosted_app
import treatment_acceptance_support as support
from treatment_acceptance_drill import Flow


class BoundaryTests(unittest.TestCase):
    def test_inherited_connections_and_tokens_are_not_used(self):
        with patch.dict(os.environ, DATABASE_URL="forbidden", MULTICLINIC_DATABASE_URL="forbidden", PGSERVICE="forbidden", PGPASSWORD="forbidden", MULTICLINIC_TOKEN_SECRET="forbidden"):
            env = support.clean_env()
            self.assertTrue(all(k not in env for k in ("DATABASE_URL", "MULTICLINIC_DATABASE_URL", "PGSERVICE", "PGPASSWORD", "MULTICLINIC_TOKEN_SECRET")))

    def test_existing_directory_is_never_initialized_or_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "existing"
            path.mkdir()
            sentinel = path / "retain.txt"
            sentinel.write_text("retain")
            with self.assertRaises(FileExistsError):
                support.Cluster(path, "/not-a-toolchain").__enter__()
            self.assertEqual(sentinel.read_text(), "retain")

    def test_modified_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "runtime.py").write_text("original")
            manifest = {"commit": "a" * 40, "tree": "b" * 40, "files": {"runtime.py": hashlib.sha256(b"original").hexdigest()}}
            (path / "acceptance-manifest.json").write_text(json.dumps(manifest))
            with patch.object(support, "ROOT", path):
                self.assertEqual(support.identity()["packaged_files_verified"], 1)
                (path / "runtime.py").write_text("changed")
                with self.assertRaisesRegex(RuntimeError, "Candidate file changed"):
                    support.identity()

    def test_constraint_equivalence_keeps_changed_values_distinct(self):
        original = "CHECK (x = ANY ((ARRAY['active'::character varying, 'revoked'::character varying])::text[]))"
        restored = "CHECK (x = ANY (ARRAY[('active'::character varying)::text, ('revoked'::character varying)::text]))"
        self.assertEqual(support.normalize_constraint(original), support.normalize_constraint(restored))
        self.assertNotEqual(support.normalize_constraint(original), support.normalize_constraint(restored.replace("revoked", "admin")))
        self.assertEqual(support.normalize_constraint("CHECK (amount > 1)"), "CHECK (amount > 1)")


@unittest.skipUnless(os.getenv("PMAI_ACCEPTANCE_POSTGRES_BIN"), "requires local PostgreSQL 17 tools, never an existing DB URL")
class HostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        cls.tmp = tempfile.TemporaryDirectory(prefix="pmai-host-check-")
        cls.state = Path(cls.tmp.name)
        cls.cluster = support.Cluster(cls.state / "postgres", os.environ["PMAI_ACCEPTANCE_POSTGRES_BIN"]).__enter__()
        cls.fixture = support.seed_legacy(cls.cluster)
        support.expand_and_seed(cls.cluster, cls.fixture)
        cls.receipt = {"session": str(cls.state), "candidate": {"baseline": support.BASELINE}, "manual_safari_result": "PENDING"}
        cls.controls = Controls(cls.state, cls.cluster.engine(), cls.fixture, cls.receipt)
        ui = cls.state / "ui"
        ui.mkdir()
        (ui / "index.html").write_text("synthetic-static-host")
        api = support.make_api(cls.cluster.url(user="pmai_treatment_runtime"), secrets.token_urlsafe(48))
        cls.client = TestClient(hosted_app(api, ui, cls.controls, 4179, cls.receipt), base_url="http://127.0.0.1:4179").__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.cluster.__exit__(None, None, None)
        cls.tmp.cleanup()

    def test_host_origin_and_unported_route(self):
        self.assertEqual(self.client.get("/").text, "synthetic-static-host")
        self.assertEqual(self.client.get("/", headers={"Host": "other.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/v2/auth/login", headers={"Origin": "https://other.example"}, json={}).status_code, 403)
        self.assertEqual(self.client.post("/api/cases", json={}).status_code, 409)
        self.assertEqual(self.client.get("/__acceptance__/health").json()["manual_safari_result"], "PENDING")

    def test_real_revocation_yields_401(self):
        a = Flow(self.client, self.fixture)
        self.controls.apply("expire")
        self.assertEqual(self.client.get(a.root + "/treatment", headers=a.auth).status_code, 401)

    def test_lost_response_commits_once_and_original_lookup_recovers(self):
        a = Flow(self.client, self.fixture, case=109)
        rid = a.freeze()
        review = a.review(rid)
        proof, value_hash = a.proof(rid)
        key = secrets.token_hex(32)
        headers = {**a.auth, "Idempotency-Key": key, "If-Match": a.get()["etag"]}
        self.controls.apply("lose-sign-response")
        with ThreadPoolExecutor(max_workers=1) as pool:
            request = pool.submit(self.client.post, a.root + f"/treatment/revisions/{rid}/signatures", headers=headers, json={"review_id": review, "content_hash": value_hash, "challenge_id": proof})
            try:
                for _ in range(100):
                    if any(e["event"] == "response_prepared" and e.get("idempotency_key") == key for e in self.controls.events):
                        break
                    time.sleep(.05)
                else:
                    self.fail("The actual API did not prepare its response")
                new = Flow(self.client, self.fixture, case=109)
                response = self.client.get(new.root + "/commands/" + key + "?operation=sign", headers=new.auth)
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(len(new.get()["signatures"]), 1)
                self.assertTrue(all(e.get("browser_receipt") is False for e in self.controls.events if e["event"].startswith("response_")))
            finally:
                self.client.portal.call(self.controls.apply, "release")
            self.assertEqual(request.result(timeout=5).status_code, 504)


if __name__ == "__main__":
    unittest.main(verbosity=2)
