#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import csv
import glob
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "b37362a2a343b068926edce4862b6f7d7c62a19d"
STAGE_ID = "PMAI-P0-03"
STAGE_TITLE = "Treatment Framework Signed Review State Persistence Migration Authenticated Staging Smoke V1"
STAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1"
PACKAGE_TOKEN = STAGE_TOKEN + "_package_v1"
ENTRY_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1"
HOLD_DECISION = "HOLD_PMAI_P0_03_PENDING_AUTHENTICATED_STAGING_SMOKE_EVIDENCE"
COMPLETION_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1"

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
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_CHECKLIST_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_EVIDENCE_REGISTER_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_TEST_MATRIX_V1.csv",
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_GO_NO_GO_V1.csv",
    "scripts/run_treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke.py",
    "scripts/validate_clinical_qa_dashboard_v2.py",
    "scripts/validate_treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
]
DANGEROUS_FLAGS = ['ENABLE_EMR_REAL_IMPORT', 'ENABLE_EMR_IMPORT_CASE_UPDATE', 'ENABLE_EMR_ATTACHMENT_DOWNLOAD', 'ENABLE_PREVENTIVE_AUTO_DELIVERY', 'ENABLE_PREVENTIVE_SMS_DELIVERY', 'ENABLE_PREVENTIVE_WECHAT_DELIVERY', 'ENABLE_PREVENTIVE_EMAIL_DELIVERY', 'ENABLE_PRESCRIPTION_STRUCTURED_WRITE', 'ENABLE_DEVICE_REAL_INGEST', 'ENABLE_BILLING_REAL_WRITE']
AUDIT_LOG_ALLOWED_FIELDS = ["log_id", "case_id", "event_type", "source", "created_at"]
AUDIT_LOG_FORBIDDEN_FIELDS = ["note", "metadata", "metadata_json", "patient_token", "clinician_id", "request_id"]

P0_02_RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_runtime_gate"
P0_02_COMPAT_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_compatibility_gate"
P0_02_COMPAT_END = "# <<< treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_compatibility_gate"
RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1_smoke_petmed_runtime_gate"
RUNTIME_END = "# <<< treatment_framework_signed_review_state_persistence_migration_authenticated_staging_smoke_v1_smoke_petmed_runtime_gate"


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
    missing = [item for item in required_ids if item not in seen]
    require(not missing, "missing rows in %s: %s" % (rel_path, ", ".join(missing)))
    for row in rows:
        require(row.get("blocking") in ("yes", "no"), "invalid blocking value in " + rel_path)
    return rows


def check_no_active_0010():
    matches = sorted(glob.glob(str(ROOT / "backend" / "migrations" / "versions" / "0010*.py")))
    require(not matches, "active backend/migrations/versions/0010*.py is forbidden in PMAI-P0-03")


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
    require(
        run_git(["cat-file", "-e", BASELINE_COMMIT + "^{commit}"], check=False).returncode == 0,
        "PMAI-P0-02 baseline commit is missing",
    )
    require(
        run_git(["merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"], check=False).returncode == 0,
        "PMAI-P0-02 baseline commit is not an ancestor of HEAD",
    )


