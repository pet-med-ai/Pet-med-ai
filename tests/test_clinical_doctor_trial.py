"""Boundary/failure tests for the real local trial launcher (no external traffic)."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = load("trial_launcher", "scripts/run_clinical_doctor_trial_cw_b26.py")
runtime = load("trial_runtime", "tests/acceptance/clinical_doctor_trial_runtime.py")
IDENTITY = {"head": "a" * 40, "source_sha256": "b" * 64, "clean": True}


class TrialBoundaries(unittest.TestCase):
    def setUp(self):
        self.directory, self.config = launcher.make_session(IDENTITY, 5174, 18027)
        self.path = self.directory / "environment.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.directory, ignore_errors=True)

    def change(self, **changes):
        self.config.update(changes)
        self.path.write_text(json.dumps(self.config))

    def test_valid_new_session_and_random_identity(self):
        config, database = runtime.validate_config(self.path)
        self.assertEqual(config, self.config)
        self.assertFalse(database.exists())
        second, other = launcher.make_session(IDENTITY, 5174, 18027)
        try:
            for key in ("password", "secret", "session", "email", "database_url"):
                self.assertNotEqual(self.config[key], other[key])
        finally:
            launcher.remove_session(second, other["session"])

    def test_existing_database_is_never_opened(self):
        database = self.directory / "synthetic.sqlite"
        database.write_bytes(b"sentinel-existing-data")
        with self.assertRaises(ValueError):
            runtime.validate_config(self.path)
        self.assertEqual(database.read_bytes(), b"sentinel-existing-data")

    def test_remote_and_other_local_database_rejected(self):
        for url in ("postgresql://127.0.0.1/pmai", "postgresql://example.com/production",
                    "sqlite:////tmp/other.sqlite", "sqlite:///:memory:"):
            with self.subTest(url=url):
                self.change(database_url=url)
                with self.assertRaises(ValueError):
                    runtime.validate_config(self.path)

    def test_symlinked_config_database_and_private_rejected(self):
        target = self.directory / "other.json"
        self.path.rename(target)
        self.path.symlink_to(target)
        with self.assertRaises(ValueError):
            runtime.validate_config(self.path)
        self.path.unlink()
        target.rename(self.path)
        (self.directory / "synthetic.sqlite").symlink_to(self.directory / "absent")
        with self.assertRaises(ValueError):
            runtime.validate_config(self.path)
        (self.directory / "synthetic.sqlite").unlink()
        (self.directory / "private").rmdir()
        (self.directory / "private").symlink_to(Path(tempfile.gettempdir()))
        with self.assertRaises(ValueError):
            runtime.validate_config(self.path)

    def test_marker_path_and_origin_are_required(self):
        for key, value in (("ui_origin", "http://0.0.0.0:5174"),
                           ("api_origin", "https://example.com"),
                           ("private_dir", "/tmp"), ("session", "bad")):
            original = self.config[key]
            self.change(**{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                runtime.validate_config(self.path)
            self.change(**{key: original})
        (self.directory / "synthetic-only").write_text("not-this-session")
        with self.assertRaises(ValueError):
            runtime.validate_config(self.path)

    def test_inherited_production_values_are_removed(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://example.com/production",
                                    "OPENAI_API_KEY": "sentinel", "VITE_API_BASE": "https://example.com",
                                    "HTTP_PROXY": "http://example.com", "SECRET_KEY": "sentinel",
                                    "NODE_OPTIONS": "--require=unexpected.js", "PYTHONPATH": "/tmp/untrusted"}):
            clean = launcher.clean_environment()
        for key in ("DATABASE_URL", "OPENAI_API_KEY", "VITE_API_BASE", "HTTP_PROXY",
                    "SECRET_KEY", "NODE_OPTIONS", "PYTHONPATH"):
            self.assertNotIn(key, clean)

    def test_audit_guard_rejects_actual_outbound_connect_and_foreign_sqlite(self):
        code = """
