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
    emr = BACKEND / "emr_webhook.py"
    if not emr.exists():
        return fail("missing backend/emr_webhook.py")
    py_compile.compile(str(emr), doraise=True)

    rc = require_text(
        emr,
        (
            '@router.post("/emr/case-mapping/dry-run"',
            "emr_case_mapping_dry_run",
            "build_case_create_preview",
            "CASE_CREATE_FIELDS",
            "patient_name",
            "chief_complaint",
            "exam_findings",
            "case_create",
            "case_create_fields",
            "import_plan",
            "can_promote_to_real_import",
            "writes_case_database",
            "creates_case",
            "updates_case",
            "downloads_attachments",
            "WebhookInbox",
        ),
        "backend/emr_webhook.py",
    )
    if rc:
        return rc

    text = emr.read_text(encoding="utf-8")
    forbidden = (
        "Case(",
        "ConsultSession(",
        "db.add(Case",
        "db.add(ConsultSession",
    )
    for needle in forbidden:
        if needle in text:
            return fail(f"case mapping dry-run must not create runtime records: {needle}")

    print("OK EMR to Case mapping dry-run: CaseCreate preview and import plan are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
