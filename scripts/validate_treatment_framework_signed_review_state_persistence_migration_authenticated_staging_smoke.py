#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import csv
import glob
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "b37362a2a343b068926edce4862b6f7d7c62a19d"
EXECUTION_COMMIT = "4ef91255e8eb1ca15be17579a1dceb2587d7b575"
EXECUTION_COMMIT_SHORT = "4ef9125"
EVIDENCE_SHA256 = "da52b46466a65316331d420c809bc406e49dfa722b1b5875667e30db50eef213"
EVIDENCE_BASENAME = "PMAI_P0_03_AUTHENTICATED_STAGING_SMOKE_V1.json"
STAGE_ID = "PMAI-P0-03"
STAGE_TITLE = "Treatment Framework Signed Review State Persistence Migration Authenticated Staging Smoke V1"
STAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1"
PACKAGE_TOKEN = STAGE_TOKEN + "_package_v1"
ENTRY_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1"
COMPLETION_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1"
EXPECTED_REVISION = "0009_diag_data"

DOC_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md"
CHECKLIST_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_CHECKLIST_V1.csv"
REGISTER_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_EVIDENCE_REGISTER_V1.csv"
MATRIX_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_TEST_MATRIX_V1.csv"
GO_NO_GO_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_GO_NO_GO_V1.csv"
API_REL = "backend/diagnostic_data_api.py"
CLINICAL_QA_REL = "backend/clinical_qa_dashboard.py"
RUNNER_REL = "scripts/run_treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke.py"
CLINICAL_QA_VALIDATOR_REL = "scripts/validate_clinical_qa_dashboard_v2.py"
VALIDATOR_REL = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke.py"
CI_REL = "scripts/ci_static_checks.sh"
SMOKE_REL = "scripts/smoke_petmed.sh"
WORKFLOW_REL = ".github/workflows/ci-gate.yml"
PREVIOUS_DOC_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1.md"
PREVIOUS_VALIDATOR_REL = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py"
TARGET_PATHS = [
    "backend/diagnostic_data_api.py",
    DOC_REL,
    CHECKLIST_REL,
    REGISTER_REL,
    MATRIX_REL,
    GO_NO_GO_REL,
    RUNNER_REL,
    CLINICAL_QA_VALIDATOR_REL,
    VALIDATOR_REL,
    CI_REL,
    SMOKE_REL,
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
AUDIT_LOG_ALLOWED_FIELDS = ["log_id", "case_id", "event_type", "source", "created_at"]
AUDIT_LOG_FORBIDDEN_FIELDS = ["note", "metadata", "metadata_json", "patient_token", "clinician_id", "request_id"]

P0_02_RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_runtime_gate"
P0_02_COMPAT_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_compatibility_gate"
P0_02_COMPAT_END = "# <<< treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_compatibility_gate"
RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1_smoke_petmed_runtime_gate"
RUNTIME_END = "# <<< treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1_smoke_petmed_runtime_gate"

CHECKLIST_STATUS = {
    "AS-001": "PASS_REFERENCE",
    "AS-002": "VERIFIED_OPERATOR_RECORD",
    "AS-003": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-004": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-005": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-006": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-007": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-008": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-009": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-010": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-011": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-012": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-013": "VERIFIED_EXTERNAL_EVIDENCE",
    "AS-014": "VERIFIED_STATIC_AND_EXTERNAL",
    "AS-015": "VERIFIED_RUNTIME_EVIDENCE",
    "AS-016": "COMPLETE_NEXT_STAGE_ENTRY_AUTHORIZED",
}
REGISTER_VALUES = {
    "ASE-001": "pet-med-ai-backend-staging-ohio",
    "ASE-002": "Ohio_US_East",
    "ASE-003": "0009_diag_data",
    "ASE-004": "0009_diag_data",
    "ASE-005": "ALL_FALSE",
    "ASE-006": "true",
    "ASE-007": "true",
    "ASE-008": "true",
    "ASE-009": "true",
    "ASE-010": "true",
    "ASE-011": "PASS",
    "ASE-012": "PASS",
    "ASE-013": "PASS_COUNT_1",
    "ASE-014": "PASS_PERSISTED_FALSE",
    "ASE-015": "PASS_WRITES_DATABASE_FALSE",
    "ASE-016": "PASS_MIGRATION_ENABLED_FALSE",
    "ASE-017": "true",
    "ASE-018": "true",
    "ASE-019": "true",
    "ASE-020": "1",
    "ASE-021": "true",
    "ASE-022": "true",
    "ASE-023": "true",
    "ASE-024": "true",
    "ASE-025": "false",
    "ASE-026": "false",
    "ASE-027": "false",
    "ASE-028": "release_operator",
    "ASE-029": "backend_owner",
    "ASE-030": "PASS_SHA256_VERIFIED",
}
MATRIX_RESULTS = {
    "AST-001": "PASS_200_REVISION_0009_FLAGS_FALSE",
    "AST-002": "PASS_BOTH_AUTHENTICATED",
    "AST-003": "PASS_HTTP_401",
    "AST-004": "PASS_HTTP_404",
    "AST-005": "PASS_NO_WRITE",
    "AST-006": "PASS_PREVIEW_ONLY",
    "AST-007": "PASS_DETERMINISTIC_MATCH",
    "AST-008": "PASS_ONE_APPEND_ONLY_ROW",
    "AST-009": "PASS_LINKED_PERSISTED_FALSE",
    "AST-010": "PASS_WRITES_DATABASE_FALSE",
    "AST-011": "PASS_MIGRATION_DISABLED_NO_0010",
    "AST-012": "PASS_HTTP_404",
    "AST-013": "PASS_HASHES_MATCH",
    "AST-014": "PASS_HTTP_422_NO_EXTRA_WRITE",
    "AST-015": "PASS_HTTP_422_NO_EXTRA_WRITE",
    "AST-016": "PASS_HTTP_422_NO_EXTRA_WRITE",
    "AST-017": "PASS_EXACTLY_ONE_LINKED_ROW",
    "AST-018": "PASS_CASE_UNCHANGED_AUDIT_COUNT_ONE",
    "AST-019": "PASS_REVISION_0009_FLAGS_FALSE",
    "AST-020": "PASS_SANITIZED_SHA256_VERIFIED",
}


def require(condition, message):
    if not condition:
        print("NO-GO: " + message)
        raise SystemExit(1)


def read(rel_path):
    path = ROOT / rel_path
    require(path.is_file(), "missing required file: " + rel_path)
    return path.read_text(encoding="utf-8")


def doc_value(text, key):
    match = re.search(r"(?m)^" + re.escape(key) + r"=(.*)$", text)
    require(match is not None, "document missing key: " + key)
    return match.group(1).strip()


def require_tokens(label, text, tokens):
    missing = [token for token in tokens if token not in text]
    require(not missing, label + " missing tokens: " + ", ".join(missing))


def run_git(args, check=True):
    result = subprocess.run(
        ["git"] + list(args),
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check:
        require(
            result.returncode == 0,
            "git command failed: git %s: %s"
            % (" ".join(args), result.stderr.strip() or result.stdout.strip()),
        )
    return result


def read_csv(rel_path, expected_columns, required_ids, id_column):
    path = ROOT / rel_path
    require(path.is_file(), "missing CSV: " + rel_path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == expected_columns, "unexpected columns in " + rel_path)
        rows = list(reader)
    seen = set(row.get(id_column, "") for row in rows)
    require(seen == set(required_ids), "unexpected row IDs in " + rel_path)
    for row in rows:
        require(row.get("blocking") in ("yes", "no"), "invalid blocking value in " + rel_path)
    return rows


def parse_utc(text, label):
    value = str(text or "").strip()
    require(value.endswith("Z"), label + " must be UTC Z format")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        require(False, label + " is not valid ISO-8601")
    require(parsed.tzinfo is not None, label + " must include timezone")
    return parsed


def check_no_active_0010():
    matches = sorted(glob.glob(str(ROOT / "backend" / "migrations" / "versions" / "0010*.py")))
    require(not matches, "active backend/migrations/versions/0010*.py is forbidden in PMAI-P0-03 promotion")


def check_no_external_evidence_committed():
    tracked = run_git(["ls-files"]).stdout.splitlines()
    require(not any(path.endswith(EVIDENCE_BASENAME) for path in tracked), "external evidence JSON must not be committed")
    found = [
        path
        for path in ROOT.rglob(EVIDENCE_BASENAME)
        if ".git" not in path.parts
    ]
    require(not found, "external evidence JSON must remain outside the repository")


def check_previous_stage():
    previous = read(PREVIOUS_DOC_REL)
    read(PREVIOUS_VALIDATOR_REL)
    require_tokens(
        "PMAI-P0-02 completion",
        previous,
        [
            "stage_id=PMAI-P0-02",
            "STAGE_STATUS=COMPLETE",
            "EVIDENCE_COMPLETENESS=COMPLETE",
            "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=true",
            "SIGNED_REVIEW_0010_STAGING_MIGRATION_EXECUTED=false",
            "ACTIVE_0010_MIGRATION_FILE_CREATED=false",
            "decision=" + ENTRY_DECISION,
            "database_revision=0009_diag_data",
            "alembic_head=0009_diag_data",
            "writes_database=false",
        ],
    )
    require(run_git(["cat-file", "-e", BASELINE_COMMIT + "^{commit}"], check=False).returncode == 0, "PMAI-P0-02 baseline commit is missing")
    require(run_git(["merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"], check=False).returncode == 0, "PMAI-P0-02 baseline commit is not an ancestor of HEAD")


def check_execution_commit():
    require(run_git(["cat-file", "-e", EXECUTION_COMMIT + "^{commit}"], check=False).returncode == 0, "approved smoke execution commit is missing")
    require(run_git(["merge-base", "--is-ancestor", EXECUTION_COMMIT, "HEAD"], check=False).returncode == 0, "approved smoke execution commit is not an ancestor of HEAD")


def check_document():
    doc = read(DOC_REL)
    required = [
        "stage_id=" + STAGE_ID,
        "stage_type=authenticated_staging_smoke",
        "PACKAGE_INITIALIZED=true",
        "STAGE_STATUS=COMPLETE",
        "EVIDENCE_COMPLETENESS=COMPLETE",
        "AUTHENTICATED_STAGING_SMOKE_COMPLETE=true",
        "EVIDENCE_INTEGRITY_VERIFIED=true",
        "STAGING_BACKEND_PROVISIONED=true",
        "STAGING_BACKEND_ISOLATED=true",
        "STAGING_DATABASE_REVISION_VERIFIED=true",
        "AUTHENTICATION_VERIFIED=true",
        "OWNER_SCOPE_VERIFIED=true",
        "CROSS_USER_DENIAL_VERIFIED=true",
        "TREATMENT_FRAMEWORK_BUILD_VERIFIED=true",
        "CLINICIAN_REVIEW_VERIFIED=true",
        "APPEND_ONLY_AUDIT_LINK_VERIFIED=true",
        "SIGNED_REVIEW_STATE_PREVIEW_VERIFIED=true",
        "PERSISTENCE_PREPARE_VERIFIED=true",
        "MIGRATION_PATH_PREVIEW_VERIFIED=true",
        "READBACK_VERIFIED=true",
        "IDEMPOTENCY_STRATEGY_VERIFIED=true",
        "FAILURE_NO_PARTIAL_WRITE_VERIFIED=true",
        "STAGING_SYNTHETIC_USERS_WRITE_EXECUTED=true",
        "STAGING_SYNTHETIC_CASE_WRITE_EXECUTED=true",
        "STAGING_APPEND_ONLY_AUDIT_WRITE_EXECUTED=true",
        "STAGING_APPEND_ONLY_AUDIT_WRITE_COUNT=1",
        "SIGNED_REVIEW_0010_STAGING_MIGRATION_EXECUTED=false",
        "PRODUCTION_MIGRATION_EXECUTED=false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED=false",
        "PRODUCTION_DATABASE_WRITE_PERFORMED=false",
        "CASE_TREATMENT_WRITE_PERFORMED=false",
        "PRESCRIPTION_WRITE_PERFORMED=false",
        "CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false",
        "RUNNER_EXECUTED_BY_CI=false",
        "PACKAGE_CONNECTS_DATABASE=false",
        "PACKAGE_WRITES_DATABASE=false",
        "P0_04_ENTRY_AUTHORIZED=true",
        "STAGING_0010_APPLY_AUTHORIZED=false",
        "PRODUCTION_MIGRATION_AUTHORIZED=false",
        "smoke_execution_commit_sha=" + EXECUTION_COMMIT,
        "smoke_execution_repo_head=" + EXECUTION_COMMIT_SHORT,
        "evidence_artifact_basename=" + EVIDENCE_BASENAME,
        "evidence_artifact_sha256=" + EVIDENCE_SHA256,
        "evidence_artifact_committed=false",
        "evidence_integrity_verified=true",
        "evidence_file_mode=600",
        "evidence_workspace_mode=700",
        "synthetic_users_created=2",
        "synthetic_cases_created=1",
        "append_only_audit_rows_created=1",
        "signed_review_state_rows_created=0",
        "case_treatment_write=false",
        "prescription_write=false",
        "medication_detail_output=false",
        "production_database_write=false",
        "active_0010_created=false",
        "migration_executed=false",
        "database_revision=" + EXPECTED_REVISION,
        "alembic_head=" + EXPECTED_REVISION,
        "schema_ok=true",
        "migration_errors=[]",
        "writes_database=false",
        "exposes_database_url=false",
        "p0_04_entry_authorized=true",
        "staging_0010_apply_authorized=false",
        "decision=" + COMPLETION_DECISION,
        "completion_decision=" + COMPLETION_DECISION,
    ]
    require_tokens("PMAI-P0-03 completed document", doc, required)
    for flag in DANGEROUS_FLAGS:
        require(flag + "=false" in doc, "dangerous feature flag false marker missing: " + flag)
    started = parse_utc(doc_value(doc, "smoke_started_at_utc"), "smoke_started_at_utc")
    completed = parse_utc(doc_value(doc, "smoke_completed_at_utc"), "smoke_completed_at_utc")
    require(completed >= started, "smoke completion timestamp precedes start")
    return doc


def check_csvs():
    checklist = read_csv(
        CHECKLIST_REL,
        ["item_id", "area", "requirement", "evidence_source", "evidence_status", "blocking", "notes"],
        ["AS-%03d" % value for value in range(1, 17)],
        "item_id",
    )
    register = read_csv(
        REGISTER_REL,
        ["evidence_id", "evidence_type", "required_field", "observed_value", "evidence_source", "evidence_sha256", "evidence_status", "blocking", "notes"],
        ["ASE-%03d" % value for value in range(1, 31)],
        "evidence_id",
    )
    matrix = read_csv(
        MATRIX_REL,
        ["test_id", "test_area", "request_or_check", "expected_result", "observed_result", "test_status", "evidence_source", "blocking", "notes"],
        ["AST-%03d" % value for value in range(1, 21)],
        "test_id",
    )
    gates = read_csv(
        GO_NO_GO_REL,
        ["gate_id", "gate", "required_state", "observed_state", "decision", "blocking", "notes"],
        ["ASG-%03d" % value for value in range(1, 13)],
        "gate_id",
    )

    for row in checklist:
        require(row["evidence_status"] == CHECKLIST_STATUS[row["item_id"]], "checklist status mismatch: " + row["item_id"])
        require("PENDING" not in row["evidence_status"] and "HOLD" not in row["evidence_status"], "checklist retains pending or HOLD state")

    for row in register:
        evidence_id = row["evidence_id"]
        require(row["observed_value"] == REGISTER_VALUES[evidence_id], "register observed value mismatch: " + evidence_id)
        if evidence_id == "ASE-002":
            require(row["evidence_source"] == "operator_verified_render_service_record", "ASE-002 source mismatch")
            require(row["evidence_sha256"] == "", "ASE-002 must not claim JSON coverage for region")
            require(row["evidence_status"] == "VERIFIED_OPERATOR_RECORD", "ASE-002 status mismatch")
        else:
            require(row["evidence_source"] == "external_sanitized_evidence_json", "register evidence source mismatch: " + evidence_id)
            require(row["evidence_sha256"] == EVIDENCE_SHA256, "register evidence SHA mismatch: " + evidence_id)
            require(row["evidence_status"] == "VERIFIED_EXTERNAL_EVIDENCE", "register evidence status mismatch: " + evidence_id)
        require(row["observed_value"] != "UNRECORDED", "register retains UNRECORDED value")

    for row in matrix:
        test_id = row["test_id"]
        require(row["observed_result"] == MATRIX_RESULTS[test_id], "matrix observed result mismatch: " + test_id)
        require(row["test_status"] == "PASS", "matrix test is not PASS: " + test_id)
        require(row["evidence_source"] == "external_sanitized_evidence_json", "matrix evidence source mismatch: " + test_id)

    for row in gates[:-1]:
        require(row["decision"] == "PASS_GATE", "gate is not PASS_GATE: " + row["gate_id"])
        require("PENDING" not in row["observed_state"], "gate retains pending state")
    final_gate = gates[-1]
    require(final_gate["gate_id"] == "ASG-012", "final gate ID mismatch")
    require(final_gate["observed_state"] == "PMAI-P0-03_COMPLETE", "final gate completion state mismatch")
    require(final_gate["decision"] == COMPLETION_DECISION, "completion decision mismatch")
    combined = "\n".join(",".join(row.values()) for row in gates)
    require("NO_GO_TO_PMAI_P0_04" not in combined, "Go/No-Go still blocks P0-04")
    require("HOLD_PMAI_P0_03" not in combined, "Go/No-Go still contains HOLD")


def check_runner():
    runner = read(RUNNER_REL)
    require_tokens(
        "external authenticated staging runner",
        runner,
        [
            "PMAI-P0-03-AUTHENTICATED-STAGING-SMOKE",
            "production backend URL is forbidden",
            "staging base URL hostname must contain the staging marker",
            "/auth/signup",
            "/auth/login",
            "/api/cases",
            "/api/diagnostic-data/clinical-qa-dashboard/v2/summary?case_id=",
            "treatment-framework/build",
            "treatment-framework/review",
            "treatment-framework/audit-log/append",
            "treatment-framework/signed-review-state/build",
            "treatment-framework/signed-review-state/persistence/prepare",
            "treatment-framework/signed-review-state/persistence/migration/dry-run",
            "I_UNDERSTAND_THIS_APPENDS_TREATMENT_FRAMEWORK_AUDIT_LOG_ONLY",
            "actual_audit_append_replayed",
            "case_treatment_write",
            "prescription_write",
            "medication_detail_output",
            "active_0010_created",
            "migration_executed",
            "production_database_write",
        ],
    )
    require("backend/migrations/versions/0010*.py" in runner, "runner must reject active 0010")
    require("alembic upgrade" not in runner, "runner must not execute Alembic upgrade")
    require("stamp head" not in runner, "runner must not execute stamp head")


def check_audit_readback_contract():
    api = read(API_REL)
    start = "# --- Clinical QA Dashboard V2 endpoint: start ---"
    end = "# --- Clinical QA Dashboard V2 endpoint: end ---"
    require(api.count(start) == 1, "Clinical QA endpoint start marker must occur once")
    require(api.count(end) == 1, "Clinical QA endpoint end marker must occur once")
    block = api.split(start, 1)[1].split(end, 1)[0]
    require_tokens(
        "PMAI-P0-03 owner-scoped audit readback contract",
        block,
        [
            "case = _owned_case_or_404(db, int(case_id), user)",
            "Case.owner_id == owner_id",
            "case_ids = [int(item.id) for item in case_rows]",
            "AuditLog.case_id.in_(case_ids)",
            '"owner_scoped": True',
            '"audit_logs": dashboard_payload["audit_logs"]',
            "**dashboard",
        ],
    )
    mapping = re.search(
        r'(?ms)^\s*"audit_logs":\s*\[\s*\{(?P<body>.*?)^\s*\}\s*\n\s*for item in audit_logs\s*\n\s*\],',
        block,
    )
    require(mapping is not None, "sanitized audit_logs mapping is missing")
    fields = re.findall(r'(?m)^\s*"([^"]+)":', mapping.group("body"))
    require(fields == AUDIT_LOG_ALLOWED_FIELDS, "audit_logs whitelist mismatch: %r" % fields)
    for field in AUDIT_LOG_FORBIDDEN_FIELDS:
        require('"%s"' % field not in mapping.group(0), "sensitive audit_logs field exposed: " + field)
    response_token = '"audit_logs": dashboard_payload["audit_logs"]'
    require(block.count(response_token) == 1, "audit_logs response passthrough must occur once")
    require(block.rfind(response_token) > block.rfind("**dashboard"), "audit_logs passthrough must follow **dashboard")
    for token in ("db.add(", "db.commit(", "db.delete(", "AuditLog(", "alembic upgrade", "stamp head"):
        require(token not in block, "read-only audit response contains forbidden token: " + token)

    behavior_validator = read(CLINICAL_QA_VALIDATOR_REL)
    require_tokens(
        "Clinical QA audit readback behavior validator",
        behavior_validator,
        [
            "AUDIT_LOG_ALLOWED_FIELDS = (",
            "def assert_audit_readback_contract() -> None:",
            'response must expose only dashboard_payload["audit_logs"]',
            "AUDIT_READBACK_CONTRACT=PASS",
        ],
    )
    dashboard = read(CLINICAL_QA_REL)
    require_tokens(
        "Clinical QA aggregate compatibility",
        dashboard,
        [
            'CLINICAL_QA_DASHBOARD_MODE = "clinical_qa_dashboard_v2"',
            '"cards": cards',
            '"metrics": metrics',
            '"qa_queue": qa_queue',
            '"writes_database": False',
        ],
    )


def check_secret_safety():
    combined = "\n".join(read(path) for path in (DOC_REL, CHECKLIST_REL, REGISTER_REL, MATRIX_REL, GO_NO_GO_REL))
    require(re.search(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://", combined) is None, "database or service connection URI found in stage documents")
    require(re.search(r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[^\s,;<>]+", combined) is None, "credential-like value found in stage documents")
    require(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", combined) is None, "email address found in stage documents")
    for flag in DANGEROUS_FLAGS:
        for pattern in (flag + "=true", flag + ": true", '"' + flag + '": true'):
            require(pattern not in combined, "dangerous feature flag enablement found: " + pattern)


def check_workflow():
    workflow = read(WORKFLOW_REL)
    match = re.search(r"(?ms)^  static-backend-gate:\n(.*?)(?=^  frontend-build-gate:|\Z)", workflow)
    require(match is not None, "static backend CI job is missing")
    static_job = match.group(1)
    require("uses: actions/checkout@v4" in static_job, "checkout action missing")
    require("fetch-depth: 0" in static_job, "static backend must fetch full history")


def check_ci():
    ci = read(CI_REL)
    require_tokens(
        "CI",
        ci,
        [
            "# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1",
            RUNNER_REL,
            VALIDATOR_REL,
            "python3 -m py_compile " + API_REL,
            "python3 -m py_compile " + RUNNER_REL,
            "python3 -m py_compile " + CLINICAL_QA_VALIDATOR_REL,
            "python3 -m py_compile " + VALIDATOR_REL,
            "python3 " + CLINICAL_QA_VALIDATOR_REL,
            "python3 " + VALIDATOR_REL + " --require-complete",
            "P0-03 authenticated staging smoke evidence promotion",
            "STAGE_STATUS=COMPLETE",
            "EVIDENCE_COMPLETENESS=COMPLETE",
            "AUTHENTICATED_STAGING_SMOKE_COMPLETE=true",
            "evidence_artifact_sha256=" + EVIDENCE_SHA256,
            "target-only tracked diff discipline",
            "sensitive staged path discipline",
            "PASS: ci_static_checks",
        ],
    )
    match = re.search(r"TARGETS=\((.*?)\n\)", ci, flags=re.S)
    require(match is not None, "CI TARGETS block missing")
    paths = re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)
    require(paths == TARGET_PATHS, "CI TARGETS are not canonical for completed PMAI-P0-03")
    require(PREVIOUS_VALIDATOR_REL not in re.findall(r"(?m)^\s*python3\s+([^\s]+)", ci), "PMAI-P0-02 validator must not execute after TARGETS advance")
    require("git add ." not in ci, "CI contains forbidden git add .")
    require("git add -A" not in ci, "CI contains forbidden git add -A")


def check_smoke():
    smoke = read(SMOKE_REL)
    require(P0_02_RUNTIME_BEGIN not in smoke, "PMAI-P0-02 runtime validator remains active")
    require(smoke.count(P0_02_COMPAT_BEGIN) == 1, "PMAI-P0-02 compatibility begin must occur once")
    require(smoke.count(P0_02_COMPAT_END) == 1, "PMAI-P0-02 compatibility end must occur once")
    require(smoke.count(RUNTIME_BEGIN) == 1, "PMAI-P0-03 runtime begin must occur once")
    require(smoke.count(RUNTIME_END) == 1, "PMAI-P0-03 runtime end must occur once")
    compat_begin = smoke.index(P0_02_COMPAT_BEGIN)
    compat_end = smoke.index(P0_02_COMPAT_END, compat_begin) + len(P0_02_COMPAT_END)
    runtime_begin = smoke.index(RUNTIME_BEGIN)
    runtime_end = smoke.index(RUNTIME_END, runtime_begin) + len(RUNTIME_END)
    final_pass = smoke.rfind("ALL PASS: smoke_petmed")
    require(final_pass >= 0, "final smoke PASS missing")
    require(compat_begin < compat_end < runtime_begin < runtime_end < final_pass, "smoke gate ordering invalid")
    compat = smoke[compat_begin:compat_end]
    require("python3" not in compat, "PMAI-P0-02 compatibility gate must be static")
    runtime = smoke[runtime_begin:runtime_end]
    require_tokens(
        "PMAI-P0-03 completed runtime gate",
        runtime,
        [
            VALIDATOR_REL,
            "--require-complete",
            PACKAGE_TOKEN + "=PASS",
            STAGE_TOKEN + "=COMPLETE",
            "evidence_completeness=COMPLETE",
            "authenticated_staging_smoke_complete=true",
            "evidence_sha256=" + EVIDENCE_SHA256,
            "append_only_audit_write_count=1",
            "p0_04_entry_authorized=true",
            "staging_0010_apply_authorized=false",
            "current_decision=" + COMPLETION_DECISION,
        ],
    )
    require(RUNNER_REL not in runtime, "external staging runner must not execute in cumulative smoke")
    require("python3 " + CLINICAL_QA_VALIDATOR_REL in smoke, "Clinical QA behavior validator is not preserved in cumulative smoke")
    summary = smoke[final_pass:]
    require_tokens(
        "final smoke summary",
        summary,
        [
            "treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1=COMPLETE",
            STAGE_TOKEN + "=COMPLETE",
            "authenticated_staging_smoke_complete=true",
            "evidence_integrity=PASS",
            "p0_04_entry_authorized=true",
            "staging_0010_apply_authorized=false",
            "previous_stage_decision=" + ENTRY_DECISION,
            "decision=" + COMPLETION_DECISION,
        ],
    )
    require(summary.count('"previous_stage_decision=') == 1, "summary must contain one previous_stage_decision")
    require(summary.count('"decision=') == 1, "summary must contain one decision")
    require(len(smoke.splitlines()) >= 1000, "cumulative smoke line count is too small")


def check_shell_syntax(rel_path):
    result = subprocess.run(
        ["bash", "-n", str(ROOT / rel_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(result.returncode == 0, rel_path + " shell syntax failed: " + result.stderr.strip())


def main():
    parser = argparse.ArgumentParser(description="Validate completed PMAI-P0-03 package")
    parser.add_argument("--require-complete", action="store_true")
    parser.parse_args()

    for rel_path in TARGET_PATHS:
        require((ROOT / rel_path).is_file(), "missing current-stage target: " + rel_path)
    check_no_active_0010()
    check_no_external_evidence_committed()
    check_previous_stage()
    check_execution_commit()
    doc = check_document()
    check_csvs()
    check_runner()
    check_audit_readback_contract()
    check_secret_safety()
    check_workflow()
    check_ci()
    check_smoke()
    check_shell_syntax(CI_REL)
    check_shell_syntax(SMOKE_REL)
    require(doc_value(doc, "STAGE_STATUS") == "COMPLETE", "PMAI-P0-03 must remain COMPLETE")

    print("PASS: " + STAGE_TITLE + " package integrity")
    print("stage_id=" + STAGE_ID)
    print("stage_status=COMPLETE")
    print("package_initialized=true")
    print("evidence_completeness=COMPLETE")
    print("authenticated_staging_smoke_complete=true")
    print("evidence_integrity=PASS")
    print("evidence_sha256=" + EVIDENCE_SHA256)
    print("runner_not_executed_by_ci=true")
    print("staging_synthetic_users_write_executed=true")
    print("staging_synthetic_case_write_executed=true")
    print("staging_append_only_audit_write_executed=true")
    print("append_only_audit_write_count=1")
    print("signed_review_0010_staging_migration_executed=false")
    print("production_migration_executed=false")
    print("active_migration_file_created=false")
    print("case_treatment_write=false")
    print("prescription_write=false")
    print("medication_detail_output=false")
    print("production_database_write=false")
    print("database_revision=0009_diag_data")
    print("alembic_head=0009_diag_data")
    print("schema_ok=true")
    print("migration_errors=[]")
    print("writes_database=false")
    print("exposes_database_url=false")
    print("audit_readback_contract=PASS")
    print("audit_log_field_whitelist=log_id,case_id,event_type,source,created_at")
    print("owner_scoped_audit_readback=true")
    print("p0_04_entry_authorized=true")
    print("staging_0010_apply_authorized=false")
    print("p0_04_execution_authorized=false")
    print("validator_previous_stage_decision=" + ENTRY_DECISION)
    print("validator_decision=" + COMPLETION_DECISION)
    print("ALL PASS: " + PACKAGE_TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