import importlib.util, socket, sqlite3, sys
from pathlib import Path
s=importlib.util.spec_from_file_location('runtime',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sys.addaudithook(m.network_guard(Path(sys.argv[2]),18027))
for f in [lambda:socket.create_connection(('192.0.2.1',443),timeout=.1),
          lambda:sqlite3.connect(':memory:'),
          lambda:socket.socket().bind(('0.0.0.0',18027))]:
 try: f()
 except RuntimeError: pass
 else: raise AssertionError('guard allowed forbidden operation')
print('PASS actual audit hooks')
"""
        result = subprocess.run([sys.executable, "-B", "-c", code,
                                 str(ROOT / "tests/acceptance/clinical_doctor_trial_runtime.py"),
                                 str(self.directory / "synthetic.sqlite")], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dependency_failure_precedes_any_session(self):
        with patch.object(launcher.importlib.util, "find_spec", return_value=None):
            with self.assertRaises(launcher.TrialError) as error:
                launcher.preflight()
        self.assertEqual(error.exception.code, "dependencies")

    def test_custom_temporary_root_survives_clean_child_environment(self):
        # Simulate macOS's per-user TMPDIR in a new interpreter (tempfile caches it).
        code = """
import importlib.util,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1])
s=importlib.util.spec_from_file_location('launcher',root/'scripts/run_clinical_doctor_trial_cw_b26.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p,c=m.make_session({'head':'a'*40,'source_sha256':'b'*64,'clean':True},5174,18027)
try:
 check="import importlib.util,sys;s=importlib.util.spec_from_file_location('runtime',sys.argv[1]);r=importlib.util.module_from_spec(s);s.loader.exec_module(r);r.validate_config(sys.argv[2])"
 result=subprocess.run([sys.executable,'-B','-c',check,str(root/'tests/acceptance/clinical_doctor_trial_runtime.py'),str(p/'environment.json')],env=m.clean_environment(),capture_output=True,text=True)
 assert result.returncode==0,result.stderr
finally:m.remove_session(p,c['session'])
"""
        with tempfile.TemporaryDirectory(prefix="cwb26-custom-tmp-") as temporary:
            result = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT)],
                                    env={**launcher.clean_environment(), "TMPDIR": temporary},
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_occupied_port_refused_without_touching_occupant_or_leaking_credentials(self):
        with socket.socket() as occupant, tempfile.TemporaryDirectory() as output:
            occupant.bind(("127.0.0.1", 0))
            occupant.listen(1)
            receipt = Path(output) / "receipt.json"
            args = argparse.Namespace(ui_port=occupant.getsockname()[1], api_port=18027,
                                      expect_head=None, receipt=receipt)
            with patch.object(launcher, "preflight", return_value=("node", IDENTITY)), \
                    patch.object(launcher, "make_session") as make, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(launcher.run(args), 1)
                make.assert_not_called()
            self.assertGreater(occupant.fileno(), -1)
            report = json.loads(receipt.read_text())
            self.assertEqual(report["error_code"], "port_busy")
            for forbidden in ("password", "secret", "token"):
                self.assertNotIn(forbidden, receipt.read_text())

    def test_cleanup_requires_own_marker_and_preserves_downloads(self):
        with tempfile.TemporaryDirectory() as output:
            downloaded = Path(output) / "saved.docx"
            downloaded.write_bytes(b"synthetic-user-download")
            with self.assertRaises(launcher.TrialError):
                launcher.remove_session(self.directory, "wrong-session")
            self.assertTrue(self.directory.exists())
            launcher.remove_session(self.directory, self.config["session"])
            self.assertFalse(self.directory.exists())
            self.assertEqual(downloaded.read_bytes(), b"synthetic-user-download")

    def test_stop_signals_only_owned_child(self):
        child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"], start_new_session=True)
        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"], start_new_session=True)
        try:
            launcher.stop_process(child)
            self.assertIsNotNone(child.poll())
            self.assertIsNone(unrelated.poll())
        finally:
            launcher.stop_process(child)
            launcher.stop_process(unrelated)

    def test_identity_requires_candidate_and_synthetic_marker(self):
        data = {**self.config, "synthetic_only": True}
        self.assertTrue(launcher.identity_matches(data, self.config))
        for field in ("session", "head", "source_sha256", "schema", "synthetic_only"):
            self.assertFalse(launcher.identity_matches({**data, field: "wrong"}, self.config))


if __name__ == "__main__":
    unittest.main(verbosity=2)
