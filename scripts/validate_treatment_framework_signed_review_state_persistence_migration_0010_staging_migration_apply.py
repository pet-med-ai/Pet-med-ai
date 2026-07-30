#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate fail-closed PMAI-P0-04 governance preparation."""
from __future__ import print_function

import argparse
import ast
import csv
import glob
import hashlib
import io
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "PMAI-P0-04"
EXPECTED_HEAD = "b85e48a80019e522a5b5d1f3df6531752de2c25c"
EXPECTED_EVIDENCE_SHA = "da52b46466a65316331d420c809bc406e49dfa722b1b5875667e30db50eef213"
EXPECTED_DRAFT_SHA = "bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d"
DRAFT_REVISION = "0010_treatment_framework_signed_review_states"
CANDIDATE_SHORT_REVISION = "0010_signed_review_states"
ENTRY_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1"
HOLD_DECISION = "HOLD_PMAI_P0_04_PENDING_STAGING_0010_APPLY_GOVERNANCE_AND_EVIDENCE"
NO_GO_DECISION = "NO_GO_TO_PMAI_P0_04_EXECUTION"

DOC_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md"
CHECKLIST_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv"
REGISTER_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv"
MATRIX_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv"
GO_NO_GO_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv"
RUNNER_REL = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"
VALIDATOR_REL = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"
CI_REL = "scripts/ci_static_checks.sh"
SMOKE_REL = "scripts/smoke_petmed.sh"
P0_03_DOC_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md"
DRAFT_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt"
GUARDRAILS_REL = "docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md"
MODELS_REL = "backend/models.py"
RENDER_REL = "render.yaml"

TARGET_PATHS = [
    DOC_REL,
    CHECKLIST_REL,
    REGISTER_REL,
    MATRIX_REL,
    GO_NO_GO_REL,
    RUNNER_REL,
    VALIDATOR_REL,
    CI_REL,
    SMOKE_REL,
]

ARTIFACT_SHA256 = {
    DOC_REL: "f8a8e0972eef311702153b46c98beea9b8bfc152213fdeb7df865cce35ac84c4",
    CHECKLIST_REL: "9f5b7923aff27540c1a4044935091563053bc2a66fb6f08bc955d4a522cd46e8",
    REGISTER_REL: "dc3eb73179af533d76813ac9117fe3a3ace2670aed98c6fa2f3fa6381a97713d",
    MATRIX_REL: "dc6c261dce7b16d068d777bf7d76938160c8716b57bd838736e1f51a5df08ef8",
    GO_NO_GO_REL: "5a48a73cba8fac8d08429e5723fd5a921ca31a4c544568289d6d81da2c0e668e",
    RUNNER_REL: "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f",
    CI_REL: "48087a354614ee2a651b39e86187bd4f4e3ef51a681c488bb235ebc60266bc6e",
    SMOKE_REL: "49d51c300dc243b460cca052ec51efcc21853a5e606427178de892ec452959d8",
}

CHECKLIST_IDS = ["P04-C%03d" % number for number in range(1, 25)]
REGISTER_IDS = ["P04-E%03d" % number for number in range(1, 21)]
MATRIX_IDS = ["P04-T%03d" % number for number in range(1, 21)]
GO_NO_GO_IDS = ["P04-G%03d" % number for number in range(1, 11)]

P0_03_COMPAT_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1_smoke_petmed_compatibility_gate"
P0_03_COMPAT_END = "# <<< treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1_smoke_petmed_compatibility_gate"
P0_04_RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate"
P0_04_RUNTIME_END = "# <<< treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate"

DANGEROUS_FLAGS = (
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
)


def require(condition, message):
    if not condition:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def read(rel):
    path = ROOT / rel
    require(path.is_file(), "missing required path: " + rel)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        require(False, "non-UTF-8 required path: " + rel)


def read_rows(rel, headers, ids):
    reader = csv.DictReader(io.StringIO(read(rel)))
    require(reader.fieldnames == headers, rel + " header mismatch")
    rows = list(reader)
    require([row[headers[0]] for row in rows] == ids, rel + " canonical row IDs mismatch")
    require(all(None not in row and "" not in row.values() for row in rows), rel + " has missing values")
    return rows


def marker_value(text, key):
    matches = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", text)
    require(len(matches) == 1, "marker must occur exactly once: " + key)
    return matches[0]


def require_tokens(label, text, tokens):
    for token in tokens:
        require(token in text, label + " missing token: " + token)


