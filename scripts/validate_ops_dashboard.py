#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "src" / "pages" / "OpsDashboard.jsx"
APP = ROOT / "frontend" / "src" / "App.jsx"
DOC = ROOT / "docs" / "ops" / "OPS_DASHBOARD_V1.md"
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
    rc = require_text(
        PAGE,
        (
            "Pet-Med-AI Ops Dashboard",
            "Release Status / Admin Ops Dashboard V1",
            'api.get("/healthz")',
            'api.get("/api/system/version")',
            'api.get("/api/system/feature-flags")',
            "schema_ok",
            "database_revision",
            "alembic_head",
            "all_dangerous_features_disabled",
            "dangerous_features_enabled",
            "writes_database=false",
            "executes_real_import=false",
            "Release Gate Summary",
            "Feature Flags",
        ),
        "frontend/src/pages/OpsDashboard.jsx",
    )
    if rc:
        return rc

    rc = require_text(
        APP,
        (
            'import OpsDashboard from "./pages/OpsDashboard";',
            '<Route path="/ops" element={<OpsDashboard />} />',
        ),
        "frontend/src/App.jsx",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Pet-Med-AI Release Status / Admin Ops Dashboard V1",
            "/ops",
            "/api/system/version",
            "/api/system/feature-flags",
            "schema_ok",
            "all_dangerous_features_disabled",
        ),
        "docs/ops/OPS_DASHBOARD_V1.md",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_ops_dashboard.py",
            "ops dashboard frontend validation",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK ops dashboard: route, page and release-status API bindings are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
