#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

REQUIRED_FILES = [
    BACKEND / "alembic.ini",
    BACKEND / "migrations" / "env.py",
    BACKEND / "migrations" / "script.py.mako",
    BACKEND / "migrations" / "README",
    BACKEND / "migrations" / "versions" / "0001_baseline_current_schema.py",
]


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        return fail("missing Alembic files: " + ", ".join(missing))

    for path in REQUIRED_FILES:
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    ini_text = (BACKEND / "alembic.ini").read_text(encoding="utf-8")
    if "script_location = migrations" not in ini_text:
        return fail("backend/alembic.ini must set script_location = migrations")

    revision_text = (BACKEND / "migrations" / "versions" / "0001_baseline_current_schema.py").read_text(encoding="utf-8")
    for needle in (
        'revision = "0001_baseline"',
        'op.create_table(\n        "users"',
        'op.create_table(\n        "cases"',
        'op.create_table(\n        "consult_sessions"',
    ):
        if needle not in revision_text:
            return fail(f"baseline migration missing expected content: {needle}")

    sys.path.insert(0, str(BACKEND))
    from db import Base  # noqa: WPS433
    import models  # noqa: F401,WPS433

    tables = set(Base.metadata.tables.keys())
    expected = {"users", "cases", "consult_sessions"}
    if tables != expected:
        return fail(f"SQLAlchemy metadata tables mismatch: actual={sorted(tables)}, expected={sorted(expected)}")

    print("OK Alembic setup: baseline revision and SQLAlchemy metadata are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
