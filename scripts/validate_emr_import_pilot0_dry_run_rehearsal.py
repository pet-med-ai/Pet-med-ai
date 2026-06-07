#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "runbook": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_V1.md",
    "checklist": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_CHECKLIST.csv",
    "operator": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_OPERATOR_RUNBOOK.csv",
    "evidence": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_EVIDENCE_TEMPLATE.csv",
    "decision": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_GO_NO_GO_TEMPLATE.csv",
    "curl": ROOT / "docs" / "integrations" / "EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_API_CURL_TEMPLATE.md",
}
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
            FILES["runbook"],
            (
                "EMR real import pilot_0 dry-run rehearsal V1",
                "ENABLE_EMR_REAL_IMPORT=false throughout",
                "webhook_inbox receipt persistence",
                "execution dry-run",
                "clinical approval",
                "HTTP 403",
                "feature flag disabled",
                "ENABLE_EMR_REAL_IMPORT remained false throughout",
            ),
            "dry-run rehearsal runbook",
        ),
        (
            FILES["checklist"],
            (
                "phase,item,owner",
                "Create signed webhook dry-run",
                "Run execution dry-run",
                "Prove execute blocked",
                "Online smoke after rehearsal",
            ),
            "dry-run rehearsal checklist",
        ),
        (
            FILES["operator"],
            (
                "step_number,phase,owner",
                "Send signed dry-run webhook",
                "Call execute while flag disabled",
                "Complete evidence template",
            ),
            "dry-run rehearsal operator runbook",
        ),
        (
            FILES["evidence"],
            (
                "rehearsal_id,date,operator_id",
                "receipt_id",
                "batch_id",
                "dry_run_quality_gate_passed",
                "execute_blocked_by_feature_flag",
            ),
            "dry-run rehearsal evidence template",
        ),
        (
            FILES["decision"],
            (
                "decision_id,rehearsal_id,batch_id",
                "decision",
                "next_stage_allowed",
            ),
            "dry-run rehearsal go/no-go template",
        ),
        (
            FILES["curl"],
            (
                "EMR real import pilot_0 dry-run rehearsal API cURL template",
                "/api/webhooks/emr/case-mapping/dry-run",
                "receipt_persisted=true",
                "ENABLE_EMR_REAL_IMPORT=false",
            ),
            "dry-run rehearsal cURL template",
        ),
        (
            SMOKE,
            (
                "validate_emr_import_pilot0_dry_run_rehearsal.py",
                "emr real import pilot0 dry-run rehearsal validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_emr_import_pilot0_dry_run_rehearsal.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK EMR real import pilot_0 dry-run rehearsal: runbook, templates and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
