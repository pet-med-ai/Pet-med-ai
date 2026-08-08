#!/usr/bin/env python3
"""Fail-closed validator for PMAI-P0-04 disposable-restore governance."""
import argparse, ast, csv, glob, hashlib, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HOLD = 'HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_RESTORE_REHEARSAL_AND_EXTERNAL_EVIDENCE'
COMPLETENESS = 'PENDING_DISPOSABLE_TARGET_PROVISIONING_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION'
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv'
REGISTER = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv'
MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv'
GOVERNANCE = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md'
RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
AUTH_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
AUTH_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py'
PROVISIONING_EVIDENCE_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py'
RESTORE_AUTH_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py'
CI = 'scripts/ci_static_checks.sh'
SMOKE = 'scripts/smoke_petmed.sh'
TARGETS = ['docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md', 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py', 'scripts/ci_static_checks.sh', 'scripts/smoke_petmed.sh', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_CHECKLIST_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_GO_NO_GO_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_TEST_MATRIX_V1.csv', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1.md', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1.md', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py']
HASHES = {'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py': 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md': '66e8caf12033b4d6ebd43759c08ffb86799d483ec85bef53082f21090136c234', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md': '99bbe0447b47d1aa0c9fd87cb6f55a4554e879a9b8151377b96cec3550cab4c6', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md': '0f36f2c4bcb673666aed6728f6dff407a8d45c4bfe9ba2a1b2f1fe0e3bbdf6b9', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt': 'bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md': '9ca66949f5c515805ade771be5d224eda5bc35827e552c30b2c81656bff7a132', 'backend/models.py': '91d1343c1ebe3df16f00bada05b2b0053f9747e6f714f726a81cd499357b448c', 'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md': 'a1996e0c022f7a42a83d40f5f2e9bdd8bec2e77a106aa7b8aa0a231b87d83844', 'render.yaml': 'd3bd51ce5fa0dffa8639d0b647784e54bebb8d1040a94f5c2ecd18a789d11150', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md': 'ad05323269f9384c9a6cde2bbd70d7379c65ed93b46731ca0dfe592d8708c014', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv': '5d6bc760b5cac6836e806ac8679bb6bef2af46a454123aa331429a17fef7c6b8', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv': '9cea65a3bddfb2b99bc301dc63791197163999c03416bc0dc25fd4db1894956c', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv': 'bae7052422f4170d99838ac14977f23649b072764461550615126fc8ddf49cb4', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv': '081cfccef00015a8e75fdc84970d4fb10ff170c98289d2073369a2e6da4a5cde', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md': '098fd0dde21b27d024f8bcea5111161808488e9d903e310317fd455a5bdce60d', 'scripts/ci_static_checks.sh': 'b795f8865470f4bfd19b20959a8abc0c4b616892ffd42d8983c77cbd0b194025', 'scripts/smoke_petmed.sh': '538f774e50514e8baec49a3b8acff99650b087ceb05b25bc0ba59d0f73f87652', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1.md': 'd2c1866922bf27c1c43a16c287d66bd69acf6e5d1fe27b1b796f9a74a7486a75', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_CHECKLIST_V1.csv': '0ed855f262f8e21493f8eaeb38118959d3172936ee4846e9a491ad66cb5b00bc', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_GO_NO_GO_V1.csv': '589467c91e9eed66658268e998effed343786663f91c0d7c6ac7c1dd12a0b2ae', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_TEST_MATRIX_V1.csv': '9ac45e15062eff74b7030b0b150e18f5dda440825d37dfca416dd99243c50d3d', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py': '5659f18d0ed37f55f2cbc460e3c2f9f509e796758d754c765b82dcf6e82e3c9d', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1.md': '6adef3f58d215c6ef07da0ba7589fe70f87a5aea782e9973da79f0654eac7879', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py': 'eaa00c6af0ffa00955de8df6c7719c2c7567851ceacc20c675175e664eb88ffb', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1.md': 'e9f47c38c4c9b99974a15779cdddd09a2fe12e2fa0b6cade7a940135199a2c43', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py': 'ba958d83af34f851163213f90a8231fec6b27f0d80a6cc1639b48987b4033a05', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md': 'b864d5d9e827d9cf431498b39ff4d1c1549a0c4a5e14940c5f9829330b78150e', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py': '8e0a04f4ef24d74bf6a345940944e0070d9fbd9e8fef6804e889044ae11f0c2f'}

def need(ok, message):
    if not ok:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)

def text(rel):
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + rel)
    return path.read_text(encoding="utf-8")

