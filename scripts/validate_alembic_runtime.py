#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate that Pet-Med-AI runtime no longer mutates database schema at startup.

Alembic V2 guardrails:
- FastAPI startup must not call Base.metadata.create_all().
- FastAPI startup must not run ad-hoc ALTER TABLE helpers.
- Schema changes must go through Alembic migrations.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "backend" / "main.py"

FORBIDDEN_SNIPPETS = [
    "Base.metadata.create_all(bind=engine)",
    "Base.metadata.create_all",
    "def ensure_consult_session_columns",
    "def ensure_case_extra_columns",
    "ensure_consult_session_columns()",
    "ensure_case_extra_columns()",
    "sql_text",
]

REQUIRED_SNIPPETS = [
    "Database schema is managed by Alembic migrations",
]


def main() -> int:
    if not MAIN.exists():
        print(f"ERROR: backend/main.py not found: {MAIN}", file=sys.stderr)
        return 1

    text = MAIN.read_text(encoding="utf-8")
    errors = []

    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            errors.append(f"forbidden startup schema mutation remains: {snippet}")

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            errors.append(f"missing Alembic runtime marker: {snippet}")

    if errors:
        print("Alembic runtime validation FAILED", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 2

    print("OK Alembic runtime: schema creation/column patching is not performed at application startup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
