"""Fresh-process Render-style imports, real DBAPI loading, no DB/network access."""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHILD = r'''
import json, os, sys
from pathlib import Path
from unittest.mock import patch

def forbid(*args, **kwargs):
    raise AssertionError("Startup must not connect to a database or network")

def guard(event, args):
    if event in {"socket.connect", "socket.connect_ex", "socket.bind",
                 "socket.getaddrinfo", "sqlite3.connect", "subprocess.Popen",
                 "os.system"}:
        forbid()

sys.addaudithook(guard)
import psycopg2
from sqlalchemy import event
from sqlalchemy.engine import Engine
event.listen(Engine, "do_connect", forbid)
# psycopg2 performs networking in C; a Python socket guard alone is insufficient.
with patch.object(psycopg2, "connect", side_effect=forbid) as connect:
    import db
    if sys.argv[1] == "health":
        from uvicorn.importer import import_from_string
        from fastapi.testclient import TestClient
        app = import_from_string("main:app")
        with TestClient(app) as client:
            response = client.get("/healthz")
            assert response.status_code == 200 and response.json() == {"ok": True}
        assert not app.dependency_overrides
    connect.assert_not_called()
    # Synthetic URLs only; no inherited credentials or environment.
    print(json.dumps({"url": db.DATABASE_URL, "driver": db.engine.dialect.driver,
                      "dbapi": db.engine.dialect.dbapi.__name__,
                      "pool_pre_ping": db.engine.pool._pre_ping,
                      "pool_recycle": db.engine.pool._recycle}))
    db.engine.dispose()
'''


class DatabaseStartupTests(unittest.TestCase):
    def probe(self, url=None, *, health=False):
        with tempfile.TemporaryDirectory(prefix="pmai-startup-") as directory:
            # Deliberately exclude DATABASE_URL, tokens and other caller settings.
            env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str(ROOT / "backend"),
                "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                "SECRET_KEY": "synthetic-startup-probe-only",
                "ENVIRONMENT": "production", "RENDER": "true",
            }
            if url is not None:
                env["DATABASE_URL"] = url
            result = subprocess.run(
                [sys.executable, "-c", CHILD, "health" if health else "db"],
                cwd=directory, env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [], "Import wrote files")
            return json.loads(result.stdout.strip().splitlines()[-1])

    def test_reviewed_dependency_pair_is_installed(self):
        self.assertEqual(importlib.metadata.version("SQLAlchemy"), "2.0.54")
        self.assertEqual(importlib.metadata.version("psycopg2-binary"), "2.9.13")

    def test_bare_postgresql_boots_real_app_without_connection(self):
        result = self.probe("postgresql://synthetic@127.0.0.1:1/unused", health=True)
        self.assertEqual(result["driver"], "psycopg2")
        self.assertEqual(result["dbapi"], "psycopg2")
        self.assertTrue(result["pool_pre_ping"])
        self.assertEqual(result["pool_recycle"], 1800)

    def test_legacy_postgres_scheme_boots_real_app(self):
        result = self.probe("postgres://synthetic@127.0.0.1:1/unused", health=True)
        self.assertEqual(result["driver"], "psycopg2")

    def test_explicit_psycopg2_is_unchanged(self):
        url = "postgresql+psycopg2://synthetic@127.0.0.1:1/unused?sslmode=require"
        self.assertEqual(self.probe(url)["url"], url)

    def test_encoded_credentials_ipv6_and_options_survive(self):
        suffix = "u%40x:p%3A%2F%40@[::1]:1/synthetic?sslmode=require&application_name=a%20b"
        result = self.probe("  postgresql://" + suffix + "  ")
        self.assertEqual(result["url"], "postgresql+psycopg2://" + suffix)

    def test_sqlite_default_still_loads_without_creating_database(self):
        result = self.probe(health=True)
        self.assertEqual(result["url"], "sqlite:///./app.db")
        self.assertEqual(result["driver"], "pysqlite")

    def test_explicit_sqlite_still_loads_without_connection(self):
        for url in ("sqlite:///:memory:", "sqlite:///synthetic.sqlite3"):
            with self.subTest(url=url):
                result = self.probe(url)
                self.assertEqual(result["url"], url)
                self.assertEqual(result["driver"], "pysqlite")


if __name__ == "__main__":
    unittest.main(verbosity=2)
