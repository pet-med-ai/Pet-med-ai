#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "src" / "App.jsx"
PAGE = ROOT / "frontend" / "src" / "pages" / "KpiDashboard.jsx"
DOC = ROOT / "docs" / "operations" / "KPI_DASHBOARD_FRONTEND_V1.md"


def require(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    app = require(APP)
    page = require(PAGE)
    require(DOC)

    checks = [
        ("App imports KpiDashboard", "KpiDashboard" in app and './pages/KpiDashboard' in app),
        ("App has /kpi route", 'path="/kpi"' in app or "path='/kpi'" in app),
        ("Dashboard calls API", '/api/kpi/dashboard' in page),
        ("Dashboard renders KPI cards", "case_completeness" in page and "repeat_imaging_rate" in page and "qa_audit_coverage" in page),
        ("Dashboard links cases", "/cases/" in page),
    ]
    failed = [label for label, ok in checks if not ok]
    if failed:
        for label in failed:
            print(f"FAIL {label}")
        return 2

    print("OK KPI dashboard frontend: route, page and API binding are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
