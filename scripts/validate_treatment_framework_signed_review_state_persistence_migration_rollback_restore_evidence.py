#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import csv
import glob
import hashlib
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "8d118180ced24b4df9af987790d47ab049346786"
STAGE_ID = "PMAI-P0-02"
STAGE_TITLE = "Treatment Framework Signed Review State Persistence Migration Rollback Restore Evidence V1"
STAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1"
PACKAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_package_v1"
PREVIOUS_STAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1"
ENTRY_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1"
HOLD_DECISION = "HOLD_PMAI_P0_02_PENDING_EXTERNAL_ROLLBACK_RESTORE_EVIDENCE"
COMPLETION_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1"

DOC_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1.md"
CHECKLIST_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_CHECKLIST_V1.csv"
REGISTER_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_REGISTER_V1.csv"
VERIFICATION_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_VERIFICATION_V1.csv"
GO_NO_GO_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_GO_NO_GO_V1.csv"
VALIDATOR_REL = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py"
CI_REL = "scripts/ci_static_checks.sh"
SMOKE_REL = "scripts/smoke_petmed.sh"
WORKFLOW_REL = ".github/workflows/ci-gate.yml"
PREVIOUS_DOC_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1.md"
PREVIOUS_CHECKLIST_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_CHECKLIST_V1.csv"
PREVIOUS_SCHEMA_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_SCHEMA_EVIDENCE_V1.csv"
PREVIOUS_SMOKE_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_SMOKE_EVIDENCE_V1.csv"
PREVIOUS_GO_NO_GO_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_GO_NO_GO_V1.csv"
PREVIOUS_VALIDATOR_REL = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence.py"
INACTIVE_DRAFT_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt"
TARGET_PATHS = ['docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_CHECKLIST_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_REGISTER_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_VERIFICATION_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_GO_NO_GO_V1.csv', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py', 'scripts/ci_static_checks.sh', 'scripts/smoke_petmed.sh', '.github/workflows/ci-gate.yml']
DANGEROUS_FLAGS = ['ENABLE_EMR_REAL_IMPORT', 'ENABLE_EMR_IMPORT_CASE_UPDATE', 'ENABLE_EMR_ATTACHMENT_DOWNLOAD', 'ENABLE_PREVENTIVE_AUTO_DELIVERY', 'ENABLE_PREVENTIVE_SMS_DELIVERY', 'ENABLE_PREVENTIVE_WECHAT_DELIVERY', 'ENABLE_PREVENTIVE_EMAIL_DELIVERY', 'ENABLE_PRESCRIPTION_STRUCTURED_WRITE', 'ENABLE_DEVICE_REAL_INGEST', 'ENABLE_BILLING_REAL_WRITE']

PREVIOUS_RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1_smoke_petmed_runtime_gate"
PREVIOUS_COMPAT_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1_smoke_petmed_compatibility_gate"
PREVIOUS_COMPAT_END = "# <<< treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1_smoke_petmed_compatibility_gate"
RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_runtime_gate"
RUNTIME_END = "# <<< treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_runtime_gate"


class ValidationError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        print("NO-GO: " + message)
        raise SystemExit(1)


def read(rel_path):
    path = ROOT / rel_path
    require(path.is_file(), "missing required file: " + rel_path)
    return path.read_text(encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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
    require(not matches, "active backend/migrations/versions/0010*.py is forbidden in PMAI-P0-02")


def check_baseline(doc):
    require(doc_value(doc, "baseline_commit_sha") == BASELINE_COMMIT, "baseline commit mismatch")
    require(
        run_git(["cat-file", "-e", BASELINE_COMMIT + "^{commit}"], check=False).returncode == 0,
        "baseline commit is missing",
    )
    require(
        run_git(["merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"], check=False).returncode == 0,
        "baseline commit is not an ancestor of HEAD",
    )
    previous_path = ROOT / PREVIOUS_DOC_REL
    require(previous_path.is_file(), "previous evidence document missing")
    require(
        doc_value(doc, "previous_evidence_document_sha256") == sha256_file(previous_path),
        "previous evidence document SHA-256 mismatch",
    )
    draft_path = ROOT / INACTIVE_DRAFT_REL
    require(draft_path.is_file(), "inactive 0010 draft missing")
    require(
        doc_value(doc, "inactive_0010_draft_sha256") == sha256_file(draft_path),
        "inactive 0010 draft SHA-256 mismatch",
    )


def check_previous_stage():
    previous_doc = read(PREVIOUS_DOC_REL)
    for rel_path in (
        PREVIOUS_CHECKLIST_REL,
        PREVIOUS_SCHEMA_REL,
        PREVIOUS_SMOKE_REL,
        PREVIOUS_GO_NO_GO_REL,
        PREVIOUS_VALIDATOR_REL,
    ):
        read(rel_path)
    require_tokens(
        "previous PMAI-P0-01 document",
        previous_doc,
        [
            "stage_id=PMAI-P0-01",
            "EVIDENCE_COMPLETENESS=PARTIAL",
            "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=false",
            "decision=" + ENTRY_DECISION,
            "database_revision=0009_diag_data",
            "alembic_head=0009_diag_data",
            "writes_database=false",
        ],
    )


def check_document():
    doc = read(DOC_REL)
    required = [
        "stage_id=" + STAGE_ID,
        "stage_name=" + STAGE_TITLE,
        "stage_type=rollback_restore_evidence_collection",
        "PACKAGE_INITIALIZED=true",
        "STAGING_MIGRATION_EXECUTED=false",
        "PRODUCTION_MIGRATION_EXECUTED=false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED=false",
        "SCHEMA_CHANGE_APPLIED=false",
        "APPLICATION_DATABASE_WRITE_PERFORMED=false",
        "PRODUCTION_DATABASE_WRITE_PERFORMED=false",
        "CASE_TREATMENT_WRITE_PERFORMED=false",
        "PRESCRIPTION_WRITE_PERFORMED=false",
        "CLIENT_FACING_RELEASE_PERFORMED=false",
        "CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false",
        "STAGING_DATABASE_URL_RECORDED=false",
        "STAGING_CREDENTIAL_RECORDED=false",
        "STAMP_HEAD_USED=false",
        "MANUAL_ALEMBIC_REVISION_EDIT_USED=false",
        "database_revision=0009_diag_data",
        "alembic_head=0009_diag_data",
        "schema_ok=true",
        "migration_errors=[]",
        "writes_database=false",
        "exposes_database_url=false",
        "baseline_commit_sha=" + BASELINE_COMMIT,
        "previous_stage_decision=" + ENTRY_DECISION,
        "completion_decision=" + COMPLETION_DECISION,
        "active_0010_migration_file_must_not_exist=true",
    ]
    require_tokens("rollback/restore document", doc, required)
    for flag in DANGEROUS_FLAGS:
        require(flag + "=false" in doc, "dangerous feature flag false marker missing: " + flag)
    state = doc_value(doc, "STAGE_STATUS")
    require(state in ("IN_PROGRESS", "COMPLETE"), "invalid STAGE_STATUS")
    return doc, state


def check_secret_safety():
    combined = "\n".join(
        read(rel_path)
        for rel_path in (
            DOC_REL,
            CHECKLIST_REL,
            REGISTER_REL,
            VERIFICATION_REL,
            GO_NO_GO_REL,
            CI_REL,
        )
    )
    require(
        re.search(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://", combined) is None,
        "database or service connection URI found in stage targets",
    )
    require(
        re.search(r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[^\s,;]+", combined) is None,
        "credential-like key/value found in stage targets",
    )
    require(
        re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", combined) is None,
        "email address found in stage evidence targets",
    )
    for flag in DANGEROUS_FLAGS:
        for pattern in (flag + "=true", flag + ": true", '"' + flag + '": true'):
            require(pattern not in combined, "dangerous feature flag enablement found: " + pattern)


def placeholder(value):
    return value.strip() in ("", "UNRECORDED", "PENDING", "NOT_EXECUTED", "NOT_APPLICABLE")


def valid_sha(value):
    return re.fullmatch(r"[0-9a-f]{64}", value.strip()) is not None


def check_csvs(state):
    checklist = read_csv(
        CHECKLIST_REL,
        ["item_id", "area", "requirement", "evidence_source", "evidence_status", "blocking", "notes"],
        ["RR-%03d" % value for value in range(1, 17)],
        "item_id",
    )
    register = read_csv(
        REGISTER_REL,
        ["evidence_id", "evidence_type", "required_field", "observed_value", "evidence_source", "evidence_sha256", "evidence_status", "blocking", "notes"],
        ["RRE-%03d" % value for value in range(1, 21)],
        "evidence_id",
    )
    verification = read_csv(
        VERIFICATION_REL,
        ["check_id", "verification_area", "object_name", "baseline_value", "restored_value", "comparison_status", "evidence_source", "blocking", "notes"],
        ["VER-%03d" % value for value in range(1, 13)],
        "check_id",
    )
    gates = read_csv(
        GO_NO_GO_REL,
        ["gate_id", "gate", "required_state", "observed_state", "decision", "blocking", "notes"],
        ["GATE-%03d" % value for value in range(1, 13)],
        "gate_id",
    )

    if state == "IN_PROGRESS":
        statuses = set(row["evidence_status"] for row in checklist)
        require("PENDING_EXTERNAL_EVIDENCE" in statuses, "checklist must retain pending external evidence")
        require("HOLD_PENDING_EXTERNAL_EVIDENCE" in statuses, "checklist must retain HOLD status")
        require(any(row["decision"] == HOLD_DECISION for row in gates), "Go/No-Go must remain on HOLD")
        require(any(row["decision"] == "NO_GO_TO_PMAI_P0_03" for row in gates), "Go/No-Go must block P0-03")
        for row in register:
            if row["blocking"] == "yes":
                require(row["evidence_status"] == "PENDING_EXTERNAL_EVIDENCE", "blocking register evidence must remain pending during initialization")
        for row in verification:
            require(row["comparison_status"] == "PENDING", "verification rows must remain pending during initialization")
    else:
        require(all(row["evidence_status"] in ("VERIFIED", "PASS_STATIC", "PASS_POLICY", "PASS_RUNTIME") for row in checklist), "completion checklist contains non-passing status")
        for row in register:
            require(row["evidence_status"] == "VERIFIED", "completion register row is not VERIFIED: " + row["evidence_id"])
            require(not placeholder(row["observed_value"]), "completion register observed value missing: " + row["evidence_id"])
            require(not placeholder(row["evidence_source"]), "completion register source missing: " + row["evidence_id"])
            if row["evidence_type"] in ("environment", "backup", "restore", "operation_output"):
                require(valid_sha(row["evidence_sha256"]), "completion evidence SHA-256 missing or invalid: " + row["evidence_id"])
        for row in verification:
            require(row["comparison_status"] in ("MATCH", "PASS"), "completion verification failed or pending: " + row["check_id"])
            require(not placeholder(row["restored_value"]), "completion restored value missing: " + row["check_id"])
            require(not placeholder(row["evidence_source"]), "completion verification source missing: " + row["check_id"])
        require(all(not row["decision"].startswith("NO_GO") for row in gates), "completion Go/No-Go still contains NO_GO")
        require(any(row["decision"] == COMPLETION_DECISION for row in gates), "completion decision missing from Go/No-Go")

    return checklist, register, verification, gates


def check_state_claims(doc, state):
    if state == "IN_PROGRESS":
        require_tokens(
            "in-progress document",
            doc,
            [
                "EVIDENCE_COMPLETENESS=PENDING_EXTERNAL_EXECUTION",
                "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=false",
                "BACKUP_EVIDENCE_COMPLETE=false",
                "RESTORE_EVIDENCE_COMPLETE=false",
                "ROLLBACK_DRY_RUN_EVIDENCE_COMPLETE=false",
                "DATA_VERIFICATION_COMPLETE=false",
                "CLINICAL_CASE_READBACK_COMPLETE=false",
                "FAILURE_PATH_OWNER_RECORDED=false",
            ],
        )
        require(doc_value(doc, "decision") == HOLD_DECISION, "in-progress decision must remain on HOLD")
        forbidden = [
            "EVIDENCE_COMPLETENESS=COMPLETE",
            "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=true",
            "BACKUP_EVIDENCE_COMPLETE=true",
            "RESTORE_EVIDENCE_COMPLETE=true",
            "ROLLBACK_DRY_RUN_EVIDENCE_COMPLETE=true",
            "DATA_VERIFICATION_COMPLETE=true",
            "CLINICAL_CASE_READBACK_COMPLETE=true",
            "FAILURE_PATH_OWNER_RECORDED=true",
        ]
        for token in forbidden:
            require(token not in doc, "unsupported completion claim found: " + token)
    else:
        require_tokens(
            "complete document",
            doc,
            [
                "EVIDENCE_COMPLETENESS=COMPLETE",
                "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=true",
                "BACKUP_EVIDENCE_COMPLETE=true",
                "RESTORE_EVIDENCE_COMPLETE=true",
                "ROLLBACK_DRY_RUN_EVIDENCE_COMPLETE=true",
                "DATA_VERIFICATION_COMPLETE=true",
                "CLINICAL_CASE_READBACK_COMPLETE=true",
                "FAILURE_PATH_OWNER_RECORDED=true",
            ],
        )
        require(doc_value(doc, "decision") == COMPLETION_DECISION, "complete decision must hand off to authenticated staging smoke")


def check_workflow_wiring():
    workflow = read(WORKFLOW_REL)
    match = re.search(
        r"(?ms)^  static-backend-gate:\n(.*?)(?=^  frontend-build-gate:|\Z)",
        workflow,
    )
    require(match is not None, "static backend CI job is missing")
    static_job = match.group(1)
    require(
        "uses: actions/checkout@v4" in static_job,
        "static backend checkout action is missing",
    )
    require(
        "fetch-depth: 0" in static_job,
        "static backend checkout must fetch full history for baseline validation",
    )


def check_ci_wiring():
    ci = read(CI_REL)
    require_tokens(
        "CI",
        ci,
        [
            "# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1",
            VALIDATOR_REL,
            "python3 -m py_compile " + VALIDATOR_REL,
            "python3 " + VALIDATOR_REL,
            'for validator in "${OPTIONAL_CORE_VALIDATORS[@]:-}"; do',
            '[ -n "$validator" ] || continue',
            PREVIOUS_STAGE_TOKEN,
            PREVIOUS_VALIDATOR_REL,
            "rollback restore evidence package markers",
            "target-only tracked diff discipline",
            "sensitive staged path discipline",
            "full history checkout for baseline verification",
            "PASS: ci_static_checks",
        ],
    )
    match = re.search(r"TARGETS=\((.*?)\n\)", ci, flags=re.S)
    require(match is not None, "CI TARGETS block missing")
    paths = re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)
    require(paths == TARGET_PATHS, "CI TARGETS are not canonical for PMAI-P0-02")
    require("git add ." not in ci, "CI contains forbidden git add .")
    require("git add -A" not in ci, "CI contains forbidden git add -A")


def check_smoke_wiring(state):
    smoke = read(SMOKE_REL)
    require(PREVIOUS_RUNTIME_BEGIN not in smoke, "previous evidence runtime validator remains active")
    require(smoke.count(PREVIOUS_COMPAT_BEGIN) == 1, "previous evidence compatibility begin must occur once")
    require(smoke.count(PREVIOUS_COMPAT_END) == 1, "previous evidence compatibility end must occur once")
    require(smoke.count(RUNTIME_BEGIN) == 1, "current runtime begin must occur once")
    require(smoke.count(RUNTIME_END) == 1, "current runtime end must occur once")
    compat_begin = smoke.index(PREVIOUS_COMPAT_BEGIN)
    compat_end = smoke.index(PREVIOUS_COMPAT_END, compat_begin) + len(PREVIOUS_COMPAT_END)
    runtime_begin = smoke.index(RUNTIME_BEGIN)
    runtime_end = smoke.index(RUNTIME_END, runtime_begin) + len(RUNTIME_END)
    final_pass = smoke.rfind("ALL PASS: smoke_petmed")
    require(final_pass >= 0, "final smoke PASS missing")
    require(compat_begin < compat_end < runtime_begin < runtime_end < final_pass, "smoke runtime ordering is invalid")
    compat = smoke[compat_begin:compat_end]
    require("python3" not in compat, "previous evidence validator must not execute in current smoke")
    require_tokens(
        "previous evidence compatibility gate",
        compat,
        [
            PREVIOUS_DOC_REL,
            PREVIOUS_CHECKLIST_REL,
            PREVIOUS_SCHEMA_REL,
            PREVIOUS_SMOKE_REL,
            PREVIOUS_GO_NO_GO_REL,
            PREVIOUS_VALIDATOR_REL,
            "stage_id=PMAI-P0-01",
            "decision=" + ENTRY_DECISION,
            PREVIOUS_STAGE_TOKEN + "=PASS",
        ],
    )
    runtime = smoke[runtime_begin:runtime_end]
    require("python3" in runtime and VALIDATOR_REL in runtime, "current validator is not executed by smoke")
    require(PACKAGE_TOKEN + "=PASS" in runtime, "package PASS marker missing from runtime gate")
    summary = smoke[final_pass:]
    expected_state = "COMPLETE" if state == "COMPLETE" else "IN_PROGRESS"
    expected_decision = COMPLETION_DECISION if state == "COMPLETE" else HOLD_DECISION
    require_tokens(
        "final smoke summary",
        summary,
        [
            PREVIOUS_STAGE_TOKEN + "=true",
            STAGE_TOKEN + "=" + expected_state,
            "rollback_restore_evidence_complete=" + ("true" if state == "COMPLETE" else "false"),
            "previous_stage_decision=" + ENTRY_DECISION,
            "decision=" + expected_decision,
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
    parser = argparse.ArgumentParser(description="Validate PMAI-P0-02 rollback/restore evidence")
    parser.add_argument("--require-complete", action="store_true", help="fail unless real external evidence is complete")
    args = parser.parse_args()

    for rel_path in TARGET_PATHS:
        require((ROOT / rel_path).is_file(), "missing current-stage target: " + rel_path)
    check_no_active_0010()
    doc, state = check_document()
    check_state_claims(doc, state)
    check_baseline(doc)
    check_previous_stage()
    check_csvs(state)
    check_secret_safety()
    check_workflow_wiring()
    check_ci_wiring()
    check_smoke_wiring(state)
    check_shell_syntax(CI_REL)
    check_shell_syntax(SMOKE_REL)
    if args.require_complete:
        require(state == "COMPLETE", "PMAI-P0-02 external evidence is not complete")

    print("PASS: " + STAGE_TITLE + " package integrity")
    print("stage_id=" + STAGE_ID)
    print("stage_status=" + state)
    print("package_initialized=true")
    print("evidence_completeness=" + doc_value(doc, "EVIDENCE_COMPLETENESS"))
    print("rollback_restore_evidence_complete=" + ("true" if state == "COMPLETE" else "false"))
    print("staging_migration_executed=false")
    print("production_migration_executed=false")
    print("active_migration_file_created=false")
    print("database_revision=0009_diag_data")
    print("alembic_head=0009_diag_data")
    print("schema_ok=true")
    print("migration_errors=[]")
    print("writes_database=false")
    print("exposes_database_url=false")
    print("PASS: dangerous feature flags disabled")
    print("PASS: no application database, Case.treatment, or prescription write")
    print("PASS: no medication amount, route, or frequency output")
    print("validator_previous_stage_decision=" + ENTRY_DECISION)
    print("validator_decision=" + (COMPLETION_DECISION if state == "COMPLETE" else HOLD_DECISION))
    if state == "COMPLETE":
        print("ALL PASS: " + STAGE_TOKEN)
    else:
        print("ALL PASS: " + PACKAGE_TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
