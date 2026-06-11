#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGE = ROOT / "frontend" / "src" / "pages" / "PreventiveCareNotificationQueuePage.jsx"
APP = ROOT / "frontend" / "src" / "App.jsx"
DOC = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_NOTIFICATION_QUEUE_UI_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require(path: Path, needles: tuple[str, ...], label: str) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    checks = [
        (
            PAGE,
            (
                "Preventive Care Reminder Notification Queue UI V1",
                "/api/preventive-care/notification-queue",
                "/api/preventive-care/notification-queue/draft",
                "mark-contacted",
                "预防保健前台待联系队列",
                "创建人工联系草稿",
                "人工审核",
                "标记已人工联系",
                "auto_send=false",
                "sends_external_message=false",
            ),
            "PreventiveCareNotificationQueuePage.jsx",
        ),
        (
            APP,
            (
                "PreventiveCareNotificationQueuePage",
                "/preventive-care/notification-queue",
                "预防保健待联系队列",
            ),
            "frontend/src/App.jsx",
        ),
        (
            DOC,
            (
                "Preventive Care Reminder Notification Queue UI V1",
                "/preventive-care/notification-queue",
                "sends_external_message=false",
                "auto_send=false",
                "manual_review_required=true",
            ),
            "notification queue UI doc",
        ),
        (
            SMOKE,
            (
                "validate_preventive_care_notification_queue_ui.py",
                "preventive care notification queue UI validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_preventive_care_notification_queue_ui.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK preventive care notification queue UI: route, page and manual queue actions are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
