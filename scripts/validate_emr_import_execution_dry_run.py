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
    forbidden_needles = (
        "Case(",
        '.status = "running"',
        ".status = 'running'",
        'downloads_attachments": True',
        'executes_real_import": True',
        'creates_case": True',
        'updates_case": True',
    )
    for needle in forbidden_needles:
        if needle in api_text:
            return fail(f"execution dry-run must not perform real import behavior: {needle}")

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