def check_artifact_hashes():
    for rel, expected in ARTIFACT_SHA256.items():
        path = ROOT / rel
        require(path.is_file(), "missing hash-locked artifact: " + rel)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(
            actual == expected,
            "hash-locked governance artifact changed: %s expected %s got %s"
            % (rel, expected, actual),
        )


def marked_block(text, begin, end, label):
    require(text.count(begin) == 1, label + " begin marker count mismatch")
    require(text.count(end) == 1, label + " end marker count mismatch")
    start = text.index(begin)
    finish = text.index(end, start) + len(end)
    return text[start:finish], start, finish


def check_document():
    doc = read(DOC_REL)
    expected = {
        "stage_id": STAGE_ID,
        "stage_type": "staging_migration_apply_governance_preparation",
        "PACKAGE_INITIALIZED": "true",
        "STAGE_STATUS": "IN_PROGRESS",
        "EVIDENCE_COMPLETENESS": "PENDING_GOVERNANCE_AND_EXTERNAL_EXECUTION",
        "P0_03_PREREQUISITE_COMPLETE": "true",
        "P0_04_ENTRY_AUTHORIZED": "true",
        "P0_04_GOVERNANCE_PREPARATION_COMPLETE": "true",
        "P0_04_EXECUTION_AUTHORIZED": "false",
        "STAGING_0010_APPLY_AUTHORIZED": "false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED": "false",
        "ACTIVE_0010_MIGRATION_FILE_ALLOWED": "false",
        "STAGING_DEPLOY_AUTHORIZED": "false",
        "STAGING_0010_MIGRATION_EXECUTED": "false",
        "PRODUCTION_MIGRATION_AUTHORIZED": "false",
        "PRODUCTION_MIGRATION_EXECUTED": "false",
        "PACKAGE_CONNECTS_DATABASE": "false",
        "PACKAGE_WRITES_DATABASE": "false",
        "RUNNER_EXECUTED_BY_CI": "false",
        "CASE_TREATMENT_WRITE_PERFORMED": "false",
        "PRESCRIPTION_WRITE_PERFORMED": "false",
        "MEDICATION_DETAIL_OUTPUT": "false",
        "CLIENT_FACING_OUTPUT": "false",
        "initializer_baseline_commit_sha": EXPECTED_HEAD,
        "previous_stage_status": "COMPLETE",
        "previous_stage_evidence_sha256": EXPECTED_EVIDENCE_SHA,
        "previous_stage_decision": ENTRY_DECISION,
        "source_database_revision": "0009_diag_data",
        "source_alembic_head": "0009_diag_data",
        "inactive_draft_sha256": EXPECTED_DRAFT_SHA,
        "inactive_draft_revision": DRAFT_REVISION,
        "inactive_draft_revision_length": "45",
        "alembic_revision_max_length": "32",
        "candidate_short_revision": CANDIDATE_SHORT_REVISION,
        "candidate_short_revision_length": "25",
        "candidate_short_revision_approved": "false",
        "draft_revision_id_approved": "false",
        "draft_audit_log_reference_type": "String(120)",
        "expected_audit_log_id_type": "String(64)",
        "draft_audit_log_reference_nullable": "true",
        "draft_audit_log_reference_index_only": "true",
        "draft_audit_log_foreign_key_present": "false",
        "draft_idempotency_key_non_null": "false",
        "draft_idempotency_unique_constraint_present": "false",
        "draft_case_foreign_key_ondelete_specified": "false",
        "migration_schema_review_approved": "false",
        "production_auto_deploy_trigger": "commit",
        "staging_only_branch_or_commit_pin_verified": "false",
        "production_deployment_freeze_verified": "false",
        "production_target_excluded": "false",
        "fresh_post_p0_03_staging_backup_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "disposable_restore_upgrade_complete": "false",
        "disposable_restore_downgrade_to_0009_complete": "false",
        "rollback_restore_path_verified": "false",
        "source_staging_fresh_backup_verified": "false",
        "source_commit_sha_pinned": "false",
        "active_migration_sha256_pinned": "false",
        "exact_target_upgrade_command_approved": "false",
        "pre_apply_schema_evidence_complete": "false",
        "post_apply_schema_evidence_complete": "false",
        "critical_row_parity_verified": "false",
        "new_table_row_count_zero_verified": "false",
        "production_remains_0009_verified": "false",
        "external_execution_evidence_complete": "false",
        "runner_execution_enabled": "false",
        "network_access": "false",
        "database_connection": "false",
        "database_write": "false",
        "alembic_invoked": "false",
        "migration_created": "false",
        "migration_executed": "false",
        "external_evidence_committed": "false",
        "case_treatment_write": "false",
        "prescription_write": "false",
        "medication_detail_output": "false",
        "production_database_write": "false",
        "decision": HOLD_DECISION,
    }
    for key, value in expected.items():
        require(marker_value(doc, key) == value, "document marker mismatch: " + key)
    require_tokens(
        "governance sequence",
        doc,
        [
            "fresh staging backup because P0-03 created later staging records",
            "restore that backup into a disposable database",
            "take a new source-staging backup immediately before the real apply",
            "alembic upgrade <approved-exact-revision>",
            "`alembic upgrade head`",
            "`alembic stamp head`",
            "critical-table row parity",
            "newly created table",
        ],
    )
    return doc


