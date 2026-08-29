#!/usr/bin/env python3
"""Validate the PMAI-P0-04 V4 SRBE execution-authorization package."""

from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "PMAI-P0-04"
SUBSTAGE = (
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_"
    "AND_REVIEW_V4_EXECUTION_AUTHORIZATION_V1"
)
WORK_BUNDLE = "PMAI-P0-04-ARR-V3-SRBE-COLLECT-REVIEW-V4-EXEC-AUTH"
AUTHORIZATION_ID = (
    "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_"
    "COLLECTION_AND_REVIEW_V4_EXECUTION_AUTHORIZATION_REPOSITORY_PATCH_"
    "CONTROLLED_EXECUTION_V1"
)
AUTHORIZATION_RECORD = (
    "PMAI-P0-04-ARR-V3-SRBE-COLLECT-REVIEW-V4-EXEC-AUTH-V1-20260827"
)
AUTHORIZATION_RECORD_SHA256 = (
    "4ccd131dd2da45fbe3016f3a9a5d0ea253cbf821c95cd7e80e5a46438459a2dc"
)
BASE_COMMIT = "11d5253d7a592c13f5a262f6ceef08046fb73866"
BASE_TREE = "c3600d0913950460dfa1e044fe1759972390d012"
INTRODUCTION_COMMIT = "c248d6b89c5dd868dc836b9f562bf15ca27285d9"
INTRODUCTION_TREE = "fced41e8ee5960e6860c38896e8888424fc211b9"
INTRODUCTION_SUBJECT = (
    "PMAI-P0-04: Record V4 sanitized runtime binding evidence collection "
    "and review execution authorization"
)
HISTORICAL_REPAIR_COMMIT = "e410804fd21aa0c7bf57040b088543190d442fc9"
HISTORICAL_REPAIR_TREE = "52a7aac761477cdd4ef3c16b7e853b70fb6856d6"
HISTORICAL_REPAIR_SUBJECT = (
    "PMAI-P0-04: Harden V4 SRBE execution authorization validator"
)
PUBLISHED_MERGE_COMMIT = "de93b4623e812a911445a4370dea40ec56b2098f"
PUBLISHED_MERGE_TREE = "52a7aac761477cdd4ef3c16b7e853b70fb6856d6"
PUBLISHED_MERGE_PARENTS = (BASE_COMMIT, HISTORICAL_REPAIR_COMMIT)
COMPATIBILITY_CORRECTION_BRANCH = (
    "pmai-p0-04-v4-exec-auth-successor-compat-correction-v2"
)
COMPATIBILITY_CORRECTION_SUBJECT = (
    "PMAI-P0-04: Correct V4 commit-message compatibility"
)
COMPATIBILITY_CORRECTION_PATH_SEQUENCE_SHA256 = (
    "0d5fa47fb9b7234822919e40ad79bb5326731f22d886006da22676b9fcd06ba3"
)
HEAD_BRANCH = "pmai-p0-04-arr-v3-srbe-v4-exec-auth"
SOURCE_HEAD = "56d31819bff4b271e9d265b032156741e8a20beb"
SOURCE_MERGE = BASE_COMMIT
SOURCE_TREE = BASE_TREE
SOURCE_CI_RUN_ID = 33077607028
SOURCE_CI_RUN_NUMBER = 226
SOURCE_REVIEW_RECORD = "PMAI-P0-04-ARR-V3-ACT-SRBE-REBIND-V4-AUTH-REV-20260827"
EXPECTED_PATH_SEQUENCE_SHA256 = (
    "414cd0d429832d7d349dd32a0d458353339b58cb0ba88a89a297a3add96450ff"
)
TARGET_LOGICAL_NAME = "pet-med-ai-db-p0-04-fresh-disposable-restore-v4-ohio"
TARGET_CONTRACT_SHA256 = (
    "e1cba6bc207fa4654d3155ef4abd8d818d8fd4323ce990446bc680fd15522529"
)
TARGET_SERVICE_SHA256 = (
    "3f0ed4e1cb1bbef10babb4d3ba7fa9ec03e048d7d30595389f30d0871bcdb4fe"
)
CANDIDATE_SHA256 = (
    "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
)
COLLECTOR_CONTRACT_SHA256 = (
    "1d4ce179cbd4ead48b6af7e3165bf7dd4e94eeef306c64cdcd40fa7788150a54"
)
OUTPUT_SCHEMA_ID = "PMAI_P0_04_ARR_V3_SRBE_COLLECTION_PHASE_OUTPUT_V4_V1"
OUTPUT_SCHEMA_SHA256 = (
    "5653dd33e114a6280c2f99d6fe3dbccb41f50b7cc483cf007575e51f9dd44683"
)
PROCEDURE_ID = "PMAI_P0_04_ARR_V3_SRBE_OPERATIONAL_COLLECTION_PROCEDURE_V4_V1"
PROCEDURE_SHA256 = (
    "760275782eec85de09ae5dd0ac6955bec6b215886b6afc5a05fd1888bc45e1a5"
)
HASH_NORMALIZATION = "SHA256_UTF8_EXACT_ORDERED_LINES_WITH_TRAILING_LF"
DECISION = (
    "GO_TO_SEPARATE_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_V4_CONTROLLED_EXECUTION_CONFIRMATION_V1"
)
NEXT_SUBJECT = (
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_"
    "AND_REVIEW_V4_CONTROLLED_EXECUTION_CONFIRMATION_V1"
)
PASS_MARKER = (
    "active_restore_runner_v3_sanitized_runtime_binding_evidence_collection_"
    "and_review_v4_execution_authorization=PASS"
)
FINAL_PASS = (
    "ALL PASS: PMAI-P0-04 V4 sanitized runtime binding evidence collection "
    "and review execution authorization"
)

PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
    "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_"
    "BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V4_EXECUTION_AUTHORIZATION_V1"
)
DOC = PREFIX + ".md"
POINTER = PREFIX + "_ACTIVE_POINTER_V1.json"
CHECKLIST = PREFIX + "_CHECKLIST_V1.csv"
GO_NO_GO = PREFIX + "_GO_NO_GO_V1.csv"
BASELINE = PREFIX + "_LOCKED_BASELINE_V1.json"
MANIFEST = PREFIX + "_PACKAGE_MANIFEST_V1.json"
TEST_MATRIX = PREFIX + "_TEST_MATRIX_V1.csv"
VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_collection_and_review_v4_execution_authorization_v1.py"
)
CENTRAL = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_staging_migration_apply.py"
)
PACKAGE_PATHS = (
    DOC,
    POINTER,
    CHECKLIST,
    GO_NO_GO,
    BASELINE,
    MANIFEST,
    TEST_MATRIX,
    VALIDATOR,
)
MANIFEST_MEMBERS = (
    DOC,
    POINTER,
    CHECKLIST,
    GO_NO_GO,
    BASELINE,
    TEST_MATRIX,
    VALIDATOR,
)
IMMUTABLE_PACKAGE_PATHS = (
    DOC,
    POINTER,
    CHECKLIST,
    GO_NO_GO,
    BASELINE,
    TEST_MATRIX,
)
PACKAGE_CLOSURE_PATHS = (MANIFEST, VALIDATOR)
EXPECTED_CHANGED_PATHS = (*PACKAGE_PATHS, CENTRAL)
HISTORICAL_REPAIR_PATHS = (MANIFEST, VALIDATOR, CENTRAL)
AUTHORIZED_CORRECTION_PATHS = (VALIDATOR, MANIFEST, CENTRAL)
CORRECTION_PATHS = tuple(
    sorted(AUTHORIZED_CORRECTION_PATHS, key=lambda value: value.encode("utf-8"))
)

SANITIZED_VALIDATOR_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
}

SOURCE_PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
    "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_"
    "SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_V1"
)
SOURCE_VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_activation_and_srbe_contract_"
    "rebind_v4_authorization_review_v1.py"
)
SOURCE_REVIEW_HASHES = {
    SOURCE_PREFIX + ".md": "0070eba77fceee826d78151d68f2d9a1cdd16cb8a027b1e2155c7cdb6cf224d8",
    SOURCE_PREFIX + "_ACTIVE_POINTER_V1.json": "da27b4576bb316e83d2d5e6e266661bb01c7bf4bcb28c82c2cd6e815c1b12121",
    SOURCE_PREFIX + "_CHECKLIST_V1.csv": "618cdf514fc6873b104e9ff74d0fd51b349063c3e8ce59e6e97e30dfc1a5a064",
    SOURCE_PREFIX + "_GO_NO_GO_V1.csv": "212e408dfbd4a25e64f69e0901cd5d5e6525f97ad467561508a7fc06755eda51",
    SOURCE_PREFIX + "_LOCKED_BASELINE_V1.json": "72920802e1de0c43a09a72d998c09fc7a9a8818cc9486fcca3b9757587862819",
    SOURCE_PREFIX + "_PACKAGE_MANIFEST_V1.json": "9731c13d92de806bd26992f8cab24e8101cc89d0aaaa2fd9520eb904133405d7",
    SOURCE_PREFIX + "_TEST_MATRIX_V1.csv": "a21e810f754755b243e5fb238dd3652642ee0a3af6bbb10e2bd354d8b0b627c4",
    SOURCE_VALIDATOR: "aab8a648154e23dc4dd9b73b3f8a9ad0c6788ecb74b7000a888d9a05df360d8b",
}
SOURCE_PASS_MARKER = (
    "active_restore_runner_v3_activation_and_srbe_contract_rebind_"
    "v4_authorization_review=PASS"
)

PREP_PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
    "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_"
    "SRBE_CONTRACT_REBIND_V4_PREPARATION_V1"
)
PREP_VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_activation_and_srbe_contract_"
    "rebind_v4_preparation_v1.py"
)
PREP_REVIEWER = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_activation_and_srbe_contract_"
    "rebind_v4_evidence_review_v1.py"
)
PREP_HASHES = {
    PREP_PREFIX + ".md": "f9268fe11137461576297db741239f77d617c6866a4359f2482eaa20aefc89ed",
    PREP_PREFIX + "_ACTIVE_POINTER_V1.json": "5fb6082e7f9a3a0d0e33eef37b4e136a42c7b8b57ee1c5a4bc7bd44a67171ece",
    PREP_PREFIX + "_CHECKLIST_V1.csv": "6e140261a6d52ab2c7345659be7e4ef0507b5850792b25951ee738b7b9f96f46",
    PREP_PREFIX + "_COLLECTOR_CANDIDATE_V1.py.txt": "753f4eb9f1cef9c98b4fca934bbbc430b77aab028fd71f77d345f695ed383fb6",
    PREP_PREFIX + "_GO_NO_GO_V1.csv": "5a8682c3547d0d63c09c02826108c1d2a2bc081bf2a339451cd6db8518317e1c",
    PREP_PREFIX + "_LOCKED_BASELINE_V1.json": "dff8cb0d90dfb7c68be8afb7a21c62ac4d6dea14cd600b89409e0a5e93586f6c",
    PREP_PREFIX + "_PACKAGE_MANIFEST_V1.json": "4e1e3b895f522e58917052d8af3e8bcdd6127ef9db2b4fc0cccff95124e2641c",
    PREP_PREFIX + "_RUNTIME_OBSERVATION_TEMPLATE_V1.json": "580a485ae62221ef4d2e3e598321bb9197e5083d0cb0926fdc85a1766544f1b2",
    PREP_PREFIX + "_SANITIZED_COLLECTOR_OUTPUT_TEMPLATE_V1.json": "f65411c98bebc8f7773724d0ee9088faeac6f3b620c853079233c360921ceee8",
    PREP_PREFIX + "_TEST_MATRIX_V1.csv": "e0a61f02d548c1583a888ee3db165aba33436da1e27c6df0682d8dc4bc2cd131",
    PREP_VALIDATOR: "7178853124e403080cdcc0c3bed63ec31c9acf5f791f5352fdd62373acdc770d",
    PREP_REVIEWER: "c655571668758332f6501cb44b3d074600a405be7984c6110d4db30190f4ef87",
}
PREP_PASS_MARKER = (
    "active_restore_runner_v3_activation_and_srbe_contract_rebind_"
    "v4_preparation=PASS"
)
IMPLEMENTATION_CANDIDATE = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
    "PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3_"
    "IMPLEMENTATION_CANDIDATE_V1.py.txt"
)
PLANNED_ACTIVE_RUNNER = (
    "scripts/run_treatment_framework_signed_review_state_persistence_"
    "migration_0010_disposable_restore_v3.py"
)
MIGRATIONS = "backend/migrations/versions"

LEGACY_CURRENT_HOLD = (
    "HOLD_PMAI_P0_04_V4_TARGET_AVAILABLE_AND_NETWORK_LOCKED_PENDING_"
    "ACTIVE_RUNNER_AND_SRBE_CONTRACT_REBIND_V4"
)
LEGACY_CURRENT_COMPLETENESS = (
    "V4_TARGET_PROVISIONING_AND_NETWORK_LOCKDOWN_EVIDENCE_COMPLETE_PENDING_"
    "ACTIVE_RUNNER_SRBE_V4_REBIND_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION"
)
LEGACY_CURRENT_NEXT = (
    "PREPARE_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4"
)
PREP_EFFECTIVE_HOLD = (
    "HOLD_PMAI_P0_04_PENDING_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_"
    "CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW"
)
PREP_EFFECTIVE_COMPLETENESS = (
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_"
    "PREPARATION_COMPLETE_PENDING_AUTHORIZATION_REVIEW_RESTORE_REHEARSAL_"
    "AND_EXTERNAL_EXECUTION"
)
PREP_EFFECTIVE_NEXT = (
    "PREPARE_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_"
    "V4_AUTHORIZATION_REVIEW"
)
REVIEW_EFFECTIVE_HOLD = (
    "HOLD_PMAI_P0_04_PENDING_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_"
    "BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V4_EXECUTION_AUTHORIZATION"
)
REVIEW_EFFECTIVE_COMPLETENESS = (
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_"
    "AUTHORIZATION_REVIEW_COMPLETE_PENDING_SRBE_COLLECTION_REVIEW_RUNTIME_"
    "BINDINGS_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION"
)
REVIEW_EFFECTIVE_NEXT = "PREPARE_" + SUBSTAGE
EXEC_EFFECTIVE_HOLD = (
    "HOLD_PMAI_P0_04_PENDING_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_"
    "BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V4_CONTROLLED_EXECUTION_"
    "CONFIRMATION"
)
EXEC_EFFECTIVE_COMPLETENESS = (
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_"
    "AND_REVIEW_V4_EXECUTION_AUTHORIZATION_COMPLETE_PENDING_ACTION_TIME_"
    "CONFIRMATION_RUNTIME_BINDINGS_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION"
)
EXEC_EFFECTIVE_NEXT = (
    "CONFIRM_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_"
    "COLLECTION_AND_REVIEW_V4_CONTROLLED_EXECUTION_V1"
)
HISTORICAL_REPAIR_CENTRAL_NORMALIZED_SHA256 = (
    "0902f01ee07cbf1e7923f76aa3585204c863e5473396e1717de0b38baa4ae65c"
)
CENTRAL_V4_OWNED_PROJECTION_SHA256 = (
    "be245ca676bc7b57aac2db164ac49bf2e7593834c7cdd63f4fe33faaf0c0fd21"
)
CENTRAL_V4_STEM = (
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_"
    "AND_REVIEW_V4_EXECUTION_AUTHORIZATION"
)
CENTRAL_V4_OWNED_ASSIGNMENTS = (
    "CURRENT_HOLD",
    "CURRENT_COMPLETENESS",
    "CURRENT_NEXT_STEP",
    "EFFECTIVE_CURRENT_HOLD",
    "EFFECTIVE_CURRENT_COMPLETENESS",
    "EFFECTIVE_CURRENT_NEXT_STEP",
    "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_HOLD",
    "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_COMPLETENESS",
    "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_NEXT_STEP",
    "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_HOLD",
    "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_COMPLETENESS",
    "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_NEXT_STEP",
    CENTRAL_V4_STEM + "_VALIDATOR",
    CENTRAL_V4_STEM + "_VALIDATOR_SHA256",
    CENTRAL_V4_STEM + "_MANIFEST",
    CENTRAL_V4_STEM + "_MANIFEST_SHA256",
    CENTRAL_V4_STEM + "_PASS_MARKER",
    "SRBE_V4_SANITIZED_CHILD_ENV_ITEMS",
)
CENTRAL_V4_BASELINE_ASSIGNMENTS = (
    "HOLD",
    "COMPLETENESS",
    "CURRENT_HOLD",
    "CURRENT_COMPLETENESS",
    "CURRENT_NEXT_STEP",
    "EFFECTIVE_CURRENT_HOLD",
    "EFFECTIVE_CURRENT_COMPLETENESS",
    "EFFECTIVE_CURRENT_NEXT_STEP",
    "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_HOLD",
    "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_COMPLETENESS",
    "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_NEXT_STEP",
    "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_HOLD",
    "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_COMPLETENESS",
    "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_NEXT_STEP",
    "DOC",
    "CHECKLIST",
    "REGISTER",
    "MATRIX",
    "GO_NO_GO",
    "GOVERNANCE",
    "RUNNER",
    "VALIDATOR",
    "AUTH_PREP_VALIDATOR",
    "AUTH_REVIEW_VALIDATOR",
    "PROVISIONING_EVIDENCE_VALIDATOR",
    "RESTORE_AUTH_REVIEW_VALIDATOR",
    "ABORT_RETIREMENT_VALIDATOR",
    "RETIREMENT_AUTH_REVIEW_VALIDATOR",
    "RETIREMENT_EXECUTION_EVIDENCE_VALIDATOR",
    "FRESH_RESTORE_GOVERNANCE_DECISION_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_VALIDATOR",
    "STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_VALIDATOR",
    "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_VALIDATOR",
    "RESTORE_RUNNER_DESIGN_PREPARATION_V3_VALIDATOR",
    "RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_VALIDATOR",
    "RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_VALIDATOR",
    "RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_VALIDATOR",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3_VALIDATOR",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3_VALIDATOR",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXTERNAL_EXECUTION_AUTHORIZATION_V3_VALIDATOR",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3_VALIDATOR",
    "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION_V1_VALIDATOR",
    "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_AUTHORIZATION_REVIEW_V1_VALIDATOR",
    "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1_VALIDATOR",
    "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_VALIDATOR",
    "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_VALIDATOR_SHA256",
    "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_MANIFEST",
    "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_MANIFEST_SHA256",
    "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_PASS_MARKER",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_VALIDATOR",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_VALIDATOR_SHA256",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_MANIFEST",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_MANIFEST_SHA256",
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_PASS_MARKER",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_VALIDATOR",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_VALIDATOR_SHA256",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_MANIFEST",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_MANIFEST_SHA256",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_PASS_MARKER",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_VALIDATOR",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_VALIDATOR_SHA256",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_MANIFEST",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_MANIFEST_SHA256",
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_PASS_MARKER",
    CENTRAL_V4_STEM + "_VALIDATOR",
    CENTRAL_V4_STEM + "_VALIDATOR_SHA256",
    CENTRAL_V4_STEM + "_MANIFEST",
    CENTRAL_V4_STEM + "_MANIFEST_SHA256",
    CENTRAL_V4_STEM + "_PASS_MARKER",
    "CI",
    "SMOKE",
    "TARGETS",
    "HASHES",
)
CENTRAL_V4_NORMALIZED_ASSIGNMENTS = (
    CENTRAL_V4_STEM + "_VALIDATOR_SHA256",
    CENTRAL_V4_STEM + "_MANIFEST_SHA256",
)
CENTRAL_V4_INTEGRATION_BEGIN = (
    "# >>> pmai_p0_04_v4_execution_authorization_integration_owned_v1"
)
CENTRAL_V4_INTEGRATION_END = (
    "# <<< pmai_p0_04_v4_execution_authorization_integration_owned_v1"
)
CENTRAL_V4_HOOKS = (
    ("preparation", "v4_rebind_preparation_result = subprocess.run("),
    ("authorization_review", "v4_rebind_authorization_review_result = subprocess.run("),
    ("execution_authorization", "srbe_v4_execution_authorization_result = subprocess.run("),
)
CENTRAL_V4_BASELINE_OUTPUT_EXPRESSIONS = (
    "'stage_id=PMAI-P0-04'",
    "'stage_status=IN_PROGRESS'",
    "'evidence_completeness=' + CURRENT_COMPLETENESS",
    "'disposable_restore_governance_preparation_complete=true'",
    "'disposable_target_provisioning_governance_ready=true'",
    "'v4_disposable_target_provisioned=true'",
    "'v4_public_external_access_blocked=true'",
    "'v4_external_resource_binding_state=BOUND_SANITIZED_HASH_ONLY'",
    "'disposable_restore_target_provisioning_authorized=false'",
    "'disposable_restore_execution_authorized=false'",
    "'restore_runner_created=false'",
    "'backup_restoreability_verified=false'",
    "'disposable_restore_rehearsal_complete=false'",
    "'corrected_migration_implementation_authorized=false'",
    "'p0_04_execution_authorized=false'",
    "'staging_0010_apply_authorized=false'",
    "'active_0010_migration_file_created=false'",
    "'database_write=false'",
    "'migration_executed=false'",
    "'production_database_write=false'",
    "'decision=' + CURRENT_HOLD",
    "'next_step=' + CURRENT_NEXT_STEP",
    "'v4_runner_srbe_rebind_preparation_complete=true'",
    "'v4_runner_srbe_rebind_authorization_review_complete=true'",
    "'v4_runner_srbe_collection_review_execution_authorization_complete=true'",
    "'runtime_binding_contract_complete=false'",
    "'srbe_collection_evidence_complete=false'",
    "'current_collection_execution_authorized=false'",
    "'current_external_execution_authorized=false'",
    "'post_effective_gate_srbe_collection_and_review_execution_authorization_eligible=true'",
    "'post_effective_gate_srbe_collection_and_review_execution_authorized=false'",
    "'post_effective_gate_runner_creation_or_activation_authorization_eligible=false'",
    "'effective_evidence_completeness=' + EFFECTIVE_CURRENT_COMPLETENESS",
    "'effective_decision=' + EFFECTIVE_CURRENT_HOLD",
    "'effective_next_step=' + EFFECTIVE_CURRENT_NEXT_STEP",
    "'authorization_review_effective_evidence_completeness=' + AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_COMPLETENESS",
    "'authorization_review_effective_decision=' + AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_HOLD",
    "'authorization_review_effective_next_step=' + AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_NEXT_STEP",
    "'srbe_execution_authorization_effective_evidence_completeness=' + SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_COMPLETENESS",
    "'srbe_execution_authorization_effective_decision=' + SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_HOLD",
    "'srbe_execution_authorization_effective_next_step=' + SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_NEXT_STEP",
    "'ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance'",
)
CENTRAL_V4_SUPPORT_FUNCTIONS = ("need", "text", "marker", "csv_map", "py_lines")
CENTRAL_V4_ROOT_ASSIGNMENT = "ROOT = Path(__file__).resolve().parents[1]"
CENTRAL_V4_ENTRYPOINT = 'if __name__ == "__main__": raise SystemExit(main())'
CENTRAL_V4_REQUIRE_COMPLETE_GUARD = (
    "if args.require_complete:\n"
    '    print("NO-GO: PMAI-P0-04 remains IN_PROGRESS; SRBE collection/review '
    'runtime bindings and restore rehearsal are incomplete", file=sys.stderr)\n'
    "    return 1\n"
)
CENTRAL_V4_SUCCESSOR_PROTECTED_LOCAL_NAMES = {
    *CENTRAL_V4_OWNED_ASSIGNMENTS,
    *CENTRAL_V4_SUPPORT_FUNCTIONS,
    "ROOT",
    "args",
    "hashlib",
    "line",
    "main",
    "print",
    "srbe_v4_execution_authorization_manifest_path",
    "srbe_v4_execution_authorization_result",
    "srbe_v4_execution_authorization_validator_path",
    "subprocess",
    "sys",
}

