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
STAGE_ID = "PMAI-P0-02"
STAGE_TITLE = "Treatment Framework Signed Review State Persistence Migration Rollback Restore Evidence V1"
STAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1"
PREVIOUS_STAGE_TOKEN = "treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1"
ENTRY_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1"
COMPLETION_DECISION = "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1"
EXPECTED_REVISION = "0009_diag_data"

DOC_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1.md'
CHECKLIST_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_CHECKLIST_V1.csv'
REGISTER_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_REGISTER_V1.csv'
VERIFICATION_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_VERIFICATION_V1.csv'
GO_NO_GO_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_GO_NO_GO_V1.csv'
VALIDATOR_REL = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py'
CI_REL = 'scripts/ci_static_checks.sh'
SMOKE_REL = 'scripts/smoke_petmed.sh'
WORKFLOW_REL = '.github/workflows/ci-gate.yml'
PREVIOUS_DOC_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1.md'
PREVIOUS_CHECKLIST_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_CHECKLIST_V1.csv'
PREVIOUS_SCHEMA_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_SCHEMA_EVIDENCE_V1.csv'
PREVIOUS_SMOKE_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_SMOKE_EVIDENCE_V1.csv'
PREVIOUS_GO_NO_GO_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_GO_NO_GO_V1.csv'
PREVIOUS_VALIDATOR_REL = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence.py'
INACTIVE_DRAFT_REL = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt'
EVIDENCE_DIR_REL = 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1'
EVIDENCE_NAMES = ['00_README.txt', '01_environment_sanitized.txt', '02_provider_backup_sanitized.txt', '03_provider_restore_sanitized.txt', '04_failure_ownership_sanitized.txt', '05_staging_baseline_preparation_sanitized.txt', '10_source_readonly_verification.csv', '11_restore_readonly_verification.csv', '12_restore_comparison_sanitized.txt']
TARGET_PATHS = ['docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_CHECKLIST_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_REGISTER_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_VERIFICATION_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_GO_NO_GO_V1.csv', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/00_README.txt', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/01_environment_sanitized.txt', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/02_provider_backup_sanitized.txt', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/03_provider_restore_sanitized.txt', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/04_failure_ownership_sanitized.txt', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/05_staging_baseline_preparation_sanitized.txt', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/10_source_readonly_verification.csv', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/11_restore_readonly_verification.csv', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/12_restore_comparison_sanitized.txt', 'docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/SHA256SUMS.txt', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py', 'scripts/ci_static_checks.sh', 'scripts/smoke_petmed.sh', '.github/workflows/ci-gate.yml']
DANGEROUS_FLAGS = ['ENABLE_EMR_REAL_IMPORT', 'ENABLE_EMR_IMPORT_CASE_UPDATE', 'ENABLE_EMR_ATTACHMENT_DOWNLOAD', 'ENABLE_PREVENTIVE_AUTO_DELIVERY', 'ENABLE_PREVENTIVE_SMS_DELIVERY', 'ENABLE_PREVENTIVE_WECHAT_DELIVERY', 'ENABLE_PREVENTIVE_EMAIL_DELIVERY', 'ENABLE_PRESCRIPTION_STRUCTURED_WRITE', 'ENABLE_DEVICE_REAL_INGEST', 'ENABLE_BILLING_REAL_WRITE']
RUNTIME_BEGIN = '# >>> treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_runtime_gate'
RUNTIME_END = '# <<< treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence_v1_smoke_petmed_runtime_gate'
PREVIOUS_COMPAT_BEGIN = "# >>> treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1_smoke_petmed_compatibility_gate"
PREVIOUS_COMPAT_END = "# <<< treatment_framework_signed_review_state_persistence_migration_staging_rehearsal_evidence_v1_smoke_petmed_compatibility_gate"