def check_previous_stage():
    p003 = read(P0_03_DOC_REL)
    require_tokens(
        "P0-03 prerequisite",
        p003,
        [
            "stage_id=PMAI-P0-03",
            "STAGE_STATUS=COMPLETE",
            "EVIDENCE_COMPLETENESS=COMPLETE",
            "AUTHENTICATED_STAGING_SMOKE_COMPLETE=true",
            "P0_04_ENTRY_AUTHORIZED=true",
            "STAGING_0010_APPLY_AUTHORIZED=false",
            "evidence_artifact_sha256=" + EXPECTED_EVIDENCE_SHA,
            "decision=" + ENTRY_DECISION,
        ],
    )


def check_draft_and_repository_contracts():
    draft_path = ROOT / DRAFT_REL
    require(draft_path.is_file(), "inactive draft is missing")
    require(hashlib.sha256(draft_path.read_bytes()).hexdigest() == EXPECTED_DRAFT_SHA, "inactive draft SHA-256 mismatch")
    draft = read(DRAFT_REL)
    revision_match = re.search(r'(?m)^revision = "([^"]+)"$', draft)
    require(revision_match is not None, "inactive draft revision missing")
    require(revision_match.group(1) == DRAFT_REVISION, "inactive draft revision changed")
    require(len(revision_match.group(1)) == 45, "inactive draft revision length blocker changed")
    require(len(revision_match.group(1)) > 32, "draft revision must remain recorded as blocked")
    require('down_revision = "0009_diag_data"' in draft, "inactive draft down_revision changed")
    require('sa.Column("audit_log_reference", sa.String(length=120), nullable=True)' in draft, "inactive draft audit reference shape changed")
    require('op.create_index("ix_tfsrs_audit_log_reference"' in draft, "inactive draft audit index missing")
    require('["audit_log.log_id"]' not in draft, "inactive draft unexpectedly contains audit foreign key")
    require("UniqueConstraint" not in draft, "inactive draft unexpectedly contains unique constraint")
    case_fk = re.search(r'sa\.ForeignKeyConstraint\(\["case_id"\].*?\)', draft)
    require(case_fk is not None, "inactive draft case foreign key missing")
    require("ondelete" not in case_fk.group(0), "inactive draft case lifecycle blocker changed")

    guardrails = read(GUARDRAILS_REL)
    require("<= 32 characters" in guardrails, "Alembic 32-character guardrail missing")
    require("VARCHAR(32)" in guardrails, "Alembic version-column guardrail missing")

    models = read(MODELS_REL)
    audit_class = re.search(r"(?ms)^class AuditLog\b.*?(?=^class \w+\b|\Z)", models)
    require(audit_class is not None, "AuditLog model missing")
    require('__tablename__ = "audit_log"' in audit_class.group(0), "audit_log table mapping missing")
    require(re.search(r"log_id:.*?String\(64\).*?primary_key=True", audit_class.group(0), flags=re.S) is not None, "audit_log.log_id String(64) primary key contract changed")

    render = read(RENDER_REL)
    production = re.search(
        r"(?ms)^  - type: web\n    name: pet-med-ai-backend\n(.*?)(?=^  - type:|\Z)",
        render,
    )
    require(production is not None, "production backend service block missing")
    require("autoDeployTrigger: commit" in production.group(0), "production auto-deploy risk changed")


