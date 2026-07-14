#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import csv
import glob
import hashlib
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "PMAI-P0-01"
STAGE_TITLE = "Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Evidence V1"
STAGE_TOKEN_UPPER = "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1"
STAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1"
PREVIOUS_STAGE_TOKEN_UPPER = "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1"
PREVIOUS_STAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1"
PREVIOUS_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1"
DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1"

DOC_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1.md"
CHECKLIST_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_CHECKLIST_V1.csv"
SCHEMA_EVIDENCE_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_SCHEMA_EVIDENCE_V1.csv"
SMOKE_EVIDENCE_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_SMOKE_EVIDENCE_V1.csv"
GO_NO_GO_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_GO_NO_GO_V1.csv"
VALIDATOR_REL = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence.py"
CI_REL = "scripts/ci_static_checks.sh"
SMOKE_REL = "scripts/smoke_petmed.sh"
PREVIOUS_DOC_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1.md"
PREVIOUS_CHECKLIST_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_CHECKLIST_V1.csv"
PREVIOUS_GO_NO_GO_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_GO_NO_GO_V1.csv"
PREVIOUS_VALIDATOR_REL = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run.py"
INACTIVE_DRAFT_REL = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt"

TARGET_PATHS = [
    DOC_REL,
    CHECKLIST_REL,
    SCHEMA_EVIDENCE_REL,
    SMOKE_EVIDENCE_REL,
    GO_NO_GO_REL,
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

DRY_RUN_RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1_smoke_petmed_runtime_gate"
DRY_RUN_COMPAT_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1_smoke_petmed_compatibility_gate"
DRY_RUN_COMPAT_END = "# <<< treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_dry_run_v1_smoke_petmed_compatibility_gate"
EVIDENCE_RUNTIME_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1_smoke_petmed_runtime_gate"
EVIDENCE_RUNTIME_END = "# <<< treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1_smoke_petmed_runtime_gate"


def require(condition, message):
    if not condition:
        print("NO-GO: " + message)
        raise SystemExit(1)


def read(rel_path):
    path = ROOT / rel_path
    require(path.is_file(), "missing required file: " + rel_path)
    return path.read_text(encoding="utf-8")


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


def check_csv(rel_path, expected_columns, required_ids, id_column):
    path = ROOT / rel_path
    require(path.is_file(), "missing required csv: " + rel_path)
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
    pattern = str(ROOT / "backend" / "migrations" / "versions" / "0010*.py")
    matches = sorted(glob.glob(pattern))
    require(not matches, "active backend/migrations/versions/0010*.py is forbidden in this phase")


def check_document():
    doc = read(DOC_REL)
    required = [
        "stage_id=PMAI-P0-01",
        "stage_name=" + STAGE_TITLE,
        "stage_type=staging_rehearsal_evidence_register_only",
        "STAGING_REHEARSAL_EVIDENCE_REGISTER_ONLY=true",
        "REAL_STAGING_MIGRATION_EXECUTED=false",
        "PRODUCTION_MIGRATION_EXECUTED=false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED=false",
        "SCHEMA_CHANGE_APPLIED=false",
        "DATABASE_WRITE_PERFORMED=false",
        "CASE_TREATMENT_WRITE_PERFORMED=false",
        "PRESCRIPTION_WRITE_PERFORMED=false",
        "CLIENT_FACING_RELEASE_PERFORMED=false",
        "CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false",
        "EVIDENCE_COMPLETENESS=PARTIAL",
        "STAGING_APPLY_AUTHORIZED=false",
        "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=false",
        "AUTHENTICATED_STAGING_SMOKE_COMPLETE=false",
        "STAGING_ENVIRONMENT_ID_RECORDED=false",
        "STAGING_DATABASE_URL_RECORDED=false",
        "BACKUP_ID_RECORDED=false",
        "RESTORE_ID_RECORDED=false",
        "MIGRATION_COMMAND_OUTPUT_RECORDED=false",
        "database_revision=0009_diag_data",
        "alembic_head=0009_diag_data",
        "schema_ok=true",
        "migration_errors=[]",
        "writes_database=false",
        "exposes_database_url=false",
        "inactive_0010_draft_path=" + INACTIVE_DRAFT_REL,
        "inactive_0010_revision=0010_treatment_framework_signed_review_states",
        "inactive_0010_down_revision=0009_diag_data",
        "inactive_0010_reference_only=true",
        "active_0010_migration_file_must_not_exist=true",
        "no_staging_secret_material_collected=true",
        "evidence_claims_must_not_mark_unexecuted_checks_as_passed=true",
        "P0_02_ROLLBACK_RESTORE_EVIDENCE_REQUIRED=true",
        "P0_03_AUTHENTICATED_STAGING_SMOKE_REQUIRED=true",
        "P0_04_STAGING_MIGRATION_APPLY_REQUIRED_LATER=true",
        "previous_stage_decision=" + PREVIOUS_DECISION,
        "decision=" + DECISION,
    ]
    require_tokens("evidence document", doc, required)
    for flag in DANGEROUS_FLAGS:
        require(flag + "=false" in doc, "dangerous feature flag false marker missing: " + flag)
    return doc


def check_baseline_and_inactive_draft(doc):
    baseline = doc_value(doc, "baseline_commit_sha")
    require(re.fullmatch(r"[0-9a-f]{40}", baseline) is not None, "invalid baseline commit SHA")

    inside = run_git(["rev-parse", "--is-inside-work-tree"], check=False)
    require(inside.returncode == 0 and inside.stdout.strip() == "true", "validator must run in Git work tree")

    require(
        run_git(["cat-file", "-e", baseline + "^{commit}"], check=False).returncode == 0,
        "baseline commit does not exist in repository: " + baseline,
    )
    require(
        run_git(["merge-base", "--is-ancestor", baseline, "HEAD"], check=False).returncode == 0,
        "baseline commit is not an ancestor of HEAD",
    )

    draft_path = ROOT / INACTIVE_DRAFT_REL
    require(draft_path.is_file(), "inactive 0010 draft reference missing")
    expected_hash = doc_value(doc, "inactive_0010_draft_sha256")
    require(re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None, "invalid inactive draft SHA-256")
    require(sha256_file(draft_path) == expected_hash, "inactive 0010 draft SHA-256 mismatch")

    draft = draft_path.read_text(encoding="utf-8")
    required_draft = [
        'revision = "0010_treatment_framework_signed_review_states"',
        'down_revision = "0009_diag_data"',
        '"treatment_framework_signed_review_states"',
        'sa.Column("id"',
        'sa.Column("case_id"',
        'sa.Column("confirmed_diagnosis_label"',
        'sa.Column("confirmed_by"',
        'sa.Column("confirmation_source"',
        'sa.Column("ai_generated"',
        'sa.Column("review_decision"',
        'sa.Column("signed_review_status"',
        'sa.Column("reviewed_by"',
        'sa.Column("signed_by"',
        'sa.Column("signoff_decision"',
        'sa.Column("audit_log_reference"',
        'sa.Column("source_preview_id"',
        'sa.Column("metadata_json"',
        'sa.Column("created_at"',
        'sa.Column("updated_at"',
        'sa.ForeignKeyConstraint(["case_id"], ["cases.id"]',
        'op.create_index("ix_tfsrs_case_id"',
        'op.create_index("ix_tfsrs_audit_log_reference"',
        'op.create_index("ix_tfsrs_created_at"',
        'op.drop_index("ix_tfsrs_created_at"',
        'op.drop_index("ix_tfsrs_audit_log_reference"',
        'op.drop_index("ix_tfsrs_case_id"',
        'op.drop_table("treatment_framework_signed_review_states")',
    ]
    require_tokens("inactive 0010 draft", draft, required_draft)


def check_previous_stage_artifacts():
    previous_doc = read(PREVIOUS_DOC_REL)
    read(PREVIOUS_CHECKLIST_REL)
    read(PREVIOUS_GO_NO_GO_REL)
    read(PREVIOUS_VALIDATOR_REL)
    require_tokens(
        "previous dry-run document",
        previous_doc,
        [
            "stage_name=Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Dry Run V1",
            "STAGING_REHEARSAL_DRY_RUN_ONLY=true",
            "REAL_STAGING_MIGRATION_EXECUTED=false",
            "ACTIVE_0010_MIGRATION_FILE_CREATED=false",
            "decision=" + PREVIOUS_DECISION,
        ],
    )


def check_evidence_csvs():
    checklist_rows = check_csv(
        CHECKLIST_REL,
        ["item_id", "area", "requirement", "evidence_source", "evidence_status", "blocking", "notes"],
        ["EVID-%03d" % value for value in range(1, 17)],
        "item_id",
    )
    checklist_statuses = set(row["evidence_status"] for row in checklist_rows)
    for required_status in (
        "CAPTURED_REFERENCE",
        "PENDING_EXTERNAL_EVIDENCE",
        "NOT_EXECUTED_BY_STAGE",
        "PENDING_P0_02",
        "PENDING_P0_03",
        "PENDING_P0_04",
    ):
        require(required_status in checklist_statuses, "checklist missing status: " + required_status)
    require(any(row["evidence_source"] == DECISION for row in checklist_rows), "checklist missing next decision")

    schema_rows = check_csv(
        SCHEMA_EVIDENCE_REL,
        ["evidence_id", "object_type", "object_name", "expected_definition", "observed_source", "observed_state", "evidence_status", "blocking", "notes"],
        ["SCH-%03d" % value for value in range(1, 27)],
        "evidence_id",
    )
    schema_by_name = dict((row["object_name"], row) for row in schema_rows)
    for name in (
        "revision",
        "down_revision",
        "treatment_framework_signed_review_states",
        "id",
        "case_id",
        "confirmed_diagnosis_label",
        "confirmed_by",
        "confirmation_source",
        "ai_generated",
        "review_decision",
        "signed_review_status",
        "reviewed_by",
        "signed_by",
        "signoff_decision",
        "audit_log_reference",
        "source_preview_id",
        "metadata_json",
        "created_at",
        "updated_at",
        "fk_tfsrs_case_id_cases",
        "ix_tfsrs_case_id",
        "ix_tfsrs_audit_log_reference",
        "ix_tfsrs_created_at",
        "downgrade",
        "active_0010_absence",
        "staging_runtime_introspection",
    ):
        require(name in schema_by_name, "schema evidence missing object: " + name)
    require(
        schema_by_name["staging_runtime_introspection"]["observed_state"] == "NOT_OBSERVED",
        "live staging schema must remain explicitly unobserved",
    )
    require(
        schema_by_name["staging_runtime_introspection"]["evidence_status"] == "PENDING_P0_04",
        "live staging schema must remain pending P0-04",
    )

    smoke_rows = check_csv(
        SMOKE_EVIDENCE_REL,
        ["evidence_id", "smoke_area", "requirement", "evidence_source", "observed_state", "evidence_status", "blocking", "notes"],
        ["SMK-%03d" % value for value in range(1, 13)],
        "evidence_id",
    )
    smoke_by_area = dict((row["smoke_area"], row) for row in smoke_rows)
    for area in (
        "staging_authentication",
        "owner_scope",
        "signed_review_workflow",
        "idempotency",
        "failure_rollback",
    ):
        require(smoke_by_area[area]["observed_state"] == "NOT_EXECUTED", area + " must remain unexecuted")
        require(smoke_by_area[area]["evidence_status"] == "PENDING_P0_03", area + " must remain pending P0-03")

    go_rows = check_csv(
        GO_NO_GO_REL,
        ["gate_id", "gate", "required_state", "observed_state", "decision", "blocking", "notes"],
        ["GATE-%03d" % value for value in range(1, 13)],
        "gate_id",
    )
    decisions = [row["decision"] for row in go_rows]
    require("NO_GO_FOR_STAGING_MIGRATION_APPLY" in decisions, "go/no-go must block staging migration apply")
    require("NO_GO_FOR_REAL_WRITE" in decisions, "go/no-go must block real write")
    require(DECISION in decisions, "go/no-go missing next-stage decision")


def check_claim_integrity():
    combined = "\n".join(
        [
            read(DOC_REL),
            read(CHECKLIST_REL),
            read(SCHEMA_EVIDENCE_REL),
            read(SMOKE_EVIDENCE_REL),
            read(GO_NO_GO_REL),
            read(CI_REL),
        ]
    )
    forbidden_claims = [
        "REAL_STAGING_MIGRATION_EXECUTED=true",
        "PRODUCTION_MIGRATION_EXECUTED=true",
        "ACTIVE_0010_MIGRATION_FILE_CREATED=true",
        "SCHEMA_CHANGE_APPLIED=true",
        "DATABASE_WRITE_PERFORMED=true",
        "CASE_TREATMENT_WRITE_PERFORMED=true",
        "PRESCRIPTION_WRITE_PERFORMED=true",
        "CLIENT_FACING_RELEASE_PERFORMED=true",
        "CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=true",
        "EVIDENCE_COMPLETENESS=COMPLETE",
        "STAGING_APPLY_AUTHORIZED=true",
        "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=true",
        "AUTHENTICATED_STAGING_SMOKE_COMPLETE=true",
        "STAGING_ENVIRONMENT_ID_RECORDED=true",
        "STAGING_DATABASE_URL_RECORDED=true",
        "BACKUP_ID_RECORDED=true",
        "RESTORE_ID_RECORDED=true",
        "MIGRATION_COMMAND_OUTPUT_RECORDED=true",
    ]
    for claim in forbidden_claims:
        require(claim not in combined, "forbidden unsupported evidence claim found: " + claim)
    for flag in DANGEROUS_FLAGS:
        for pattern in (flag + "=true", flag + ": true", '"' + flag + '": true'):
            require(pattern not in combined, "dangerous feature flag enablement found: " + pattern)
    require(
        re.search(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://", combined) is None,
        "database or service credential URI found in evidence targets",
    )


def check_ci_wiring():
    ci = read(CI_REL)
    required = [
        "# " + STAGE_TOKEN_UPPER,
        VALIDATOR_REL,
        "python3 -m py_compile " + VALIDATOR_REL,
        "python3 " + VALIDATOR_REL,
        'for validator in "${OPTIONAL_CORE_VALIDATORS[@]:-}"; do',
        '[ -n "$validator" ] || continue',
        PREVIOUS_STAGE_TOKEN_UPPER,
        PREVIOUS_VALIDATOR_REL,
        "previous_stage_decision=" + PREVIOUS_DECISION,
        "signed review state persistence migration staging rehearsal evidence markers",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "PASS: ci_static_checks",
    ]
    require_tokens("ci", ci, required)

    match = re.search(r"TARGETS=\((.*?)\n\)", ci, flags=re.S)
    require(match is not None, "CI TARGETS block missing")
    paths = re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)
    require(paths == TARGET_PATHS, "CI TARGETS must contain only current-stage paths in canonical order")
    require(PREVIOUS_DOC_REL not in paths, "previous-stage document must not be a current CI target")
    require("git add ." not in ci, "CI contains forbidden git add .")
    require("git add -A" not in ci, "CI contains forbidden git add -A")


def check_smoke_wiring():
    smoke = read(SMOKE_REL)

    require(DRY_RUN_RUNTIME_BEGIN not in smoke, "obsolete dry-run runtime validator gate remains active")
    require(smoke.count(DRY_RUN_COMPAT_BEGIN) == 1, "dry-run compatibility gate begin must occur once")
    require(smoke.count(DRY_RUN_COMPAT_END) == 1, "dry-run compatibility gate end must occur once")
    require(smoke.count(EVIDENCE_RUNTIME_BEGIN) == 1, "evidence runtime gate begin must occur once")
    require(smoke.count(EVIDENCE_RUNTIME_END) == 1, "evidence runtime gate end must occur once")

    compat_begin = smoke.index(DRY_RUN_COMPAT_BEGIN)
    compat_end = smoke.index(DRY_RUN_COMPAT_END, compat_begin) + len(DRY_RUN_COMPAT_END)
    runtime_begin = smoke.index(EVIDENCE_RUNTIME_BEGIN)
    runtime_end = smoke.index(EVIDENCE_RUNTIME_END, runtime_begin) + len(EVIDENCE_RUNTIME_END)
    final_pass = smoke.rfind("ALL PASS: smoke_petmed")
    require(final_pass >= 0, "final smoke PASS marker missing")
    require(compat_begin < compat_end < runtime_begin < runtime_end < final_pass, "smoke gate ordering is invalid")

    compat_block = smoke[compat_begin:compat_end]
    require("python3" not in compat_block, "historical dry-run validator must not execute in current cumulative smoke")
    require_tokens(
        "dry-run compatibility block",
        compat_block,
        [
            PREVIOUS_DOC_REL,
            PREVIOUS_CHECKLIST_REL,
            PREVIOUS_GO_NO_GO_REL,
            PREVIOUS_VALIDATOR_REL,
            "STAGING_REHEARSAL_DRY_RUN_ONLY=true",
            "REAL_STAGING_MIGRATION_EXECUTED=false",
            "decision=" + PREVIOUS_DECISION,
            PREVIOUS_STAGE_TOKEN + "=PASS",
        ],
    )

    runtime_block = smoke[runtime_begin:runtime_end]
    require("python3" in runtime_block, "current evidence runtime gate does not execute Python")
    require(VALIDATOR_REL in runtime_block, "current evidence runtime gate does not execute the validator")
    require(STAGE_TOKEN + "=PASS" in runtime_block, "current evidence runtime PASS marker missing")

    summary = smoke[final_pass:]
    require_tokens(
        "final smoke summary",
        summary,
        [
            "treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_plan_v1=true",
            PREVIOUS_STAGE_TOKEN + "=true",
            STAGE_TOKEN + "=true",
            "previous_stage_decision=" + PREVIOUS_DECISION,
            "decision=" + DECISION,
        ],
    )
    require(summary.count('"previous_stage_decision=') == 1, "summary must have exactly one previous_stage_decision")
    require(summary.count('"decision=') == 1, "summary must have exactly one decision")
    require(
        '"decision=' + PREVIOUS_DECISION + '"' not in summary,
        "summary still points to the already-completed evidence stage",
    )
    require(len(smoke.splitlines()) >= 1000, "cumulative smoke coverage line count is too small")


def check_shell_syntax(rel_path):
    result = subprocess.run(
        ["bash", "-n", str(ROOT / rel_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(result.returncode == 0, rel_path + " shell syntax failed: " + result.stderr.strip())


def main():
    for rel_path in TARGET_PATHS:
        require((ROOT / rel_path).is_file(), "missing current-stage target: " + rel_path)

    check_no_active_0010()
    doc = check_document()
    check_baseline_and_inactive_draft(doc)
    check_previous_stage_artifacts()
    check_evidence_csvs()
    check_claim_integrity()
    check_ci_wiring()
    check_smoke_wiring()
    check_shell_syntax(CI_REL)
    check_shell_syntax(SMOKE_REL)

    print("PASS: " + STAGE_TITLE)
    print("stage_id=" + STAGE_ID)
    print("evidence_register_only=true")
    print("evidence_completeness=PARTIAL")
    print("real_staging_migration_executed=false")
    print("production_migration_executed=false")
    print("active_migration_file_created=false")
    print("staging_apply_authorized=false")
    print("rollback_restore_evidence_complete=false")
    print("authenticated_staging_smoke_complete=false")
    print("database_revision=0009_diag_data")
    print("alembic_head=0009_diag_data")
    print("schema_ok=true")
    print("migration_errors=[]")
    print("writes_database=false")
    print("exposes_database_url=false")
    print("PASS: dangerous feature flags disabled")
    print("PASS: no database, Case.treatment, or prescription write")
    print("PASS: no medication amount, route, or frequency output")
    print("validator_previous_stage_decision=" + PREVIOUS_DECISION)
    print("validator_decision=" + DECISION)
    print("ALL PASS: " + STAGE_TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
