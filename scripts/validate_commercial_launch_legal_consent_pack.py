#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PACK = ROOT / "docs" / "legal" / "COMMERCIAL_LAUNCH_CONSENT_PACK_V1.md"
CLIENT_CONSENT = ROOT / "docs" / "legal" / "CLIENT_DATA_USE_CONSENT_TEMPLATE_V1.md"
AI_NOTICE = ROOT / "docs" / "legal" / "AI_ASSISTED_CLINICAL_NOTICE_V1.md"
REMINDER_NOTICE = ROOT / "docs" / "legal" / "PREVENTIVE_CARE_REMINDER_NOTICE_V1.md"
OPTOUT = ROOT / "docs" / "legal" / "CLIENT_DATA_OPT_OUT_SOP_V1.md"
PRIVACY = ROOT / "docs" / "legal" / "PRIVACY_DATA_HANDLING_SOP_V1.md"
CHECKLIST = ROOT / "docs" / "legal" / "COMMERCIAL_LAUNCH_LEGAL_CONSENT_CHECKLIST.csv"
RISKS = ROOT / "docs" / "legal" / "COMMERCIAL_LAUNCH_LEGAL_RISK_REGISTER.csv"
EVIDENCE = ROOT / "docs" / "legal" / "COMMERCIAL_LAUNCH_LEGAL_REVIEW_EVIDENCE_TEMPLATE.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


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


def require_csv(path: Path, required_columns: tuple[str, ...], needles: tuple[str, ...], label: str, min_rows: int = 1) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")

    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return fail(f"{label} has no header")
            missing = [col for col in required_columns if col not in reader.fieldnames]
            if missing:
                return fail(f"{label} missing columns: {', '.join(missing)}")
            rows = list(reader)
    except Exception as exc:
        return fail(f"{label} is not valid CSV: {exc}")

    if len(rows) < min_rows:
        return fail(f"{label} should contain at least {min_rows} rows")
    return 0


def main() -> int:
    py_compile.compile(str(Path(__file__)), doraise=True)

    rc = require_text(
        PACK,
        (
            "Commercial Launch Legal / Consent Pack V1",
            "not jurisdiction-specific legal advice",
            "AI consultation assistance",
            "automated SMS sending",
            "EMR real import",
            "clinic_owner_signoff",
            "legal_review_signoff",
            "AI output is not a final diagnosis",
            "Preventive care reminders are convenience reminders",
            "NO-GO until legal/professional review",
        ),
        "legal consent pack",
    )
    if rc:
        return rc

    rc = require_text(
        CLIENT_CONSENT,
        (
            "Client Data Use Consent Template V1",
            "AI output is not a final diagnosis",
            "AI output is not a prescription",
            "does not replace a veterinarian",
            "preventive care reminders",
            "opt out",
            "Commercial V1 does not require external SMS, WeChat, email",
        ),
        "client data use consent template",
    )
    if rc:
        return rc

    rc = require_text(
        AI_NOTICE,
        (
            "AI Assisted Clinical Notice V1",
            "Pet-Med-AI does not replace the veterinarian",
            "Veterinarian final responsibility statement",
            "not be represented as",
            "autonomous prescription system",
            "Required clinical review",
        ),
        "AI assisted clinical notice",
    )
    if rc:
        return rc

    rc = require_text(
        REMINDER_NOTICE,
        (
            "Preventive Care Reminder Notice V1",
            "Non-diagnosis / non-prescription statement",
            "No automated external sending in Commercial V1",
            "SMS",
            "WeChat",
            "email",
            "opt-out",
        ),
        "preventive care reminder notice",
    )
    if rc:
        return rc

    rc = require_text(
        OPTOUT,
        (
            "Client Data Opt-Out SOP V1",
            "opt_out_all",
            "opt_out_sms",
            "opt_out_wechat",
            "opt_out_email",
            "Commercial V1 has no live SMS/WeChat/email automated sending",
            "client is contacted after opt-out",
        ),
        "client data opt-out SOP",
    )
    if rc:
        return rc

    rc = require_text(
        PRIVACY,
        (
            "Privacy / Data Handling SOP V1",
            "Data minimization",
            "Owner-scoped data",
            "User B must not access User A data",
            "Do not commit or share evidence containing",
            "DATABASE_URL",
            "cross-user data visible",
        ),
        "privacy data handling SOP",
    )
    if rc:
        return rc

    rc = require_csv(
        CHECKLIST,
        (
            "check_id",
            "area",
            "item",
            "required_state",
            "evidence",
            "owner",
            "go_no_go",
            "status",
            "notes",
        ),
        (
            "LEGAL-001",
            "Client data use consent template exists",
            "AI assisted clinical notice exists",
            "Veterinarian final responsibility statement",
            "Preventive reminder notice exists",
            "Client opt-out SOP exists",
            "Legal/professional review completed",
            "No secrets in evidence",
        ),
        "legal consent checklist",
        min_rows=12,
    )
    if rc:
        return rc

    rc = require_csv(
        RISKS,
        (
            "risk_id",
            "risk",
            "severity",
            "trigger",
            "mitigation",
            "go_no_go",
            "owner",
            "status",
        ),
        (
            "LEGAL-R001",
            "no legal/professional review",
            "AI represented as replacing veterinarian",
            "preventive reminder represented as diagnosis/prescription",
            "automated external sending implied enabled",
            "opt-out ignored",
            "jurisdiction mismatch",
        ),
        "legal consent risk register",
        min_rows=10,
    )
    if rc:
        return rc

    rc = require_csv(
        EVIDENCE,
        (
            "review_id",
            "date",
            "clinic_name",
            "legal_review_owner",
            "legal_review_completed",
            "clinic_owner_signoff",
            "clinical_director_signoff",
            "security_owner_signoff",
            "release_owner_signoff",
            "client_consent_template_approved",
            "ai_notice_approved",
            "preventive_notice_approved",
            "opt_out_sop_approved",
            "privacy_sop_approved",
            "no_secrets_in_evidence",
            "no_phi_in_evidence",
            "commercial_v1_manual_contact_only",
            "automated_live_delivery_disabled",
            "emr_real_import_disabled",
            "decision",
            "notes",
        ),
        (
            "LEGAL-CONSENT-V1",
            "NO-GO until review and signoff are filled",
        ),
        "legal review evidence template",
        min_rows=1,
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_launch_legal_consent_pack.py",
            "commercial launch legal consent pack validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_launch_legal_consent_pack.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial launch legal consent pack: consent templates, notices, SOPs, checklist, risk register and evidence template are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