UNBOUND_FIELDS = (
    "successor_activation_authorization_record_id",
    "successor_activation_authorization_record_sha256",
    "expected_active_source_sha256",
    "expected_target_identity_sha256",
    "forbidden_production_identity_sha256",
    "forbidden_staging_identity_sha256",
    "expected_schema_manifest_sha256",
    "source_observation_bundle_sha256",
    "target_available_recheck_evidence_sha256",
    "target_lifecycle_evidence_sha256",
    "target_application_attachment_recheck_evidence_sha256",
    "target_open_connection_recheck_evidence_sha256",
    "target_network_lockdown_recheck_evidence_sha256",
)
EXECUTION_FALSE_FIELDS = (
    "render_readonly_access",
    "render_control_plane_write",
    "render_settings_change",
    "temporary_inbound_allowlist_change",
    "credential_or_connection_value_access",
    "database_connection",
    "database_read_write_export",
    "runtime_evidence_collection",
    "runner_creation",
    "runner_activation",
    "runner_import",
    "runner_execution",
    "backup_or_archive_access",
    "restore_execution",
    "pg_restore_or_psql_execution",
    "migration_creation_or_execution",
    "deployment",
    "target_deletion",
    "production_staging_v3_v4_resource_operations",
    "library_master_directory_update",
    "operational_collection_adapter_creation",
    "operational_collection_adapter_present",
    "raw_identifier_url_connection_or_credential_capture",
    "manual_retry",
    "automatic_retry",
)

OUTPUT_SCHEMA_LINES = (
    "schema=fixed:PMAI_P0_04_ARR_V3_SRBE_COLLECTION_PHASE_OUTPUT_V4_V1",
    "collection_execution_authorization_record_sha256=lowercase_sha256",
    "collection_execution_authorized=boolean",
    "collector_contract_sha256=lowercase_sha256",
    "evidence_complete=boolean",
    "expected_active_source_sha256=lowercase_sha256_or_UNBOUND",
    "expected_schema_manifest_sha256=lowercase_sha256",
    "expected_target_identity_sha256=lowercase_sha256",
    "final_service_inbound_ip_rule_set_empty=boolean",
    "fixture_only=boolean",
    "forbidden_production_identity_sha256=lowercase_sha256",
    "forbidden_staging_identity_sha256=lowercase_sha256",
    "operational_collection_procedure_contract_sha256=lowercase_sha256",
    "public_external_access_blocked=boolean",
    "raw_connection_values_disclosed=boolean",
    "runtime_binding_contract_complete=boolean",
    "source_observation_bundle_sha256=lowercase_sha256",
    "srbe_collection_evidence_complete=boolean",
    "successor_activation_authorization_record_sha256=lowercase_sha256_or_UNBOUND",
    "target_application_attachment_count_zero=boolean",
    "target_application_attachment_recheck_evidence_sha256=lowercase_sha256",
    "target_available_recheck_evidence_sha256=lowercase_sha256",
    "target_lifecycle_evidence_sha256=lowercase_sha256",
    "target_lifecycle_within_72h=boolean",
    "target_network_lockdown_recheck_evidence_sha256=lowercase_sha256",
    "target_open_connection_count_zero=boolean",
    "target_open_connection_recheck_evidence_sha256=lowercase_sha256",
    "target_status_available=boolean",
)

PROCEDURE_LINES = (
    "contract=fixed:PMAI_P0_04_ARR_V3_SRBE_OPERATIONAL_COLLECTION_PROCEDURE_V4_V1",
    "procedure_form=NON_EXECUTABLE_ORDERED_CONTRACT_ONLY",
    "provider=RENDER",
    "target_logical_name=" + TARGET_LOGICAL_NAME,
    "collection_phase_output_schema_sha256=" + OUTPUT_SCHEMA_SHA256,
    "collection_attempt_limit=1",
    "step_01=VERIFY_ACTION_TIME_ONE_TIME_CONFIRMATION_NAMES_THIS_PROCEDURE_CONTRACT_SHA256",
    "step_02=VERIFY_EXACT_TARGET_AND_STATIC_PROVENANCE_HASHES",
    "step_03=READ_ONLY_RECHECK_EXACT_V4_TARGET_INFO_APPLICATION_ATTACHMENTS_AND_NETWORK",
    "step_04=REQUIRE_STATUS_AVAILABLE_AND_LIFECYCLE_AGE_AT_MOST_72_HOURS",
    "step_05=REQUIRE_APPLICATION_ATTACHMENT_COUNT_ZERO_AND_OPEN_CONNECTION_COUNT_ZERO",
    "step_06=REQUIRE_INITIAL_INBOUND_IP_RULE_SET_EMPTY_AND_PUBLIC_EXTERNAL_ACCESS_BLOCKED",
    "step_07=DERIVE_FORBIDDEN_PRODUCTION_AND_STAGING_IDENTITY_HASHES_WITHOUT_DATABASE_CONNECTION",
    "step_08=IF_TARGET_DATABASE_METADATA_READ_REQUIRED_ADD_EXACT_SINGLE_OPERATOR_IPV4_CIDR_32_AND_SAVE_ONCE",
    "step_09=IF_REQUIRED_CONNECT_ONLY_TO_EXACT_V4_TARGET_FOR_READ_ONLY_IDENTITY_AND_SCHEMA_METADATA",
    "step_10=NORMALIZE_AND_HASH_EPHEMERAL_VALUES_IN_MEMORY_WITH_NO_RAW_OUTPUT",
    "step_11=CLOSE_EXACT_V4_TARGET_DATABASE_CONNECTION_BEFORE_CLEANUP",
    "step_12=FINALLY_IF_TEMPORARY_RULE_ADDED_REMOVE_EXACT_RULE_AND_SAVE_ONCE",
    "step_13=FINALLY_READ_ONLY_VERIFY_EMPTY_INBOUND_RULE_SET_AND_PUBLIC_EXTERNAL_ACCESS_BLOCKED",
    "step_14=EMIT_ONLY_HASH_LOCKED_COLLECTION_PHASE_OUTPUT_SCHEMA_AND_STOP",
    "temporary_allowlist=EXACT_SINGLE_OPERATOR_IPV4_CIDR_32_ONLY_IF_DATABASE_METADATA_READ_REQUIRED",
    "maximum_allowlist_add_save_count=1",
    "maximum_allowlist_remove_save_count=1",
    "initial_inbound_ip_rule_set=[]",
    "final_inbound_ip_rule_set=[]",
    "target_database_scope=READ_ONLY_IDENTITY_AND_SCHEMA_METADATA_ONLY",
    "production_database_connection=false",
    "staging_database_connection=false",
    "target_database_write=false",
    "database_export=false",
    "raw_value_output=false",
    "collector_input_persistence=false",
    "credential_or_connection_value_persistence=false",
    "runner_creation_activation_import_or_execution=false",
    "backup_archive_restore_migration_deployment_or_deletion=false",
    "temporary_rule_removal_in_finally=true",
    "cleanup_required_on_success_failure_or_ambiguity=true",
    "success_rule=STOP_AFTER_SANITIZED_OUTPUT_AND_FINALLY_CLEANUP",
    "failure_rule=HOLD_NO_RETRY_AND_FINALLY_CLEANUP",
    "ambiguity_rule=HOLD_NO_RETRY_AND_FINALLY_CLEANUP",
    "retry_rule=NO_MANUAL_OR_AUTOMATIC_RETRY",
    "inert_collector_is_live_adapter=false",
    "operational_adapter_supplied_by_contract=false",
)


def need(condition: bool, message: str) -> None:
    if not condition:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def safe_path(relative: str) -> Path:
    path = ROOT / relative
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + relative)
    return path


def digest(relative: str) -> str:
    return hashlib.sha256(safe_path(relative).read_bytes()).hexdigest()


def text(relative: str) -> str:
    value = safe_path(relative).read_text(encoding="utf-8")
    need(value.endswith("\n"), "final newline " + relative)
    need("\r" not in value, "CR byte " + relative)
    for line_number, line in enumerate(value.splitlines(), 1):
        need(line == line.rstrip(), f"trailing whitespace {relative}:{line_number}")
    return value


def read_json(relative: str) -> dict[str, Any]:
    value = json.loads(text(relative))
    need(type(value) is dict, "JSON object " + relative)
    return value


def strict_manifest_json(source: str) -> Any:
    def object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("MANIFEST_STRUCTURE_MISMATCH")
            value[key] = item
        return value

    try:
        return json.loads(source, object_pairs_hook=object_from_pairs)
    except json.JSONDecodeError:
        raise ValueError("MANIFEST_STRUCTURE_MISMATCH") from None


def rows(relative: str, fieldnames: list[str]) -> list[dict[str, str]]:
    with safe_path(relative).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        need(reader.fieldnames == fieldnames, "CSV header " + relative)
        value = list(reader)
    need(all(set(row) == set(fieldnames) for row in value), "CSV row schema " + relative)
    return value


def marker(source: str, key: str) -> str:
    values = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", source)
    if not values:
        raise ValueError("missing governed marker " + key)
    if len(set(values)) != 1:
        raise ValueError("conflicting governed marker " + key)
    return values[0]