def check_document():
    doc = read(DOC_REL)
    required = [
        "stage_id=" + STAGE_ID,
        "stage_type=authenticated_staging_smoke",
        "PACKAGE_INITIALIZED=true",
        "STAGE_STATUS=IN_PROGRESS",
        "EVIDENCE_COMPLETENESS=PENDING_EXTERNAL_EXECUTION",
        "AUTHENTICATED_STAGING_SMOKE_COMPLETE=false",
        "STAGING_BACKEND_PROVISIONED=false",
        "AUTHENTICATION_VERIFIED=false",
        "OWNER_SCOPE_VERIFIED=false",
        "CROSS_USER_DENIAL_VERIFIED=false",
        "IDEMPOTENCY_STRATEGY_VERIFIED=false",
        "FAILURE_NO_PARTIAL_WRITE_VERIFIED=false",
        "SIGNED_REVIEW_0010_STAGING_MIGRATION_EXECUTED=false",
        "PRODUCTION_MIGRATION_EXECUTED=false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED=false",
        "PRODUCTION_DATABASE_WRITE_PERFORMED=false",
        "CASE_TREATMENT_WRITE_PERFORMED=false",
        "PRESCRIPTION_WRITE_PERFORMED=false",
        "CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false",
        "RUNNER_REQUIRES_EXPLICIT_CONFIRMATION=true",
        "PACKAGE_CONNECTS_DATABASE=false",
        "PACKAGE_WRITES_DATABASE=false",
        "baseline_commit_sha=" + BASELINE_COMMIT,
        "previous_stage_decision=" + ENTRY_DECISION,
        "database_revision=0009_diag_data",
        "alembic_head=0009_diag_data",
        "schema_ok=true",
        "migration_errors=[]",
        "writes_database=false",
        "exposes_database_url=false",
        "decision=" + HOLD_DECISION,
        "completion_decision=" + COMPLETION_DECISION,
    ]
    require_tokens("PMAI-P0-03 document", doc, required)
    for flag in DANGEROUS_FLAGS:
        require(flag + "=false" in doc, "dangerous feature flag false marker missing: " + flag)
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
    require(any(row["evidence_status"] == "PENDING_EXTERNAL_EVIDENCE" for row in checklist), "checklist must retain pending evidence")
    require(any(row["evidence_status"] == "HOLD_PENDING_EXTERNAL_EVIDENCE" for row in checklist), "checklist must retain HOLD")
    for row in register:
        require(row["observed_value"] == "UNRECORDED", "register observed value must remain UNRECORDED during initialization")
        require(row["evidence_status"] == "PENDING_EXTERNAL_EVIDENCE", "register must remain pending during initialization")
    for row in matrix:
        require(row["observed_result"] == "UNRECORDED", "matrix observed result must remain UNRECORDED")
        require(row["test_status"] == "PENDING", "matrix test must remain PENDING")
    require(any(row["decision"] == HOLD_DECISION for row in gates), "Go/No-Go HOLD decision missing")
    require(any(row["decision"] == "NO_GO_TO_PMAI_P0_04" for row in gates), "Go/No-Go must block P0-04")


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
            "missing audit reference failure",
            "missing migration acknowledgement failure",
            "forbidden medication detail failure",
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

    runner = read(RUNNER_REL)
    require_tokens(
        "PMAI-P0-03 runner audit readback expectation",
        runner,
        [
            'rows = data.get("audit_logs")',
            'fail("audit readback has no audit_logs list")',
            "owner-scoped audit readback",
        ],
    )

    behavior_validator = read(CLINICAL_QA_VALIDATOR_REL)
    require_tokens(
        "Clinical QA audit readback behavior validator",
        behavior_validator,
        [
            "AUDIT_LOG_ALLOWED_FIELDS = (",
            "AUDIT_LOG_FORBIDDEN_FIELDS = (",
            "def assert_audit_readback_contract() -> None:",
            'response must expose only dashboard_payload["audit_logs"]',
            "cross-user 404 helper token missing",
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
    combined = "\n".join(
        read(path)
        for path in (
            DOC_REL,
            CHECKLIST_REL,
            REGISTER_REL,
            MATRIX_REL,
            GO_NO_GO_REL,
        )
    )
    require(
        re.search(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://", combined) is None,
        "database or service connection URI found in stage documents",
    )
    require(
        re.search(r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[^\s,;<>]+", combined) is None,
        "credential-like value found in stage documents",
    )
    require(
        re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", combined) is None,
        "email address found in stage documents",
    )
    for flag in DANGEROUS_FLAGS:
        for pattern in (flag + "=true", flag + ": true", '"' + flag + '": true'):
            require(pattern not in combined, "dangerous feature flag enablement found: " + pattern)


def check_workflow():
    workflow = read(WORKFLOW_REL)
    match = re.search(
        r"(?ms)^  static-backend-gate:\n(.*?)(?=^  frontend-build-gate:|\Z)",
        workflow,
    )
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
            "python3 " + VALIDATOR_REL,
            "P0-03 audit readback contract repair",
            'for validator in "${OPTIONAL_CORE_VALIDATORS[@]:-}"; do',
            '[ -n "$validator" ] || continue',
            "authenticated staging smoke package markers",
            "target-only tracked diff discipline",
            "sensitive staged path discipline",
            "PASS: ci_static_checks",
        ],
    )
    match = re.search(r"TARGETS=\((.*?)\n\)", ci, flags=re.S)
    require(match is not None, "CI TARGETS block missing")
    paths = re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)
    require(paths == TARGET_PATHS, "CI TARGETS are not canonical for PMAI-P0-03")
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
    require_tokens(
        "PMAI-P0-02 compatibility gate",
        compat,
        [
            PREVIOUS_DOC_REL,
            PREVIOUS_VALIDATOR_REL,
            "stage_id=PMAI-P0-02",
            "STAGE_STATUS=COMPLETE",
            "decision=" + ENTRY_DECISION,
            "treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1=PASS",
        ],
    )
    runtime = smoke[runtime_begin:runtime_end]
    require("python3" in runtime and VALIDATOR_REL in runtime, "PMAI-P0-03 validator is not executed by smoke")
    require("python3 " + CLINICAL_QA_VALIDATOR_REL in smoke, "Clinical QA behavior validator is not preserved in cumulative smoke")
    require(PACKAGE_TOKEN + "=PASS" in runtime, "PMAI-P0-03 package PASS marker missing")
    summary = smoke[final_pass:]
    require_tokens(
        "final smoke summary",
        summary,
        [
            "treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1=COMPLETE",
            STAGE_TOKEN + "=IN_PROGRESS",
            "authenticated_staging_smoke_complete=false",
            "previous_stage_decision=" + ENTRY_DECISION,
            "decision=" + HOLD_DECISION,
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
    parser = argparse.ArgumentParser(description="Validate PMAI-P0-03 package")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    for rel_path in TARGET_PATHS:
        require((ROOT / rel_path).is_file(), "missing current-stage target: " + rel_path)
    check_no_active_0010()
    check_previous_stage()
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

    if args.require_complete:
        require(
            doc_value(doc, "STAGE_STATUS") == "COMPLETE",
            "PMAI-P0-03 authenticated staging smoke evidence is not complete",
        )

    print("PASS: " + STAGE_TITLE + " package integrity")
    print("stage_id=" + STAGE_ID)
    print("stage_status=IN_PROGRESS")
    print("package_initialized=true")
    print("evidence_completeness=PENDING_EXTERNAL_EXECUTION")
    print("authenticated_staging_smoke_complete=false")
    print("runner_not_executed_by_ci=true")
    print("signed_review_0010_staging_migration_executed=false")
    print("production_migration_executed=false")
    print("active_migration_file_created=false")
    print("database_revision=0009_diag_data")
    print("alembic_head=0009_diag_data")
    print("schema_ok=true")
    print("migration_errors=[]")
    print("writes_database=false")
    print("exposes_database_url=false")
    print("PASS: dangerous feature flags disabled")
    print("PASS: no Case.treatment, prescription, or medication-detail output")
    print("audit_readback_contract=PASS")
    print("audit_log_field_whitelist=log_id,case_id,event_type,source,created_at")
    print("owner_scoped_audit_readback=true")
    print("validator_previous_stage_decision=" + ENTRY_DECISION)
    print("validator_decision=" + HOLD_DECISION)
    print("ALL PASS: " + PACKAGE_TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
