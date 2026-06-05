#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM_INFO = ROOT / "backend" / "system_info.py"
MAIN = ROOT / "backend" / "main.py"
DOC = ROOT / "docs" / "ops" / "SYSTEM_VERSION_BUILD_INFO_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    for path in (SYSTEM_INFO, MAIN, Path(__file__)):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    rc = require_text(
        SYSTEM_INFO,
        (
            'router = APIRouter(prefix="/api/system"',
            '@router.get("/version"',
            '@router.get("/health"',
            "system_version",
            "database_revision",
            "alembic_head",
            "schema_ok",
            "upgrade_ready",
            "writes_database",
            "exposes_database_url",
            "DATABASE_URL",
            "alembic_version",
        ),
        "backend/system_info.py",
    )
    if rc:
        return rc

    text = SYSTEM_INFO.read_text(encoding="utf-8")
    forbidden = (
        "db.add(",
        "db.commit(",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "DROP ",
        "ALTER TABLE",
    )
    for needle in forbidden:
        if needle in text:
            return fail(f"system info endpoint must stay read-only; forbidden marker found: {needle}")

    rc = require_text(
        MAIN,
        (
            "system_info_router",
            "app.include_router(system_info_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Pet-Med-AI Version / Build Info V1",
            "GET /api/system/version",
            "database_revision",
            "alembic_head",
            "schema_ok",
            "writes_database=false",
        ),
        "version/build info doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_system_version_info.py",
            "system version",
            "/api/system/version",
            "system_version",
            "schema_ok",
            "writes_database",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK system version/build info: read-only version endpoint and smoke coverage are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