def marker(value, key):
    found = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", value)
    need(len(found) == 1, "marker count " + key)
    return found[0]

def csv_map(rel, id_name):
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle); rows = list(reader)
    need(reader.fieldnames and reader.fieldnames[0] == id_name, "CSV header " + rel)
    ids = [row[id_name] for row in rows]
    need(len(ids) == len(set(ids)), "duplicate CSV id " + rel)
    return {row[id_name]: row for row in rows}

def py_lines(value):
    return [line.strip() for line in value.splitlines() if line.strip().startswith("python3 ") and not line.strip().startswith("python3 -m py_compile ")]

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--require-complete", action="store_true"); args = parser.parse_args()
    for rel, expected in HASHES.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), "missing protected file " + rel)
        need(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "protected hash " + rel)
    need(set(HASHES) == (set(TARGETS) - {VALIDATOR}) | {
        'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md', 'backend/models.py', 'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md', 'render.yaml'
    }, "protected hash scope")
    need(not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")), "active 0010 migration exists")
    doc = text(DOC); gov = text(GOVERNANCE)
    for key, expected in {
        "stage_id": "PMAI-P0-04", "STAGE_STATUS": "IN_PROGRESS",
        "EVIDENCE_COMPLETENESS": COMPLETENESS,
        "DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_PREPARATION_COMPLETE": "true",
        "disposable_target_provisioning_governance_ready": "true",
        "third_manual_deploy_observation_status": "OPERATOR_OBSERVATION_UNPROMOTED",
        "new_manual_deploy_deviation_observed": "true",
        "cumulative_observed_manual_deploy_count": "3",
        "production_auto_deploy_verified": "false",
        "P0_04_EXECUTION_AUTHORIZED": "false", "STAGING_0010_APPLY_AUTHORIZED": "false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED": "false", "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false", "decision": HOLD,
        "next_step": "RUN_LOCAL_VALIDATOR_AND_CI_STATIC_GUARDS_THEN_COMMIT_GOVERNANCE_PREPARATION",
    }.items(): need(marker(doc, key) == expected, "document marker " + key)
    for key, expected in {
        "governance_scope": "REPOSITORY_ONLY_NO_EXTERNAL_EXECUTION",
        "disposable_restore_governance_preparation_complete": "true",
        "disposable_target_provisioning_governance_ready": "true",
        "disposable_restore_target_provisioning_authorized": "false",
        "disposable_restore_execution_authorized": "false",
        "disposable_restore_database_created": "false",
        "disposable_restore_database_write_authorized": "false",
        "restore_runner_created": "false", "restore_runner_execution_enabled": "false",
        "restore_runner_executed_by_ci": "false", "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "corrected_migration_implementation_authorized": "false",
        "active_0010_migration_file_created": "false", "p0_04_execution_authorized": "false",
        "staging_0010_apply_authorized": "false", "production_auto_deploy_verified": "false",
        "observation_status": "OPERATOR_OBSERVATION_UNPROMOTED",
        "new_manual_deploy_deviation_observed": "true",
        "cumulative_observed_manual_deploy_count": "3",
        "manual_deploy_deviation_service": "production",
        "manual_deploy_deviation_postdeploy_readonly_verified": "true",
        "production_database_revision": "0009_diag_data", "staging_database_revision": "0009_diag_data",
        "candidate_migration_deployed": "false", "database_write": "false",
        "migration_created": "false", "migration_executed": "false",
        "production_database_write": "false", "decision": HOLD,
        "next_step": "RUN_LOCAL_VALIDATOR_AND_CI_STATIC_GUARDS_THEN_COMMIT_GOVERNANCE_PREPARATION",
    }.items(): need(marker(gov, key) == expected, "governance marker " + key)
    checklist = csv_map(CHECKLIST, "item_id"); register = csv_map(REGISTER, "evidence_id")
    matrix = csv_map(MATRIX, "test_id"); gates = csv_map(GO_NO_GO, "gate_id")
    need(checklist["P04-C027"]["status"] == "GOVERNANCE_PREPARED", "checklist governance")
    need(checklist["P04-C028"]["status"] == "OPERATOR_OBSERVATION_UNPROMOTED", "checklist observation")
    need(register["P04-E023"]["status"] == "GOVERNANCE_PREPARED", "register governance")
    need(register["P04-E024"]["status"] == "OPERATOR_OBSERVATION_UNPROMOTED", "register observation")
    need(matrix["P04-T023"]["status"] == "PASS_GOVERNANCE_ONLY", "matrix governance")
    need(matrix["P04-T024"]["status"] == "OPERATOR_OBSERVATION_UNPROMOTED", "matrix observation")
    need(gates["P04-G013"]["current_state"] == "PASS_GOVERNANCE_ONLY", "gate governance")
    need(gates["P04-G014"]["current_state"] == "OPERATOR_OBSERVATION_UNPROMOTED", "gate observation")
    need(gates["P04-G006"]["current_state"] == "BLOCKED", "restore remains blocked")
    need(gates["P04-G010"]["decision"] == HOLD, "final hold")
    runner = text(RUNNER); tree = ast.parse(runner); imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.add((node.module or "").split(".")[0])
    need(imports == {"__future__", "argparse", "sys"}, "locked runner imports")
    need("EXECUTION_ENABLED = False" in runner and "DATABASE_URL" not in runner, "locked runner source")
    ci = text(CI); block = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)", ci)
    need(block is not None, "CI target block")
    need(re.findall(r'^\s*"([^"]+)"\s*$', block.group(1), flags=re.M) == TARGETS,
         "CI canonical target scope")
    need(py_lines(ci) == [
        "python3 " + VALIDATOR,
        "python3 " + AUTH_PREP_VALIDATOR + " || exit 1",
        "python3 " + AUTH_REVIEW_VALIDATOR + " || exit 1",
        "python3 " + PROVISIONING_EVIDENCE_VALIDATOR + " || exit 1",
        "python3 " + RESTORE_AUTH_REVIEW_VALIDATOR + " || exit 1",
    ], "CI executes only approved validators")
    smoke = text(SMOKE)
    gate = re.search(r"(?ms)^# >>> treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate$.*?^# <<< treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate$", smoke)
    need(gate is not None, "P0-04 smoke gate")
    need(py_lines(gate.group(0)) == ['python3 "${PETMED_P0_04_ROOT}/' + VALIDATOR + '"'], "smoke executes only validator")
    need(RUNNER not in "\n".join(py_lines(smoke)), "smoke executes runner")
    need("disposable_restore_governance_preparation_complete=true" in gate.group(0), "smoke governance marker")
    for rel in (CI, SMOKE):
        result = subprocess.run(
            ["/bin/bash", "-n", str(ROOT / rel)], input=b"",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
        )
        need(result.returncode == 0, "shell syntax " + rel)
    if args.require_complete:
        print("NO-GO: PMAI-P0-04 remains IN_PROGRESS; disposable target provisioning and restore rehearsal are incomplete", file=sys.stderr)
        return 1
    for line in (
        "stage_id=PMAI-P0-04", "stage_status=IN_PROGRESS", "evidence_completeness=" + COMPLETENESS,
        "disposable_restore_governance_preparation_complete=true",
        "disposable_target_provisioning_governance_ready=true",
        "disposable_restore_target_provisioning_authorized=false",
        "disposable_restore_execution_authorized=false", "restore_runner_created=false",
        "backup_restoreability_verified=false", "disposable_restore_rehearsal_complete=false",
        "corrected_migration_implementation_authorized=false", "p0_04_execution_authorized=false",
        "staging_0010_apply_authorized=false", "active_0010_migration_file_created=false",
        "database_write=false", "migration_executed=false", "production_database_write=false",
        "decision=" + HOLD,
        "next_step=RUN_LOCAL_VALIDATOR_AND_CI_STATIC_GUARDS_THEN_COMMIT_GOVERNANCE_PREPARATION",
        "ALL PASS: PMAI-P0-04 disposable restore rehearsal governance preparation",
    ): print(line)
    return 0
if __name__ == "__main__": raise SystemExit(main())
