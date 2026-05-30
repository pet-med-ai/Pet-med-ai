#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT / "backend" / "kpi_api.py",
    ROOT / "backend" / "main.py",
]

REQUIRED_ROUTES = [
    'prefix="/api/kpi"',
    '@router.get("/cases"',
    '@router.get("/imaging"',
    '@router.get("/followups"',
    '@router.get("/qa"',
    '@router.get("/dashboard"',
]

MAIN_REQUIRED = [
    "kpi_api_router",
    "app.include_router(kpi_api_router)",
]


def assert_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        raise SystemExit(f"ERROR: {path} missing expected text: {needle}")


def main() -> int:
    for path in REQUIRED_FILES:
        if not path.exists():
            raise SystemExit(f"ERROR: missing file: {path}")
        py_compile.compile(str(path), doraise=True)

    kpi_path = ROOT / "backend" / "kpi_api.py"
    main_path = ROOT / "backend" / "main.py"

    for needle in REQUIRED_ROUTES:
        assert_contains(kpi_path, needle)

    for needle in MAIN_REQUIRED:
        assert_contains(main_path, needle)

    print("OK KPI aggregation API: router, endpoints and main.py include are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