def contract_sha256(lines: tuple[str, ...]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        env=SANITIZED_VALIDATOR_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if check:
        need(result.returncode == 0, "git " + " ".join(args))
        need(result.stderr == "", "git stderr " + " ".join(args))
    return result.stdout.strip()


def git_lines(*args: str) -> list[str]:
    output = git(*args)
    return output.splitlines() if output else []


def parse_git_nul_paths(payload: bytes) -> list[str]:
    if payload == b"":
        return []
    if not payload.endswith(b"\0"):
        raise ValueError("HISTORY_AMBIGUITY")
    raw_paths = payload[:-1].split(b"\0")
    if any(path == b"" for path in raw_paths):
        raise ValueError("HISTORY_AMBIGUITY")
    try:
        paths = [path.decode("utf-8", errors="strict") for path in raw_paths]
    except UnicodeDecodeError:
        raise ValueError("HISTORY_AMBIGUITY") from None
    if len(paths) != len(set(paths)):
        raise ValueError("HISTORY_AMBIGUITY")
    return paths


def git_paths(*args: str) -> list[str]:
    need("-z" in args, "git path command NUL mode")
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        env=SANITIZED_VALIDATOR_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    need(result.returncode == 0, "git path command exit")
    need(result.stderr == b"", "git path command stderr")
    try:
        return parse_git_nul_paths(result.stdout)
    except ValueError as error:
        need(False, str(error))
        return []


def canonical_commit_message_body(message_bytes: bytes) -> str:
    if type(message_bytes) is not bytes:
        raise ValueError("git commit message bytes")
    if b"\0" in message_bytes or b"\r" in message_bytes:
        raise ValueError("git commit message bytes")
    if message_bytes.endswith(b"\n\n"):
        raise ValueError("git commit message terminal newline ambiguity")
    if message_bytes.endswith(b"\n"):
        message_bytes = message_bytes[:-1]
    try:
        return message_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ValueError("git commit message UTF-8") from None


def canonical_single_line_commit_subject(subject: str) -> bool:
    if type(subject) is not str or subject == "":
        return False
    if subject[0].isspace() or subject[-1].isspace():
        return False
    return all(
        character.isprintable()
        and ord(character) >= 0x20
        and ord(character) != 0x7F
        and (character == " " or not character.isspace())
        for character in subject
    )


def git_commit_message(commit: str) -> str:
    result = subprocess.run(
        ["git", "cat-file", "commit", commit],
        cwd=ROOT,
        env=SANITIZED_VALIDATOR_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    need(result.returncode == 0, "git commit object " + commit)
    need(result.stderr == b"", "git commit object stderr " + commit)
    parts = result.stdout.split(b"\n\n", 1)
    need(len(parts) == 2 and parts[0].startswith(b"tree "), "git commit object format")
    try:
        return canonical_commit_message_body(parts[1])
    except ValueError as error:
        need(False, str(error))
        return ""


def git_is_ancestor(ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        env=SANITIZED_VALIDATOR_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    need(result.returncode in {0, 1}, "git ancestry status")
    need(result.stdout == b"" and result.stderr == b"", "git ancestry output")
    return result.returncode == 0


def path_sequence_sha256(paths: list[str] | tuple[str, ...]) -> str:
    return hashlib.sha256(("\n".join(paths) + "\n").encode("utf-8")).hexdigest()


def working_changed_paths() -> list[str]:
    tracked = git_paths("diff", "--name-only", "--no-renames", "-z", "HEAD")
    untracked = git_paths("ls-files", "-z", "--others", "--exclude-standard")
    return sorted(set(tracked + untracked), key=lambda value: value.encode("utf-8"))


def git_blob_text(commit: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "show", commit + ":" + relative],
        cwd=ROOT,
        env=SANITIZED_VALIDATOR_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    need(result.returncode == 0 and result.stderr == "", "git blob " + relative)
    return result.stdout


def git_blob_bytes(commit: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", commit + ":" + relative],
        cwd=ROOT,
        env=SANITIZED_VALIDATOR_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    need(
        result.returncode == 0 and result.stderr == b"",
        "git blob bytes " + relative,
    )
    return result.stdout


def unique_literal_assignments(source: str, names: tuple[str, ...]) -> dict[str, Any]:
    occurrences: dict[str, list[Any]] = {name: [] for name in names}
    tree = ast.parse(source, filename=CENTRAL)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in occurrences:
                raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
            continue
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id in occurrences:
                raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
            continue
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in occurrences:
                raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
            continue
        else:
            continue
        owned_targets = [
            target
            for target in targets
            if isinstance(target, ast.Name) and target.id in occurrences
        ]
        if not owned_targets:
            continue
        if (
            len(targets) != 1
            or len(owned_targets) != 1
            or not isinstance(targets[0], ast.Name)
            or value_node is None
        ):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        try:
            value = ast.literal_eval(value_node)
        except (ValueError, TypeError, SyntaxError):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE") from None
        occurrences[targets[0].id].append(value)
    if any(len(values) != 1 for values in occurrences.values()):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    values = {name: occurrences[name][0] for name in names}
    return values


def top_level_assignment_names(source: str) -> tuple[str, ...]:
    names: list[str] = []
    for node in ast.parse(source, filename=CENTRAL).body:
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ValueError("HISTORY_AMBIGUITY")
            if node.targets[0].id != "ROOT":
                names.append(node.targets[0].id)
        elif isinstance(node, ast.AnnAssign):
            raise ValueError("HISTORY_AMBIGUITY")
    return tuple(names)


def ast_dump(node: ast.AST) -> str:
    ignored_fields = {"kind", "type_comment", "type_ignores", "type_params"}

    def encode(value: Any) -> Any:
        if isinstance(value, ast.AST):
            encoded: dict[str, Any] = {"node": type(value).__name__}
            for field in value._fields:
                if field not in ignored_fields:
                    encoded[field] = encode(getattr(value, field))
            return encoded
        if isinstance(value, list):
            return [encode(item) for item in value]
        if isinstance(value, tuple):
            return [encode(item) for item in value]
        if value is Ellipsis:
            return {"constant": "Ellipsis"}
        if value is None or type(value) in {bool, int, float, complex, str, bytes}:
            if type(value) is complex:
                return {"constant": "complex", "real": value.real, "imag": value.imag}
            if type(value) is bytes:
                return {"constant": "bytes", "hex": value.hex()}
            return value
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")

    return json.dumps(
        encode(node), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def canonical_literal(value: Any) -> Any:
    if value is None or type(value) in {bool, int, float, str}:
        return {"type": type(value).__name__, "value": value}
    if type(value) is complex:
        return {"type": "complex", "real": value.real, "imag": value.imag}
    if type(value) is bytes:
        return {"type": "bytes", "hex": value.hex()}
    if type(value) in {list, tuple}:
        return {
            "type": type(value).__name__,
            "items": [canonical_literal(item) for item in value],
        }
    if type(value) is dict:
        return {
            "type": "dict",
            "items": [
                [canonical_literal(key), canonical_literal(item)]
                for key, item in value.items()
            ],
        }
    if type(value) in {set, frozenset}:
        items = [canonical_literal(item) for item in value]
        items.sort(
            key=lambda item: json.dumps(
                item, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            )
        )
        return {"type": type(value).__name__, "items": items}
    raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")


def parsed_statement(source: str) -> ast.stmt:
    body = ast.parse(source).body
    if len(body) != 1:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    return body[0]


def top_level_binding_names(node: ast.stmt) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.asname or alias.name.split(".")[0] for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return tuple(alias.asname or alias.name for alias in node.names)
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        return (node.targets[0].id,)
    if isinstance(node, ast.FunctionDef):
        return (node.name,)
    return ()


def function_definition_is_inert(node: ast.FunctionDef) -> bool:
    arguments = (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    )
    return (
        not node.decorator_list
        and not getattr(node, "type_params", ())
        and not node.args.defaults
        and not any(value is not None for value in node.args.kw_defaults)
        and node.returns is None
        and all(argument.annotation is None for argument in arguments)
        and (node.args.vararg is None or node.args.vararg.annotation is None)
        and (node.args.kwarg is None or node.args.kwarg.annotation is None)
    )


def v4_central_module_structure(
    source: str,
) -> tuple[ast.Module, ast.FunctionDef, dict[str, Any], dict[str, Any]]:
    tree = ast.parse(source, filename=CENTRAL)
    if (
        not source.startswith("#!/usr/bin/env python3\n")
        or not tree.body
        or not isinstance(tree.body[0], ast.Expr)
        or not isinstance(tree.body[0].value, ast.Constant)
        or type(tree.body[0].value.value) is not str
        or tree.body[0].lineno != 2
        or getattr(tree.body[0], "end_lineno", None) != 2
        or tree.body[0].col_offset != 0
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    expected_entrypoint = parsed_statement(CENTRAL_V4_ENTRYPOINT)
    if ast_dump(tree.body[-1]) != ast_dump(expected_entrypoint):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")

    bound: set[str] = set()
    imports: list[str] = []
    functions: dict[str, ast.FunctionDef] = {}
    literal_values: dict[str, Any] = {}
    root_assignment = ""
    owned_target_nodes: set[int] = set()
    for index, node in enumerate(tree.body[:-1]):
        if index == 0:
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast_dump(node))
        elif isinstance(node, ast.Assign):
            target = node.targets[0]
            value = node.value
            if not isinstance(target, ast.Name) or value is None:
                raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
            if target.id == "ROOT":
                if ast_dump(node) != ast_dump(parsed_statement(CENTRAL_V4_ROOT_ASSIGNMENT)):
                    raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
                root_assignment = ast_dump(node)
            else:
                try:
                    literal_value = ast.literal_eval(value)
                except (ValueError, TypeError, SyntaxError):
                    raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE") from None
                if target.id != target.id.upper():
                    raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
                literal_values[target.id] = literal_value
            if target.id in CENTRAL_V4_OWNED_ASSIGNMENTS:
                owned_target_nodes.add(id(target))
        elif isinstance(node, ast.FunctionDef):
            if not function_definition_is_inert(node):
                raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
            if node.name in {
                "Path",
                "SystemExit",
                "dict",
                "isinstance",
                "len",
                "list",
                "print",
                "set",
                "sorted",
                "str",
                "tuple",
                "type",
            }:
                raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
            functions[node.name] = node
        else:
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        names = top_level_binding_names(node)
        if len(names) != len(set(names)) or bound.intersection(names):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        bound.update(names)

    if (
        root_assignment == ""
        or set(functions) != {*CENTRAL_V4_SUPPORT_FUNCTIONS, "main"}
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    for name, value in literal_values.items():
        sensitive_assignment = name.lower() + "=" + (
            value if type(value) is str else "plaintext"
        )
        if sensitive_output_value_is_forbidden(sensitive_assignment):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and type(node.value) is str
            and (
                sensitive_material_violation(node.value) is not None
                or sensitive_output_value_is_forbidden(node.value)
            )
        ):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id in CENTRAL_V4_OWNED_ASSIGNMENTS
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and id(node) not in owned_target_nodes
        ):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")

    payload = {
        "docstring_ast": ast_dump(tree.body[0]),
        "entrypoint_ast": ast_dump(tree.body[-1]),
        "imports_ast": imports,
        "main_signature_ast": ast_dump(functions["main"].args),
        "root_assignment_ast": root_assignment,
        "support_functions_ast": [
            ast_dump(functions[name]) for name in CENTRAL_V4_SUPPORT_FUNCTIONS
        ],
    }
    return tree, functions["main"], payload, literal_values


def v4_central_marker_indexes(source: str) -> tuple[int, int]:
    lines = source.splitlines()
    begin_indexes = [
        index
        for index, line in enumerate(lines)
        if line.strip() == CENTRAL_V4_INTEGRATION_BEGIN
    ]
    end_indexes = [
        index
        for index, line in enumerate(lines)
        if line.strip() == CENTRAL_V4_INTEGRATION_END
    ]
    if len(begin_indexes) != 1 or len(end_indexes) != 1:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    start = begin_indexes[0]
    stop = end_indexes[0]
    if start >= stop:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    return start, stop


def v4_central_integration_block(source: str) -> str:
    lines = source.splitlines()
    start, stop = v4_central_marker_indexes(source)
    return "\n".join(lines[start : stop + 1]) + "\n"


def static_string_expression(
    node: ast.AST, literal_values: dict[str, Any]
) -> str | None:
    if isinstance(node, ast.Constant):
        return node.value if type(node.value) is str else None
    if isinstance(node, ast.Name):
        if isinstance(node.ctx, ast.Load):
            value = literal_values.get(node.id)
            return value if type(value) is str else None
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = static_string_expression(node.left, literal_values)
        right = static_string_expression(node.right, literal_values)
        if left is not None and right is not None:
            return left + right
    return None


def sensitive_output_value_is_forbidden(value: str) -> bool:
    key, separator, item = value.partition("=")
    if separator == "":
        return False
    tokens = key.split("_")
    token_set = set(tokens)
    token_pairs = set(zip(tokens, tokens[1:]))
    sensitive = bool(
        token_set.intersection(
            {"credential", "password", "secret", "token", "dsn", "username", "email"}
        )
        or token_pairs.intersection(
            {
                ("api", "key"),
                ("private", "key"),
                ("database", "url"),
                ("connection", "value"),
                ("connection", "string"),
                ("connection", "uri"),
                ("connection", "url"),
                ("connection", "host"),
                ("connection", "port"),
                ("relation", "name"),
                ("raw", "relation"),
                ("raw", "identifier"),
            }
        )
    )
    safe_value = item in {"false", "UNBOUND", "REDACTED"} or (
        key.endswith("_sha256")
        and re.fullmatch(r"[0-9a-f]{64}", item) is not None
    )
    return sensitive and not safe_value


def assigned_name(statement: ast.stmt) -> str | None:
    if (
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
    ):
        return statement.targets[0].id
    return None


def expression_call(statement: ast.stmt, name: str) -> ast.Call | None:
    if (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == name
    ):
        return statement.value
    return None


def exact_name(node: ast.AST, expected: str) -> bool:
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == expected


def exact_attribute(node: ast.AST, base: str, attribute: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and exact_name(node.value, base)
        and node.attr == attribute
        and isinstance(node.ctx, ast.Load)
    )


def path_assignment_components(
    statement: ast.stmt,
    suffix: str,
    literal_values: dict[str, Any],
    protected_names: set[str],
) -> tuple[str, str] | None:
    local_name = assigned_name(statement)
    if local_name is None or not local_name.endswith(suffix.lower() + "_path"):
        return None
    if local_name in protected_names:
        return None
    value = statement.value
    path_value = (
        literal_values.get(value.right.id)
        if isinstance(value, ast.BinOp) and isinstance(value.right, ast.Name)
        else None
    )
    path_pattern = (
        r"scripts/validate_[a-z0-9_]+\.py"
        if suffix == "_VALIDATOR"
        else r"docs/clinical_data/[A-Z0-9_]+_PACKAGE_MANIFEST_V1\.json"
    )
    if not (
        isinstance(value, ast.BinOp)
        and isinstance(value.op, ast.Div)
        and exact_name(value.left, "ROOT")
        and isinstance(value.right, ast.Name)
        and isinstance(value.right.ctx, ast.Load)
        and value.right.id.endswith(suffix)
        and type(path_value) is str
        and re.fullmatch(path_pattern, path_value) is not None
    ):
        return None
    return local_name, value.right.id


def need_call_condition(statement: ast.stmt) -> ast.AST | None:
    call = expression_call(statement, "need")
    message = (
        call.args[1].value
        if call is not None
        and len(call.args) == 2
        and isinstance(call.args[1], ast.Constant)
        else None
    )
    if (
        call is None
        or len(call.args) != 2
        or call.keywords
        or not isinstance(call.args[1], ast.Constant)
        or type(message) is not str
        or re.fullmatch(r"[\x20-\x7e]+", message) is None
        or sensitive_material_violation(message) is not None
        or sensitive_output_value_is_forbidden(message)
    ):
        return None
    return call.args[0]


def safe_path_condition(node: ast.AST, local_name: str) -> bool:
    if not (isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And) and len(node.values) == 2):
        return False
    exists, not_symlink = node.values
    return (
        isinstance(exists, ast.Call)
        and not exists.args
        and not exists.keywords
        and isinstance(exists.func, ast.Attribute)
        and exact_name(exists.func.value, local_name)
        and exists.func.attr == "is_file"
        and isinstance(not_symlink, ast.UnaryOp)
        and isinstance(not_symlink.op, ast.Not)
        and isinstance(not_symlink.operand, ast.Call)
        and not not_symlink.operand.args
        and not not_symlink.operand.keywords
        and isinstance(not_symlink.operand.func, ast.Attribute)
        and exact_name(not_symlink.operand.func.value, local_name)
        and not_symlink.operand.func.attr == "is_symlink"
    )


def hash_pin_condition(
    node: ast.AST,
    local_name: str,
    pin_name: str,
    literal_values: dict[str, Any],
) -> bool:
    if not (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and len(node.comparators) == 1
        and exact_name(node.comparators[0], pin_name)
    ):
        return False
    pin = literal_values.get(pin_name)
    if type(pin) is not str or re.fullmatch(r"[0-9a-f]{64}", pin) is None:
        return False
    hexdigest_call = node.left
    if not (
        isinstance(hexdigest_call, ast.Call)
        and not hexdigest_call.args
        and not hexdigest_call.keywords
        and isinstance(hexdigest_call.func, ast.Attribute)
        and hexdigest_call.func.attr == "hexdigest"
        and isinstance(hexdigest_call.func.value, ast.Call)
    ):
        return False
    sha_call = hexdigest_call.func.value
    if not (
        isinstance(sha_call.func, ast.Attribute)
        and exact_name(sha_call.func.value, "hashlib")
        and sha_call.func.attr == "sha256"
        and len(sha_call.args) == 1
        and not sha_call.keywords
    ):
        return False
    read_call = sha_call.args[0]
    return (
        isinstance(read_call, ast.Call)
        and not read_call.args
        and not read_call.keywords
        and isinstance(read_call.func, ast.Attribute)
        and exact_name(read_call.func.value, local_name)
        and read_call.func.attr == "read_bytes"
    )


def result_field_condition(
    node: ast.AST, result_name: str, field: str, expected: Any
) -> bool:
    return (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and len(node.comparators) == 1
        and exact_attribute(node.left, result_name, field)
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value == expected
        and type(node.comparators[0].value) is type(expected)
    )


def pass_marker_condition(node: ast.AST, result_name: str, marker_name: str) -> bool:
    if not (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and type(node.comparators[0].value) is int
        and node.comparators[0].value == 1
        and isinstance(node.left, ast.Call)
        and len(node.left.args) == 1
        and not node.left.keywords
        and exact_name(node.left.args[0], marker_name)
        and isinstance(node.left.func, ast.Attribute)
        and node.left.func.attr == "count"
        and isinstance(node.left.func.value, ast.Call)
    ):
        return False
    splitlines_call = node.left.func.value
    return (
        not splitlines_call.args
        and not splitlines_call.keywords
        and isinstance(splitlines_call.func, ast.Attribute)
        and splitlines_call.func.attr == "splitlines"
        and exact_attribute(splitlines_call.func.value, result_name, "stdout")
    )


def sanitized_successor_env(node: ast.AST, literal_values: dict[str, Any]) -> bool:
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dict"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
    ):
        return False
    env_name = node.args[0].id
    items = literal_values.get(env_name)
    return (
        env_name not in CENTRAL_V4_BASELINE_ASSIGNMENTS
        and env_name not in CENTRAL_V4_OWNED_ASSIGNMENTS
        and type(items) is tuple
        and all(
            type(item) is tuple
            and len(item) == 2
            and all(type(value) is str for value in item)
            for item in items
        )
        and items == tuple(SANITIZED_VALIDATOR_ENV.items())
    )


def successor_subprocess_call(
    node: ast.AST,
    validator_path_name: str,
    literal_values: dict[str, Any],
) -> bool:
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and exact_name(node.func.value, "subprocess")
        and node.func.attr == "run"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.List)
    ):
        return False
    argv = node.args[0].elts
    if not (
        len(argv) == 4
        and exact_attribute(argv[0], "sys", "executable")
        and isinstance(argv[1], ast.Constant)
        and argv[1].value == "-I"
        and isinstance(argv[2], ast.Constant)
        and argv[2].value == "-B"
        and isinstance(argv[3], ast.Call)
        and isinstance(argv[3].func, ast.Name)
        and argv[3].func.id == "str"
        and len(argv[3].args) == 1
        and not argv[3].keywords
        and exact_name(argv[3].args[0], validator_path_name)
    ):
        return False
    keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
    if len(keywords) != len(node.keywords) or set(keywords) != {
        "check",
        "cwd",
        "env",
        "stderr",
        "stdin",
        "stdout",
        "text",
        "timeout",
    }:
        return False
    timeout = keywords["timeout"]
    return (
        exact_name(keywords["cwd"], "ROOT")
        and sanitized_successor_env(keywords["env"], literal_values)
        and exact_attribute(keywords["stdin"], "subprocess", "DEVNULL")
        and exact_attribute(keywords["stdout"], "subprocess", "PIPE")
        and exact_attribute(keywords["stderr"], "subprocess", "PIPE")
        and isinstance(keywords["text"], ast.Constant)
        and keywords["text"].value is True
        and isinstance(keywords["check"], ast.Constant)
        and keywords["check"].value is False
        and isinstance(timeout, ast.Constant)
        and type(timeout.value) is int
        and 1 <= timeout.value <= 120
    )


