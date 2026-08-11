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
ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_authorization_review_v1.py'
ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_execution_evidence_v1.py'
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
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_CHECKLIST_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_GO_NO_GO_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_TEST_MATRIX_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V1.py.txt',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_authorization_review_v1.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1_CHECKLIST_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1_GO_NO_GO_V1.csv',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1_TEST_MATRIX_V1.csv',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_execution_evidence_v1.py']
HASHES = {'backend/models.py': '91d1343c1ebe3df16f00bada05b2b0053f9747e6f714f726a81cd499357b448c',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1.md': 'b1b3b87d44acc189e67d8f03cbe5d90526851f2c677eee0d6d986554d1e56a9f',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_CHECKLIST_V1.csv': 'f789c3cc21466e311889aa58bea93bf8c90ae3dc856f0883c109f8d3913cd2a0',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_GO_NO_GO_V1.csv': '02a34d195dda7cfc07f14ce45d364445c1cfa24e78a546901cab248a8ed113ef',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_TEST_MATRIX_V1.csv': '06744d00386f9a5d2ad8d986e9b07af106297dd5ad0591737100ff8f1eaff2e6',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1.md': '60b1ffcf36d1ac2bac11d38187b17ed07040a7249f8850d979db534083a5a2a9',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1_CHECKLIST_V1.csv': '470e211268055449ebc0f20a938ed44e55d6aecb0c7605136cf4cce5c847615f',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1_GO_NO_GO_V1.csv': 'fbd1db1102b1aa5d18065e76922d11ce5e9e8af8c2e94365339b5ca4462406ea',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1_TEST_MATRIX_V1.csv': '48a72492b887a4949d5edae57b32f07e102a1bc7390caf8a0efca8b65f95df25',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1.md': '0b7bed7d1142fc5f5aacdf9aebfc0613d592fb5b71ee1eaf6ebabb299eb4ab4a',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_CHECKLIST_V1.csv': '4f66489d29d70cfc7f8b5ea07b2a4e9c3e33fc394474c54c9eb13112adb58811',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_GO_NO_GO_V1.csv': '78f2c820ba94ee8994868e219050aef1c718bcb8dc22d91628c7ea447a3a3ea7',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_TEST_MATRIX_V1.csv': 'd1a7e9f77d1b4b8eef02b52db060ef602e20e080cafe666fa52d7eef773015ee',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V1.py.txt': '2b99a7446fbd5509e22c9fa5f6cb18eca920711208aa37fb4af568fd21f6faab',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md': '99bbe0447b47d1aa0c9fd87cb6f55a4554e879a9b8151377b96cec3550cab4c6',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md': '580dde32fc58381cd6f6b3e1b9d781ea1f438da22fd43c85a1519a0eaff95825',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md': '098fd0dde21b27d024f8bcea5111161808488e9d903e310317fd455a5bdce60d',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1.md': 'd2c1866922bf27c1c43a16c287d66bd69acf6e5d1fe27b1b796f9a74a7486a75',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_CHECKLIST_V1.csv': '0ed855f262f8e21493f8eaeb38118959d3172936ee4846e9a491ad66cb5b00bc',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_GO_NO_GO_V1.csv': '589467c91e9eed66658268e998effed343786663f91c0d7c6ac7c1dd12a0b2ae',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_TEST_MATRIX_V1.csv': '9ac45e15062eff74b7030b0b150e18f5dda440825d37dfca416dd99243c50d3d',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1.md': '6adef3f58d215c6ef07da0ba7589fe70f87a5aea782e9973da79f0654eac7879',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1.md': 'e9f47c38c4c9b99974a15779cdddd09a2fe12e2fa0b6cade7a940135199a2c43',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md': '0b9d94181e34df30395175ecb0784707023de9b69cd8c04eca57f8923acc7d3e',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md': '22a56c3fcc9ee1edc9ef30c2469b88e59745d43be8105b8ce64f11dc07115155',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md': '81fef32e3f029c117c0a54d345361a351e56174f00526fae074ecb8d4faafc1d',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md': '0f36f2c4bcb673666aed6728f6dff407a8d45c4bfe9ba2a1b2f1fe0e3bbdf6b9',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1.md': 'f7dbce26dc7b68d571b4553dbf06dc1f52f2bc2c6eabb5e21517950824f90e65',
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
 'scripts/ci_static_checks.sh': '80bd7f4e5186a33c3420fe4804a636c90e954d2d9349330803d0bb90bebc0870',
 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py': 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f',
 'scripts/smoke_petmed.sh': '538f774e50514e8baec49a3b8acff99650b087ceb05b25bc0ba59d0f73f87652',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_authorization_review_v1.py': '84c52f070b5d05b801e79f4a86c9d61e5fbe0e0b34147db708c10e8960290230',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_execution_evidence_v1.py': '8f12a7c7f0ac71162f87b1829e67c4f39f2ef6582b0b723d5f9a9fec6e735a18',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py': '04965fb1514f61b7f63707213809f3475d1a24d4beae5c23bb19582f9326628a',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py': 'e50beb864dbb7f6cc317ac06fe00c7af5f143de2b64239d18f0484a3756d9d8b',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py': '92f41b7e0840ff2faffa61b987aac11a99e333dc25cc90c1f6f4af54b4fc41d9',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py': '89db59ef6ab68bc2529297b23995948fa6d886d8ff0d795b34aea83f8131c278',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py': '203851d9176a6a2aa1ef1cc24ba81d1f7b04d073708a331118e18c3340327d8a',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py': '5d1fecc1c16835ae840cfc06280770ac85637d957bf15e43ce1501c970d90d18',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_execution_evidence_v1.py': '58fe30a3da3f1a4b645b5cbc2aefc315d5bc74ca5621b90057fe42ba7166122c',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py': '409a5c97cf52754bf68ccf1c4e925a5107ec4dcd011c74ac3a2a6a5806aa64c1',
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_restore_governance_decision_v1.py': '755d87c09cd036dd546bdce4309d067631f43abe3e8be6952554fc12bb29c0ef'}

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
        "python3 " + ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_VALIDATOR + " || exit 1",
        "python3 " + ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_VALIDATOR + " || exit 1",
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