FORBIDDEN_PATTERNS = (
    (re.compile(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"), "database/service URI"),
    (re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret|database_url)\s*[:=]\s*[^\s,;]+"), "credential-like key/value"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "email address"),
    (re.compile(r"(?i)\b(?:owner_name|owner_phone|patient_name|full_name)\s*[:=]\s*[^\n]+"), "direct clinical or owner identifier"),
)


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


def parse_kv(rel_path):
    values = {}
    for line_number, raw_line in enumerate(read(rel_path).splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        require("=" in line, "invalid key/value row %s:%d" % (rel_path, line_number))
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        require(key and key not in values, "duplicate key %s in %s" % (key, rel_path))
        values[key] = value
    return values


def parse_capture(rel_path):
    values = {}
    with (ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row_number, row in enumerate(reader, start=1):
            if not row:
                continue
            require(len(row) == 2, "invalid capture row %s:%d" % (rel_path, row_number))
            key, value = row[0].strip(), row[1].strip()
            require(key not in values, "duplicate capture key %s" % key)
            values[key] = value
    return values


def read_csv(rel_path, expected_columns, required_ids, id_column):
    with (ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == expected_columns, "unexpected columns in " + rel_path)
        rows = list(reader)
    require([row[id_column] for row in rows] == required_ids, "unexpected row IDs/order in " + rel_path)
    for row in rows:
        require(row.get("blocking") in ("yes", "no"), "invalid blocking value in " + rel_path)
    return rows


def run_git(args, check=True):
    result = subprocess.run(["git"] + list(args), cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check:
        require(result.returncode == 0, "git command failed: git %s: %s" % (" ".join(args), result.stderr.strip() or result.stdout.strip()))
    return result


def check_no_active_0010():
    matches = sorted(glob.glob(str(ROOT / "backend" / "migrations" / "versions" / "0010*.py")))
    require(not matches, "active backend/migrations/versions/0010*.py is forbidden in PMAI-P0-02")


def check_document():
    doc = read(DOC_REL)
    required = [
        "stage_id=PMAI-P0-02",
        "STAGE_STATUS=COMPLETE",
        "EVIDENCE_COMPLETENESS=COMPLETE",
        "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=true",
        "BACKUP_EVIDENCE_COMPLETE=true",
        "RESTORE_EVIDENCE_COMPLETE=true",
        "ROLLBACK_DRY_RUN_EVIDENCE_COMPLETE=true",
        "DATA_VERIFICATION_COMPLETE=true",
        "CLINICAL_CASE_READBACK_COMPLETE=true",
        "FAILURE_PATH_OWNER_RECORDED=true",
        "STAGING_MIGRATION_EXECUTED=false",
        "STAGING_MIGRATION_EXECUTED_SCOPE=signed_review_0010_only",
        "STAGING_BASELINE_0001_TO_0009_PREPARATION_EXECUTED=true",
        "STAGING_SYNTHETIC_FIXTURE_WRITE_EXECUTED=true",
        "STAGING_DATABASE_WRITE_PERFORMED=true",
        "SIGNED_REVIEW_0010_STAGING_MIGRATION_EXECUTED=false",
        "SIGNED_REVIEW_0010_SCHEMA_CHANGE_APPLIED=false",
        "PRODUCTION_MIGRATION_EXECUTED=false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED=false",
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
        "STAGING_APPLY_AUTHORIZED=false",
        "AUTHENTICATED_STAGING_SMOKE_AUTHORIZED=true",
        "PRODUCTION_MIGRATION_AUTHORIZED=false",
        "database_revision=0009_diag_data",
        "alembic_head=0009_diag_data",
        "schema_ok=true",
        "migration_errors=[]",
        "writes_database=false",
        "exposes_database_url=false",
        "row_count_parity=MATCH",
        "sample_case_readback=MATCH",
        "referential_integrity=PASS",
        "synthetic_fixture_only=true",
        "previous_stage_decision=" + ENTRY_DECISION,
        "decision=" + COMPLETION_DECISION,
    ]
    for token in required:
        require(token in doc, "completion document missing token: " + token)
    for flag in DANGEROUS_FLAGS:
        require(flag + "=false" in doc, "dangerous feature flag marker missing: " + flag)
    for key in ("baseline_commit_sha", "completion_baseline_commit_sha"):
        sha = doc_value(doc, key)
        require(re.fullmatch(r"[0-9a-f]{40}", sha) is not None, "invalid commit SHA: " + key)
        require(run_git(["cat-file", "-e", sha + "^{commit}"], check=False).returncode == 0, key + " commit is missing")
        require(run_git(["merge-base", "--is-ancestor", sha, "HEAD"], check=False).returncode == 0, key + " is not an ancestor of HEAD")
    require(doc_value(doc, "previous_evidence_document_sha256") == sha256_file(ROOT / PREVIOUS_DOC_REL), "previous evidence document hash mismatch")
    require(doc_value(doc, "inactive_0010_draft_sha256") == sha256_file(ROOT / INACTIVE_DRAFT_REL), "inactive 0010 draft hash mismatch")
    return doc


def check_previous_stage():
    previous = read(PREVIOUS_DOC_REL)
    for rel in (PREVIOUS_CHECKLIST_REL, PREVIOUS_SCHEMA_REL, PREVIOUS_SMOKE_REL, PREVIOUS_GO_NO_GO_REL, PREVIOUS_VALIDATOR_REL):
        read(rel)
    for token in (
        "stage_id=PMAI-P0-01",
        "EVIDENCE_COMPLETENESS=PARTIAL",
        "ROLLBACK_RESTORE_EVIDENCE_COMPLETE=false",
        "decision=" + ENTRY_DECISION,
        "database_revision=0009_diag_data",
        "alembic_head=0009_diag_data",
        "writes_database=false",
    ):
        require(token in previous, "previous stage marker missing: " + token)


def check_evidence(doc):
    manifest_rel = EVIDENCE_DIR_REL + "/SHA256SUMS.txt"
    manifest = {}
    for line_number, raw_line in enumerate(read(manifest_rel).splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/]+)", raw_line.strip())
        require(match is not None, "invalid manifest row %d" % line_number)
        digest, name = match.groups()
        require(name not in manifest, "duplicate manifest entry: " + name)
        manifest[name] = digest
    require(set(manifest) == set(EVIDENCE_NAMES), "manifest file set mismatch")
    for name in EVIDENCE_NAMES:
        rel = EVIDENCE_DIR_REL + "/" + name
        require(manifest[name] == sha256_file(ROOT / rel), "evidence SHA mismatch: " + name)
        text = read(rel)
        for pattern, description in FORBIDDEN_PATTERNS:
            require(pattern.search(text) is None, "%s contains %s" % (rel, description))
    require(doc_value(doc, "evidence_manifest_sha256") == sha256_file(ROOT / manifest_rel), "manifest SHA mismatch in document")
    environment = parse_kv(EVIDENCE_DIR_REL + "/01_environment_sanitized.txt")
    backup = parse_kv(EVIDENCE_DIR_REL + "/02_provider_backup_sanitized.txt")
    restore_meta = parse_kv(EVIDENCE_DIR_REL + "/03_provider_restore_sanitized.txt")
    ownership = parse_kv(EVIDENCE_DIR_REL + "/04_failure_ownership_sanitized.txt")
    baseline = parse_kv(EVIDENCE_DIR_REL + "/05_staging_baseline_preparation_sanitized.txt")
    source = parse_capture(EVIDENCE_DIR_REL + "/10_source_readonly_verification.csv")
    restored = parse_capture(EVIDENCE_DIR_REL + "/11_restore_readonly_verification.csv")
    comparison = parse_kv(EVIDENCE_DIR_REL + "/12_restore_comparison_sanitized.txt")
    require(environment.get("staging_service_label") == "pet-med-ai-db-staging-source-ohio", "staging service mismatch")
    require(environment.get("database_engine") == "PostgreSQL 18", "database engine mismatch")
    require(environment.get("isolated_from_production") == "true", "isolation proof missing")
    require(environment.get("production_backend_attached") == "false", "production backend attached")
    require(backup.get("backup_method") == "PITR", "backup method mismatch")
    require(backup.get("backup_integrity_status") == "VERIFIED", "backup integrity mismatch")
    require(backup.get("provider_operation_status") == "SUCCESS", "backup operation mismatch")
    require(restore_meta.get("restore_status") == "SUCCESS", "restore status mismatch")
    require(restore_meta.get("restore_target_is_disposable") == "true", "restore target is not disposable")
    require(restore_meta.get("restore_target_isolated_from_production") == "true", "restore target isolation missing")
    require(ownership.get("stamp_head_used") == "false", "stamp head used")
    require(ownership.get("manual_alembic_revision_edit_used") == "false", "manual revision edit used")
    require(baseline.get("database_revision") == EXPECTED_REVISION, "baseline revision mismatch")
    require(baseline.get("synthetic_fixture_only") == "true", "baseline fixture is not synthetic-only")
    require(baseline.get("case_treatment_written") == "false", "Case.treatment write detected")
    require(baseline.get("prescription_written") == "false", "prescription write detected")
    for label, capture in (("source", source), ("restore", restored)):
        require(capture.get("database_revision") == EXPECTED_REVISION, label + " revision mismatch")
        require(capture.get("schema_ok") == "true", label + " schema mismatch")
        require(capture.get("migration_errors") == "[]", label + " migration errors")
        require(capture.get("treatment_framework_signed_review_states_present") == "false", label + " 0010 table present")
        for key in capture:
            if key.startswith("orphan."):
                require(capture[key] == "0", label + " orphan mismatch: " + key)
    for key, value in source.items():
        if key not in ("schema_ok", "migration_errors"):
            require(restored.get(key) == value, "source/restore mismatch: " + key)
    require(comparison.get("comparison_status") == "PASS", "comparison status mismatch")
    require(comparison.get("row_count_parity") == "MATCH", "row count parity mismatch")
    require(comparison.get("sample_case_readback") == "MATCH", "sample readback mismatch")
    require(comparison.get("referential_integrity") == "PASS", "referential integrity mismatch")
    require(comparison.get("mismatch_count") == "0", "comparison mismatch count is nonzero")
    require(comparison.get("validation_error_count") == "0", "comparison validation errors are nonzero")
    return manifest, environment, backup, restore_meta, ownership, source, restored, comparison


def check_csvs(manifest, environment, backup, restore_meta, ownership, source, restored, comparison):
    checklist = read_csv(
        CHECKLIST_REL,
        ["item_id", "area", "requirement", "evidence_source", "evidence_status", "blocking", "notes"],
        ["RR-%03d" % value for value in range(1, 17)],
        "item_id",
    )
    require(all(row["evidence_status"] in ("VERIFIED", "PASS_STATIC", "PASS_POLICY", "PASS_RUNTIME") for row in checklist), "completion checklist contains non-passing status")
    register = read_csv(
        REGISTER_REL,
        ["evidence_id", "evidence_type", "required_field", "observed_value", "evidence_source", "evidence_sha256", "evidence_status", "blocking", "notes"],
        ["RRE-%03d" % value for value in range(1, 21)],
        "evidence_id",
    )
    for row in register:
        require(row["evidence_status"] == "VERIFIED", "register row not VERIFIED: " + row["evidence_id"])
        require(row["observed_value"] not in ("", "UNRECORDED", "PENDING"), "register observed value missing: " + row["evidence_id"])
        require((ROOT / row["evidence_source"]).is_file() or row["evidence_source"] == COMPLETION_DECISION, "register evidence source missing: " + row["evidence_id"])
        require(re.fullmatch(r"[0-9a-f]{64}", row["evidence_sha256"]) is not None, "register evidence SHA invalid: " + row["evidence_id"])
        require(row["evidence_sha256"] == sha256_file(ROOT / row["evidence_source"]), "register evidence SHA mismatch: " + row["evidence_id"])
    verification = read_csv(
        VERIFICATION_REL,
        ["check_id", "verification_area", "object_name", "baseline_value", "restored_value", "comparison_status", "evidence_source", "blocking", "notes"],
        ["VER-%03d" % value for value in range(1, 13)],
        "check_id",
    )
    require(all(row["comparison_status"] in ("MATCH", "PASS") for row in verification), "verification row failed or pending")
    for row in verification:
        require(row["restored_value"] not in ("", "UNRECORDED", "PENDING"), "verification restored value missing: " + row["check_id"])
        require((ROOT / row["evidence_source"]).is_file(), "verification evidence source missing: " + row["check_id"])
    gates = read_csv(
        GO_NO_GO_REL,
        ["gate_id", "gate", "required_state", "observed_state", "decision", "blocking", "notes"],
        ["GATE-%03d" % value for value in range(1, 13)],
        "gate_id",
    )
    require(all(not row["decision"].startswith("NO_GO") for row in gates), "Go/No-Go still contains NO_GO")
    require(gates[-1]["decision"] == COMPLETION_DECISION, "final Go/No-Go decision mismatch")


def check_secret_safety():
    evidence_paths = [DOC_REL, CHECKLIST_REL, REGISTER_REL, VERIFICATION_REL, GO_NO_GO_REL] + [EVIDENCE_DIR_REL + "/" + name for name in EVIDENCE_NAMES + ["SHA256SUMS.txt"]]
    for rel in evidence_paths:
        text = read(rel)
        for pattern, description in FORBIDDEN_PATTERNS:
            require(pattern.search(text) is None, "%s contains %s" % (rel, description))
    for rel in TARGET_PATHS:
        if rel == WORKFLOW_REL:
            continue
        text = read(rel)
        for flag in DANGEROUS_FLAGS:
            for marker in (flag + "=true", flag + ": true", '"' + flag + '": true'):
                require(marker not in text, "dangerous flag enabled in %s: %s" % (rel, marker))


def check_workflow_wiring():
    workflow = read(WORKFLOW_REL)
    match = re.search(r"(?ms)^  static-backend-gate:\n(.*?)(?=^  frontend-build-gate:|\Z)", workflow)
    require(match is not None, "static backend CI job missing")
    require("uses: actions/checkout@v4" in match.group(1), "static backend checkout missing")
    require("fetch-depth: 0" in match.group(1), "full history checkout missing")


def check_ci_wiring():
    ci = read(CI_REL)
    for token in (
        "# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1",
        "python3 -m py_compile " + VALIDATOR_REL,
        "python3 " + VALIDATOR_REL + " --require-complete",
        'for validator in "${OPTIONAL_CORE_VALIDATORS[@]:-}"; do',
        '[ -n "$validator" ] || continue',
        "full history checkout for baseline verification",
        "rollback restore evidence completion markers",
        "target-only tracked diff discipline",
        "sensitive staged path discipline",
        "PASS: ci_static_checks",
    ):
        require(token in ci, "CI missing token: " + token)
    match = re.search(r"TARGETS=\((.*?)\n\)", ci, flags=re.S)
    require(match is not None, "CI TARGETS block missing")
    paths = re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)
    require(paths == TARGET_PATHS, "CI TARGETS are not canonical for completed PMAI-P0-02")
    require("git add ." not in ci and "git add -A" not in ci, "CI contains forbidden broad git add")


def check_smoke_wiring():
    smoke = read(SMOKE_REL)
    require(smoke.count(RUNTIME_BEGIN) == 1 and smoke.count(RUNTIME_END) == 1, "current smoke runtime gate markers must occur once")
    begin = smoke.index(RUNTIME_BEGIN)
    end = smoke.index(RUNTIME_END, begin) + len(RUNTIME_END)
    final_pass = smoke.rfind("ALL PASS: smoke_petmed")
    require(0 <= begin < end < final_pass, "smoke runtime ordering is invalid")
    runtime = smoke[begin:end]
    for token in (
        "python3",
        VALIDATOR_REL,
        "--require-complete",
        STAGE_TOKEN + "=PASS",
        "stage_status=COMPLETE",
        "evidence_completeness=COMPLETE",
        "rollback_restore_evidence_complete=true",
        "staging_baseline_0001_to_0009_preparation_executed=true",
        "staging_synthetic_fixture_write_executed=true",
        "signed_review_0010_staging_migration_executed=false",
        "production_migration_executed=false",
        "current_decision=" + COMPLETION_DECISION,
    ):
        require(token in runtime, "smoke runtime gate missing token: " + token)
    summary = smoke[final_pass:]
    for token in (
        PREVIOUS_STAGE_TOKEN + "=true",
        STAGE_TOKEN + "=COMPLETE",
        "rollback_restore_evidence_complete=true",
        "previous_stage_decision=" + ENTRY_DECISION,
        "decision=" + COMPLETION_DECISION,
    ):
        require(token in summary, "final smoke summary missing token: " + token)
    require(summary.count('"previous_stage_decision=') == 1, "summary must contain one previous_stage_decision")
    require(summary.count('"decision=') == 1, "summary must contain one decision")
    require(len(smoke.splitlines()) >= 1000, "cumulative smoke line count is too small")


def check_shell_syntax(rel_path):
    result = subprocess.run(["bash", "-n", str(ROOT / rel_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    require(result.returncode == 0, rel_path + " shell syntax failed: " + result.stderr.strip())


def main():
    parser = argparse.ArgumentParser(description="Validate completed PMAI-P0-02 rollback/restore evidence")
    parser.add_argument("--require-complete", action="store_true", help="require completed external evidence")
    parser.parse_args()
    for rel in TARGET_PATHS:
        require((ROOT / rel).is_file(), "missing current-stage target: " + rel)
    check_no_active_0010()
    doc = check_document()
    check_previous_stage()
    evidence = check_evidence(doc)
    check_csvs(*evidence)
    check_secret_safety()
    check_workflow_wiring()
    check_ci_wiring()
    check_smoke_wiring()
    check_shell_syntax(CI_REL)
    check_shell_syntax(SMOKE_REL)
    print("PASS: " + STAGE_TITLE)
    print("stage_id=" + STAGE_ID)
    print("stage_status=COMPLETE")
    print("evidence_completeness=COMPLETE")
    print("rollback_restore_evidence_complete=true")
    print("staging_baseline_0001_to_0009_preparation_executed=true")
    print("staging_synthetic_fixture_write_executed=true")
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
    print("PASS: no production database, Case.treatment, or prescription write")
    print("PASS: no medication amount, route, or frequency output")
    print("validator_previous_stage_decision=" + ENTRY_DECISION)
    print("validator_decision=" + COMPLETION_DECISION)
    print("ALL PASS: " + STAGE_TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
