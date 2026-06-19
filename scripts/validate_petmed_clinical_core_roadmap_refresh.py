#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_PRODUCT = ROOT / "docs" / "product"

ROADMAP = DOCS_PRODUCT / "PET_MED_AI_CLINICAL_CORE_ROADMAP_REFRESH_V1.md"
MASTER = DOCS_PRODUCT / "PET_MED_AI_MASTER_BUILD_DIRECTORY_V1.md"
HANDOFF = DOCS_PRODUCT / "PET_MED_AI_COMMERCIAL_V1_TO_CLINICAL_CORE_HANDOFF_V1.md"
SCOPE = DOCS_PRODUCT / "PET_MED_AI_CLINICAL_CORE_SCOPE_LOCK_V1.md"
MATRIX = DOCS_PRODUCT / "PET_MED_AI_CLINICAL_CORE_NEXT_STAGE_MATRIX.csv"

REQUIRED_FILES = [ROADMAP, MASTER, HANDOFF, SCOPE, MATRIX]

MATRIX_COLUMNS = [
    "stage_id", "stage_name", "track", "purpose", "allowed_outputs",
    "blocked_outputs", "entry_gate", "exit_gate", "next_stage",
]

def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)

def require_file(path: Path) -> str:
    if not path.exists():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    if path.stat().st_size <= 0:
        fail(f"empty required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")

def require_phrases(path: Path, phrases: tuple[str, ...]) -> None:
    text = require_file(path)
    for phrase in phrases:
        if phrase not in text:
            fail(f"{path.relative_to(ROOT)} missing phrase: {phrase}")

def read_matrix() -> list[dict[str, str]]:
    with MATRIX.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        fail("next stage matrix has no data rows")
    missing = [col for col in MATRIX_COLUMNS if col not in rows[0]]
    if missing:
        fail(f"next stage matrix missing columns: {missing}")
    return rows

def main() -> int:
    for path in REQUIRED_FILES:
        require_file(path)

    require_phrases(
        ROADMAP,
        (
            "Pet-Med-AI Clinical Core Roadmap Refresh V1",
            "DiagnosticReport / Observation / ImagingStudy",
            "Integration API",
            "Local Device Gateway",
            "Lab Result Ingest Dry-run V1",
            "Imaging / DICOM Ingest Dry-run V1",
            "AI Lab Abnormal Summary V1",
            "AI Imaging Report Summary V1",
            "Treatment Recommendation Boundary V1",
            "Drug Dose Safety Framework V1",
            "Diagnostic Data Model Gap Review V1",
            "AI assists doctors",
        ),
    )

    require_phrases(
        MASTER,
        (
            "Pet-Med-AI Master Build Directory V1",
            "AI Consultation and Session System",
            "Species Knowledge Base",
            "Structured Consultation Templates",
            "Case System and Clinical Data Hub",
            "Diagnostic Data Model",
            "Lab / Imaging / Device Integration",
            "AI Clinical Reasoning",
            "Treatment and Drug Dose Safety",
            "Clinical Documentation",
            "Commercial Launch, Ops, Security",
        ),
    )

    require_phrases(
        HANDOFF,
        (
            "Pet-Med-AI Commercial V1 to Clinical Core Handoff V1",
            "GO_CLOSE_D0_D7_OBSERVATION_WINDOW",
            "DiagnosticReport / Observation / ImagingStudy production model",
            "GO_HANDOFF_TO_CLINICAL_CORE",
            "DIAGNOSTIC_DATA_MODEL_GAP_REVIEW_V1",
        ),
    )

    require_phrases(
        SCOPE,
        (
            "Pet-Med-AI Clinical Core Scope Lock V1",
            "This stage is a roadmap and validation stage only",
            "Out of Scope",
            "ENABLE_EMR_REAL_IMPORT=false",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
            "ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false",
            "decision=GO_TO_DIAGNOSTIC_DATA_MODEL_GAP_REVIEW_V1",
        ),
    )

    rows = read_matrix()
    required_stage_names = {
        "Clinical Core Roadmap Refresh V1",
        "Diagnostic Data Model Gap Review V1",
        "DiagnosticReport Observation ImagingStudy Design V1",
        "Integration API and Local Device Gateway Roadmap V1",
        "Lab Result Ingest Dry-run V1",
        "Imaging DICOM Ingest Dry-run V1",
        "AI Lab Abnormal Summary V1",
        "AI Imaging Report Summary V1",
        "Treatment Recommendation Boundary V1",
        "Drug Dose Safety Framework V1",
        "Drug Dose Knowledge Base V1",
    }
    found = {row.get("stage_name", "") for row in rows}
    missing = sorted(required_stage_names - found)
    if missing:
        fail(f"next stage matrix missing stages: {missing}")

    blocked_text = "\n".join(row.get("blocked_outputs", "") for row in rows)
    for forbidden_boundary in (
        "no real device ingest",
        "no real lab equipment ingest",
        "no production prescription write",
        "no runtime code or migration",
    ):
        if forbidden_boundary not in blocked_text:
            fail(f"next stage matrix missing blocked boundary: {forbidden_boundary}")

    print("PASS: Pet-Med-AI Clinical Core Roadmap Refresh V1 files are present and structurally valid")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