def validate_successor_hook_group(
    group: list[ast.stmt],
    literal_values: dict[str, Any],
    protected_names: set[str],
) -> tuple[str, str, str, str]:
    if len(group) != 11:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    validator = path_assignment_components(
        group[0], "_VALIDATOR", literal_values, protected_names
    )
    manifest = path_assignment_components(
        group[3], "_MANIFEST", literal_values, protected_names
    )
    if validator is None or manifest is None:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    validator_local, validator_constant = validator
    manifest_local, manifest_constant = manifest
    stem = validator_constant[: -len("_VALIDATOR")]
    if (
        re.fullmatch(r"[A-Z][A-Z0-9_]*", stem) is None
        or manifest_constant != stem + "_MANIFEST"
        or stem == CENTRAL_V4_STEM
        or any(
            constant in CENTRAL_V4_BASELINE_ASSIGNMENTS
            for constant in (
                validator_constant,
                stem + "_VALIDATOR_SHA256",
                manifest_constant,
                stem + "_MANIFEST_SHA256",
                stem + "_PASS_MARKER",
            )
        )
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    validator_pin = stem + "_VALIDATOR_SHA256"
    manifest_pin = stem + "_MANIFEST_SHA256"
    marker_name = stem + "_PASS_MARKER"
    marker_value = literal_values.get(marker_name)
    baseline_values = {
        literal_values.get(name)
        for name in CENTRAL_V4_BASELINE_ASSIGNMENTS
        if type(literal_values.get(name)) is str
    }
    if (
        type(marker_value) is not str
        or marker_value != stem.lower() + "=PASS"
        or marker_value in baseline_values
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    validator_path = literal_values[validator_constant]
    manifest_path = literal_values[manifest_constant]
    if validator_path in baseline_values or manifest_path in baseline_values:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    result_name = assigned_name(group[6])
    local_stem = validator_local[: -len("_validator_path")]
    if (
        manifest_local != local_stem + "_manifest_path"
        or result_name != local_stem + "_result"
        or result_name in protected_names
        or not safe_path_condition(need_call_condition(group[1]), validator_local)
        or not hash_pin_condition(
            need_call_condition(group[2]), validator_local, validator_pin, literal_values
        )
        or not safe_path_condition(need_call_condition(group[4]), manifest_local)
        or not hash_pin_condition(
            need_call_condition(group[5]), manifest_local, manifest_pin, literal_values
        )
        or not successor_subprocess_call(
            group[6].value, validator_local, literal_values
        )
        or not result_field_condition(
            need_call_condition(group[7]), result_name, "returncode", 0
        )
        or not result_field_condition(
            need_call_condition(group[8]), result_name, "stderr", ""
        )
        or not pass_marker_condition(
            need_call_condition(group[9]), result_name, marker_name
        )
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    print_call = expression_call(group[10], "print")
    if not (
        print_call is not None
        and len(print_call.args) == 1
        and not print_call.keywords
        and exact_name(print_call.args[0], marker_name)
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    return local_stem, validator_path, manifest_path, marker_value


def validate_successor_main_statements(
    statements: list[ast.stmt],
    literal_values: dict[str, Any],
    protected_names: set[str],
) -> set[str]:
    if len(statements) % 11 != 0:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    identities = [
        validate_successor_hook_group(
            statements[start : start + 11], literal_values, protected_names
        )
        for start in range(0, len(statements), 11)
    ]
    if any(
        len({identity[index] for identity in identities}) != len(identities)
        for index in range(4)
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    return {identity[3] for identity in identities}


def v4_central_main_projection(
    source: str,
    main_function: ast.FunctionDef,
    literal_values: dict[str, Any],
) -> dict[str, Any]:
    start_index, stop_index = v4_central_marker_indexes(source)
    begin_line = start_index + 1
    end_line = stop_index + 1
    integration_indexes = [
        index
        for index, node in enumerate(main_function.body)
        if node.lineno > begin_line
        and getattr(node, "end_lineno", node.lineno) < end_line
    ]
    if (
        len(integration_indexes) != 11
        or integration_indexes
        != list(range(integration_indexes[0], integration_indexes[-1] + 1))
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    integration_statements = [main_function.body[index] for index in integration_indexes]
    first = integration_statements[0]
    last = integration_statements[-1]
    if (
        not isinstance(first, ast.Assign)
        or len(first.targets) != 1
        or not isinstance(first.targets[0], ast.Name)
        or first.targets[0].id != "srbe_v4_execution_authorization_validator_path"
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    pass_marker_name = CENTRAL_V4_STEM + "_PASS_MARKER"
    if not (
        isinstance(last, ast.Expr)
        and isinstance(last.value, ast.Call)
        and isinstance(last.value.func, ast.Name)
        and last.value.func.id == "print"
        and len(last.value.args) == 1
        and isinstance(last.value.args[0], ast.Name)
        and last.value.args[0].id == pass_marker_name
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    hook_names = tuple(hook.split(" =", 1)[0] for _, hook in CENTRAL_V4_HOOKS)
    hook_indexes: list[int] = []
    for hook_name in hook_names:
        matches = [
            index
            for index, node in enumerate(main_function.body[: integration_indexes[-1] + 1])
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == hook_name
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "subprocess"
            and node.value.func.attr == "run"
        ]
        if len(matches) != 1:
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        hook_indexes.append(matches[0])
    if hook_indexes != sorted(hook_indexes):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")

    expected_guard_ast = ast_dump(parsed_statement(CENTRAL_V4_REQUIRE_COMPLETE_GUARD))
    if len(main_function.body) < 3:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    guard = main_function.body[-3]
    output_loop = main_function.body[-2]
    final_return = main_function.body[-1]
    if ast_dump(guard) != expected_guard_ast:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    if not (
        isinstance(final_return, ast.Return)
        and isinstance(final_return.value, ast.Constant)
        and final_return.value.value == 0
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    if not (
        isinstance(output_loop, ast.For)
        and isinstance(output_loop.target, ast.Name)
        and output_loop.target.id == "line"
        and isinstance(output_loop.iter, ast.Tuple)
        and len(output_loop.body) == 1
        and not output_loop.orelse
        and isinstance(output_loop.body[0], ast.Expr)
        and isinstance(output_loop.body[0].value, ast.Call)
        and isinstance(output_loop.body[0].value.func, ast.Name)
        and output_loop.body[0].value.func.id == "print"
        and len(output_loop.body[0].value.args) == 1
        and isinstance(output_loop.body[0].value.args[0], ast.Name)
        and output_loop.body[0].value.args[0].id == "line"
        and not output_loop.body[0].value.keywords
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    output_values = [
        static_string_expression(item, literal_values) for item in output_loop.iter.elts
    ]
    if any(value is None for value in output_values):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    if len(output_values) != len(set(output_values)):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    if (
        literal_values.get(CENTRAL_V4_STEM + "_PASS_MARKER")
        in output_values
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    final_output = "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance"
    if output_values.count(final_output) != 1 or output_values[-1] != final_output:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    nonfinal_output_values = output_values[:-1]
    if any(
        re.fullmatch(r"[a-z0-9_]+=[\x20-\x7e]*", value) is None
        for value in nonfinal_output_values
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    if any(
        value.endswith("=PASS")
        or sensitive_material_violation(value) is not None
        or sensitive_output_value_is_forbidden(value)
        for value in nonfinal_output_values
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    output_keys = [value.split("=", 1)[0] for value in nonfinal_output_values]
    if len(output_keys) != len(set(output_keys)):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    baseline_output_ast = [
        ast_dump(ast.parse(expression, mode="eval").body)
        for expression in CENTRAL_V4_BASELINE_OUTPUT_EXPRESSIONS
    ]
    output_item_ast = [ast_dump(item) for item in output_loop.iter.elts]
    cursor = 0
    for required in baseline_output_ast:
        if output_item_ast.count(required) != 1:
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        try:
            cursor = output_item_ast.index(required, cursor) + 1
        except ValueError:
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE") from None

    prefix_body = main_function.body[: integration_indexes[-1] + 1]
    prefix_marker_values: list[str] = []
    for statement in prefix_body:
        print_call = expression_call(statement, "print")
        if print_call is None:
            continue
        if (
            len(print_call.args) != 1
            or print_call.keywords
            or not isinstance(print_call.args[0], ast.Name)
        ):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        marker_value = literal_values.get(print_call.args[0].id)
        if (
            type(marker_value) is not str
            or re.fullmatch(r"[a-z0-9_]+=PASS", marker_value) is None
        ):
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        prefix_marker_values.append(marker_value)
    if len(prefix_marker_values) != 5:
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    prefix_store_names = {
        node.id
        for statement in prefix_body
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    protected_names = (
        set(CENTRAL_V4_SUCCESSOR_PROTECTED_LOCAL_NAMES) | prefix_store_names
    )
    successor_statements = main_function.body[integration_indexes[-1] + 1 : -3]
    successor_markers = validate_successor_main_statements(
        successor_statements, literal_values, protected_names
    )
    successor_marker_keys = {
        marker_value.split("=", 1)[0] for marker_value in successor_markers
    }
    prefix_marker_keys = {
        marker_value.split("=", 1)[0] for marker_value in prefix_marker_values
    }
    if (
        successor_markers.intersection(value for value in output_values if value)
        or len(prefix_marker_keys) != len(prefix_marker_values)
        or successor_marker_keys.intersection(output_keys)
        or prefix_marker_keys.intersection(output_keys)
        or prefix_marker_keys.intersection(successor_marker_keys)
    ):
        raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
    prefix = ast.Module(body=prefix_body, type_ignores=[])
    return {
        "hook_order": list(hook_names),
        "main_prefix_ast": ast_dump(prefix),
        "output_guard_ast": expected_guard_ast,
        "output_loop_body_ast": ast_dump(output_loop.body[0]),
        "baseline_output_ast": baseline_output_ast,
        "final_return_ast": ast_dump(final_return),
    }


def v4_central_projection(source: str) -> str:
    _, main_function, module_payload, literal_values = v4_central_module_structure(
        source
    )
    assignments = unique_literal_assignments(source, CENTRAL_V4_OWNED_ASSIGNMENTS)
    baseline_assignments = unique_literal_assignments(
        source, CENTRAL_V4_BASELINE_ASSIGNMENTS
    )
    for name in CENTRAL_V4_NORMALIZED_ASSIGNMENTS:
        value = assignments[name]
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
        assignments[name] = "<NORMALIZED_SHA256>"
        baseline_assignments[name] = "<NORMALIZED_SHA256>"
    payload = {
        "assignments": [
            [name, canonical_literal(assignments[name])]
            for name in CENTRAL_V4_OWNED_ASSIGNMENTS
        ],
        "baseline_assignments": [
            [name, canonical_literal(baseline_assignments[name])]
            for name in CENTRAL_V4_BASELINE_ASSIGNMENTS
        ],
        "integration_block": v4_central_integration_block(source),
        "main": v4_central_main_projection(
            source, main_function, literal_values
        ),
        "module": module_payload,
        "schema": "PMAI_P0_04_V4_EXECUTION_AUTHORIZATION_CENTRAL_PROJECTION_V1",
    }
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def v4_central_projection_sha256(source: str) -> str:
    return hashlib.sha256(v4_central_projection(source).encode("utf-8")).hexdigest()


def historical_central_normalized_sha256(source: str) -> str:
    normalized = source
    for name in CENTRAL_V4_NORMALIZED_ASSIGNMENTS:
        pattern = (
            r"(" + re.escape(name) + r"\s*=\s*\(\s*[\"'])"
            r"[0-9a-f]{64}"
            r"([\"']\s*\))"
        )
        normalized, count = re.subn(pattern, r"\1<NORMALIZED_SHA256>\2", normalized)
        if count != 1:
            raise ValueError("HISTORY_AMBIGUITY")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HistoryRecord:
    oid: str
    parents: tuple[str, ...]
    subject: str
    tree: str
    changed_paths: tuple[str, ...]
    second_parent_changed_paths: tuple[str, ...]
    central_projection_sha256: str | None
    bindings_valid: bool
    ephemeral_pr_test_merge: bool = False


@dataclass(frozen=True)
class HistoryDecision:
    historical_repair: str
    compatibility_correction: str
    publication_merge: str | None
    successor_central_commits: tuple[str, ...]
    successor_publication_merges: tuple[str, ...]
    history_lineage: tuple[str, ...]
    pending_successor: str | None
    ephemeral_pr_test_merge: str | None


def classify_postpublication_history(
    records: tuple[HistoryRecord, ...],
) -> HistoryDecision:
    correction: HistoryRecord | None = None
    publication_merge: HistoryRecord | None = None
    published_anchor: HistoryRecord | None = None
    pending_successor: HistoryRecord | None = None
    successors: list[str] = []
    successor_merges: list[str] = []
    lineage: list[str] = []
    ephemeral_pr_test_merge: str | None = None
    immutable = set(IMMUTABLE_PACKAGE_PATHS)
    closure = set(PACKAGE_CLOSURE_PATHS)
    correction_paths = set(CORRECTION_PATHS)
    relevant_paths = set(PACKAGE_PATHS) | {CENTRAL}
    for record in records:
        if ephemeral_pr_test_merge is not None:
            raise ValueError("HISTORY_AMBIGUITY")
        changed = set(record.changed_paths)
        second_parent_changed = set(record.second_parent_changed_paths)
        if (
            len(changed) != len(record.changed_paths)
            or len(second_parent_changed)
            != len(record.second_parent_changed_paths)
        ):
            raise ValueError("HISTORY_AMBIGUITY")
        if len(record.parents) == 2:
            if correction is not None and publication_merge is None:
                merge_subject = re.fullmatch(
                    r"Merge pull request #[1-9][0-9]* from pet-med-ai/"
                    + re.escape(COMPATIBILITY_CORRECTION_BRANCH)
                    + r"\n\n"
                    + re.escape(COMPATIBILITY_CORRECTION_SUBJECT),
                    record.subject,
                )
                ephemeral_subject = re.fullmatch(
                    r"Merge ([0-9a-f]{7,40}) into ([0-9a-f]{7,40})",
                    record.subject,
                )
                ephemeral_subject_valid = (
                    record.ephemeral_pr_test_merge
                    and ephemeral_subject is not None
                    and record.parents[1].startswith(ephemeral_subject.group(1))
                    and record.parents[0].startswith(ephemeral_subject.group(2))
                )
                if (
                    record.parents
                    != (PUBLISHED_MERGE_COMMIT, correction.oid)
                    or (merge_subject is None and not ephemeral_subject_valid)
                    or record.tree != correction.tree
                    or len(record.changed_paths) != len(CORRECTION_PATHS)
                    or changed != correction_paths
                    or second_parent_changed
                    or record.central_projection_sha256
                    != CENTRAL_V4_OWNED_PROJECTION_SHA256
                    or not record.bindings_valid
                ):
                    raise ValueError("HISTORY_AMBIGUITY")
                if ephemeral_subject_valid:
                    ephemeral_pr_test_merge = record.oid
                    continue
                publication_merge = record
                published_anchor = record
                lineage.append(record.oid)
                continue
            if (
                correction is None
                or publication_merge is None
                or published_anchor is None
                or pending_successor is None
            ):
                raise ValueError("HISTORY_AMBIGUITY")
            successor_merge_subject = re.fullmatch(
                r"Merge pull request #[1-9][0-9]* from pet-med-ai/"
                r"pmai-p0-04-[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?"
                r"\n\n"
                + re.escape(pending_successor.subject),
                record.subject,
            )
            ephemeral_subject = re.fullmatch(
                r"Merge ([0-9a-f]{7,40}) into ([0-9a-f]{7,40})",
                record.subject,
            )
            ephemeral_subject_valid = (
                record.ephemeral_pr_test_merge
                and ephemeral_subject is not None
                and record.parents[1].startswith(ephemeral_subject.group(1))
                and record.parents[0].startswith(ephemeral_subject.group(2))
            )
            pending_paths = set(pending_successor.changed_paths)
            if (
                record.parents
                != (pending_successor.parents[0], pending_successor.oid)
                or (
                    successor_merge_subject is None
                    and not ephemeral_subject_valid
                )
                or record.tree != pending_successor.tree
                or len(record.changed_paths)
                != len(pending_successor.changed_paths)
                or changed != pending_paths
                or second_parent_changed
                or record.central_projection_sha256
                != CENTRAL_V4_OWNED_PROJECTION_SHA256
                or not record.bindings_valid
            ):
                raise ValueError("HISTORY_AMBIGUITY")
            if ephemeral_subject_valid:
                ephemeral_pr_test_merge = record.oid
                continue
            successor_merges.append(record.oid)
            published_anchor = record
            pending_successor = None
            lineage.append(record.oid)
            continue
        if len(record.parents) != 1:
            raise ValueError("HISTORY_AMBIGUITY")
        if not changed & relevant_paths:
            continue
        if changed & immutable:
            raise ValueError("SECOND_REPAIR_PACKAGE_MUTATION")
        if changed & closure:
            if correction is not None:
                raise ValueError("SECOND_REPAIR_PACKAGE_MUTATION")
            if (
                record.parents != (PUBLISHED_MERGE_COMMIT,)
                or record.subject != COMPATIBILITY_CORRECTION_SUBJECT
                or len(record.changed_paths) != len(CORRECTION_PATHS)
                or changed != correction_paths
            ):
                raise ValueError("UNAUTHORIZED_CLOSURE_CHANGE")
            if record.central_projection_sha256 != CENTRAL_V4_OWNED_PROJECTION_SHA256:
                raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
            if not record.bindings_valid:
                raise ValueError("MANIFEST_HASH_MISMATCH")
            correction = record
            published_anchor = record
            lineage.append(record.oid)
            continue
        if CENTRAL in changed:
            if not canonical_single_line_commit_subject(record.subject):
                raise ValueError("HISTORY_AMBIGUITY")
            if (
                correction is None
                or publication_merge is None
                or published_anchor is None
                or pending_successor is not None
            ):
                raise ValueError("HISTORY_AMBIGUITY")
            if record.central_projection_sha256 != CENTRAL_V4_OWNED_PROJECTION_SHA256:
                raise ValueError("UNAUTHORIZED_V4_PROJECTION_CHANGE")
            if not record.bindings_valid:
                raise ValueError("MANIFEST_HASH_MISMATCH")
            successors.append(record.oid)
            pending_successor = record
            lineage.append(record.oid)
    if correction is None:
        raise ValueError("HISTORY_AMBIGUITY")
    return HistoryDecision(
        historical_repair=HISTORICAL_REPAIR_COMMIT,
        compatibility_correction=correction.oid,
        publication_merge=(publication_merge.oid if publication_merge else None),
        successor_central_commits=tuple(successors),
        successor_publication_merges=tuple(successor_merges),
        history_lineage=tuple(lineage),
        pending_successor=(pending_successor.oid if pending_successor else None),
        ephemeral_pr_test_merge=ephemeral_pr_test_merge,
    )


def validate_history_ancestry(
    decision: HistoryDecision, is_ancestor: Any
) -> None:
    if (
        not decision.history_lineage
        or decision.history_lineage[0] != decision.compatibility_correction
        or not is_ancestor(PUBLISHED_MERGE_COMMIT, decision.history_lineage[0])
    ):
        raise ValueError("HISTORY_AMBIGUITY")
    if any(
        not is_ancestor(ancestor, descendant)
        for ancestor, descendant in zip(
            decision.history_lineage, decision.history_lineage[1:]
        )
    ):
        raise ValueError("HISTORY_AMBIGUITY")


def validate_historical_anchors() -> None:
    need(git("rev-parse", BASE_COMMIT + "^{tree}") == BASE_TREE, "base tree")
    need(
        git("rev-parse", INTRODUCTION_COMMIT + "^{tree}") == INTRODUCTION_TREE,
        "introduction tree",
    )
    need(
        tuple(git("show", "-s", "--format=%P", INTRODUCTION_COMMIT).split())
        == (BASE_COMMIT,),
        "introduction parent",
    )
    need(
        git_commit_message(INTRODUCTION_COMMIT) == INTRODUCTION_SUBJECT,
        "introduction subject",
    )
    need(
        git_paths(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            BASE_COMMIT + ".." + INTRODUCTION_COMMIT,
        )
        == list(EXPECTED_CHANGED_PATHS),
        "introduction changed paths",
    )
    need(
        git("rev-parse", HISTORICAL_REPAIR_COMMIT + "^{tree}")
        == HISTORICAL_REPAIR_TREE,
        "historical repair tree",
    )
    need(
        tuple(git("show", "-s", "--format=%P", HISTORICAL_REPAIR_COMMIT).split())
        == (INTRODUCTION_COMMIT,),
        "historical repair parent",
    )
    need(
        git_commit_message(HISTORICAL_REPAIR_COMMIT) == HISTORICAL_REPAIR_SUBJECT,
        "historical repair subject",
    )
    need(
        git_paths(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            INTRODUCTION_COMMIT + ".." + HISTORICAL_REPAIR_COMMIT,
        )
        == list(HISTORICAL_REPAIR_PATHS),
        "historical repair changed paths",
    )
    need(
        git("rev-parse", PUBLISHED_MERGE_COMMIT + "^{tree}")
        == PUBLISHED_MERGE_TREE,
        "published merge tree",
    )
    need(
        tuple(git("show", "-s", "--format=%P", PUBLISHED_MERGE_COMMIT).split())
        == PUBLISHED_MERGE_PARENTS,
        "published merge parents",
    )
    try:
        baseline_assignment_names = top_level_assignment_names(
            git_blob_text(PUBLISHED_MERGE_COMMIT, CENTRAL)
        )
    except (SyntaxError, ValueError) as error:
        need(False, str(error))
        return
    need(
        baseline_assignment_names == CENTRAL_V4_BASELINE_ASSIGNMENTS,
        "published central baseline assignment scope",
    )
    repair_commits = git_lines(
        "rev-list",
        "--reverse",
        "--full-history",
        INTRODUCTION_COMMIT + ".." + PUBLISHED_MERGE_COMMIT,
        "--",
        *PACKAGE_PATHS,
    )
    need(
        repair_commits == [HISTORICAL_REPAIR_COMMIT],
        "unique historical V4 repair",
    )
    try:
        historical_hash = historical_central_normalized_sha256(
            git_blob_text(HISTORICAL_REPAIR_COMMIT, CENTRAL)
        )
    except ValueError as error:
        need(False, str(error))
        return
    need(
        historical_hash == HISTORICAL_REPAIR_CENTRAL_NORMALIZED_SHA256,
        "historical repair central normalized hash",
    )


def commit_v4_bindings_valid(commit: str, central_source: str) -> bool:
    try:
        assignments = unique_literal_assignments(
            central_source, CENTRAL_V4_OWNED_ASSIGNMENTS
        )
        validator_bytes = git_blob_bytes(commit, VALIDATOR)
        manifest_bytes = git_blob_bytes(commit, MANIFEST)
        if (
            assignments[CENTRAL_V4_STEM + "_VALIDATOR_SHA256"]
            != hashlib.sha256(validator_bytes).hexdigest()
            or assignments[CENTRAL_V4_STEM + "_MANIFEST_SHA256"]
            != hashlib.sha256(manifest_bytes).hexdigest()
        ):
            return False
        manifest = strict_manifest_json(manifest_bytes.decode("utf-8"))
        if type(manifest) is not dict or "files" not in manifest:
            return False
        member_blobs = {
            relative: git_blob_bytes(commit, relative)
            for relative in MANIFEST_MEMBERS
        }
        validate_manifest_closure_items(
            manifest["files"], MANIFEST_MEMBERS, member_blobs
        )
    except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return False
    return True


def exact_pr_merge_ref_points_to_head(head: str) -> bool:
    matches = []
    for line in git_lines(
        "for-each-ref",
        "--format=%(objectname) %(refname)",
        "refs/remotes/pull",
        "refs/pull",
    ):
        fields = line.split()
        if (
            len(fields) == 2
            and fields[0] == head
            and re.fullmatch(
                r"refs/(?:remotes/)?pull/[1-9][0-9]*/merge", fields[1]
            )
            is not None
        ):
            matches.append(fields[1])
    return len(matches) == 1


def history_record(commit: str, head: str) -> HistoryRecord:
    parents = tuple(git("show", "-s", "--format=%P", commit).split())
    changed_paths = (
        tuple(
            git_paths(
                "diff",
                "--name-only",
                "--no-renames",
                "-z",
                parents[0] + ".." + commit,
            )
        )
        if parents
        else ()
    )
    second_parent_changed_paths = (
        tuple(
            git_paths(
                "diff",
                "--name-only",
                "--no-renames",
                "-z",
                parents[1] + ".." + commit,
            )
        )
        if len(parents) == 2
        else ()
    )
    projection = None
    bindings_valid = True
    if CENTRAL in set(changed_paths) | set(second_parent_changed_paths):
        central_source = git_blob_text(commit, CENTRAL)
        try:
            projection = v4_central_projection_sha256(central_source)
        except (SyntaxError, ValueError):
            projection = "INVALID"
        bindings_valid = commit_v4_bindings_valid(commit, central_source)
    return HistoryRecord(
        oid=commit,
        parents=parents,
        subject=git_commit_message(commit),
        tree=git("rev-parse", commit + "^{tree}"),
        changed_paths=changed_paths,
        second_parent_changed_paths=second_parent_changed_paths,
        central_projection_sha256=projection,
        bindings_valid=bindings_valid,
        ephemeral_pr_test_merge=(
            commit == head
            and len(parents) == 2
            and git("rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
            and exact_pr_merge_ref_points_to_head(head)
        ),
    )


def history_record_is_relevant(record: HistoryRecord) -> bool:
    return bool(set(record.changed_paths) & (set(PACKAGE_PATHS) | {CENTRAL}))


def validate_ancestry_merge_orientation(
    records: tuple[HistoryRecord, ...], is_ancestor: Any
) -> None:
    for record in records:
        if len(record.parents) > 1 and not is_ancestor(
            PUBLISHED_MERGE_COMMIT, record.parents[0]
        ):
            raise ValueError("HISTORY_AMBIGUITY")


def working_context(
    head: str, branch: str, working_paths: tuple[str, ...]
) -> str:
    if not working_paths:
        return "clean"
    changed = set(working_paths)
    if len(changed) != len(working_paths):
        raise ValueError("HISTORY_AMBIGUITY")
    if head == PUBLISHED_MERGE_COMMIT:
        if (
            branch != COMPATIBILITY_CORRECTION_BRANCH
            or len(working_paths) != len(CORRECTION_PATHS)
            or changed != set(CORRECTION_PATHS)
        ):
            raise ValueError("UNAUTHORIZED_CLOSURE_CHANGE")
        return "compatibility_correction"
    if changed.intersection(PACKAGE_PATHS):
        raise ValueError("UNAUTHORIZED_CLOSURE_CHANGE")
    if CENTRAL in changed and re.fullmatch(
        r"pmai-p0-04-[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?", branch
    ) is None:
        raise ValueError("HISTORY_AMBIGUITY")
    return "successor"


def validate_working_history_context(
    context: str, decision: HistoryDecision
) -> None:
    if context == "successor" and (
        decision.publication_merge is None
        or decision.pending_successor is not None
    ):
        raise ValueError("HISTORY_AMBIGUITY")


def validate_repository_history() -> None:
    validate_historical_anchors()
    head = git("rev-parse", "HEAD")
    need(
        git_is_ancestor(PUBLISHED_MERGE_COMMIT, head),
        "published merge is not ancestor",
    )
    working_paths = working_changed_paths()
    current_branch = git("rev-parse", "--abbrev-ref", "HEAD")
    try:
        context = working_context(head, current_branch, tuple(working_paths))
    except ValueError as error:
        need(False, str(error))
        return
    if context == "compatibility_correction":
        return
    ancestry_commits = git_lines(
        "rev-list",
        "--reverse",
        "--topo-order",
        "--ancestry-path",
        PUBLISHED_MERGE_COMMIT + ".." + head,
    )
    ancestry_records: list[HistoryRecord] = []
    for commit in ancestry_commits:
        record = history_record(commit, head)
        ancestry_records.append(record)
    try:
        validate_ancestry_merge_orientation(
            tuple(ancestry_records), git_is_ancestor
        )
    except ValueError as error:
        need(False, str(error))
        return
    records_list = [
        record for record in ancestry_records if history_record_is_relevant(record)
    ]
    records = tuple(records_list)
    try:
        decision = classify_postpublication_history(records)
    except ValueError as error:
        need(False, str(error))
        return
    try:
        validate_working_history_context(context, decision)
    except ValueError as error:
        need(False, str(error))
        return
    need(
        decision.historical_repair == HISTORICAL_REPAIR_COMMIT,
        "historical repair classification",
    )
    try:
        validate_history_ancestry(decision, git_is_ancestor)
    except ValueError as error:
        need(False, str(error))
        return
    history_anchor = decision.history_lineage[-1]
    need(git_is_ancestor(history_anchor, head), "V4 history anchor is not HEAD ancestor")
    if decision.publication_merge is None:
        need(
            (
                head == decision.compatibility_correction
                and current_branch == COMPATIBILITY_CORRECTION_BRANCH
            )
            or decision.ephemeral_pr_test_merge == head,
            "unpublished compatibility correction context",
        )
    if decision.pending_successor is not None:
        need(
            (
                head == decision.pending_successor
                and re.fullmatch(
                    r"pmai-p0-04-[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?",
                    current_branch,
                )
                is not None
            )
            or decision.ephemeral_pr_test_merge == head,
            "unpublished successor context",
        )
    expected_tree_modes = {VALIDATOR: "100644", MANIFEST: "100644", CENTRAL: "100755"}
    for relative, expected_mode in expected_tree_modes.items():
        entry = git("ls-tree", decision.compatibility_correction, "--", relative)
        fields = entry.split(None, 1)
        need(
            len(fields) == 2 and fields[0] == expected_mode,
            "compatibility correction tree mode " + relative,
        )


def contract_lines(source: str, begin: str, end: str) -> tuple[str, ...]:
    lines = source.splitlines()
    if lines.count(begin) != 1 or lines.count(end) != 1:
        raise ValueError("contract marker uniqueness " + begin)
    start = lines.index(begin)
    stop = lines.index(end)
    if start >= stop:
        raise ValueError("contract marker order " + begin)
    envelope = lines[start + 1 : stop]
    if (
        len(envelope) < 4
        or envelope[0] != ""
        or envelope[1] != "~~~text"
        or envelope[-2] != "~~~"
        or envelope[-1] != ""
    ):
        raise ValueError("contract envelope " + begin)
    return tuple(envelope[2:-2])


def document_marker_scope(source: str) -> str:
    lines = source.splitlines()
    specifications = (
        (
            "collection_phase_output_schema_contract_begin",
            "collection_phase_output_schema_contract_end",
            OUTPUT_SCHEMA_LINES,
        ),
        (
            "operational_collection_procedure_contract_begin",
            "operational_collection_procedure_contract_end",
            PROCEDURE_LINES,
        ),
    )
    ranges: list[tuple[int, int]] = []
    for begin, end, expected in specifications:
        actual = contract_lines(source, begin, end)
        if actual != expected:
            raise ValueError("contract byte exactness " + begin)
        ranges.append((lines.index(begin), lines.index(end)))
    if ranges[0][1] >= ranges[1][0]:
        raise ValueError("contract block order")
    scoped = [
        line
        for index, line in enumerate(lines)
        if not any(start <= index <= stop for start, stop in ranges)
    ]
    return "\n".join(scoped) + "\n"


def require_document_value(source: str, key: str, expected: str) -> None:
    try:
        actual = marker(source, key)
    except ValueError as error:
        need(False, str(error))
        return
    need(actual == expected, "document marker " + key)


def validate_document_negative_tests() -> None:
    key = "current_collection_execution_authorized"
    expected = "false"

    def synthetic_document(
        marker_lines: tuple[str, ...],
        schema_lines: tuple[str, ...] = OUTPUT_SCHEMA_LINES,
    ) -> str:
        prefix = "\n".join(marker_lines)
        if prefix:
            prefix += "\n"
        return (
            prefix
            + "collection_phase_output_schema_contract_begin\n\n~~~text\n"
            + "\n".join(schema_lines)
            + "\n~~~\n\ncollection_phase_output_schema_contract_end\n"
            + "operational_collection_procedure_contract_begin\n\n~~~text\n"
            + "\n".join(PROCEDURE_LINES)
            + "\n~~~\n\noperational_collection_procedure_contract_end\n"
        )

    def case_passes(
        marker_lines: tuple[str, ...],
        schema_lines: tuple[str, ...] = OUTPUT_SCHEMA_LINES,
    ) -> bool:
        try:
            scoped = document_marker_scope(synthetic_document(marker_lines, schema_lines))
            return marker(scoped, key) == expected
        except ValueError:
            return False

    cases = (
        ("single expected value", (key + "=false",), True),
        ("duplicate identical expected values", (key + "=false", key + "=false"), True),
        ("missing value", (), False),
        ("single wrong value", (key + "=true",), False),
        ("expected then conflicting value", (key + "=false", key + "=true"), False),
        ("conflicting then expected value", (key + "=true", key + "=false"), False),
        ("unbound then bound value", (key + "=UNBOUND", key + "=false"), False),
    )
    for label, marker_lines, expected_result in cases:
        need(case_passes(marker_lines) is expected_result, "negative test " + label)
    contract_key = "collection_execution_authorized"
    try:
        contract_scope = document_marker_scope(
            synthetic_document((contract_key + "=false",))
        )
        contract_scope_isolated = marker(contract_scope, contract_key) == "false"
    except ValueError:
        contract_scope_isolated = False
    need(contract_scope_isolated, "negative test contract type marker scope isolation")
    mutated_schema = tuple(
        contract_key + "=true" if line == contract_key + "=boolean" else line
        for line in OUTPUT_SCHEMA_LINES
    )
    need(
        not case_passes((key + "=false",), mutated_schema),
        "negative test contract block mutation",
    )


def validate_manifest_closure_items(
    files: Any,
    expected_paths: tuple[str, ...],
    blobs: dict[str, bytes],
) -> None:
    if type(files) is not list or len(files) != len(expected_paths):
        raise ValueError("MANIFEST_STRUCTURE_MISMATCH")
    if [item.get("path") if type(item) is dict else None for item in files] != list(
        expected_paths
    ):
        raise ValueError("MANIFEST_STRUCTURE_MISMATCH")
    for item, relative in zip(files, expected_paths, strict=True):
        if type(item) is not dict or set(item) != {"path", "bytes", "sha256"}:
            raise ValueError("MANIFEST_STRUCTURE_MISMATCH")
        if relative not in blobs or type(blobs[relative]) is not bytes:
            raise ValueError("MANIFEST_STRUCTURE_MISMATCH")
        content = blobs[relative]
        if type(item["bytes"]) is not int or item["bytes"] != len(content):
            raise ValueError("MANIFEST_BYTES_MISMATCH")
        expected_sha256 = hashlib.sha256(content).hexdigest()
        if type(item["sha256"]) is not str or item["sha256"] != expected_sha256:
            raise ValueError("MANIFEST_HASH_MISMATCH")


def expect_contract_error(action: Any, expected: str, label: str) -> None:
    actual = None
    try:
        action()
    except ValueError as error:
        actual = str(error)
    need(actual == expected, "synthetic negative test " + label)


def validate_successor_compatibility_synthetic_tests() -> None:
    need(
        parse_git_nul_paths(b" \0allowed \0") == [" ", "allowed "],
        "NUL path parser preserves boundary whitespace",
    )
    for payload, label in (
        (b"allowed", "missing NUL terminator"),
        (b"allowed\0allowed\0", "duplicate path"),
        (b"\xff\0", "non-UTF-8 path"),
    ):
        expect_contract_error(
            lambda value=payload: parse_git_nul_paths(value),
            "HISTORY_AMBIGUITY",
            "NUL path parser " + label,
        )
    correction_subject_bytes = COMPATIBILITY_CORRECTION_SUBJECT.encode("utf-8")
    need(
        canonical_commit_message_body(correction_subject_bytes)
        == COMPATIBILITY_CORRECTION_SUBJECT,
        "commit message no terminal LF positive control",
    )
    need(
        canonical_commit_message_body(correction_subject_bytes + b"\n")
        == COMPATIBILITY_CORRECTION_SUBJECT,
        "commit message single terminal LF positive control",
    )
    need(
        canonical_commit_message_body(b" leading boundary \n")
        == " leading boundary ",
        "commit message boundary whitespace preservation",
    )
    need(
        canonical_commit_message_body(b"\tboundary tab\t\n")
        == "\tboundary tab\t",
        "commit message boundary tab preservation",
    )
    need(
        canonical_commit_message_body(b"synthetic title\nsynthetic body\n")
        == "synthetic title\nsynthetic body",
        "commit message internal LF preservation",
    )
    for payload, expected_error, label in (
        (
            correction_subject_bytes + b"\n\n",
            "git commit message terminal newline ambiguity",
            "multiple terminal LF",
        ),
        (
            correction_subject_bytes + b"\n\n\n",
            "git commit message terminal newline ambiguity",
            "three terminal LF",
        ),
        (
            correction_subject_bytes + b"\r",
            "git commit message bytes",
            "bare CR",
        ),
        (
            correction_subject_bytes + b"\r\n",
            "git commit message bytes",
            "CRLF",
        ),
        (
            correction_subject_bytes + b"\0",
            "git commit message bytes",
            "NUL",
        ),
        (b"\xff", "git commit message UTF-8", "invalid UTF-8"),
        ):
        expect_contract_error(
            lambda value=payload: canonical_commit_message_body(value),
            expected_error,
            "commit message " + label,
        )
    central_source = text(CENTRAL)
    projection_sha256 = v4_central_projection_sha256(central_source)
    correction = HistoryRecord(
        oid="c" * 40,
        parents=(PUBLISHED_MERGE_COMMIT,),
        subject=canonical_commit_message_body(correction_subject_bytes + b"\n"),
        tree="synthetic-correction-tree",
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256=projection_sha256,
        bindings_valid=True,
    )
    for subject_bytes, label in (
        (b" " + correction_subject_bytes + b"\n", "leading whitespace"),
        (correction_subject_bytes + b" \n", "trailing whitespace"),
        (correction_subject_bytes + b"\t\n", "trailing tab"),
        (correction_subject_bytes + b" changed\n", "wrong subject"),
        (correction_subject_bytes + b"\nbody\n", "extra body"),
        (
            correction_subject_bytes + b"\n\nSigned-off-by: synthetic\n",
            "extra trailer",
        ),
    ):
        altered_subject_correction = HistoryRecord(
            **{
                **correction.__dict__,
                "oid": "subject-" + label.replace(" ", "-"),
                "subject": canonical_commit_message_body(subject_bytes),
            }
        )
        expect_contract_error(
            lambda record=altered_subject_correction: classify_postpublication_history(
                (record,)
            ),
            "UNAUTHORIZED_CLOSURE_CHANGE",
            "commit message " + label,
        )
    correction_decision = classify_postpublication_history((correction,))
    validate_history_ancestry(
        correction_decision,
        lambda ancestor, descendant: (ancestor, descendant)
        == (PUBLISHED_MERGE_COMMIT, correction.oid),
    )
    need(
        correction_decision.historical_repair == HISTORICAL_REPAIR_COMMIT,
        "positive control historical repair",
    )
    need(
        correction_decision.compatibility_correction == correction.oid
        and correction_decision.publication_merge is None
        and not correction_decision.successor_central_commits,
        "positive control compatibility correction",
    )
    need(
        working_context(
            PUBLISHED_MERGE_COMMIT,
            COMPATIBILITY_CORRECTION_BRANCH,
            CORRECTION_PATHS,
        )
        == "compatibility_correction",
        "compatibility correction dirty-worktree positive control",
    )
    publication_merge = HistoryRecord(
        oid="d" * 40,
        parents=(PUBLISHED_MERGE_COMMIT, correction.oid),
        subject=canonical_commit_message_body(
            (
                "Merge pull request #123 from pet-med-ai/"
                + COMPATIBILITY_CORRECTION_BRANCH
                + "\n\n"
                + COMPATIBILITY_CORRECTION_SUBJECT
                + "\n"
            ).encode("utf-8")
        ),
        tree=correction.tree,
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256=projection_sha256,
        bindings_valid=True,
    )
    published_correction_decision = classify_postpublication_history(
        (correction, publication_merge)
    )
    successor_dirty_context = working_context(
        publication_merge.oid,
        "pmai-p0-04-synthetic-successor",
        (CENTRAL, "scripts/validate_synthetic_successor.py"),
    )
    need(
        successor_dirty_context == "successor",
        "published successor dirty-worktree positive control",
    )
    validate_working_history_context(
        successor_dirty_context, published_correction_decision
    )
    expect_contract_error(
        lambda: working_context(
            publication_merge.oid,
            "pmai-p0-04-synthetic-successor",
            (VALIDATOR,),
        ),
        "UNAUTHORIZED_CLOSURE_CHANGE",
        "dirty successor V4 package mutation",
    )
    unpublished_successor_context = working_context(
        correction.oid,
        "pmai-p0-04-synthetic-successor",
        (CENTRAL, "scripts/validate_synthetic_successor.py"),
    )
    expect_contract_error(
        lambda: validate_working_history_context(
            unpublished_successor_context, correction_decision
        ),
        "HISTORY_AMBIGUITY",
        "dirty successor before correction publication",
    )
    ephemeral_correction_merge = HistoryRecord(
        **{
            **publication_merge.__dict__,
            "oid": "7" * 40,
            "subject": "Merge " + correction.oid + " into " + PUBLISHED_MERGE_COMMIT,
            "ephemeral_pr_test_merge": True,
        }
    )
    ephemeral_correction_decision = classify_postpublication_history(
        (correction, ephemeral_correction_merge)
    )
    need(
        ephemeral_correction_decision.publication_merge is None
        and ephemeral_correction_decision.ephemeral_pr_test_merge
        == ephemeral_correction_merge.oid
        and ephemeral_correction_decision.history_lineage == (correction.oid,),
        "ephemeral correction PR test merge positive control",
    )
    wrong_ephemeral_correction_sha = HistoryRecord(
        **{
            **ephemeral_correction_merge.__dict__,
            "oid": "8" * 40,
            "subject": "Merge " + "0" * 40 + " into " + PUBLISHED_MERGE_COMMIT,
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (correction, wrong_ephemeral_correction_sha)
        ),
        "HISTORY_AMBIGUITY",
        "ephemeral correction merge parent binding",
    )
    successor = HistoryRecord(
        oid="5" * 40,
        parents=(publication_merge.oid,),
        subject=canonical_commit_message_body(
            b"PMAI-P0-04: Synthetic successor integration\n"
        ),
        tree="synthetic-successor-tree",
        changed_paths=(CENTRAL, "scripts/synthetic_successor_validator.py"),
        second_parent_changed_paths=(),
        central_projection_sha256=projection_sha256,
        bindings_valid=True,
    )
    successor_subject_bytes = b"PMAI-P0-04: Synthetic successor integration"
    for subject_bytes, label in (
        (b"\n", "empty"),
        (b" " + successor_subject_bytes + b"\n", "leading whitespace"),
        (successor_subject_bytes + b" \n", "trailing whitespace"),
        (successor_subject_bytes + b"\t\n", "trailing tab"),
        (successor_subject_bytes + b"\nbody\n", "extra body"),
        (
            successor_subject_bytes + b"\n\nSigned-off-by: synthetic\n",
            "extra trailer",
        ),
        (successor_subject_bytes + b"\x1b\n", "control character"),
        (successor_subject_bytes + b"\xc2\x81\n", "C1 control character"),
        (
            successor_subject_bytes + b"\xe2\x80\xae\n",
            "Unicode bidi control character",
        ),
    ):
        altered_subject_successor = HistoryRecord(
            **{
                **successor.__dict__,
                "oid": "successor-subject-" + label.replace(" ", "-"),
                "subject": canonical_commit_message_body(subject_bytes),
            }
        )
        expect_contract_error(
            lambda record=altered_subject_successor: classify_postpublication_history(
                (correction, publication_merge, record)
            ),
            "HISTORY_AMBIGUITY",
            "successor commit message " + label,
        )
    successor_branch_decision = classify_postpublication_history(
        (correction, publication_merge, successor)
    )
    validate_history_ancestry(
        successor_branch_decision,
        lambda ancestor, descendant: (ancestor, descendant)
        in {
            (PUBLISHED_MERGE_COMMIT, correction.oid),
            (correction.oid, publication_merge.oid),
            (publication_merge.oid, successor.oid),
        },
    )
    need(
        successor_branch_decision.publication_merge == publication_merge.oid
        and successor_branch_decision.successor_central_commits
        == (successor.oid,),
        "LEGITIMATE_SUCCESSOR_CENTRAL_EVOLUTION_NOT_COUNTED_AS_V4_REPAIR",
    )
    expect_contract_error(
        lambda: validate_working_history_context(
            "successor", successor_branch_decision
        ),
        "HISTORY_AMBIGUITY",
        "dirty changes over pending successor",
    )
    expect_contract_error(
        lambda: validate_history_ancestry(
            successor_branch_decision,
            lambda ancestor, descendant: (ancestor, descendant)
            in {
                (PUBLISHED_MERGE_COMMIT, correction.oid),
                (correction.oid, publication_merge.oid),
            },
        ),
        "HISTORY_AMBIGUITY",
        "parallel successor ancestry",
    )
    successor_publication_merge = HistoryRecord(
        oid="6" * 40,
        parents=(publication_merge.oid, successor.oid),
        subject=canonical_commit_message_body(
            (
                "Merge pull request #124 from pet-med-ai/"
                "pmai-p0-04-synthetic-successor\n\n"
                + successor.subject
                + "\n"
            ).encode("utf-8")
        ),
        tree=successor.tree,
        changed_paths=successor.changed_paths,
        second_parent_changed_paths=(),
        central_projection_sha256=projection_sha256,
        bindings_valid=True,
    )
    ephemeral_successor_merge = HistoryRecord(
        **{
            **successor_publication_merge.__dict__,
            "oid": "9" * 40,
            "subject": "Merge " + successor.oid + " into " + publication_merge.oid,
            "ephemeral_pr_test_merge": True,
        }
    )
    ephemeral_successor_decision = classify_postpublication_history(
        (correction, publication_merge, successor, ephemeral_successor_merge)
    )
    need(
        ephemeral_successor_decision.pending_successor == successor.oid
        and not ephemeral_successor_decision.successor_publication_merges
        and ephemeral_successor_decision.ephemeral_pr_test_merge
        == ephemeral_successor_merge.oid,
        "ephemeral successor PR test merge positive control",
    )
    merged_decision = classify_postpublication_history(
        (correction, publication_merge, successor, successor_publication_merge)
    )
    validate_history_ancestry(
        merged_decision,
        lambda ancestor, descendant: (ancestor, descendant)
        in {
            (PUBLISHED_MERGE_COMMIT, correction.oid),
            (correction.oid, publication_merge.oid),
            (publication_merge.oid, successor.oid),
            (successor.oid, successor_publication_merge.oid),
        },
    )
    need(
        merged_decision.successor_publication_merges
        == (successor_publication_merge.oid,)
        and merged_decision.history_lineage[-1]
        == successor_publication_merge.oid,
        "transparent successor publication merge positive control",
    )
    unrelated_main_parent = "4" * 40
    successor_after_unrelated_main = HistoryRecord(
        **{
            **successor.__dict__,
            "oid": "a" * 40,
            "parents": (unrelated_main_parent,),
        }
    )
    merge_after_unrelated_main = HistoryRecord(
        **{
            **successor_publication_merge.__dict__,
            "oid": "b" * 40,
            "parents": (
                unrelated_main_parent,
                successor_after_unrelated_main.oid,
            ),
            "subject": (
                "Merge pull request #125 from pet-med-ai/"
                "pmai-p0-04-synthetic-successor\n\n"
                + successor_after_unrelated_main.subject
            ),
            "tree": successor_after_unrelated_main.tree,
            "changed_paths": successor_after_unrelated_main.changed_paths,
        }
    )
    unrelated_main_decision = classify_postpublication_history(
        (
            correction,
            publication_merge,
            successor_after_unrelated_main,
            merge_after_unrelated_main,
        )
    )
    validate_history_ancestry(
        unrelated_main_decision,
        lambda ancestor, descendant: (ancestor, descendant)
        in {
            (PUBLISHED_MERGE_COMMIT, correction.oid),
            (correction.oid, publication_merge.oid),
            (publication_merge.oid, successor_after_unrelated_main.oid),
            (successor_after_unrelated_main.oid, merge_after_unrelated_main.oid),
        },
    )
    need(
        unrelated_main_decision.successor_publication_merges
        == (merge_after_unrelated_main.oid,),
        "successor merge after unrelated main evolution positive control",
    )
    drifted_successor_first_parent = HistoryRecord(
        **{
            **merge_after_unrelated_main.__dict__,
            "oid": "e" * 40,
            "parents": ("0" * 40, successor_after_unrelated_main.oid),
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (
                correction,
                publication_merge,
                successor_after_unrelated_main,
                drifted_successor_first_parent,
            )
        ),
        "HISTORY_AMBIGUITY",
        "successor merge first-parent drift",
    )
    wrong_merge_subject = HistoryRecord(
        **{
            **publication_merge.__dict__,
            "oid": "synthetic-wrong-merge-subject",
            "subject": "Merge synthetic compatibility correction",
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history((correction, wrong_merge_subject)),
        "HISTORY_AMBIGUITY",
        "publication merge subject",
    )
    wrong_merge_tree = HistoryRecord(
        **{
            **publication_merge.__dict__,
            "oid": "synthetic-wrong-merge-tree",
            "tree": "synthetic-conflict-resolution-tree",
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history((correction, wrong_merge_tree)),
        "HISTORY_AMBIGUITY",
        "publication merge tree",
    )
    wrong_second_parent_diff = HistoryRecord(
        **{
            **publication_merge.__dict__,
            "oid": "synthetic-second-parent-diff",
            "second_parent_changed_paths": (CENTRAL,),
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (correction, wrong_second_parent_diff)
        ),
        "HISTORY_AMBIGUITY",
        "publication merge second-parent diff",
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (correction, publication_merge, publication_merge)
        ),
        "HISTORY_AMBIGUITY",
        "duplicate publication merge",
    )
    wrong_successor_merge_subject = HistoryRecord(
        **{
            **successor_publication_merge.__dict__,
            "oid": "synthetic-wrong-successor-merge-subject",
            "subject": "Merge synthetic successor",
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (correction, publication_merge, successor, wrong_successor_merge_subject)
        ),
        "HISTORY_AMBIGUITY",
        "successor publication merge subject",
    )
    wrong_successor_merge_paths = HistoryRecord(
        **{
            **successor_publication_merge.__dict__,
            "oid": "synthetic-wrong-successor-merge-paths",
            "changed_paths": (*successor.changed_paths, "scripts/unexpected.py"),
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (correction, publication_merge, successor, wrong_successor_merge_paths)
        ),
        "HISTORY_AMBIGUITY",
        "successor publication merge paths",
    )
    wrong_successor_second_parent_diff = HistoryRecord(
        **{
            **successor_publication_merge.__dict__,
            "oid": "synthetic-wrong-successor-second-parent-diff",
            "second_parent_changed_paths": (CENTRAL,),
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (
                correction,
                publication_merge,
                successor,
                wrong_successor_second_parent_diff,
            )
        ),
        "HISTORY_AMBIGUITY",
        "successor publication merge second-parent diff",
    )
    irrelevant_old_branch_merge = HistoryRecord(
        oid="a" * 40,
        parents=(publication_merge.oid, "b" * 40),
        subject="Merge unrelated old branch",
        tree="synthetic-unrelated-tree",
        changed_paths=("README.md",),
        second_parent_changed_paths=(CENTRAL,),
        central_projection_sha256=None,
        bindings_valid=True,
    )
    need(
        not history_record_is_relevant(irrelevant_old_branch_merge),
        "unrelated old-branch merge second-parent history ignored",
    )
    validate_ancestry_merge_orientation(
        (irrelevant_old_branch_merge,),
        lambda ancestor, descendant: (ancestor, descendant)
        == (PUBLISHED_MERGE_COMMIT, publication_merge.oid),
    )
    reversed_parent_merge = HistoryRecord(
        **{
            **irrelevant_old_branch_merge.__dict__,
            "oid": "f" * 40,
            "parents": ("0" * 40, publication_merge.oid),
            "changed_paths": (),
        }
    )
    expect_contract_error(
        lambda: validate_ancestry_merge_orientation(
            (reversed_parent_merge,), lambda _ancestor, _descendant: False
        ),
        "HISTORY_AMBIGUITY",
        "reversed protected-main merge parents",
    )
    irrelevant_octopus_merge = HistoryRecord(
        **{
            **irrelevant_old_branch_merge.__dict__,
            "oid": "1" * 40,
            "parents": (publication_merge.oid, "2" * 40, "3" * 40),
        }
    )
    validate_ancestry_merge_orientation(
        (irrelevant_octopus_merge,), lambda _ancestor, _descendant: True
    )
    need(
        not history_record_is_relevant(irrelevant_octopus_merge),
        "unrelated octopus merge ignored",
    )
    relevant_octopus_merge = HistoryRecord(
        **{
            **irrelevant_octopus_merge.__dict__,
            "oid": "2" * 40,
            "changed_paths": (CENTRAL,),
            "central_projection_sha256": projection_sha256,
        }
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (correction, publication_merge, relevant_octopus_merge)
        ),
        "HISTORY_AMBIGUITY",
        "relevant octopus merge",
    )
    successor_constants = (
        "SRBE_V5_ADAPTER_PREPARATION_EFFECTIVE_CURRENT_HOLD = "
        "'HOLD_SYNTHETIC_HELD_V5_STYLE_SUCCESSOR'\n"
        "SYNTHETIC_HELD_V5_STYLE_SANITIZED_ENV_ITEMS = "
        + repr(tuple(SANITIZED_VALIDATOR_ENV.items()))
        + "\n"
        "SYNTHETIC_HELD_V5_STYLE_VALIDATOR = "
        "'scripts/validate_synthetic_held_v5_style_validator.py'\n"
        "SYNTHETIC_HELD_V5_STYLE_VALIDATOR_SHA256 = '" + "1" * 64 + "'\n"
        "SYNTHETIC_HELD_V5_STYLE_MANIFEST = "
        "'docs/clinical_data/SYNTHETIC_HELD_V5_STYLE_PACKAGE_MANIFEST_V1.json'\n"
        "SYNTHETIC_HELD_V5_STYLE_MANIFEST_SHA256 = '" + "2" * 64 + "'\n"
        "SYNTHETIC_HELD_V5_STYLE_PASS_MARKER = "
        "'synthetic_held_v5_style=PASS'\n"
    )
    successor_hook = (
        "    synthetic_held_v5_style_validator_path = "
        "ROOT / SYNTHETIC_HELD_V5_STYLE_VALIDATOR\n"
        "    need(synthetic_held_v5_style_validator_path.is_file() and not "
        "synthetic_held_v5_style_validator_path.is_symlink(), "
        "'synthetic validator path')\n"
        "    need(hashlib.sha256(synthetic_held_v5_style_validator_path.read_bytes()).hexdigest() "
        "== SYNTHETIC_HELD_V5_STYLE_VALIDATOR_SHA256, 'synthetic validator hash')\n"
        "    synthetic_held_v5_style_manifest_path = "
        "ROOT / SYNTHETIC_HELD_V5_STYLE_MANIFEST\n"
        "    need(synthetic_held_v5_style_manifest_path.is_file() and not "
        "synthetic_held_v5_style_manifest_path.is_symlink(), "
        "'synthetic manifest path')\n"
        "    need(hashlib.sha256(synthetic_held_v5_style_manifest_path.read_bytes()).hexdigest() "
        "== SYNTHETIC_HELD_V5_STYLE_MANIFEST_SHA256, 'synthetic manifest hash')\n"
        "    synthetic_held_v5_style_result = subprocess.run([sys.executable, "
        "'-I', '-B', str(synthetic_held_v5_style_validator_path)], cwd=ROOT, "
        "env=dict(SYNTHETIC_HELD_V5_STYLE_SANITIZED_ENV_ITEMS), "
        "stdin=subprocess.DEVNULL, "
        "stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120, "
        "check=False)\n"
        "    need(synthetic_held_v5_style_result.returncode == 0, "
        "'synthetic validator exit')\n"
        "    need(synthetic_held_v5_style_result.stderr == '', "
        "'synthetic validator stderr')\n"
        "    need(synthetic_held_v5_style_result.stdout.splitlines().count("
        "SYNTHETIC_HELD_V5_STYLE_PASS_MARKER) == 1, 'synthetic marker')\n"
        "    print(SYNTHETIC_HELD_V5_STYLE_PASS_MARKER)\n"
    )
    unrelated_successor_source = central_source.replace(
        "DOC = ", successor_constants + "DOC = ", 1
    ).replace(
        "    " + CENTRAL_V4_INTEGRATION_END + "\n",
        "    " + CENTRAL_V4_INTEGRATION_END + "\n" + successor_hook,
        1,
    ).replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        '        "srbe_v5_adapter_preparation_effective_decision=" '
        "+ SRBE_V5_ADAPTER_PREPARATION_EFFECTIVE_CURRENT_HOLD,\n"
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    need(
        unrelated_successor_source != central_source
        and unrelated_successor_source.count(
            "SYNTHETIC_HELD_V5_STYLE_SANITIZED_ENV_ITEMS = "
        )
        == 1
        and unrelated_successor_source.count(
            "    synthetic_held_v5_style_result = subprocess.run("
        )
        == 1
        and unrelated_successor_source.count(
            "    print(SYNTHETIC_HELD_V5_STYLE_PASS_MARKER)\n"
        )
        == 1
        and unrelated_successor_source.count(
            '"srbe_v5_adapter_preparation_effective_decision="'
        )
        == 1,
        "held-V5-style successor fixture anchors",
    )
    need(
        v4_central_projection_sha256(unrelated_successor_source)
        == projection_sha256,
        "positive control successor projection isolation",
    )
    sensitive_output_value = (
        "data" + "base_url=" + "postgres" + "ql://redacted.invalid/example"
    )
    sensitive_successor_source = unrelated_successor_source.replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        "        "
        + repr(sensitive_output_value)
        + ",\n"
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(sensitive_successor_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "sensitive successor output",
    )
    split_sensitive_successor_source = unrelated_successor_source.replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        '        "endpoint=post" + "gresql://redacted.invalid/example",\n'
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    need(
        sensitive_material_violation(split_sensitive_successor_source) is None,
        "split sensitive output raw-source fixture",
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(split_sensitive_successor_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "split-token sensitive successor output",
    )
    sensitive_credential_value = "creden" + "tial=redacted"
    split_credential_successor_source = unrelated_successor_source.replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        "        "
        + repr(sensitive_credential_value)
        + ",\n"
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(split_credential_successor_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "sensitive credential successor output",
    )
    sensitive_key_values = (
        "credential_" + "value=plaintext",
        "auth_" + "token=plaintext",
        "connection_" + "uri=host.invalid",
        "raw_relation_" + "name=patients",
    )
    for sensitive_key_value in sensitive_key_values:
        sensitive_key_source = unrelated_successor_source.replace(
            '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
            "        "
            + repr(sensitive_key_value)
            + ",\n"
            '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
            1,
        )
        expect_contract_error(
            lambda source=sensitive_key_source: v4_central_projection_sha256(
                source
            ),
            "UNAUTHORIZED_V4_PROJECTION_CHANGE",
            "sensitive successor output key " + sensitive_key_value.split("=", 1)[0],
        )
    redacted_sensitive_output = "credential_" + "value=REDACTED"
    redacted_sensitive_source = unrelated_successor_source.replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        "        "
        + repr(redacted_sensitive_output)
        + ",\n"
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    need(
        v4_central_projection_sha256(redacted_sensitive_source)
        == projection_sha256,
        "redacted sensitive successor output positive control",
    )
    unbound_pass_output_source = unrelated_successor_source.replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        '        "synthetic_unverified=PASS",\n'
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(unbound_pass_output_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "unbound PASS output",
    )
    successor_marker_alias_source = unrelated_successor_source.replace(
        "'synthetic_held_v5_style=PASS'",
        repr(PASS_MARKER),
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(successor_marker_alias_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor marker aliases V4 marker",
    )
    successor_output_key_alias_source = unrelated_successor_source.replace(
        "SYNTHETIC_HELD_V5_STYLE", "DATABASE_WRITE"
    ).replace(
        "'synthetic_held_v5_style=PASS'", "'database_write=PASS'", 1
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(successor_output_key_alias_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor marker aliases baseline output key",
    )
    successor_without_isolation = unrelated_successor_source.replace(
        "[sys.executable, '-I', '-B', " ,
        "[sys.executable, '-B', ",
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(successor_without_isolation),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor missing isolated invocation",
    )
    successor_without_sanitized_env = unrelated_successor_source.replace(
        "env=dict(SYNTHETIC_HELD_V5_STYLE_SANITIZED_ENV_ITEMS),",
        "env={},",
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(successor_without_sanitized_env),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor missing sanitized environment",
    )
    for control_code, control_label in ((0, "NUL"), (27, "ESC")):
        control_message_source = unrelated_successor_source.replace(
            "'synthetic validator path'",
            repr("synthetic validator path" + chr(control_code)),
            1,
        )
        expect_contract_error(
            lambda source=control_message_source: v4_central_projection_sha256(
                source
            ),
            "UNAUTHORIZED_V4_PROJECTION_CHANGE",
            "successor failure message " + control_label,
        )
    sensitive_message_expression = "'client_' 'se" + "cret=redacted'"
    sensitive_message_source = unrelated_successor_source.replace(
        "'synthetic validator path'",
        sensitive_message_expression,
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(sensitive_message_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor sensitive failure message",
    )
    successor_mutable_env_source = unrelated_successor_source.replace(
        "env=dict(SYNTHETIC_HELD_V5_STYLE_SANITIZED_ENV_ITEMS),",
        "env=SYNTHETIC_HELD_V5_STYLE_SANITIZED_ENV_ITEMS,",
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(successor_mutable_env_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor mutable environment binding",
    )
    successor_list_env_source = unrelated_successor_source.replace(
        repr(tuple(SANITIZED_VALIDATOR_ENV.items())),
        repr(list(SANITIZED_VALIDATOR_ENV.items())),
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(successor_list_env_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor list environment items",
    )
    successor_path_escape_source = unrelated_successor_source.replace(
        "scripts/validate_synthetic_held_v5_style_validator.py",
        "scripts/validate_alias/../"
        + Path(VALIDATOR).name,
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(successor_path_escape_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor validator path escape",
    )
    successor_nested_path_source = unrelated_successor_source.replace(
        "scripts/validate_synthetic_held_v5_style_validator.py",
        "scripts/validate_alias/fixture.py",
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(successor_nested_path_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "successor validator nested-parent alias",
    )
    v4_marker_output_alias_source = central_source.replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        "        " + CENTRAL_V4_STEM + "_PASS_MARKER,\n"
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(v4_marker_output_alias_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "V4 marker repeated in output loop",
    )
    prefix_marker_key = PASS_MARKER.split("=", 1)[0]
    prefix_marker_key_alias_source = central_source.replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        "        "
        + repr(prefix_marker_key + "=false")
        + ",\n"
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(prefix_marker_key_alias_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "prefix marker key aliases final output key",
    )
    list_env_source, list_env_count = re.subn(
        r"(?ms)^SRBE_V4_SANITIZED_CHILD_ENV_ITEMS = \(\n(.*?)^\)\n",
        r"SRBE_V4_SANITIZED_CHILD_ENV_ITEMS = [\n\1]\n",
        central_source,
        count=1,
    )
    need(
        list_env_count == 1
        and v4_central_projection_sha256(list_env_source) != projection_sha256,
        "UNAUTHORIZED_V4_PROJECTION_CHANGE literal container type",
    )

    second_closure = HistoryRecord(
        oid="synthetic-second-closure",
        parents=(correction.oid,),
        subject="PMAI-P0-04: Synthetic second closure",
        tree="synthetic-second-closure-tree",
        changed_paths=(VALIDATOR, CENTRAL),
        second_parent_changed_paths=(),
        central_projection_sha256=projection_sha256,
        bindings_valid=True,
    )
    expect_contract_error(
        lambda: classify_postpublication_history((correction, second_closure)),
        "SECOND_REPAIR_PACKAGE_MUTATION",
        "second repair",
    )
    immutable_mutation = HistoryRecord(
        oid="synthetic-immutable-mutation",
        parents=(correction.oid,),
        subject="PMAI-P0-04: Synthetic immutable mutation",
        tree="synthetic-immutable-tree",
        changed_paths=(DOC,),
        second_parent_changed_paths=(),
        central_projection_sha256=None,
        bindings_valid=True,
    )
    expect_contract_error(
        lambda: classify_postpublication_history((correction, immutable_mutation)),
        "SECOND_REPAIR_PACKAGE_MUTATION",
        "immutable package mutation",
    )
    unauthorized_closure = HistoryRecord(
        oid="synthetic-unauthorized-closure",
        parents=(PUBLISHED_MERGE_COMMIT,),
        subject="PMAI-P0-04: Synthetic unauthorized closure",
        tree="synthetic-unauthorized-tree",
        changed_paths=(VALIDATOR,),
        second_parent_changed_paths=(),
        central_projection_sha256=None,
        bindings_valid=True,
    )
    expect_contract_error(
        lambda: classify_postpublication_history((unauthorized_closure,)),
        "UNAUTHORIZED_CLOSURE_CHANGE",
        "unauthorized closure",
    )
    ambiguous_correction = HistoryRecord(
        oid="synthetic-ambiguous-correction",
        parents=(PUBLISHED_MERGE_COMMIT, "synthetic-second-parent"),
        subject=COMPATIBILITY_CORRECTION_SUBJECT,
        tree="synthetic-ambiguous-tree",
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256=projection_sha256,
        bindings_valid=True,
    )
    expect_contract_error(
        lambda: classify_postpublication_history((ambiguous_correction,)),
        "HISTORY_AMBIGUITY",
        "history ambiguity",
    )
    projection_mutation = HistoryRecord(
        oid="synthetic-projection-mutation",
        parents=(PUBLISHED_MERGE_COMMIT,),
        subject=COMPATIBILITY_CORRECTION_SUBJECT,
        tree="synthetic-projection-tree",
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256="0" * 64,
        bindings_valid=True,
    )
    expect_contract_error(
        lambda: classify_postpublication_history((projection_mutation,)),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "unauthorized projection history",
    )
    binding_mismatch = HistoryRecord(
        oid="synthetic-binding-mismatch",
        parents=(PUBLISHED_MERGE_COMMIT,),
        subject=COMPATIBILITY_CORRECTION_SUBJECT,
        tree="synthetic-binding-mismatch-tree",
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256=projection_sha256,
        bindings_valid=False,
    )
    expect_contract_error(
        lambda: classify_postpublication_history((binding_mismatch,)),
        "MANIFEST_HASH_MISMATCH",
        "same-commit binding mismatch",
    )

    integration_block = v4_central_integration_block(central_source)
    block_without_isolation = integration_block.replace('            "-I",\n', "", 1)
    need(
        block_without_isolation != integration_block,
        "synthetic projection fixture isolation mutation",
    )
    need(
        v4_central_projection_sha256(
            central_source.replace(integration_block, block_without_isolation, 1)
        )
        != projection_sha256,
        "UNAUTHORIZED_V4_PROJECTION_CHANGE isolation",
    )
    block_without_env = integration_block.replace(
        "        env=dict(SRBE_V4_SANITIZED_CHILD_ENV_ITEMS),\n", "", 1
    )
    need(
        block_without_env != integration_block,
        "synthetic projection fixture environment mutation",
    )
    need(
        v4_central_projection_sha256(
            central_source.replace(integration_block, block_without_env, 1)
        )
        != projection_sha256,
        "UNAUTHORIZED_V4_PROJECTION_CHANGE environment",
    )
    duplicate_marker_source = central_source + CENTRAL_V4_INTEGRATION_BEGIN + "\n"
    expect_contract_error(
        lambda: v4_central_projection_sha256(duplicate_marker_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "duplicate projection marker",
    )
    nonliteral_rebind_source = central_source.replace(
        CENTRAL_V4_ENTRYPOINT,
        "SRBE_V4_SANITIZED_CHILD_ENV_ITEMS = tuple()\n"
        + CENTRAL_V4_ENTRYPOINT,
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(nonliteral_rebind_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "nonliteral owned-name rebind",
    )
    early_return_source = central_source.replace(
        "    " + CENTRAL_V4_INTEGRATION_BEGIN + "\n",
        "    if True:\n        return 0\n    "
        + CENTRAL_V4_INTEGRATION_BEGIN
        + "\n",
        1,
    )
    need(
        early_return_source != central_source,
        "synthetic projection fixture early return mutation",
    )
    need(
        v4_central_projection_sha256(early_return_source) != projection_sha256,
        "UNAUTHORIZED_V4_PROJECTION_CHANGE inactive integration block",
    )
    entrypoint_bypass_source = central_source.replace(
        CENTRAL_V4_ENTRYPOINT,
        'if __name__ == "__main__": raise SystemExit(0)',
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(entrypoint_bypass_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "entrypoint bypass",
    )
    inactive_entrypoint_source = central_source.replace(
        CENTRAL_V4_ENTRYPOINT,
        "def __name__():\n    pass\n" + CENTRAL_V4_ENTRYPOINT,
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(inactive_entrypoint_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "implicit name entrypoint bypass",
    )
    coding_cookie_source = central_source.replace(
        "#!/usr/bin/env python3\n",
        "#!/usr/bin/env python3\n# coding: utf-7\n",
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(coding_cookie_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "coding cookie parser differential",
    )
    active_safety_output = '        "database_write=false", '
    need(
        central_source.count(active_safety_output) == 1,
        "synthetic safety output fixture",
    )
    relocated_safety_source = central_source.replace(
        active_safety_output, "", 1
    ).replace(
        CENTRAL_V4_ENTRYPOINT,
        '# "database_write=false"\n' + CENTRAL_V4_ENTRYPOINT,
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(relocated_safety_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "inactive safety output relocation",
    )
    contradictory_safety_source = central_source.replace(
        active_safety_output,
        '        "database_write=true", ' + active_safety_output,
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(contradictory_safety_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "contradictory safety output",
    )
    rewritten_safety_source = central_source.replace(
        '"production_database_write=false"',
        '"production_database_write=true"',
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(rewritten_safety_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "baseline safety output rewrite",
    )
    noncanonical_output_key_source = central_source.replace(
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        '        "database_write =true",\n'
        '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(noncanonical_output_key_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "noncanonical output key alias",
    )
    for control_code, control_label in ((0, "NUL"), (27, "ESC")):
        control_output_source = central_source.replace(
            '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
            "        "
            + repr("synthetic_control=" + chr(control_code))
            + ",\n"
            '        "ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance",\n',
            1,
        )
        expect_contract_error(
            lambda source=control_output_source: v4_central_projection_sha256(
                source
            ),
            "UNAUTHORIZED_V4_PROJECTION_CHANGE",
            "control-byte output " + control_label,
        )
    prep_hook = "    v4_rebind_preparation_result = subprocess.run("
    relocated_hook_source = central_source.replace(
        prep_hook,
        "    v4_rebind_preparation_result_relocated = subprocess.run(",
        1,
    ).replace(
        CENTRAL_V4_ENTRYPOINT,
        "# " + prep_hook.strip() + "\n" + CENTRAL_V4_ENTRYPOINT,
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(relocated_hook_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "inactive predecessor hook relocation",
    )
    nested_owned_rebind_source = central_source.replace(
        CENTRAL_V4_ENTRYPOINT,
        "def synthetic_owned_rebind():\n"
        "    CURRENT_HOLD = 'synthetic-rebind'\n"
        + CENTRAL_V4_ENTRYPOINT,
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(nested_owned_rebind_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "nested owned-name rebind",
    )
    baseline_mutation_source = central_source.replace(
        "CI = 'scripts/ci_static_checks.sh'",
        "CI = 'scripts/synthetic_ci_bypass.sh'",
        1,
    )
    need(
        baseline_mutation_source != central_source
        and v4_central_projection_sha256(baseline_mutation_source)
        != projection_sha256,
        "UNAUTHORIZED_V4_PROJECTION_CHANGE baseline assignment",
    )
    helper_bypass_source = central_source.replace(
        "def need(ok, message):\n    if not ok:\n",
        "def need(ok, message):\n    if False:\n",
        1,
    )
    need(
        helper_bypass_source != central_source
        and v4_central_projection_sha256(helper_bypass_source)
        != projection_sha256,
        "UNAUTHORIZED_V4_PROJECTION_CHANGE helper bypass",
    )
    executing_annotation_source = central_source.replace(
        "CURRENT_HOLD = ",
        "CURRENT_HOLD: print('synthetic_annotation_bypass') = ",
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(executing_annotation_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "executing annotated assignment",
    )
    sensitive_assignment_source = central_source.replace(
        "DOC = ",
        "CLIENT_SECRET = 'plaintext'\nDOC = ",
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(sensitive_assignment_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "sensitive literal assignment name",
    )
    split_unused_sensitive_source = central_source.replace(
        "DOC = ",
        "UNUSED_ENDPOINT = 'post' 'gresql://redacted.invalid/example'\nDOC = ",
        1,
    )
    expect_contract_error(
        lambda: v4_central_projection_sha256(split_unused_sensitive_source),
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "split unused sensitive literal",
    )
    if "type_params" in ast.FunctionDef._fields:
        generic_main_source = central_source.replace(
            "def main():", "def main[T]():", 1
        )
        expect_contract_error(
            lambda: v4_central_projection_sha256(generic_main_source),
            "UNAUTHORIZED_V4_PROJECTION_CHANGE",
            "generic main type parameters",
        )
        generic_helper_source = central_source.replace(
            "def need(ok, message):", "def need[T](ok, message):", 1
        )
        expect_contract_error(
            lambda: v4_central_projection_sha256(generic_helper_source),
            "UNAUTHORIZED_V4_PROJECTION_CHANGE",
            "generic support function type parameters",
        )

    expect_contract_error(
        lambda: strict_manifest_json('{"files":[],"files":[]}'),
        "MANIFEST_STRUCTURE_MISMATCH",
        "manifest duplicate JSON key",
    )
    fixture_blobs = {"fixture": b"closed"}
    fixture_files = [
        {
            "path": "fixture",
            "bytes": len(fixture_blobs["fixture"]),
            "sha256": hashlib.sha256(fixture_blobs["fixture"]).hexdigest(),
        }
    ]
    validate_manifest_closure_items(fixture_files, ("fixture",), fixture_blobs)
    hash_mismatch = [dict(fixture_files[0], sha256="0" * 64)]
    expect_contract_error(
        lambda: validate_manifest_closure_items(
            hash_mismatch, ("fixture",), fixture_blobs
        ),
        "MANIFEST_HASH_MISMATCH",
        "manifest hash mismatch",
    )
    bytes_mismatch = [dict(fixture_files[0], bytes=1)]
    expect_contract_error(
        lambda: validate_manifest_closure_items(
            bytes_mismatch, ("fixture",), fixture_blobs
        ),
        "MANIFEST_BYTES_MISMATCH",
        "manifest bytes mismatch",
    )
    expect_contract_error(
        lambda: validate_manifest_closure_items([], ("fixture",), fixture_blobs),
        "MANIFEST_STRUCTURE_MISMATCH",
        "manifest structure mismatch",
    )


def run_validator(relative: str, pass_marker: str, label: str) -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(ROOT / relative)],
        cwd=ROOT,
        env=SANITIZED_VALIDATOR_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=False,
    )
    need(result.returncode == 0, label + " validator exit")
    need(result.stderr == "", label + " validator stderr")
    need(result.stdout.splitlines().count(pass_marker) == 1, label + " PASS marker")


def validate_source_anchors() -> None:
    need(git("rev-parse", BASE_COMMIT + "^{tree}") == BASE_TREE, "locked base tree")
    for relative, expected in PREP_HASHES.items():
        need(digest(relative) == expected, "preparation protected hash " + relative)
    for relative, expected in SOURCE_REVIEW_HASHES.items():
        need(digest(relative) == expected, "source review protected hash " + relative)
    candidate = safe_path(IMPLEMENTATION_CANDIDATE)
    need(digest(IMPLEMENTATION_CANDIDATE) == CANDIDATE_SHA256, "implementation candidate hash")
    need(
        not candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
        "implementation candidate executable",
    )
    collector = safe_path(PREP_PREFIX + "_COLLECTOR_CANDIDATE_V1.py.txt")
    need(
        not collector.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
        "inert collector executable",
    )
    need(not (ROOT / PLANNED_ACTIVE_RUNNER).exists(), "planned active runner path present")
    need(not list((ROOT / MIGRATIONS).glob("0010*.py")), "active 0010 migration present")
    run_validator(PREP_VALIDATOR, PREP_PASS_MARKER, "preparation")
    run_validator(SOURCE_VALIDATOR, SOURCE_PASS_MARKER, "source authorization review")


def validate_document() -> None:
    source = text(DOC)
    try:
        governed_source = document_marker_scope(source)
    except ValueError as error:
        need(False, str(error))
        return
    required = {
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "authorization_subject": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "authorization_id": AUTHORIZATION_ID,
        "stage_status": "IN_PROGRESS",
        "package_status": SUBSTAGE.removesuffix("_V1") + "_RECORD_ONLY",
        "review_status": "PROPOSED_APPROVE_FUTURE_SINGLE_USE_SRBE_COLLECTION_AND_OFFLINE_REVIEW_ACTION_ENVELOPE",
        "authorization_record_id": AUTHORIZATION_RECORD,
        "collection_execution_authorization_record_id": AUTHORIZATION_RECORD,
        "collection_execution_authorization_record_sha256": AUTHORIZATION_RECORD_SHA256,
        "authorization_record_scope": "REPOSITORY_STATIC_AUTHORIZATION_ENVELOPE_ONLY",
        "authorization_record_only": "true",
        "current_turn_scope": "REPOSITORY_ONLY_AUTHORIZATION_RECORD",
        "authorization_scope": "ONE_EXACT_V4_TARGET_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_OFFLINE_REVIEW_ACTION_ONLY",
        "current_execution_decision": "HOLD_NO_RUNTIME_COLLECTION_OR_EXTERNAL_EXECUTION",
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "source_authorization_review_pr": "19",
        "source_authorization_review_head_commit": SOURCE_HEAD,
        "source_authorization_review_merge_commit": SOURCE_MERGE,
        "source_authorization_review_tree_sha": SOURCE_TREE,
        "source_authorization_review_ci_run_id": str(SOURCE_CI_RUN_ID),
        "source_authorization_review_ci_run_number": str(SOURCE_CI_RUN_NUMBER),
        "source_authorization_review_ci_status": "PASS",
        "source_authorization_review_record_id": SOURCE_REVIEW_RECORD,
        "target_logical_name": TARGET_LOGICAL_NAME,
        "target_contract_identity_sha256": TARGET_CONTRACT_SHA256,
        "target_service_identifier_sha256": TARGET_SERVICE_SHA256,
        "restore_runner_v3_implementation_candidate_sha256": CANDIDATE_SHA256,
        "collector_contract_sha256": COLLECTOR_CONTRACT_SHA256,
        "planned_active_runner_path": PLANNED_ACTIVE_RUNNER,
        "changed_path_scope": "EXACT_9_PATHS",
        "changed_path_sequence_sha256": EXPECTED_PATH_SEQUENCE_SHA256,
        "package_path_count": "8",
        "manifest_member_count": "7",
        "manifest_self_excluded": "true",
        "collection_phase_output_schema_id": OUTPUT_SCHEMA_ID,
        "collection_phase_output_schema_hash_normalization": HASH_NORMALIZATION,
        "collection_phase_output_schema_sha256": OUTPUT_SCHEMA_SHA256,
        "operational_collection_procedure_contract_id": PROCEDURE_ID,
        "operational_collection_procedure_contract_hash_normalization": HASH_NORMALIZATION,
        "operational_collection_procedure_contract_sha256": PROCEDURE_SHA256,
        "proposed_future_action_scope": "EXACT_V4_TARGET_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_OFFLINE_REVIEW_ONLY",
        "proposed_future_target_status_required": "AVAILABLE",
        "proposed_future_target_lifecycle_max_hours": "72",
        "proposed_future_target_application_attachment_count_required": "0",
        "proposed_future_target_open_connection_count_required": "0",
        "proposed_future_initial_inbound_ip_rule_set_required": "[]",
        "proposed_future_final_inbound_ip_rule_set_required": "[]",
        "proposed_future_temporary_allowlist": "EXACT_SINGLE_OPERATOR_IPV4_CIDR_32_ONLY_IF_DATABASE_METADATA_READ_REQUIRED",
        "proposed_future_maximum_allowlist_add_save_count": "1",
        "proposed_future_maximum_allowlist_remove_save_count": "1",
        "proposed_future_target_database_scope": "READ_ONLY_IDENTITY_AND_SCHEMA_METADATA_ONLY",
        "proposed_future_output_types": "LOWERCASE_SHA256_BOOLEAN_AND_FIXED_PUBLIC_SCHEMA_ONLY",
        "decision": DECISION,
        "post_review_sole_next_subject": NEXT_SUBJECT,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in required.items():
        require_document_value(governed_source, key, expected)
    source_hash_markers = {
        "source_authorization_review_main_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + ".md"],
        "source_authorization_review_active_pointer_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_ACTIVE_POINTER_V1.json"],
        "source_authorization_review_checklist_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_CHECKLIST_V1.csv"],
        "source_authorization_review_go_no_go_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_GO_NO_GO_V1.csv"],
        "source_authorization_review_locked_baseline_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_LOCKED_BASELINE_V1.json"],
        "source_authorization_review_package_manifest_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_PACKAGE_MANIFEST_V1.json"],
        "source_authorization_review_test_matrix_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_TEST_MATRIX_V1.csv"],
        "source_authorization_review_validator_sha256": SOURCE_REVIEW_HASHES[SOURCE_VALIDATOR],
    }
    for key, expected in source_hash_markers.items():
        require_document_value(governed_source, key, expected)
    for key in UNBOUND_FIELDS:
        require_document_value(governed_source, key, "UNBOUND")
    false_fields = (
        "current_collection_execution_authorized",
        "current_external_execution_authorized",
        "current_runtime_evidence_collection_authorized",
        "post_effective_gate_collection_execution_authorized",
        "one_time_action_confirmation_present",
        "authorization_reuse_allowed",
        "target_contract_hash_may_substitute_runtime_identity",
        "target_service_hash_may_substitute_runtime_identity",
        "target_live_metadata_revalidation",
        "planned_active_runner_path_present",
        "active_0010_migration_present",
        "runtime_evidence_collected",
        "srbe_collection_evidence_complete",
        "runtime_binding_contract_complete",
        "evidence_complete",
        "collection_execution_authorized",
        "runtime_evidence_collection_authorized",
        "external_execution_authorized",
        "operational_collection_procedure_contract_executable",
        "operational_collection_adapter_creation",
        "operational_collection_adapter_present",
        "actual_collection_execution_authorized",
        "actual_runtime_evidence_collection_authorized",
        "actual_external_execution_authorized",
    )
    true_fields = (
        "authorization_scope_recorded",
        "post_effective_gate_collection_execution_eligible",
        "separate_action_time_confirmation_required",
        "authorization_single_use",
        "target_hashes_are_sanitized_provenance_only",
        "target_live_revalidation_required_at_action_time",
        "define_hash_locked_collection_phase_output_schema",
        "collection_phase_output_schema_defined",
        "collection_phase_output_schema_hash_locked",
        "collection_phase_successor_activation_authorization_may_remain_unbound",
        "collection_phase_expected_active_source_may_remain_unbound",
        "collection_phase_schema_must_not_claim_runtime_binding_complete",
        "define_hash_locked_operational_collection_procedure_contract",
        "operational_collection_procedure_contract_defined",
        "operational_collection_procedure_contract_reviewed",
        "operational_collection_procedure_contract_hash_locked",
        "operational_collection_procedure_contract_available",
        "inert_collector_may_not_be_represented_as_live_adapter",
        "action_time_confirmation_must_name_reviewed_procedure_contract_sha256",
        "proposed_future_render_target_info_apps_network_readonly_revalidation",
        "proposed_future_public_external_access_blocked_required",
        "proposed_future_cleanup_required_on_success_failure_or_ambiguity",
    )
    for key in false_fields:
        require_document_value(governed_source, key, "false")
    for key in true_fields:
        require_document_value(governed_source, key, "true")
    for key in EXECUTION_FALSE_FIELDS:
        require_document_value(governed_source, key, "false")
    need(contract_sha256(OUTPUT_SCHEMA_LINES) == OUTPUT_SCHEMA_SHA256, "validator output schema hash")
    need(contract_sha256(PROCEDURE_LINES) == PROCEDURE_SHA256, "validator procedure hash")
    need(
        contract_lines(
            source,
            "collection_phase_output_schema_contract_begin",
            "collection_phase_output_schema_contract_end",
        )
        == OUTPUT_SCHEMA_LINES,
        "document exact collection phase output schema block",
    )
    need(
        contract_lines(
            source,
            "operational_collection_procedure_contract_begin",
            "operational_collection_procedure_contract_end",
        )
        == PROCEDURE_LINES,
        "document exact operational collection procedure block",
    )


def validate_baseline_and_pointer() -> None:
    baseline = read_json(BASELINE)
    top_required: dict[str, Any] = {
        "schema": "PMAI_P0_04_" + SUBSTAGE + "_LOCKED_BASELINE_V1",
        "stage_id": STAGE_ID,
        "authorization_subject": SUBSTAGE,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "authorization_record_id": AUTHORIZATION_RECORD,
        "collection_execution_authorization_record_id": AUTHORIZATION_RECORD,
        "collection_execution_authorization_record_sha256": AUTHORIZATION_RECORD_SHA256,
        "stage_status": "IN_PROGRESS",
        "package_status": SUBSTAGE.removesuffix("_V1") + "_RECORD_ONLY",
        "review_status": "PROPOSED_APPROVE_FUTURE_SINGLE_USE_SRBE_COLLECTION_AND_OFFLINE_REVIEW_ACTION_ENVELOPE",
        "authorization_record_scope": "REPOSITORY_STATIC_AUTHORIZATION_ENVELOPE_ONLY",
        "authorization_record_only": True,
        "current_execution_decision": "HOLD_NO_RUNTIME_COLLECTION_OR_EXTERNAL_EXECUTION",
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "actual_collection_execution_authorized": False,
        "actual_runtime_evidence_collection_authorized": False,
        "actual_external_execution_authorized": False,
        "decision": DECISION,
        "post_review_sole_next_subject": NEXT_SUBJECT,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in top_required.items():
        need(type(baseline.get(key)) is type(expected) and baseline.get(key) == expected, "baseline " + key)
    envelope = baseline["authorization_envelope"]
    envelope_required: dict[str, Any] = {
        "authorization_id": AUTHORIZATION_ID,
        "authorization_single_use": True,
        "authorization_scope": "ONE_EXACT_V4_TARGET_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_OFFLINE_REVIEW_ACTION_ONLY",
        "authorization_scope_recorded": True,
        "risk_lane": "YELLOW_REPOSITORY_ONLY",
        "changed_path_scope": "EXACT_9_PATHS",
        "changed_path_sequence_sha256": EXPECTED_PATH_SEQUENCE_SHA256,
        "maximum_changed_path_count": 9,
        "maximum_new_file_count": 8,
        "maximum_existing_file_modification_count": 1,
        "package_path_count": 8,
        "manifest_member_count": 7,
        "manifest_self_excluded": True,
        "current_collection_execution_authorized": False,
        "current_external_execution_authorized": False,
        "current_runtime_evidence_collection_authorized": False,
        "post_effective_gate_collection_execution_eligible": True,
        "post_effective_gate_collection_execution_authorized": False,
        "separate_action_time_confirmation_required": True,
        "one_time_action_confirmation_present": False,
        "current_collection_attempts_authorized": 0,
        "post_confirmation_collection_attempts_authorized": 1,
        "collection_attempts_consumed": 0,
        "authorization_reuse_allowed": False,
    }
    for key, expected in envelope_required.items():
        need(type(envelope.get(key)) is type(expected) and envelope.get(key) == expected, "baseline envelope " + key)
    source = baseline["source_authorization_review"]
    source_required: dict[str, Any] = {
        "pull_request": 19,
        "head_commit": SOURCE_HEAD,
        "merge_commit": SOURCE_MERGE,
        "tree_sha": SOURCE_TREE,
        "ci_run_id": SOURCE_CI_RUN_ID,
        "ci_run_number": SOURCE_CI_RUN_NUMBER,
        "ci_status": "PASS",
        "authorization_review_record_id": SOURCE_REVIEW_RECORD,
        "main_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + ".md"],
        "active_pointer_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_ACTIVE_POINTER_V1.json"],
        "checklist_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_CHECKLIST_V1.csv"],
        "go_no_go_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_GO_NO_GO_V1.csv"],
        "locked_baseline_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_LOCKED_BASELINE_V1.json"],
        "package_manifest_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_PACKAGE_MANIFEST_V1.json"],
        "test_matrix_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_TEST_MATRIX_V1.csv"],
        "validator_sha256": SOURCE_REVIEW_HASHES[SOURCE_VALIDATOR],
        "package_files_byte_exact": True,
        "historical_files_byte_exact": True,
    }
    for key, expected in source_required.items():
        need(type(source.get(key)) is type(expected) and source.get(key) == expected, "baseline source " + key)
    static = baseline["static_provenance"]
    static_required: dict[str, Any] = {
        "target_logical_name": TARGET_LOGICAL_NAME,
        "target_contract_identity_sha256": TARGET_CONTRACT_SHA256,
        "target_service_identifier_sha256": TARGET_SERVICE_SHA256,
        "target_hashes_are_sanitized_provenance_only": True,
        "target_live_metadata_revalidation": False,
        "target_live_revalidation_required_at_action_time": True,
        "implementation_candidate_sha256": CANDIDATE_SHA256,
        "collector_contract_sha256": COLLECTOR_CONTRACT_SHA256,
        "planned_active_runner_path": PLANNED_ACTIVE_RUNNER,
        "planned_active_runner_path_present": False,
        "active_0010_migration_present": False,
    }
    for key, expected in static_required.items():
        need(type(static.get(key)) is type(expected) and static.get(key) == expected, "baseline static " + key)
    runtime = baseline["runtime_binding_state"]
    for key in UNBOUND_FIELDS:
        need(runtime.get(key) == "UNBOUND", "baseline unbound " + key)
    need(runtime.get("collection_execution_authorization_record_id") == AUTHORIZATION_RECORD, "baseline runtime record ID")
    need(runtime.get("collection_execution_authorization_record_sha256") == AUTHORIZATION_RECORD_SHA256, "baseline runtime record hash")
    for key in (
        "runtime_binding_contract_complete",
        "collection_execution_authorized",
        "runtime_evidence_collection_authorized",
        "runtime_evidence_collected",
        "srbe_collection_evidence_complete",
        "evidence_complete",
        "external_execution_authorized",
    ):
        need(runtime.get(key) is False, "baseline runtime false " + key)
    contract = baseline["collection_phase_contract"]
    contract_required: dict[str, Any] = {
        "define_hash_locked_collection_phase_output_schema": True,
        "collection_phase_output_schema_defined": True,
        "collection_phase_output_schema_hash_locked": True,
        "collection_phase_output_schema_id": OUTPUT_SCHEMA_ID,
        "collection_phase_output_schema_hash_normalization": HASH_NORMALIZATION,
        "collection_phase_output_schema_sha256": OUTPUT_SCHEMA_SHA256,
        "collection_phase_successor_activation_authorization_may_remain_unbound": True,
        "collection_phase_expected_active_source_may_remain_unbound": True,
        "collection_phase_schema_must_not_claim_runtime_binding_complete": True,
        "collection_phase_dynamic_output_types": "LOWERCASE_SHA256_BOOLEAN_AND_FIXED_PUBLIC_SCHEMA_ONLY",
        "define_hash_locked_operational_collection_procedure_contract": True,
        "operational_collection_procedure_contract_defined": True,
        "operational_collection_procedure_contract_id": PROCEDURE_ID,
        "operational_collection_procedure_contract_hash_normalization": HASH_NORMALIZATION,
        "operational_collection_procedure_contract_sha256": PROCEDURE_SHA256,
        "operational_collection_procedure_contract_reviewed": True,
        "operational_collection_procedure_contract_hash_locked": True,
        "operational_collection_procedure_contract_available": True,
        "operational_collection_procedure_contract_executable": False,
        "operational_collection_adapter_creation": False,
        "operational_collection_adapter_present": False,
        "inert_collector_may_not_be_represented_as_live_adapter": True,
        "action_time_confirmation_must_name_reviewed_procedure_contract_sha256": True,
    }
    for key, expected in contract_required.items():
        need(type(contract.get(key)) is type(expected) and contract.get(key) == expected, "baseline collection contract " + key)
    need(all(value is False for value in baseline["live_observation_state"].values()), "baseline live observation state")
    for key in EXECUTION_FALSE_FIELDS:
        need(baseline["execution_boundaries"].get(key) is False, "baseline execution false " + key)
    post = baseline["post_effective_boundary"]
    need(post["collection_execution_eligible"] is True, "baseline post eligibility")
    need(post["collection_execution_authorized"] is False, "baseline post authorization")
    need(post["separate_action_time_confirmation_required"] is True, "baseline post confirmation")
    need(post["one_time_action_confirmation_present"] is False, "baseline post confirmation absent")
    need(post["post_confirmation_collection_attempts_authorized"] == 1, "baseline post attempt limit")
    need(post["authorization_reuse_allowed"] is False, "baseline post reuse")

    pointer = read_json(POINTER)
    pointer_required: dict[str, Any] = {
        "schema": "PMAI_P0_04_" + SUBSTAGE + "_ACTIVE_POINTER_V1",
        "stage_id": STAGE_ID,
        "authorization_subject": SUBSTAGE,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "authorization_record_id": AUTHORIZATION_RECORD,
        "pointer_version": 1,
        "supersedes_pointer_sha256": SOURCE_REVIEW_HASHES[SOURCE_PREFIX + "_ACTIVE_POINTER_V1.json"],
        "active_locked_baseline_sha256": digest(BASELINE),
        "source_authorization_review_merge_commit": SOURCE_MERGE,
        "source_authorization_review_tree_sha": SOURCE_TREE,
        "source_authorization_review_ci_run_number": SOURCE_CI_RUN_NUMBER,
        "source_authorization_review_ci_status": "PASS",
        "collection_execution_authorization_record_id": AUTHORIZATION_RECORD,
        "collection_execution_authorization_record_sha256": AUTHORIZATION_RECORD_SHA256,
        "target_contract_identity_sha256": TARGET_CONTRACT_SHA256,
        "target_service_identifier_sha256": TARGET_SERVICE_SHA256,
        "implementation_candidate_sha256": CANDIDATE_SHA256,
        "collector_contract_sha256": COLLECTOR_CONTRACT_SHA256,
        "collection_phase_output_schema_id": OUTPUT_SCHEMA_ID,
        "collection_phase_output_schema_sha256": OUTPUT_SCHEMA_SHA256,
        "collection_phase_output_schema_defined": True,
        "collection_phase_output_schema_hash_locked": True,
        "operational_collection_procedure_contract_id": PROCEDURE_ID,
        "operational_collection_procedure_contract_sha256": PROCEDURE_SHA256,
        "operational_collection_procedure_contract_defined": True,
        "operational_collection_procedure_contract_reviewed": True,
        "operational_collection_procedure_contract_hash_locked": True,
        "operational_collection_procedure_contract_available": True,
        "operational_collection_procedure_contract_executable": False,
        "operational_collection_adapter_creation": False,
        "operational_collection_adapter_present": False,
        "action_time_confirmation_must_name_reviewed_procedure_contract_sha256": True,
        "runtime_binding_contract_complete": False,
        "runtime_evidence_collected": False,
        "srbe_collection_evidence_complete": False,
        "evidence_complete": False,
        "current_collection_execution_authorized": False,
        "current_runtime_evidence_collection_authorized": False,
        "current_external_execution_authorized": False,
        "post_effective_gate_collection_execution_eligible": True,
        "post_effective_gate_collection_execution_authorized": False,
        "separate_action_time_confirmation_required": True,
        "one_time_action_confirmation_present": False,
        "current_collection_attempts_authorized": 0,
        "post_confirmation_collection_attempts_authorized": 1,
        "collection_attempts_consumed": 0,
        "authorization_reuse_allowed": False,
        "target_live_metadata_revalidation": False,
        "planned_active_runner_path_present": False,
        "active_0010_migration_present": False,
        "current_execution_decision": "HOLD_NO_RUNTIME_COLLECTION_OR_EXTERNAL_EXECUTION",
        "decision": DECISION,
        "post_review_sole_next_subject": NEXT_SUBJECT,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in pointer_required.items():
        need(type(pointer.get(key)) is type(expected) and pointer.get(key) == expected, "pointer " + key)
    for key in UNBOUND_FIELDS:
        need(pointer.get(key) == "UNBOUND", "pointer unbound " + key)


def validate_csvs() -> None:
    checklist = rows(
        CHECKLIST,
        ["control_id", "control", "expected", "current", "status", "evidence_source", "hard_stop_if"],
    )
    gates = rows(
        GO_NO_GO,
        ["gate_id", "gate", "required", "current", "status", "decision_if_failed"],
    )
    tests = rows(
        TEST_MATRIX,
        ["test_id", "scenario", "method", "expected", "status", "decision_if_failed"],
    )
    prefix = "PMAI-P0-04-ARR-V3-SRBE-V4-EXEC-AUTH-"
    need([row["control_id"] for row in checklist] == [prefix + f"{index:03d}" for index in range(1, 134)], "checklist IDs")
    need(all(row["status"] == "PASS" for row in checklist), "checklist status")
    need(all(row["expected"] == row["current"] for row in checklist), "checklist expected/current")
    controls = {row["control"]: row for row in checklist}
    need(len(controls) == len(checklist), "checklist unique controls")
    control_expected = {
        "collection_execution_authorization_record_id": AUTHORIZATION_RECORD,
        "collection_execution_authorization_record_sha256": AUTHORIZATION_RECORD_SHA256,
        "current_collection_execution_authorized": "false",
        "post_effective_gate_collection_execution_eligible": "true",
        "post_effective_gate_collection_execution_authorized": "false",
        "collection_phase_output_schema_sha256": OUTPUT_SCHEMA_SHA256,
        "operational_collection_procedure_contract_sha256": PROCEDURE_SHA256,
        "operational_collection_procedure_contract_defined": "true",
        "operational_collection_procedure_contract_reviewed": "true",
        "operational_collection_procedure_contract_hash_locked": "true",
        "operational_collection_procedure_contract_available": "true",
        "operational_collection_adapter_creation": "false",
        "operational_collection_adapter_present": "false",
        "action_time_reviewed_procedure_contract_sha256": "UNBOUND",
        "planned_active_runner_path_present": "false",
        "active_0010_migration_present": "false",
        "current_execution_decision": "HOLD_NO_RUNTIME_COLLECTION_OR_EXTERNAL_EXECUTION",
        "next_action": "REQUEST_SEPARATE_ONE_TIME_ACTION_CONFIRMATION_NAMING_HASH_LOCKED_OPERATIONAL_PROCEDURE",
    }
    for control, expected in control_expected.items():
        need(control in controls and controls[control]["current"] == expected, "checklist control " + control)
    need([row["gate_id"] for row in gates] == [prefix + f"G{index:03d}" for index in range(1, 68)], "Go/No-Go IDs")
    need({row["status"] for row in gates} <= {"PASS", "HOLD"}, "Go/No-Go status")
    need(
        {row["decision_if_failed"] for row in gates}
        <= {
            "HOLD",
            "CLEANUP_AND_STOP",
            "SEPARATE_ACTION_TIME_CONFIRMATION_REQUIRED",
            "SEPARATE_HASH_NAMING_CONFIRMATION_REQUIRED",
            "WAIT_FOR_ONE_TIME_CONFIRMATION",
        },
        "Go/No-Go failure decisions",
    )
    need([row["test_id"] for row in tests] == [prefix + f"T{index:03d}" for index in range(1, 102)], "test IDs")
    need(all(row["status"] == "DESIGNED" for row in tests), "test status")
    need({row["expected"] for row in tests} <= {"ACCEPT", "PASS", "HOLD", "HOLD_CURRENT_BUT_ELIGIBLE_POST_EFFECTIVE"}, "test expected enum")
    need({row["decision_if_failed"] for row in tests} <= {"HOLD", "CLEANUP_AND_HOLD"}, "test failure decisions")


def validate_manifest() -> None:
    try:
        manifest = strict_manifest_json(text(MANIFEST))
    except ValueError as error:
        need(False, str(error))
        return
    need(type(manifest) is dict, "manifest JSON object")
    expected_keys = {
        "schema", "stage_id", "substage", "work_bundle",
        "collection_execution_authorization_record_id", "repository", "base_branch",
        "base_commit", "base_tree_sha", "head_branch", "authorized_changed_path_count",
        "authorized_changed_path_sequence_sha256", "package_path_count",
        "manifest_member_count", "manifest_self_excluded", "central_integration_path",
        "ci_entrypoint_changed", "github_workflow_changed", "smoke_entrypoint_changed", "files",
    }
    need(set(manifest) == expected_keys, "manifest exact schema")
    metadata: dict[str, Any] = {
        "schema": "PMAI_P0_04_" + SUBSTAGE + "_PACKAGE_MANIFEST_V1",
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "collection_execution_authorization_record_id": AUTHORIZATION_RECORD,
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "authorized_changed_path_count": 9,
        "authorized_changed_path_sequence_sha256": EXPECTED_PATH_SEQUENCE_SHA256,
        "package_path_count": 8,
        "manifest_member_count": 7,
        "manifest_self_excluded": True,
        "central_integration_path": CENTRAL,
        "ci_entrypoint_changed": False,
        "github_workflow_changed": False,
        "smoke_entrypoint_changed": False,
    }
    for key, expected in metadata.items():
        need(type(manifest.get(key)) is type(expected) and manifest.get(key) == expected, "manifest " + key)
    files = manifest["files"]
    blobs = {relative: safe_path(relative).read_bytes() for relative in MANIFEST_MEMBERS}
    try:
        validate_manifest_closure_items(files, MANIFEST_MEMBERS, blobs)
    except ValueError as error:
        need(False, str(error))
        return
    need(MANIFEST not in {item["path"] for item in files}, "manifest self exclusion")
    need(CENTRAL not in {item["path"] for item in files}, "central manifest exclusion")


def validate_central() -> None:
    source = text(CENTRAL)
    try:
        assignments = unique_literal_assignments(
            source, CENTRAL_V4_OWNED_ASSIGNMENTS
        )
    except ValueError as error:
        need(False, str(error))
        return
    stem = CENTRAL_V4_STEM
    expected = {
        "CURRENT_HOLD": LEGACY_CURRENT_HOLD,
        "CURRENT_COMPLETENESS": LEGACY_CURRENT_COMPLETENESS,
        "CURRENT_NEXT_STEP": LEGACY_CURRENT_NEXT,
        "EFFECTIVE_CURRENT_HOLD": PREP_EFFECTIVE_HOLD,
        "EFFECTIVE_CURRENT_COMPLETENESS": PREP_EFFECTIVE_COMPLETENESS,
        "EFFECTIVE_CURRENT_NEXT_STEP": PREP_EFFECTIVE_NEXT,
        "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_HOLD": REVIEW_EFFECTIVE_HOLD,
        "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_COMPLETENESS": REVIEW_EFFECTIVE_COMPLETENESS,
        "AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_NEXT_STEP": REVIEW_EFFECTIVE_NEXT,
        "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_HOLD": EXEC_EFFECTIVE_HOLD,
        "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_COMPLETENESS": EXEC_EFFECTIVE_COMPLETENESS,
        "SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_NEXT_STEP": EXEC_EFFECTIVE_NEXT,
        stem + "_VALIDATOR": VALIDATOR,
        stem + "_VALIDATOR_SHA256": digest(VALIDATOR),
        stem + "_MANIFEST": MANIFEST,
        stem + "_MANIFEST_SHA256": digest(MANIFEST),
        stem + "_PASS_MARKER": PASS_MARKER,
        "SRBE_V4_SANITIZED_CHILD_ENV_ITEMS": tuple(
            SANITIZED_VALIDATOR_ENV.items()
        ),
    }
    for key, expected_value in expected.items():
        need(assignments.get(key) == expected_value, "central constant " + key)
    try:
        integration_block = v4_central_integration_block(source)
    except ValueError as error:
        need(False, str(error))
        return
    isolated_command = (
        "        [\n"
        "            sys.executable,\n"
        "            \"-I\",\n"
        "            \"-B\",\n"
        "            str(srbe_v4_execution_authorization_validator_path),\n"
        "        ],\n"
    )
    need(integration_block.count(isolated_command) == 1, "execution authorization isolated command")
    need(
        integration_block.count(
            "        env=dict(SRBE_V4_SANITIZED_CHILD_ENV_ITEMS),\n"
        )
        == 1,
        "execution authorization sanitized environment",
    )
    try:
        projection_sha256 = v4_central_projection_sha256(source)
    except ValueError as error:
        need(False, str(error))
        return
    need(
        projection_sha256 == CENTRAL_V4_OWNED_PROJECTION_SHA256,
        "central V4-owned projection hash",
    )


def sensitive_material_violation(source: str) -> str | None:
    forbidden = (
        ("external URL", r"(?i)\bhttps?://"),
        ("database URI", r"(?i)\bpostgres(?:ql)?://"),
        ("raw provider identifier", r"(?i)\b(?:dpg|srv)-[a-z0-9]{6,}\b"),
        (
            "email address",
            r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        ),
        (
            "credential assignment",
            r"(?i)\b(?:password|secret|database_url|access_token|credential|"
            r"connection_value|connection_string|api_key|relation_name|dsn|"
            r"private_key)\s*[:=]\s*[^\s,}\]]+",
        ),
    )
    for label, pattern in forbidden:
        if re.search(pattern, source) is not None:
            return label
    return None


def validate_no_sensitive_material() -> None:
    combined = "\n".join(text(relative) for relative in PACKAGE_PATHS)
    combined += "\n" + text(CENTRAL)
    violation = sensitive_material_violation(combined)
    need(violation is None, "forbidden " + str(violation))


def main() -> int:
    for relative in PACKAGE_PATHS:
        safe_path(relative)
    need(
        list(EXPECTED_CHANGED_PATHS)
        == sorted(EXPECTED_CHANGED_PATHS, key=lambda value: value.encode("utf-8")),
        "changed path sort",
    )
    need(path_sequence_sha256(EXPECTED_CHANGED_PATHS) == EXPECTED_PATH_SEQUENCE_SHA256, "changed path sequence hash")
    need(
        path_sequence_sha256(AUTHORIZED_CORRECTION_PATHS)
        == COMPATIBILITY_CORRECTION_PATH_SEQUENCE_SHA256,
        "compatibility correction path sequence hash",
    )
    need(
        list(CORRECTION_PATHS)
        == sorted(CORRECTION_PATHS, key=lambda value: value.encode("utf-8")),
        "compatibility correction Git path sort",
    )
    expected_modes = {VALIDATOR: 0o644, MANIFEST: 0o644, CENTRAL: 0o755}
    for relative, expected_mode in expected_modes.items():
        need(
            stat.S_IMODE(safe_path(relative).stat().st_mode) == expected_mode,
            "file mode " + relative,
        )
    validate_repository_history()
    validate_source_anchors()
    validate_document_negative_tests()
    validate_successor_compatibility_synthetic_tests()
    validate_document()
    validate_baseline_and_pointer()
    validate_csvs()
    validate_manifest()
    validate_central()
    validate_no_sensitive_material()
    print(PASS_MARKER)
    print("stage_id=" + STAGE_ID)
    print("work_bundle=" + WORK_BUNDLE)
    print("source_authorization_review_pr=19")
    print("source_authorization_review_merge_commit=" + SOURCE_MERGE)
    print("source_authorization_review_ci_run_number=226")
    print("collection_execution_authorization_record_id=" + AUTHORIZATION_RECORD)
    print("authorization_record_only=true")
    print("current_execution_decision=HOLD_NO_RUNTIME_COLLECTION_OR_EXTERNAL_EXECUTION")
    print("successor_activation_authorization_record_id=UNBOUND")
    print("expected_active_source_sha256=UNBOUND")
    print("expected_target_identity_sha256=UNBOUND")
    print("expected_schema_manifest_sha256=UNBOUND")
    print("collection_phase_output_schema_sha256=" + OUTPUT_SCHEMA_SHA256)
    print("operational_collection_procedure_contract_sha256=" + PROCEDURE_SHA256)
    print("operational_collection_procedure_contract_hash_locked=true")
    print("operational_collection_adapter_present=false")
    print("current_collection_execution_authorized=false")
    print("current_runtime_evidence_collection_authorized=false")
    print("current_external_execution_authorized=false")
    print("post_effective_gate_collection_execution_eligible=true")
    print("post_effective_gate_collection_execution_authorized=false")
    print("one_time_action_confirmation_present=false")
    print("runtime_binding_contract_complete=false")
    print("runtime_evidence_collected=false")
    print("srbe_collection_evidence_complete=false")
    print("evidence_complete=false")
    print("planned_active_runner_path_present=false")
    print("active_0010_migration_present=false")
    print("render_readonly_access=false")
    print("database_connection=false")
    print("runner_creation=false")
    print("runner_execution=false")
    print("restore_execution=false")
    print("migration_creation_or_execution=false")
    print("deployment=false")
    print("decision=" + DECISION)
    print("post_review_sole_next_subject=" + NEXT_SUBJECT)
    print("sole_next_subject=" + NEXT_SUBJECT)
    print(FINAL_PASS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
