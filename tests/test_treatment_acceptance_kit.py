"""Boundary checks for the fresh-target acceptance tooling (not old PR72 replay)."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from treatment_acceptance import Controls, hosted_app
import treatment_acceptance_support as support
import treatment_acceptance_drill as drill
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
                legacy = support.identity()
                self.assertIsNone(legacy["parents"])
                self.assertEqual(legacy["packaged_files_verified"], 1)
                (path / "runtime.py").write_text("changed")
                with self.assertRaisesRegex(RuntimeError, "Candidate file changed"):
                    support.identity()

    def test_manifest_parent_ids_must_match_the_candidate_object_format(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(support, "ROOT", Path(tmp)):
            path = Path(tmp) / "acceptance-manifest.json"
            manifest = {"format": "pmai-treatment-kit-v1", "commit": "a" * 64, "tree": "b" * 64, "files": {}}
            parent = "c" * 64
            path.write_text(json.dumps({**manifest, "parents": [parent]}))
            self.assertEqual(support.identity()["parents"], [parent])
            for invalid in (None, parent, [None], [parent.upper()], ["g" * 64], ["c" * 40]):
                with self.subTest(invalid=invalid):
                    path.write_text(json.dumps({**manifest, "parents": invalid}))
                    with self.assertRaises(RuntimeError):
                        support.identity()

    def test_constraint_equivalence_keeps_changed_values_distinct(self):
        original = "CHECK (x = ANY ((ARRAY['active'::character varying, 'revoked'::character varying])::text[]))"
        restored = "CHECK (x = ANY (ARRAY[('active'::character varying)::text, ('revoked'::character varying)::text]))"
        self.assertEqual(support.normalize_constraint(original), support.normalize_constraint(restored))
        self.assertNotEqual(support.normalize_constraint(original), support.normalize_constraint(restored.replace("revoked", "admin")))
        self.assertEqual(support.normalize_constraint("CHECK (amount > 1)"), "CHECK (amount > 1)")


class PackageTests(unittest.TestCase):
    packager = Path("scripts/package_treatment_acceptance.py")
    prefix = "PMAI-treatment-acceptance/"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = self.tmp / "original"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.contents = {
            "backend/合成病例.txt": b"frozen text\n",
            "scripts/treatment_acceptance_mac.command": b"#!/bin/sh\n",
            "scripts/treatment_acceptance_provenance.py": (ROOT / "scripts/treatment_acceptance_provenance.py").read_bytes(),
        }
        for path, contents in self.contents.items():
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / path).write_bytes(contents)
        (self.repo / "scripts/treatment_acceptance_mac.command").chmod(0o755)
        (self.repo / ".gitignore").write_text("__pycache__/\n")
        (self.repo / ".gitattributes").write_text("*.txt text eol=crlf\n")
        (self.repo / "backend/.env.local").write_text("synthetic-only")
        (self.repo / "backend/example.sqlite3").write_bytes(b"fixture")
        shutil.copyfile(ROOT / self.packager, self.repo / self.packager)
        self.git("add", "-f", "--", ".")
        self.commit("synthetic fixture")
        self.clone = self.tmp / "clone"
        self.git("clone", "-q", "--no-local", str(self.repo), str(self.clone))

    def git(self, *args):
        return subprocess.run(["git", "-C", self.repo, *args], check=True, capture_output=True).stdout.decode().strip()

    def commit(self, message, *args):
        self.git("commit", "-qm", message, *args)

    def package(self, repo, name, *, umask=0o022, check=True):
        return subprocess.run([sys.executable, repo / self.packager, self.tmp / name],
                              capture_output=True, text=True, check=check, umask=umask)

    def test_same_commit_produces_identical_archives_across_checkouts(self):
        second_clone = self.tmp / "second-checkout"
        self.git("clone", "-q", "--no-local", str(self.repo), str(second_clone))
        for path in self.contents:
            os.utime(second_clone / path, (1000000, 1000000))
        first = self.tmp / "local-kit.tar.gz"
        second = self.tmp / "ci-kit.tar.gz"
        left = json.loads(self.package(self.clone, first.name).stdout)
        right = json.loads(self.package(second_clone, second.name, umask=0o077).stdout)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(left, right)
        self.assertEqual(left["sha256"], hashlib.sha256(first.read_bytes()).hexdigest())
        self.assertEqual(left["bytes"], first.stat().st_size)

    def test_manifest_and_members_use_git_blob_bytes_and_execution_modes(self):
        command = "scripts/treatment_acceptance_mac.command"
        label = "backend/合成病例.txt"
        subprocess.run(["git", "-C", self.clone, "config", "core.filemode", "false"], check=True)
        (self.clone / command).chmod(0o600)
        (self.clone / label).chmod(0o755)
        self.assertEqual((self.clone / label).read_bytes(), b"frozen text\r\n")
        output = self.tmp / "exact.tar.gz"
        receipt = json.loads(self.package(self.clone, output.name).stdout)
        self.assertEqual(receipt["files"], len(self.contents))
        self.assertEqual(receipt["parents"], [])
        with patch.object(support, "ROOT", self.clone):
            self.assertEqual(support.identity()["parents"], [])
        with tarfile.open(output) as archive:
            manifest_name = self.prefix + "acceptance-manifest.json"
            self.assertCountEqual(archive.getnames(), [self.prefix + n for n in self.contents] + [manifest_name])
            manifest = json.loads(archive.extractfile(manifest_name).read())
            self.assertEqual(manifest["format"], "pmai-treatment-kit-v1")
            self.assertEqual(manifest["commit"], self.git("rev-parse", "HEAD"))
            self.assertEqual(manifest["tree"], self.git("rev-parse", "HEAD^{tree}"))
            self.assertEqual(manifest["parents"], [])
            self.assertEqual(set(manifest["files"]), set(self.contents))
            for path, expected in self.contents.items():
                member = archive.getmember(self.prefix + path)
                self.assertEqual(archive.extractfile(member).read(), expected)
                self.assertEqual(manifest["files"][path], hashlib.sha256(expected).hexdigest())
                self.assertEqual(member.mode, 0o755 if path == command else 0o644)

    def test_shallow_merge_preserves_both_parents_in_order_through_offline_kit(self):
        self.git("checkout", "-qb", "other-parent")
        self.commit("side history", "--allow-empty")
        second = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", "-")
        self.commit("main history", "--allow-empty")
        first = self.git("rev-parse", "HEAD")
        self.git("merge", "-q", "--no-ff", "-m", "merge history\n\nparent " + "f" * 40, "other-parent")
        commit = self.git("rev-parse", "HEAD")
        shallow = self.tmp / "shallow"
        self.git("clone", "-q", "--depth=1", self.repo.as_uri(), str(shallow))
        self.assertNotEqual(subprocess.run(["git", "-C", shallow, "cat-file", "-e", first], capture_output=True).returncode, 0)
        with patch.object(support, "ROOT", shallow):
            checkout = support.identity()
        output = self.tmp / "merge.tar.gz"
        summary = json.loads(self.package(shallow, output.name).stdout)
        with tarfile.open(output) as archive:
            archive.extractall(self.tmp, filter="data")
        with patch.object(support, "ROOT", self.tmp / self.prefix):
            offline = support.identity()
        for identity in (checkout, summary, offline):
            self.assertEqual(identity["commit"], commit)
            self.assertEqual(identity["parents"], [first, second])

    def test_replace_ref_cannot_change_reported_parents(self):
        first = self.git("rev-parse", "HEAD")
        self.commit("successor", "--allow-empty")
        self.git("replace", "HEAD", first)
        with patch.object(support, "ROOT", self.repo):
            self.assertEqual(support.identity()["parents"], [first])
        summary = json.loads(self.package(self.repo, "replaced.tar.gz").stdout)
        self.assertEqual(summary["parents"], [first])

    def test_dirty_checkout_cannot_replace_existing_archive(self):
        output = self.tmp / "existing.tar.gz"
        output.write_bytes(b"previous archive")
        (self.clone / "backend/合成病例.txt").write_bytes(b"unsaved\n")
        self.assertNotEqual(self.package(self.clone, output.name, check=False).returncode, 0)
        self.assertEqual(output.read_bytes(), b"previous archive")

    def test_unsupported_tracked_symlink_leaves_only_previous_archive(self):
        link = self.repo / "backend/链接.txt"
        link.symlink_to("合成病例.txt")
        self.git("add", "-f", "--", "backend/链接.txt")
        self.commit("track an unsupported symbolic link")
        self.assertEqual(self.git("status", "--porcelain"), "")
        outdir = self.tmp / "output"
        outdir.mkdir()
        output = outdir / "kit.tar.gz"
        output.write_bytes(b"previous archive")
        result = self.package(self.repo, output.relative_to(self.tmp), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_bytes(), b"previous archive")
        self.assertEqual(list(outdir.iterdir()), [output])


class RestoreFingerprintTests(unittest.TestCase):
    """Exercise the real receipt and file writer, replacing the database operations."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state = Path(directory.name)
        self.pre = {"tables": {"cases": {"rows": 1}}, "sequences": {}, "catalog": {}}
        self.post = {"tables": {"cases": {"rows": 2}, "signatures": {"rows": 1}}, "sequences": {}, "catalog": {}}
        self.restored_pre = self.pre
        self.restored_post = self.post
        source_readings = iter([self.pre, self.post])

        def cluster(path, *args):
            return nullcontext(SimpleNamespace(engine=lambda: path.name))

        def fingerprint(engine):
            if engine == "source":
                return next(source_readings)
            return {"restore-pre": self.restored_pre, "restore-post": self.restored_post}[engine]

        self.restore = Mock()
        self.expand = Mock(return_value={})
        operations = patch.multiple(
            drill, Cluster=cluster, fingerprint=fingerprint, backup=Mock(return_value={}),
            restore=self.restore, seed_legacy=Mock(return_value={}), expand_and_seed=self.expand,
            exercise=Mock(return_value={}), verify_restored=Mock(return_value={}),
        )
        operations.start()
        self.addCleanup(operations.stop)

    def run_drill(self):
        return drill.run_drill(self.state, "/unused", {"commit": "a" * 40, "tree": "b" * 40})

    def assert_file_evidence(self, record, name, expected):
        raw = (self.state / name).read_bytes()
        self.assertEqual(json.loads(raw), expected)
        self.assertEqual(record, {"file": name, "sha256": hashlib.sha256(raw).hexdigest()})

    def assert_pair(self, receipt, phase, source, restored, matches):
        key, prefix = {
            "pre": ("pre_migration_restore", "pre-"),
            "post": ("post_migration_restore", ""),
        }[phase]
        entry = receipt[key]
        self.assertIs(entry["fingerprint_match"], matches)
        self.assertEqual(entry["tables"], len(source["tables"]))
        self.assert_file_evidence(entry["fingerprints"]["source"], prefix + "source-fingerprint.json", source)
        self.assert_file_evidence(entry["fingerprints"]["restored"], prefix + "restored-fingerprint.json", restored)

    def failed_receipt(self, message):
        with self.assertRaisesRegex(RuntimeError, message):
            self.run_drill()
        receipt = json.loads((self.state / "drill-receipt.json").read_bytes())
        self.assertEqual(receipt["status"], "FAILED")
        return receipt

    def test_both_stage_receipts_bind_independent_source_and_restored_files(self):
        result = self.run_drill()
        persisted = json.loads((self.state / "drill-receipt.json").read_bytes())
        self.assertEqual(persisted, result)
        self.assertEqual(result["status"], "PASS")
        self.assert_pair(result, "pre", self.pre, self.pre, True)
        self.assert_pair(result, "post", self.post, self.post, True)

    def test_pre_restore_mismatch_preserves_both_original_fingerprints(self):
        self.restored_pre = {"tables": {"cases": {"rows": 0}}, "sequences": {}, "catalog": {}}
        receipt = self.failed_receipt("Pre-migration restore fingerprint differs")
        self.assert_pair(receipt, "pre", self.pre, self.restored_pre, False)
        self.expand.assert_not_called()
        self.assertNotIn("post_migration_restore", receipt)

    def test_post_restore_mismatch_preserves_pre_and_post_evidence(self):
        self.restored_post = self.pre
        receipt = self.failed_receipt("Post-signing restore fingerprint differs")
        self.assert_pair(receipt, "pre", self.pre, self.pre, True)
        self.assert_pair(receipt, "post", self.post, self.restored_post, False)

    def test_failed_restore_retains_only_the_measured_source_for_that_stage(self):
        self.restore.side_effect = [None, RuntimeError("synthetic restore failed")]
        receipt = self.failed_receipt("synthetic restore failed")
        self.assert_pair(receipt, "pre", self.pre, self.pre, True)
        post = receipt["post_migration_restore"]
        self.assertNotIn("fingerprint_match", post)
        self.assertEqual(set(post["fingerprints"]), {"source"})
        self.assert_file_evidence(post["fingerprints"]["source"], "source-fingerprint.json", self.post)
        self.assertFalse((self.state / "restored-fingerprint.json").exists())


@unittest.skipUnless(os.getenv("PMAI_ACCEPTANCE_POSTGRES_BIN"), "requires local PostgreSQL 17 tools, never an existing DB URL")
class HostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        cls.tmp = tempfile.TemporaryDirectory(prefix="pmai-host-check-")
        cls.state = Path(cls.tmp.name)
        cls.cluster = support.Cluster(cls.state / "postgres", os.environ["PMAI_ACCEPTANCE_POSTGRES_BIN"]).__enter__()
        support.check(cls.cluster.password != cls.cluster.runtime_password, "Admin and runtime passwords must be independent")
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