def check_csvs():
    checklist = read_rows(
        CHECKLIST_REL,
        ["item_id", "area", "requirement", "status", "evidence", "blocking", "decision"],
        CHECKLIST_IDS,
    )
    register = read_rows(
        REGISTER_REL,
        ["evidence_id", "category", "evidence_item", "status", "value", "storage", "secret_safety", "decision"],
        REGISTER_IDS,
    )
    matrix = read_rows(
        MATRIX_REL,
        ["test_id", "phase", "test", "expected", "status", "evidence", "write_scope", "decision"],
        MATRIX_IDS,
    )
    go_no_go = read_rows(
        GO_NO_GO_REL,
        ["gate_id", "gate", "required_state", "current_state", "evidence_status", "decision", "notes"],
        GO_NO_GO_IDS,
    )

    pending_statuses = {
        "BLOCKED_REQUIRES_DECISION",
        "PENDING_EXTERNAL_EVIDENCE",
        "PENDING_GOVERNANCE",
        "HOLD",
    }
    for row in checklist:
        if row["blocking"] == "yes" and row["status"] in pending_statuses:
            require(row["decision"] == NO_GO_DECISION, "pending checklist gate is not NO-GO: " + row["item_id"])
    require(sum(row["status"] == "BLOCKED_REQUIRES_DECISION" for row in checklist) == 4, "four schema-decision blockers are required")
    require(any(row["status"] == "UNRECORDED" for row in register), "evidence register must retain unrecorded execution evidence")
    require(any(row["status"] == "NOT_AUTHORIZED" for row in matrix), "test matrix must retain unauthorized execution tests")
    for row in go_no_go[2:-1]:
        require(row["decision"] == NO_GO_DECISION, "pending Go/No-Go gate is not NO-GO: " + row["gate_id"])
    require(go_no_go[-1]["decision"] == HOLD_DECISION, "final Go/No-Go decision mismatch")


def check_runner():
    runner = read(RUNNER_REL)
    try:
        tree = ast.parse(runner, filename=RUNNER_REL)
    except SyntaxError as exc:
        require(False, "runner syntax error: %s" % exc)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden_imports = {"requests", "psycopg", "psycopg2", "sqlalchemy", "alembic", "subprocess", "socket", "urllib", "httpx"}
    require(not (imported & forbidden_imports), "runner has execution-capable import")
    require_tokens(
        "locked runner",
        runner,
        [
            "EXECUTION_ENABLED = False",
            'REQUIRED_FUTURE_CONFIRMATION = "PMAI-P0-04-0010-STAGING-MIGRATION-APPLY"',
            'parser.add_argument("--execute", action="store_true")',
            "PMAI-P0-04 migration execution is not authorized",
            "return 1",
        ],
    )
    for token in ("--database-url", "DATABASE_URL", "os.environ", "upgrade head", "stamp head"):
        require(token not in runner, "runner contains forbidden execution token: " + token)


