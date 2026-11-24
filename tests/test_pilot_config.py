"""Offline pilot configuration checks, using only synthetic settings."""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_pilot_config as preflight

READ = "pmai_scope_runtime"
TREATMENT = "pmai_treatment_runtime"
SECRET = "密" * 32


class PilotConfigurationTests(unittest.TestCase):
    def run_check(self, mode="read_pilot", url=None, status=0, **settings):
        env = {
            "PMAI_MULTICLINIC_MODE": mode,
            "MULTICLINIC_DATABASE_URL": url if url is not None else f"postgresql://{READ}@/test",
            "MULTICLINIC_TOKEN_SECRET": SECRET,
            **settings,
        }
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            self.assertEqual(preflight.main([mode], env), status, out.getvalue())
        self.assertNotIn(SECRET, out.getvalue())
        return out.getvalue()

    def test_both_roles_unix_socket_and_runtime_driver_selection(self):
        self.run_check()
        self.run_check("treatment_pilot", f"postgresql+psycopg://{TREATMENT}@/test?host=/tmp")
        self.run_check("read_pilot", f"postgresql://{TREATMENT}@/test", 1)
        self.run_check("treatment_pilot", f"postgresql://{READ}@/test", 1)

    def test_expected_mode_explicit_and_token_character_count(self):
        self.run_check(PMAI_MULTICLINIC_MODE="treatment_pilot", status=1)
        self.run_check(PMAI_MULTICLINIC_MODE="off", status=1)
        self.run_check(PMAI_MULTICLINIC_MODE="", status=1)
        self.run_check(MULTICLINIC_TOKEN_SECRET="密" * 31, status=1)
        self.run_check(MULTICLINIC_TOKEN_SECRET="", status=1)
        self.run_check(MULTICLINIC_TOKEN_SECRET="密" * 32)

    def test_query_and_nested_dsn_precedence(self):
        self.run_check(url=f"postgresql://{READ}@/test?user=synthetic-admin", status=1)
        self.run_check(url=f"postgresql://synthetic-admin@/test?user={READ}")
        self.run_check(url=f"postgresql:///test?user={READ}")
        self.run_check(url="postgresql://pmai%5Fscope%5Fruntime@/test")
        dsn = quote("user=synthetic-admin dbname=test", safe="")
        self.run_check(url=f"postgresql://?dsn={dsn}", status=1)
        self.run_check(url=f"postgresql://?dsn={dsn}&user={READ}")
        self.run_check(url=f"postgresql:///test?user={READ}&user=synthetic-admin", status=1)

    def test_malformed_unrelated_or_missing_url_has_no_fallback(self):
        for url in ("", "not-a-url", "sqlite:///:memory:", "postgresql://host:invalid-port/db",
                    f"postgresql://{READ}@/test?unknown-libpq-option=redacted"):
            with self.subTest(url=url):
                self.run_check(url=url, status=1, DATABASE_URL=f"postgresql://{READ}@/test")

    def test_indirect_settings_do_not_report_a_verified_role(self):
        for url in ("postgresql:///test", f"postgresql://{READ}@/test?service=synthetic",
                    f"postgresql://{READ}@/test?options=-c%20role%3Dother",
                    f"postgresql://{READ}@/test?plugin=not-loaded",
                    f"postgresql://{READ}@/?dbname=postgresql%3A%2F%2Fother%40localhost%2Ftest"):
            with self.subTest(url=url):
                self.run_check(url=url, status=3)
        self.run_check(PGSERVICE="synthetic", status=3)
        self.run_check(PGOPTIONS="-c role=other", status=3)
        self.run_check(url="postgresql:///test", PGUSER=READ, status=3)
        self.run_check(url="postgresql:///test", MULTICLINIC_TOKEN_SECRET="", status=1)

    def test_cli_reports_no_input_values_even_on_errors(self):
        sentinel = "UNPRINTABLE_TEST_SENTINEL"
        cmd = [sys.executable, "-I", "-B", str(ROOT / "scripts/check_pilot_config.py")]
        env = {"PMAI_MULTICLINIC_MODE": sentinel,
               "MULTICLINIC_TOKEN_SECRET": sentinel,
               "MULTICLINIC_DATABASE_URL": f"postgresql://{sentinel}:{sentinel}@host:{sentinel}/db"}
        for args, expected in [(["read_pilot"], 1), ([sentinel], 2), (["--url", sentinel], 2), (["--help"], 0)]:
            result = subprocess.run(cmd + args, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, expected)
            self.assertNotIn(sentinel, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_help_usage_and_dependency_hint_without_site_packages(self):
        cmd = [sys.executable, "-I", "-B", "-S", str(ROOT / "scripts/check_pilot_config.py")]
        env = {"PMAI_MULTICLINIC_MODE": "read_pilot", "MULTICLINIC_TOKEN_SECRET": SECRET,
               "MULTICLINIC_DATABASE_URL": f"postgresql://{READ}@/test"}
        for args, code, hint in [
            (["--help"], 0, "Usage:"),
            (["invalid-private-value"], 2, "Usage:"),
            (["read_pilot"], 2, "backend/requirements.txt"),
        ]:
            result = subprocess.run(cmd + args, env=env, capture_output=True, text=True, check=False)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, code, output)
            self.assertIn(hint, output)
            self.assertNotIn("Traceback", output)
            self.assertNotIn("invalid-private-value", output)
            self.assertNotIn(SECRET, output)

    def test_parser_does_not_open_a_database_or_network_connection(self):
        def deny(*args, **kwargs):
            raise AssertionError("configuration checks must stay offline")
        with patch("psycopg2.connect", side_effect=deny), patch("socket.socket", side_effect=deny):
            self.run_check()
            self.run_check(url=f"postgresql://{READ}@does-not-resolve.invalid/not-real?service=synthetic", status=3)


if __name__ == "__main__":
    unittest.main()
