#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "src" / "App.jsx"
DOC = ROOT / "docs" / "compliance" / "AI_REVIEW_AUDIT_UI_V1.md"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not APP.exists():
        return fail("frontend/src/App.jsx is missing")
    if not DOC.exists():
        return fail("docs/compliance/AI_REVIEW_AUDIT_UI_V1.md is missing")

    text = APP.read_text(encoding="utf-8")
    required = [
        "AiReviewAuditBlock",
        "handleSubmitAiReviewAudit",
        "/api/audit-log",
        "auditReviewAction",
        "auditClinicianId",
        "auditLogReceipt",
        "AI 建议人工覆核",
        "请先完成 AI 建议人工覆核并写入审计日志",
        "确认覆核并写入审计",
    ]
    for needle in required:
        if needle not in text:
            return fail(f"App.jsx missing expected UI/API marker: {needle}")

    if "disabled={previewingConsultCase || savingConsultCase || !consultSessionId || !isAuthed || auditReviewRequired}" not in text:
        return fail("Save preview button is not gated by auditReviewRequired")

    doc_text = DOC.read_text(encoding="utf-8")
    for needle in (
        "AI 建议人工覆核 UI V1",
        "POST /api/audit-log",
        "接受 / 修改 / 拒绝",
        "提交后不可更改",
    ):
        if needle not in doc_text:
            return fail(f"AI review audit UI doc missing expected content: {needle}")

    print("OK AI review audit UI: frontend review block and audit-log binding are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
