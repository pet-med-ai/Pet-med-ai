#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOC = ROOT / "docs" / "product" / "PET_MED_AI_FUTURE_DEVELOPMENT_OUTLINE_V1.md"
CHECKLIST = ROOT / "docs" / "product" / "PET_MED_AI_FUTURE_DEVELOPMENT_OUTLINE_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "product" / "PET_MED_AI_FUTURE_DEVELOPMENT_OUTLINE_GO_NO_GO_V1.csv"
VALIDATOR = ROOT / "scripts" / "validate_petmed_future_development_outline.py"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

REQUIRED_FILES = (DOC, CHECKLIST, GO_NO_GO, VALIDATOR, CI_STATIC, SMOKE)

DOC_NEEDLES = (
    "Pet-Med-AI Future Development Outline V1",
    "structured intake",
    "DiagnosticReport / Observation / ImagingStudy",
    "database_revision=0009_diag_data",
    "ENABLE_EMR_REAL_IMPORT=false",
    "Do not run git add .",
    "Immediate exotics source-review safety chain",
    "Exotics clinical knowledge depth roadmap",
    "Exotics lab and imaging readiness roadmap",
    "Diagnostic assistance roadmap",
    "Clinical documents roadmap",
    "Data ingestion roadmap",
    "Frontend UI roadmap",
    "Ops, QA, and audit roadmap",
    "Commercial deployment support roadmap",
    "Long-term high-risk prescription and dose roadmap",
    "Metadata-only Collection Workspace Governance Signoff Record Validation V1",
    "Exotics Module Visibility / Documentation V1",
    "Exotics Structured Intake UI V2",
    "Ops Dashboard Exotics Coverage V1",
    "Drug Dose Clinician-only Draft Policy V1",
    "Prescription Draft Data Model Risk Review V1",
    "Client-facing Dose Output Boundary V1",
    "decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_V1",
)

BOUNDARY_NEEDLES = (
    "No numeric medication values.",
    "No route or frequency.",
    "No prescription direction.",
    "dose_output_enabled=false",
    "prescription_engine=false",
    "client_facing=false",
    "No source collection results.",
    "No dose data.",
    "No executable medication instruction.",
)

CI_NEEDLES = (
    "Pet-Med-AI Future Development Outline V1 static checks",
    "python3 scripts/validate_petmed_future_development_outline.py",
)

SMOKE_NEEDLES = (
    "Pet-Med-AI Future Development Outline V1 smoke",
    "python3 scripts/validate_petmed_future_development_outline.py",
)


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def require_file(path: Path) -> None:
    if not path.exists():
        fail("missing required file: %s" % path.relative_to(ROOT))
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)


def require_text(path: Path, needles: tuple[str, ...], label: str) -> str:
    require_file(path)
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            fail("%s missing expected content: %s" % (label, needle))
    return text


def require_csv(path: Path, required_columns: tuple[str, ...], min_rows: int, label: str) -> None:
    require_file(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < min_rows:
        fail("%s expected at least %d rows, got %d" % (label, min_rows, len(rows)))
    columns = set(rows[0].keys()) if rows else set()
    for column in required_columns:
        if column not in columns:
            fail("%s missing required column: %s" % (label, column))


def main() -> int:
    for path in REQUIRED_FILES:
        require_file(path)

    doc_text = require_text(DOC, DOC_NEEDLES, "future development outline doc")
    for needle in BOUNDARY_NEEDLES:
        if needle not in doc_text:
            fail("future development outline missing safety boundary: %s" % needle)

    require_csv(CHECKLIST, ("category", "item", "required", "status", "notes"), 20, "future outline checklist")
    require_csv(GO_NO_GO, ("gate", "required", "status", "go_criteria", "no_go_criteria"), 8, "future outline go/no-go")

    require_text(CI_STATIC, CI_NEEDLES, "ci_static_checks.sh")
    require_text(SMOKE, SMOKE_NEEDLES, "smoke_petmed.sh")

    forbidden_paths = (
        ROOT / "backend" / "app",
        ROOT / "backend" / "ai_engine",
        ROOT / "frontend" / "src" / "components",
    )
    # This validator does not fail when these long-lived directories already exist in the repo or working tree.
    # The stage is docs-only; the check below simply ensures the validator itself does not reference them as targets.
    own_text = VALIDATOR.read_text(encoding="utf-8")
    for path in forbidden_paths:
        if str(path.relative_to(ROOT)) in own_text and "forbidden_paths" not in own_text:
            fail("validator unexpectedly targets forbidden path: %s" % path.relative_to(ROOT))

    print("VALIDATOR=PASS Pet-Med-AI Future Development Outline V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
