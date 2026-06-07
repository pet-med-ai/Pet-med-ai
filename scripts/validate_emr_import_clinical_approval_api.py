#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "backend" / "emr_import_batch_api.py"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
DOC = ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_CLINICAL_APPROVAL_API_V1.md"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def section_between(text: str, start_marker: str, end_markers: tuple[str, ...], label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"missing section start for {label}: {start_marker}")

    candidates = []
    for marker in end_markers:
        idx = text.find(marker, start + len(start_marker))
        if idx >= 0:
            candidates.append(idx)

    end = min(candidates) if candidates else len(text)
    return text[start:end]


def main() -> int:
    for path in (API, SMOKE, DOC):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
    py_compile.compile(str(API), doraise=True)

    rc = require_text(
        API,
        (
            "EmrImportClinicalApprovalIn",
            '@router.post("/{batch_id}/clinical-approval"',
            "emr_import_clinical_approval",
            "clinical_approval_api",
            "build_execution_dry_run_report",
            "quality_gate",
            "writes_emr_import_batches",
            "writes_audit_log",
            "writes_case_database",
            "creates_case",
            "updates_case",
            "downloads_attachments",
            "executes_real_import",
            "can_execute_import",
            "audit_log_id",
        ),
        "backend/emr_import_batch_api.py",
    )
    if rc:
        return rc

    text = API.read_text(encoding="utf-8")

    try:
        clinical_section = section_between(
            text,
            '@router.post("/{batch_id}/clinical-approval"',
            (
                "\n\nCREATE_ONLY_PILOT_MAX_RECEIPTS",
                '\n\n@router.post("/{batch_id}/execute"',
                '\n\n@router.post("/{batch_id}/execution-dry-run"',
                '\n\n@router.get("", response_model=dict)',
            ),
            "clinical approval route",
        )
    except ValueError as exc:
        return fail(str(exc))

    # These markers are forbidden only inside the clinical-approval route.
    # They are allowed in the real /execute create-only endpoint.
    forbidden = (
        "Case(",
        "EmrImportExecutionRun(",
        "EmrImportExecutionItemResult(",
        "db.delete(",
        ".delete(",
        'downloads_attachments": True',
        'creates_case": True',
        'updates_case": True',
        'executes_real_import": True',
    )
    for needle in forbidden:
        if needle in clinical_section:
            return fail(f"clinical approval API must not perform real import or Case writes inside clinical section: {needle}")

    for needle in (
        '"writes_emr_import_batches": True',
        '"writes_audit_log": True',
        '"writes_case_database": False',
        '"creates_case": False',
        '"updates_case": False',
        '"downloads_attachments": False',
        '"executes_real_import": False',
        '"can_execute_import": False',
        '"quality_gate"',
        '"audit_log_id"',
    ):
        if needle not in clinical_section:
            return fail(f"clinical approval section missing safety marker: {needle}")

    rc = require_text(
        SMOKE,
        (
            "emr real import clinical approval",
            "/clinical-approval",
            "emr_import_clinical_approval",
            "writes_emr_import_batches",
            "writes_audit_log",
            "writes_case_database",
            "can_execute_import",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK EMR real import clinical approval API: approval gate and safety checks are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
