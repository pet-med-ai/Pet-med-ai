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
ABORT_RETIREMENT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py'
RETIREMENT_AUTH_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py'
RETIREMENT_EXECUTION_EVIDENCE_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_execution_evidence_v1.py'
FRESH_RESTORE_GOVERNANCE_DECISION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_restore_governance_decision_v1.py'
ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py'
CI = 'scripts/ci_static_checks.sh'
SMOKE = 'scripts/smoke_petmed.sh'
TARGETS = ['docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md',
 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py',
 'scripts/ci_static_checks.sh',
 'scripts/smoke_petmed.sh',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_CHECKLIST_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_GO_NO_GO_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_TEST_MATRIX_V1.csv',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1.md',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1.md',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_execution_evidence_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_CHECKLIST_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_GO_NO_GO_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_TEST_MATRIX_V1.csv',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_restore_governance_decision_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_CHECKLIST_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_GO_NO_GO_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_TEST_MATRIX_V1.csv',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py']
HASHES = {'backend/models.py': '91d1343c1ebe3df16f00bada05b2b0053f9747e6f714f726a81cd499357b448c',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1.md': '7b49914ffdc24fbb8580ae7814d4af27c91cbe75a131ef3a884705bfd0ae660b',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_CHECKLIST_V1.csv': '4f66489d29d70cfc7f8b5ea07b2a4e9c3e33fc394474c54c9eb13112adb58811',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_GO_NO_GO_V1.csv': '78f2c820ba94ee8994868e219050aef1c718bcb8dc22d91628c7ea447a3a3ea7',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_TEST_MATRIX_V1.csv': 'd1a7e9f77d1b4b8eef02b52db060ef602e20e080cafe666fa52d7eef773015ee',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md': '99bbe0447b47d1aa0c9fd87cb6f55a4554e879a9b8151377b96cec3550cab4c6',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md': '025b5fe663143fd8861ba2d818b88d5dfa8f35a5c6ea2cc3c96d274fbdce774e',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md': '098fd0dde21b27d024f8bcea5111161808488e9d903e310317fd455a5bdce60d',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1.md': 'd2c1866922bf27c1c43a16c287d66bd69acf6e5d1fe27b1b796f9a74a7486a75',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_CHECKLIST_V1.csv': '0ed855f262f8e21493f8eaeb38118959d3172936ee4846e9a491ad66cb5b00bc',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_GO_NO_GO_V1.csv': '589467c91e9eed66658268e998effed343786663f91c0d7c6ac7c1dd12a0b2ae',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_TEST_MATRIX_V1.csv': '9ac45e15062eff74b7030b0b150e18f5dda440825d37dfca416dd99243c50d3d',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1.md': '6adef3f58d215c6ef07da0ba7589fe70f87a5aea782e9973da79f0654eac7879',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1.md': 'e9f47c38c4c9b99974a15779cdddd09a2fe12e2fa0b6cade7a940135199a2c43',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md': '7ae339557be9f5d6e2aa882397bec6d8ef8779d4f1ca2c5f625edf421b025900',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md': '7d424f4527e103f3c977fa1f4cc1a71a0d767b66168acec73b55b8a1c8b57b2b',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md': '26e1d4a6d14bb6610acab361f595b3e2d965e1f61cae8acf32669c48668b55bf',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md': '0f36f2c4bcb673666aed6728f6dff407a8d45c4bfe9ba2a1b2f1fe0e3bbdf6b9',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1.md': 'c4121a5c0bd8a7651dabaa7136286f039a3316e15d0e6d7151cd4a0065194b81',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_CHECKLIST_V1.csv': '2e49ac6baf5e6a67340fd368f677e1c6538a9515b620bf86cf7e6d79c296c48f',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_GO_NO_GO_V1.csv': 'e0c52a042ec50b39e785f4c45b6219e5861c4d64e1b99324a4d7340e4421064d',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_TEST_MATRIX_V1.csv': '2cf0cb72a8d3452024fe5b89c9b49bb94e6e36a46548a985b3cc30010cbce568',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md': '66e8caf12033b4d6ebd43759c08ffb86799d483ec85bef53082f21090136c234',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv': '5d6bc760b5cac6836e806ac8679bb6bef2af46a454123aa331429a17fef7c6b8',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv': '9cea65a3bddfb2b99bc301dc63791197163999c03416bc0dc25fd4db1894956c',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv': '081cfccef00015a8e75fdc84970d4fb10ff170c98289d2073369a2e6da4a5cde',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv': 'bae7052422f4170d99838ac14977f23649b072764461550615126fc8ddf49cb4',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md': 'ad05323269f9384c9a6cde2bbd70d7379c65ed93b46731ca0dfe592d8708c014',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md': '9ca66949f5c515805ade771be5d224eda5bc35827e552c30b2c81656bff7a132',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt': 'bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d',
 'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md': 'a1996e0c022f7a42a83d40f5f2e9bdd8bec2e77a106aa7b8aa0a231b87d83844',
 'render.yaml': 'd3bd51ce5fa0dffa8639d0b647784e54bebb8d1040a94f5c2ecd18a789d11150',
 'scripts/ci_static_checks.sh': 'a1684935365edfbe4db7ac08aa9b08e264d9dde533ca15685cd8bbb122b5f248',
 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py': 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f',
 'scripts/smoke_petmed.sh': '538f774e50514e8baec49a3b8acff99650b087ceb05b25bc0ba59d0f73f87652',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py': '8a59984f5534090e31c3024123deb7a3d85a38d1134df0ba3eb38f405062a4f8',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py': '5999c9f660010a8fbd9e09a67562cde006124fb369ea976c60f1ef02bd2b1791',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py': '60a8a245b786c3c07fff92ceb00ec5ccaad6f395bad8bdc68583a246e5761b0b',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py': 'c754514e7913ee1497ffb1b5fdd1399efe719a98baf1fb459667f3f342d14300',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py': '4c74994b7704facb5d108c41dee905bef8b5cde59d18eb46ff7d0a5c5cdba6df',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py': '0cdc145b576ce66f559481d3577be822ee2b8a46da7d6f1aeb66fcd5be11a78d',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_execution_evidence_v1.py': '8e653ce8375993f57022b4886175c2063fe8dc646d0ccf9f7e2c3d1cdd7612ca',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py': '183a7a93ec3575f7b686d8bf06202f1fb565f22a46641fe396b6b7faa12e08fa',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_restore_governance_decision_v1.py': '20f1303345af724fa580650ce7511acc70307beebdcf0b79ef2adaa49bca37ff'}

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
        "python3 " + ABORT_RETIREMENT_VALIDATOR + " || exit 1",
        "python3 " + RETIREMENT_AUTH_REVIEW_VALIDATOR + " || exit 1",
        "python3 " + RETIREMENT_EXECUTION_EVIDENCE_VALIDATOR + " || exit 1",
        "python3 " + FRESH_RESTORE_GOVERNANCE_DECISION_VALIDATOR + " || exit 1",
        "python3 " + ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_VALIDATOR + " || exit 1",
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
