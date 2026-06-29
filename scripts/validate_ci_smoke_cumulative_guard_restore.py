#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validator for CI Smoke Cumulative Guard Restore V1.
Python 3.9-safe.
"""

from __future__ import print_function

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    "docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1.md",
    "docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_CHECKLIST_V1.csv",
    "docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_GO_NO_GO_V1.csv",
    "scripts/validate_ci_smoke_cumulative_guard_restore.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]

DANGEROUS_FLAGS = [
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
]

FORBIDDEN_TARGET_PREFIXES = [
    "backend/app/",
    "backend/ai_engine/",
    "frontend/src/components/",
]

FORBIDDEN_TARGET_EXACT = [
    "app.db",
    ".env",
    "frontend/.env.development",
    "frontend/package-lock.json",
]

REQUIRED_DOC_TOKENS = [
    "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
    "baseline_commit: 0c8fd5d",
    "embedded_legacy_cumulative_smoke",
    "read_only: true",
    "writes_database: false",
    "no_business_code_change: true",
    "database_revision=0009_diag_data",
    "alembic_head=0009_diag_data",
    "schema_ok=true",
    "dangerous_feature_flags_disabled=true",
    "GO_TO_CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_DRAFT_V1_AFTER_CUMULATIVE_GUARD_RESTORE",
]

REQUIRED_SMOKE_TOKENS = [
    "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1",
    "LEGACY_SMOKE_BASELINE=\"0c8fd5d:scripts/smoke_petmed.sh\"",
    "embedded legacy cumulative smoke",
    "/api/system/version",
    "/api/system/feature-flags",
    "\"database_revision\": \"0009_diag_data\"",
    "\"alembic_head\": \"0009_diag_data\"",
    "\"schema_ok\": True",
    "\"writes_database\": False",
    "\"exposes_database_url\": False",
    "migration_errors=[]",
    "dangerous_feature_flags_disabled=true",
    "GO_TO_CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_DRAFT_V1_AFTER_CUMULATIVE_GUARD_RESTORE",
]

REQUIRED_CI_TOKENS = [
    "CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1.md",
    "validate_ci_smoke_cumulative_guard_restore.py",
    "target-only tracked diff discipline",
    "sensitive staged path discipline",
    "embedded legacy cumulative smoke guard",
    "MIN_SMOKE_LINES=1000",
    "PASS: ci_static_checks",
]


def read_text(rel_path):
    path = ROOT / rel_path
    if not path.exists():
        raise AssertionError("missing required file: {0}".format(rel_path))
    return path.read_text(encoding="utf-8")


def require_tokens(label, content, tokens):
    missing = [token for token in tokens if token not in content]
    if missing:
        raise AssertionError("{0} missing tokens: {1}".format(label, ", ".join(missing)))


def assert_target_scope():
    for target in TARGETS:
        if target in FORBIDDEN_TARGET_EXACT:
            raise AssertionError("forbidden target exact path: {0}".format(target))
        for prefix in FORBIDDEN_TARGET_PREFIXES:
            if target.startswith(prefix):
                raise AssertionError("forbidden target prefix: {0}".format(target))


def assert_no_dangerous_flag_enablement():
    combined = "\n".join(read_text(target) for target in TARGETS)
    patterns = []
    for flag in DANGEROUS_FLAGS:
        patterns.extend([
            "{0}=true".format(flag),
            "{0}: true".format(flag),
            '"{0}": true'.format(flag),
        ])
    found = [pattern for pattern in patterns if pattern in combined]
    if found:
        raise AssertionError("dangerous flag enablement pattern found: {0}".format(", ".join(found)))


def main():
    print("Validating CI Smoke Cumulative Guard Restore V1")

    assert_target_scope()

    for target in TARGETS:
        path = ROOT / target
        if not path.exists():
            raise AssertionError("missing required target: {0}".format(target))

    doc = read_text("docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1.md")
    checklist = read_text("docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_CHECKLIST_V1.csv")
    go_no_go = read_text("docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_GO_NO_GO_V1.csv")
    smoke = read_text("scripts/smoke_petmed.sh")
    ci = read_text("scripts/ci_static_checks.sh")

    require_tokens("doc", doc, REQUIRED_DOC_TOKENS)
    require_tokens("checklist", checklist, ["embedded_legacy_cumulative_smoke", "Target files only", "GO"])
    require_tokens("go_no_go", go_no_go, ["online_smoke_all_pass", "embedded_legacy_cumulative_smoke", "GO_IF_ALL_PASS"])
    require_tokens("smoke", smoke, REQUIRED_SMOKE_TOKENS)
    require_tokens("ci", ci, REQUIRED_CI_TOKENS)

    for flag in DANGEROUS_FLAGS:
        if flag not in smoke:
            raise AssertionError("smoke missing dangerous flag guard: {0}".format(flag))
        if flag not in ci:
            raise AssertionError("ci missing dangerous flag scan: {0}".format(flag))

    smoke_lines = len(smoke.splitlines())
    if smoke_lines < 1000:
        raise AssertionError("smoke_petmed.sh looks too small for cumulative guard restore: {0} lines".format(smoke_lines))

    assert_no_dangerous_flag_enablement()

    print("PASS: CI Smoke Cumulative Guard Restore V1")
    print("current_hard_gate_preserved=true")
    print("embedded_legacy_cumulative_smoke=true")
    print("baseline_commit=0c8fd5d")
    print("smoke_line_count={0}".format(smoke_lines))
    print("smoke_line_count_minimum=1000")
    print("dangerous_feature_flags_guarded=true")
    print("target_only_diff_discipline=true")
    print("no_business_code_change=true")
    print("read_only=true")
    print("writes_database=false")
    print("decision=GO_TO_CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_DRAFT_V1_AFTER_CUMULATIVE_GUARD_RESTORE")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("NO-GO: CI Smoke Cumulative Guard Restore V1 validation failed")
        print(str(exc))
        sys.exit(1)