def check_secret_safety():
    combined = "\n".join(read(rel) for rel in (DOC_REL, CHECKLIST_REL, REGISTER_REL, MATRIX_REL, GO_NO_GO_REL))
    require(re.search(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://", combined) is None, "connection URI found in governance artifacts")
    require(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", combined) is None, "email address found in governance artifacts")
    require(re.search(r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[^\s,;<>]+", combined) is None, "credential-like value found in governance artifacts")
    all_targets = "\n".join(read(rel) for rel in TARGET_PATHS)
    for flag in DANGEROUS_FLAGS:
        for pattern in (flag + "=true", flag + ": true", '"' + flag + '": true'):
            require(pattern not in all_targets, "dangerous feature flag enablement found: " + pattern)


def parse_ci_targets(ci):
    match = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)", ci)
    require(match is not None, "CI TARGETS block missing")
    return re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)


def executable_python_lines(text):
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("python3 "):
            continue
        if stripped.startswith("python3 -m py_compile "):
            continue
        lines.append(stripped)
    return lines


def check_ci():
    ci = read(CI_REL)
    require(parse_ci_targets(ci) == TARGET_PATHS, "CI TARGETS are not the exact PMAI-P0-04 nine-file scope")
    require_tokens(
        "CI governance gate",
        ci,
        [
            "# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1",
            "python3 -m py_compile " + RUNNER_REL,
            "python3 -m py_compile " + VALIDATOR_REL,
            "python3 " + VALIDATOR_REL,
            "P0-03 completed prerequisite static compatibility",
            "PMAI-P0-04 governance preparation package validator",
            "STAGE_STATUS=IN_PROGRESS",
            "EVIDENCE_COMPLETENESS=PENDING_GOVERNANCE_AND_EXTERNAL_EXECUTION",
            "P0_04_EXECUTION_AUTHORIZED=false",
            "STAGING_0010_APPLY_AUTHORIZED=false",
            "ACTIVE_0010_MIGRATION_FILE_ALLOWED=false",
            "decision=" + HOLD_DECISION,
            P0_03_COMPAT_BEGIN,
            P0_04_RUNTIME_BEGIN,
            "PASS: ci_static_checks",
        ],
    )
    executable = executable_python_lines(ci)
    require(executable == ["python3 " + VALIDATOR_REL], "CI must execute only the default PMAI-P0-04 validator")
    require(RUNNER_REL not in "\n".join(executable), "CI executes locked runner")
    require("validate_treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke.py" not in "\n".join(executable), "CI executes P0-03 validator")
    require("--require-complete" not in ci, "CI must not require PMAI-P0-04 completion")
    require("alembic upgrade" not in ci and "alembic stamp" not in ci, "CI contains Alembic execution")


def check_smoke():
    smoke = read(SMOKE_REL)
    p003, p003_start, p003_end = marked_block(
        smoke, P0_03_COMPAT_BEGIN, P0_03_COMPAT_END, "P0-03 compatibility gate"
    )
    p004, p004_start, p004_end = marked_block(
        smoke, P0_04_RUNTIME_BEGIN, P0_04_RUNTIME_END, "P0-04 runtime gate"
    )
    final_pass = smoke.rfind("ALL PASS: smoke_petmed")
    require(final_pass >= 0, "final cumulative smoke PASS missing")
    require(p003_start < p003_end < p004_start < p004_end < final_pass, "cumulative smoke gate ordering invalid")
    require("python3" not in p003, "P0-03 compatibility gate must be static")
    p004_exec = executable_python_lines(p004)
    require(len(p004_exec) == 1, "P0-04 smoke gate must execute exactly one Python command")
    require(VALIDATOR_REL in p004_exec[0], "P0-04 smoke gate must execute the new validator")
    require(RUNNER_REL not in p004, "cumulative smoke executes locked runner")
    all_exec = "\n".join(executable_python_lines(smoke))
    require("validate_treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke.py" not in all_exec, "cumulative smoke executes P0-03 validator")
    require("validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py" not in all_exec, "cumulative smoke executes P0-02 validator")
    summary = smoke[final_pass:]
    require_tokens(
        "final cumulative smoke summary",
        summary,
        [
            "treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1=COMPLETE",
            "treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1=IN_PROGRESS",
            "p0_04_governance_preparation_complete=true",
            "p0_04_execution_authorized=false",
            "staging_0010_apply_authorized=false",
            "active_0010_migration_file_created=false",
            "previous_stage_decision=" + ENTRY_DECISION,
            "decision=" + HOLD_DECISION,
        ],
    )
    require(len(smoke.splitlines()) >= 1000, "cumulative smoke line count is too small")


def check_shell_syntax(rel):
    result = subprocess.run(
        ["bash", "-n", str(ROOT / rel)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(result.returncode == 0, rel + " shell syntax failed: " + result.stderr.strip())


def main():
    parser = argparse.ArgumentParser(description="Validate PMAI-P0-04 governance preparation")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    for rel in TARGET_PATHS:
        require((ROOT / rel).is_file(), "missing current-stage target: " + rel)
    require(not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")), "active 0010 migration exists")
    check_artifact_hashes()
    check_previous_stage()
    check_draft_and_repository_contracts()
    check_document()
    check_csvs()
    check_runner()
    check_secret_safety()
    check_ci()
    check_smoke()
    check_shell_syntax(CI_REL)
    check_shell_syntax(SMOKE_REL)

    if args.require_complete:
        print("NO-GO: PMAI-P0-04 remains IN_PROGRESS; completion is intentionally unavailable", file=sys.stderr)
        return 1

    print("stage_id=PMAI-P0-04")
    print("stage_status=IN_PROGRESS")
    print("package_initialized=true")
    print("evidence_completeness=PENDING_GOVERNANCE_AND_EXTERNAL_EXECUTION")
    print("p0_03_prerequisite_complete=true")
    print("p0_04_entry_authorized=true")
    print("p0_04_governance_preparation_complete=true")
    print("migration_schema_review_approved=false")
    print("draft_revision_length_blocked=true")
    print("draft_audit_fk_blocked=true")
    print("draft_idempotency_constraint_blocked=true")
    print("draft_case_lifecycle_blocked=true")
    print("production_auto_deploy_risk_blocked=true")
    print("fresh_post_p0_03_staging_backup_verified=false")
    print("disposable_restore_rehearsal_complete=false")
    print("runner_execution_enabled=false")
    print("runner_executed_by_ci=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("active_0010_migration_file_created=false")
    print("staging_0010_migration_executed=false")
    print("production_migration_authorized=false")
    print("production_migration_executed=false")
    print("database_revision=0009_diag_data")
    print("alembic_head=0009_diag_data")
    print("database_connection=false")
    print("database_write=false")
    print("case_treatment_write=false")
    print("prescription_write=false")
    print("medication_detail_output=false")
    print("production_database_write=false")
    print("decision=" + HOLD_DECISION)
    print("ALL PASS: treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_governance_preparation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
