#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "frontend/src/pages/OpsDashboard.jsx",
    "docs/ops/OPS_DASHBOARD_CLINICAL_CORE_V2.md",
    "docs/ops/OPS_DASHBOARD_CLINICAL_CORE_CHECKLIST_V2.csv",
    "docs/ops/OPS_DASHBOARD_CLINICAL_CORE_GO_NO_GO_V2.csv",
    "scripts/validate_ops_dashboard_clinical_core_v2.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

REQUIRED_SNIPPETS = {
    "frontend/src/pages/OpsDashboard.jsx": [
        "Ops Dashboard Clinical Core V2",
        "/api/diagnostic-data/clinical-qa-dashboard/v2/summary",
        "clinicalCoreOps",
        "clinicalCoreOpsError",
        "clinicalCoreReadOnlyOk",
        "clinicalCoreNoDxOk",
        "clinicalCoreReviewRequiredOk",
        "clinicalCoreMetrics",
        "clinicalCoreQueue",
        "read_only=true；writes_database=false",
        "no final diagnosis；no treatment plan；no prescription；no drug dose",
        "requires_human_review=true · not_a_diagnosis=true · not_client_facing=true",
    ],
    "docs/ops/OPS_DASHBOARD_CLINICAL_CORE_V2.md": [
        "Ops Dashboard Clinical Core V2",
        "GET /api/diagnostic-data/clinical-qa-dashboard/v2/summary",
        "read_only=true",
        "writes_database=false",
        "not_client_facing=true",
        "next=LAB_RESULT_PARSER_EXPANSION_V2",
    ],
}

FORBIDDEN_FRONTEND_SNIPPETS = [
    'api.post("/api/diagnostic-data/clinical-qa-dashboard',
    'api.put("/api/diagnostic-data/clinical-qa-dashboard',
    'api.patch("/api/diagnostic-data/clinical-qa-dashboard',
    'api.delete("/api/diagnostic-data/clinical-qa-dashboard',
    "final diagnosis:",
    "confirmed diagnosis:",
    "definitive diagnosis:",
    "drug dose:",
]


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    return path.read_text(encoding="utf-8")


def assert_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        read(rel)
    for rel, snippets in REQUIRED_SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))

    ui_text = read("frontend/src/pages/OpsDashboard.jsx")
    if ui_text.count("Ops Dashboard Clinical Core V2") < 3:
        fail("OpsDashboard clinical core section appears incomplete")
    for snippet in FORBIDDEN_FRONTEND_SNIPPETS:
        if snippet in ui_text:
            fail("forbidden frontend snippet found: %s" % snippet)


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Ops Dashboard Clinical Core V2 static checks" not in ci:
        fail("ci_static_checks missing Ops Dashboard Clinical Core V2 block")
    if "python3 scripts/validate_ops_dashboard_clinical_core_v2.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "Ops Dashboard Clinical Core V2 smoke" not in smoke:
        fail("smoke missing Ops Dashboard Clinical Core V2 block")
    if "clinical_qa_dashboard_v2_summary" not in smoke:
        fail("smoke missing Clinical QA dashboard endpoint assertion")


def main() -> None:
    assert_files_and_snippets()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Ops Dashboard Clinical Core V2")


if __name__ == "__main__":
    main()
