#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


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
    api = BACKEND / "emr_import_batch_api.py"
    main_py = BACKEND / "main.py"

    for path in (api, main_py):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    rc = require_text(
        api,
        (
            '@router.post("/{batch_id}/execution-dry-run"',
            "EmrImportExecutionDryRunIn",
            "build_execution_dry_run_report",
            "import_diff",
            "rollback_plan",
            "snapshot_required",
            "writes_case_database",
            "creates_case",
            "updates_case",
            "downloads_attachments",
            "executes_real_import",
            "can_execute_import",
            "would_create_count",
            "would_update_count",
            "blocked_count",
        ),
        "backend/emr_import_batch_api.py",
    )
    if rc:
        return rc

    api_text = api.read_text(encoding="utf-8")

    try:
        build_section = section_between(
            api_text,
            "def build_execution_dry_run_report(",
            (
                '\n\n@router.post("/{batch_id}/clinical-approval"',
                "\n\nCREATE_ONLY_PILOT_MAX_RECEIPTS",
                '\n\n@router.post("/{batch_id}/execute"',
                '\n\n@router.post("/{batch_id}/execution-dry-run"',
            ),
            "build_execution_dry_run_report",
        )
        route_section = section_between(
            api_text,
            '@router.post("/{batch_id}/execution-dry-run"',
            (
                '\n\n@router.get("", response_model=dict)',
                '\n\n@router.get("/{batch_id}"',
            ),
            "execution-dry-run route",
        )
    except ValueError as exc:
        return fail(str(exc))

    dry_run_scope = build_section + "\n" + route_section

    forbidden_needles = (
        "Case(",
        "EmrImportExecutionRun(",
        "EmrImportExecutionItemResult(",
        "AuditLog(",
        "db.add(",
        "db.commit(",
        '.status = "running"',
        ".status = 'running'",
        'downloads_attachments": True',
        'executes_real_import": True',
        'creates_case": True',
        'updates_case": True',
    )
    for needle in forbidden_needles:
        if needle in dry_run_scope:
            return fail(f"execution dry-run must not perform real import behavior inside dry-run scope: {needle}")

    for needle in (
        '"writes_database": False',
        '"writes_case_database": False',
        '"creates_case": False',
        '"updates_case": False',
        '"downloads_attachments": False',
        '"executes_real_import": False',
        '"can_execute_import": False',
        '"quality_gate"',
        '"import_diff"',
        '"rollback_plan"',
    ):
        if needle not in dry_run_scope:
            return fail(f"execution dry-run scope missing safety marker: {needle}")

    rc = require_text(
        main_py,
        (
            "emr_import_batch_api_router",
            "app.include_router(emr_import_batch_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    print("OK EMR real import execution dry-run: import diff and rollback plan endpoint are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
