# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter
from sqlalchemy import text

try:
    from backend.db import DATABASE_URL, engine
except ModuleNotFoundError:
    from db import DATABASE_URL, engine


router = APIRouter(prefix="/api/system", tags=["system"])

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
MIGRATION_VERSIONS = BACKEND_DIR / "migrations" / "versions"


def _short(value: Optional[str], length: int = 12) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None
    return raw[:length]


def _db_backend() -> str:
    raw = str(DATABASE_URL or "").lower()
    if raw.startswith("sqlite"):
        return "sqlite"
    if raw.startswith("postgresql") or raw.startswith("postgres"):
        return "postgresql"
    return "unknown"


def _git_commit_from_env() -> Optional[str]:
    for name in (
        "GIT_COMMIT",
        "RENDER_GIT_COMMIT",
        "COMMIT_SHA",
        "SOURCE_VERSION",
        "RAILWAY_GIT_COMMIT_SHA",
    ):
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def _git_commit_from_repo() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=2,
        )
    except Exception:
        return None
    value = (result.stdout or "").strip()
    return value or None


def _git_commit() -> Optional[str]:
    return _git_commit_from_env() or _git_commit_from_repo()


def _read_alembic_current() -> Optional[str]:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.first()
            return str(row[0]).strip() if row and row[0] else None
    except Exception:
        return None


def _literal_assignment(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    return None


def _migration_graph() -> dict[str, Any]:
    revisions: dict[str, str] = {}
    down_revisions: set[str] = set()

    if not MIGRATION_VERSIONS.exists():
        return {
            "revisions": [],
            "heads": [],
            "head": None,
            "errors": ["missing migrations/versions"],
        }

    errors: list[str] = []

    for path in sorted(MIGRATION_VERSIONS.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            revision = _literal_assignment(path, "revision")
            down_revision = _literal_assignment(path, "down_revision")
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        if not isinstance(revision, str) or not revision:
            errors.append(f"{path.name}: missing revision")
            continue

        revisions[revision] = path.name

        if isinstance(down_revision, str):
            down_revisions.add(down_revision)
        elif isinstance(down_revision, (tuple, list)):
            for item in down_revision:
                if isinstance(item, str):
                    down_revisions.add(item)

    heads = sorted(set(revisions.keys()) - down_revisions)
    return {
        "revisions": sorted(revisions.keys()),
        "heads": heads,
        "head": heads[0] if len(heads) == 1 else None,
        "errors": errors,
    }


def _schema_status(current_revision: Optional[str], graph: dict[str, Any]) -> dict[str, Any]:
    head = graph.get("head")
    heads = graph.get("heads") or []
    errors = graph.get("errors") or []
    ok = bool(current_revision and head and current_revision == head and not errors)
    return {
        "database_revision": current_revision,
        "alembic_head": head,
        "alembic_heads": heads,
        "schema_ok": ok,
        "migration_errors": errors,
    }


@router.get("/version", response_model=dict)
def system_version():
    """
    Read-only build/version endpoint.

    This endpoint intentionally does not expose DATABASE_URL and does not mutate
    database state. It is used for release verification and upgrade support.
    """

    graph = _migration_graph()
    current_revision = _read_alembic_current()
    schema = _schema_status(current_revision, graph)
    commit = _git_commit()

    return {
        "message": "system_version",
        "app_name": "Pet-Med-AI",
        "app_version": os.getenv("APP_VERSION", "development"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "service_name": os.getenv("RENDER_SERVICE_NAME") or os.getenv("SERVICE_NAME") or "local",
        "git_commit": commit,
        "git_commit_short": _short(commit),
        "database_backend": _db_backend(),
        **schema,
        "release_framework": True,
        "upgrade_ready": bool(schema.get("schema_ok")),
        "writes_database": False,
        "exposes_database_url": False,
    }


@router.get("/health", response_model=dict)
def system_health():
    version = system_version()
    return {
        "ok": bool(version.get("schema_ok")),
        "message": "system_health",
        "schema_ok": version.get("schema_ok"),
        "database_revision": version.get("database_revision"),
        "alembic_head": version.get("alembic_head"),
        "writes_database": False,
    }
