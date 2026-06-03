#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

REQUIRED_FILES = [
    BACKEND / "audit_log_api.py",
    BACKEND / "main.py",
    BACKEND / "models.py",
]


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require(text: str, needle: str, label: str) -> int:
    if needle not in text:
        return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        return fail("missing files: " + ", ".join(missing))

    for path in REQUIRED_FILES:
        py_compile.compile(str(path), doraise=True)

    api_text = (BACKEND / "audit_log_api.py").read_text(encoding="utf-8")
    main_text = (BACKEND / "main.py").read_text(encoding="utf-8")
    models_text = (BACKEND / "models.py").read_text(encoding="utf-8")

    expectations = [
        (api_text, 'router = APIRouter(prefix="/api", tags=["audit"])', "audit API"),
        (api_text, '@router.post("/audit-log", response_model=dict, status_code=201)', "audit API"),
        (api_text, "class AuditLogCreateIn(BaseModel):", "audit API"),
        (api_text, "confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)", "audit API"),
        (api_text, "AuditLog(", "audit API"),
        (api_text, "append_only", "audit API"),
        (main_text, "audit_log_api_router", "main.py"),
        (main_text, "app.include_router(audit_log_api_router)", "main.py"),
        (models_text, "class AuditLog(Base):", "models.py"),
        (models_text, '__tablename__ = "audit_log"', "models.py"),
    ]

    for text, needle, label in expectations:
        rc = require(text, needle, label)
        if rc:
            return rc

    forbidden = [
        '@router.put("/audit-log',
        '@router.delete("/audit-log',
        '@router.patch("/audit-log',
    ]
    for needle in forbidden:
        if needle in api_text:
            return fail(f"audit API must be append-only; remove route decorator: {needle}")

    print("OK audit log append-only API: create-only router and main.py include are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
