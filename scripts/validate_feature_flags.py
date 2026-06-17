#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE_FLAGS = ROOT / "backend" / "feature_flags.py"
MAIN = ROOT / "backend" / "main.py"
DOC = ROOT / "docs" / "ops" / "FEATURE_FLAGS_SAFETY_GATES_V1.md"
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
    for path in (FEATURE_FLAGS, MAIN, Path(__file__)):
        if not path.exists():
            return fail(f"missing file: {path.relative_to(ROOT)}")
        py_compile.compile(str(path), doraise=True)

    rc = require_text(
        FEATURE_FLAGS,
        (
            'router = APIRouter(prefix="/api/system"',
            '@router.get("/feature-flags"',
            "FEATURE_FLAG_DEFINITIONS",
            "ENABLE_EMR_REAL_IMPORT",
            "ENABLE_EMR_IMPORT_CASE_UPDATE",
            "ENABLE_EMR_ATTACHMENT_DOWNLOAD",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY",
            "ENABLE_PREVENTIVE_SMS_DELIVERY",
            "ENABLE_PREVENTIVE_WECHAT_DELIVERY",
            "ENABLE_PREVENTIVE_EMAIL_DELIVERY",
            "ENABLE_PRESCRIPTION_STRUCTURED_WRITE",
            "ENABLE_DEVICE_REAL_INGEST",
            "ENABLE_BILLING_REAL_WRITE",
            "ENABLE_KB_PRODUCTION_PATCH",
            "ENABLE_CASE_DELETE_IMPORT",
            "all_dangerous_features_disabled",
            "writes_database",
            "exposes_secret_values",
            "assert_feature_enabled",
        ),
        "backend/feature_flags.py",
    )
    if rc:
        return rc

    text = FEATURE_FLAGS.read_text(encoding="utf-8")
    forbidden = (
        "db.add(",
        "db.commit(",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "DROP ",
        "ALTER TABLE",
        "DATABASE_URL",
        "SECRET_KEY",
    )
    for needle in forbidden:
        if needle in text:
            return fail(f"feature flag endpoint must be read-only and must not expose secrets: {needle}")

    # Make sure high-risk features are default-disabled in the definitions.
    for flag in (
        "ENABLE_EMR_REAL_IMPORT",
        "ENABLE_EMR_IMPORT_CASE_UPDATE",
        "ENABLE_EMR_ATTACHMENT_DOWNLOAD",
        "ENABLE_PREVENTIVE_AUTO_DELIVERY",
        "ENABLE_PREVENTIVE_SMS_DELIVERY",
        "ENABLE_PREVENTIVE_WECHAT_DELIVERY",
        "ENABLE_PREVENTIVE_EMAIL_DELIVERY",
        "ENABLE_PRESCRIPTION_STRUCTURED_WRITE",
        "ENABLE_DEVICE_REAL_INGEST",
        "ENABLE_BILLING_REAL_WRITE",
        "ENABLE_CASE_DELETE_IMPORT",
    ):
        marker = f'"{flag}":'
        idx = text.find(marker)
        if idx < 0:
            return fail(f"missing feature flag definition: {flag}")
        window = text[idx: idx + 380]
        if '"default": False' not in window:
            return fail(f"feature flag must default to false: {flag}")

    rc = require_text(
        MAIN,
        (
            "feature_flags_router",
            "app.include_router(feature_flags_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Pet-Med-AI Feature Flag / Safety Gate V1",
            "GET /api/system/feature-flags",
            "ENABLE_EMR_REAL_IMPORT=false",
            "ENABLE_EMR_IMPORT_CASE_UPDATE=false",
            "ENABLE_EMR_ATTACHMENT_DOWNLOAD=false",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
            "ENABLE_PREVENTIVE_SMS_DELIVERY=false",
            "ENABLE_PREVENTIVE_WECHAT_DELIVERY=false",
            "ENABLE_PREVENTIVE_EMAIL_DELIVERY=false",
            "ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false",
            "writes_database=false",
        ),
        "feature flag doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_feature_flags.py",
            "system feature flags",
            "/api/system/feature-flags",
            "system_feature_flags",
            "all_dangerous_features_disabled",
            "ENABLE_EMR_REAL_IMPORT",
            "writes_database",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK feature flags: safety gates default off and read-only system endpoint is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
