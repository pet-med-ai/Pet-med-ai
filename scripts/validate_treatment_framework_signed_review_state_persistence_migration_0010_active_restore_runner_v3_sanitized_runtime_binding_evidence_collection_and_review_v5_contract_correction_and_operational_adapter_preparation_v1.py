#!/usr/bin/env python3
"""Fail-closed validator for the PMAI-P0-04 V5 SRBE adapter package."""
from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Mapping, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
GIT_EXECUTABLE_CANDIDATES = (Path("/usr/local/bin/git"), Path("/usr/bin/git"))
GIT_EXECUTABLE = next(
    (candidate for candidate in GIT_EXECUTABLE_CANDIDATES if candidate.is_file()),
    Path("/nonexistent/pmai-git"),
)
SAFE_PATH = "/usr/local/bin:/usr/bin:/bin"
BASE_COMMIT = "19327dd0c1c5141d391716d6844f230ec35efa6a"
BASE_TREE = "1c1a4cd8053b47107d47a9df3b281d1bac487e78"
BASE_PARENTS = (
    "de93b4623e812a911445a4370dea40ec56b2098f",
    "74ba74b2200870b0833e6f657b2f212747781ad6",
)
SOURCE_PULL_REQUEST = 21
SOURCE_CI_RUN_ID = 33245499297
SOURCE_CI_RUN_NUMBER = 230
SOURCE_CI_EVENT = "push"
SOURCE_CI_ATTEMPT = 1
SOURCE_CI_STATUS = "completed"
SOURCE_CI_CONCLUSION = "success"
HEAD_BRANCH = "pmai-p0-04-arr-v3-srbe-v5-operational-adapter-prep-v2"
COMMIT_MESSAGE = "PMAI-P0-04: Rebuild V5 SRBE operational adapter"
INTRODUCTION_COMMIT = "6bbb5dfc9b00772f7225a6a18840da23b15ae778"
INTRODUCTION_TREE = "0ff211b1920d527c81aef0769b9eb06d03c8051e"
PUBLISHED_MERGE_COMMIT = "697a134ae025f62685d0a746a18ed1d1e1d1680e"
PUBLISHED_MERGE_TREE = "0ff211b1920d527c81aef0769b9eb06d03c8051e"
PUBLISHED_MERGE_PARENTS = (BASE_COMMIT, INTRODUCTION_COMMIT)
COMPATIBILITY_CORRECTION_BRANCH = (
    "pmai-p0-04-v5-validator-successor-compat-correction"
)
COMPATIBILITY_CORRECTION_SUBJECT = (
    "PMAI-P0-04: Correct V5 validator successor compatibility"
)
COMPATIBILITY_CORRECTION_AUTHORIZATION_ID = (
    "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_SRBE_V5_VALIDATOR_SUCCESSOR_"
    "COMPATIBILITY_EXACT_3_PATH_REPOSITORY_PATCH_CONTROLLED_EXECUTION_V1"
)
COMPATIBILITY_CORRECTION_AUTHORIZATION_ID_SHA256 = (
    "e38fe1e08dfc488d46157c0ec89636a2a1723868c72b50be773dd71bb0fb649e"
)
COMPATIBILITY_CORRECTION_PATH_SEQUENCE_SHA256 = (
    "14e69395d27385eb7521b01c3f807ee3bf443b0dba1d87ee67dc854af7e65bba"
)
FIRST_COMPATIBILITY_CORRECTION_COMMIT = (
    "00fcbba251e2b82337af8d094d16df76a8452a00"
)
FIRST_COMPATIBILITY_CORRECTION_TREE = (
    "84ff95f60be932247e369d28e40fc651f7aac9ae"
)
FIRST_COMPATIBILITY_PUBLICATION_MERGE = (
    "82779197c3a4e0f8500cdf36b491e24ff9bb5033"
)
FIRST_COMPATIBILITY_PUBLICATION_TREE = (
    "84ff95f60be932247e369d28e40fc651f7aac9ae"
)
FIRST_COMPATIBILITY_PUBLICATION_PARENTS = (
    PUBLISHED_MERGE_COMMIT,
    FIRST_COMPATIBILITY_CORRECTION_COMMIT,
)
FIRST_COMPATIBILITY_VALIDATOR_SHA256 = (
    "d8778ac4c81094c28b661fd79cef4d0cb7389bcd9104b50abc005141cdfda8fe"
)
FIRST_COMPATIBILITY_MANIFEST_SHA256 = (
    "c45b1980897d5a0171a16e5234e48c62205b40122e0da5e71b02177758c39480"
)
FIRST_COMPATIBILITY_CENTRAL_SHA256 = (
    "cb96bad8a9aebea3a4263d8e9757eb905e0fda42bc95ff4c95b4ddc7021e9b96"
)
DISCIPLINE_CORRECTION_BRANCH = (
    "pmai-p0-04-v5-validator-successor-precommit-discipline-correction"
)
DISCIPLINE_CORRECTION_SUBJECT = (
    "PMAI-P0-04: Correct V5 successor precommit discipline"
)
DISCIPLINE_CORRECTION_AUTHORIZATION_ID = (
    "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_SRBE_V5_VALIDATOR_SUCCESSOR_"
    "PRECOMMIT_DIRTY_WORKTREE_DISCIPLINE_COMPATIBILITY_CORRECTION_EXACT_"
    "3_PATH_REPOSITORY_PATCH_CONTROLLED_EXECUTION_V1"
)
DISCIPLINE_CORRECTION_AUTHORIZATION_ID_SHA256 = (
    "da0e774bf0711edc5885403af5e2c6f6dae875309298ce6c9557baa396bf5cc4"
)
DISCIPLINE_CORRECTION_PATH_SEQUENCE_SHA256 = (
    "14e69395d27385eb7521b01c3f807ee3bf443b0dba1d87ee67dc854af7e65bba"
)
CENTRAL_TWO_PIN_NORMALIZED_SHA256 = (
    "04fee748261708bc5ae05c6ffb10b8faf9a0636123a706d526766cf903856f4d"
)
LEGACY_COMPAT_CORRECTION_PRECOMMIT = "LEGACY_COMPAT_CORRECTION_PRECOMMIT"
DISCIPLINE_CORRECTION_PRECOMMIT = "DISCIPLINE_CORRECTION_PRECOMMIT"
SUCCESSOR_PRECOMMIT_CANDIDATE = "SUCCESSOR_PRECOMMIT_CANDIDATE"
POSTCOMMIT_CLEAN = "POSTCOMMIT_CLEAN"
INVALID = "INVALID"
REPOSITORY_VALIDATION_PHASES = (
    LEGACY_COMPAT_CORRECTION_PRECOMMIT,
    DISCIPLINE_CORRECTION_PRECOMMIT,
    SUCCESSOR_PRECOMMIT_CANDIDATE,
    POSTCOMMIT_CLEAN,
    INVALID,
)
PUBLISHED_VALIDATOR_SHA256 = (
    "80c64646de57bcca87dfeffc967547a30a3bd4d3b13ca89caa30c0aeb73af7ca"
)
PUBLISHED_MANIFEST_SHA256 = (
    "2b4e3fa201a7ef2b8d47a81e37c138fcc91e5c4599967405e708ea87af3f2a5f"
)
PUBLISHED_CENTRAL_SHA256 = (
    "0001563d53db087d9e67bb2de1002b5fbd1c9d86bf6fa01d81a13c2ad390e351"
)
PACKAGE_RECORD_ID = (
    "PMAI-P0-04-ARR-V3-SRBE-V5-CONTRACT-ADAPTER-PREP-REPLACEMENT-V2-"
    "20260829"
)
PACKAGE_RECORD_ID_SHA256 = (
    "d265596288da1729bcc428349d4491d1c87fbc02a03224281d2bcc0fd42b65ae"
)
AUTHORIZATION_ID_SHA256 = (
    "395d54b50459a7c392263fe4fe69bbd280ba272cc64c1be6e003e18dd498f253"
)
BASE_CENTRAL_SHA256 = (
    "48f23d4f0a14ba883bd1e9696ec09ec424f91e9de6305ec75583c4da02816936"
)
HELD_V5_COMMIT = "da4d347066c464b0ad8799acc9a26802469488ed"
HELD_V5_TREE = "e55fa46f65562a82c44f4bc5524d45dcb4f5bd49"
HELD_V5_PARENT = "de93b4623e812a911445a4370dea40ec56b2098f"
EXPECTED_PATH_SEQUENCE_SHA256 = (
    "59e58e5f3511fe8f666b3f9391d61a1814b140b4f73e4d437c5816ef97042a31"
)
EXPECTED_EMPTY_SCHEMA_CANONICAL_LINE = (
    '{"relations":[],"schema":"PMAI_P0_04_SRBE_STRUCTURAL_SCHEMA_MANIFEST_V5_V1"}'
)
EXPECTED_EMPTY_SCHEMA_SHA256 = (
    "f87acbf36011fa8656e82f1cb6067614a59d019e32ea36781fe1dc2ceb4fc010"
)
PROCEDURE_CONTRACT_SHA256 = (
    "17e15afbf3aa75f0dde528174f654a3da8fd1a0907c82e8cec9527ebf35c4e11"
)
TLS_READONLY_CONTRACT_SHA256 = (
    "4f9afb65990161559a449bc2ceef49804e90c6da6583060cc35a3dffbca94129"
)
FIXED_SQL_TRACE_SHA256 = (
    "b486a55153f1c9c6027e3de6e67443e5ad8d1de8902ccde5a6d34e78277cdfb0"
)
CENTRAL_V4_OWNED_PROJECTION_SHA256 = (
    "be245ca676bc7b57aac2db164ac49bf2e7593834c7cdd63f4fe33faaf0c0fd21"
)
CENTRAL_V5_OWNED_PROJECTION_SHA256 = (
    "c0687e3d16fe2fc16f625f8ff027d0b66541281801e9134454db0f10cb2384ad"
)
LEGACY_TEST_MATRIX_PREFIX_BYTES = 29868
LEGACY_TEST_MATRIX_PREFIX_SHA256 = (
    "7ec23c187401a485cebef73de5ac85a4f88239f17aa06a5a72fe95f566b7fa55"
)
RUNTIME_SCHEMA_ID = "PMAI_P0_04_SRBE_V5_SANITIZED_RUNTIME_OBSERVATION_V1"
RUNTIME_SCHEMA_URN = "urn:pmai:p0-04:srbe:v5:runtime-observation-schema:v1"
RESULT_SCHEMA_ID = "PMAI_P0_04_SRBE_V5_SANITIZED_COLLECTION_RESULT_V1"
RESULT_SCHEMA_URN = "urn:pmai:p0-04:srbe:v5:sanitized-result-schema:v1"
AUTHORIZATION_ID = (
    "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_SRBE_V5_POST_V4_COMPATIBILITY_"
    "MERGE_REPLACEMENT_REBUILD_EXACT_13_PATH_REPOSITORY_PATCH_CONTROLLED_"
    "EXECUTION_V1"
)
PASS_MARKER = (
    "active_restore_runner_v3_sanitized_runtime_binding_evidence_collection_"
    "and_review_v5_contract_correction_and_operational_adapter_preparation=PASS"
)
FINAL_PASS = (
    "ALL PASS: PMAI-P0-04 V5 SRBE contract correction and operational "
    "adapter preparation"
)

PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_"
    "ADAPTER_PREPARATION_V1"
)
DOC = PREFIX + ".md"
POINTER = PREFIX + "_ACTIVE_POINTER_V1.json"
CHECKLIST = PREFIX + "_CHECKLIST_V1.csv"
GO_NO_GO = PREFIX + "_GO_NO_GO_V1.csv"
BASELINE = PREFIX + "_LOCKED_BASELINE_V1.json"
MANIFEST = PREFIX + "_PACKAGE_MANIFEST_V1.json"
RUNTIME_SCHEMA = PREFIX + "_RUNTIME_OBSERVATION_SCHEMA_V1.json"
RESULT_SCHEMA = PREFIX + "_SANITIZED_RESULT_SCHEMA_V1.json"
TEST_MATRIX = PREFIX + "_TEST_MATRIX_V1.csv"
ADAPTER = (
    "scripts/collect_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_collection_and_review_v5_operational_adapter_v1.py"
)
VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_collection_and_review_v5_contract_correction_and_operational_"
    "adapter_preparation_v1.py"
)
REVIEWER = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_review_v5_operational_v1.py"
)
CENTRAL = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_staging_migration_apply.py"
)
ACTIVE_RUNNER = (
    "scripts/run_treatment_framework_signed_review_state_persistence_"
    "migration_0010_disposable_restore_v3.py"
)

PACKAGE_PATHS = (
    DOC,
    POINTER,
    CHECKLIST,
    GO_NO_GO,
    BASELINE,
    MANIFEST,
    RUNTIME_SCHEMA,
    RESULT_SCHEMA,
    TEST_MATRIX,
    ADAPTER,
    VALIDATOR,
    REVIEWER,
)
EXPECTED_CHANGED_PATHS = (*PACKAGE_PATHS, CENTRAL)
MANIFEST_MEMBERS = (
    DOC,
    POINTER,
    CHECKLIST,
    GO_NO_GO,
    BASELINE,
    RUNTIME_SCHEMA,
    RESULT_SCHEMA,
    TEST_MATRIX,
    ADAPTER,
    VALIDATOR,
    REVIEWER,
)
IMMUTABLE_PACKAGE_PATHS = (
    DOC,
    POINTER,
    CHECKLIST,
    GO_NO_GO,
    BASELINE,
    RUNTIME_SCHEMA,
    RESULT_SCHEMA,
    TEST_MATRIX,
    ADAPTER,
    REVIEWER,
)
PACKAGE_CLOSURE_PATHS = (MANIFEST, VALIDATOR)
AUTHORIZED_CORRECTION_PATHS = (MANIFEST, VALIDATOR, CENTRAL)
CORRECTION_PATHS = tuple(
    sorted(AUTHORIZED_CORRECTION_PATHS, key=lambda value: value.encode("utf-8"))
)
FUTURE_B_CONTRACT_PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_V5_B_CONTRACT_BOUNDARY_AND_HASH_LOCK_"
    "FINALIZATION_V1"
)
FUTURE_B_CONTRACT_VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_collection_and_review_v5_b_contract_boundary_and_hash_lock_"
    "finalization_v1.py"
)
FUTURE_EXACT_7_PATHS = (
    FUTURE_B_CONTRACT_PREFIX + ".md",
    FUTURE_B_CONTRACT_PREFIX
    + "_COMPONENT_PLACEMENT_AND_EXTERNAL_INVENTORY_V1.json",
    FUTURE_B_CONTRACT_PREFIX
    + "_CANONICAL_BINDING_STATE_AND_RECEIPT_SCHEMA_BUNDLE_V1.json",
    FUTURE_B_CONTRACT_PREFIX + "_FAULT_MODEL_TEST_MATRIX_V1.csv",
    FUTURE_B_CONTRACT_PREFIX + "_PACKAGE_MANIFEST_V1.json",
    FUTURE_B_CONTRACT_VALIDATOR,
    CENTRAL,
)
FUTURE_EXACT_7_PATH_SEQUENCE_SHA256 = (
    "01d5c2480f796726ca9594ec8f410eb03b4d1d437a7fbb96dcc444070372d77a"
)
FUTURE_EXACT_7_BRANCH = (
    "pmai-p0-04-v5-b-contract-boundary-hash-lock-finalization-v2"
)
FUTURE_EXACT_7_MODES = (
    "100644",
    "100644",
    "100644",
    "100644",
    "100644",
    "100755",
    "100755",
)

V4_PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_V4_EXECUTION_AUTHORIZATION_V1"
)
V4_PROTECTED_HASHES = {
    V4_PREFIX + ".md": "25f27029077540c859ffb11371ddb4873a1302d71a315c479c51467b52dbf66e",
    V4_PREFIX + "_ACTIVE_POINTER_V1.json": "95e373986571b260ed392395dd2fb5d415d66f61f82e5ca6521429b4768959e8",
    V4_PREFIX + "_CHECKLIST_V1.csv": "b5f89fa5818a4d87befba8cc65fbe7dbc787e5a222de7dafa72e15f6b5676b99",
    V4_PREFIX + "_GO_NO_GO_V1.csv": "092ec716a7904711b5372b5389a9e63a682d726b917a8801cc55239d1952531c",
    V4_PREFIX + "_LOCKED_BASELINE_V1.json": "895a320b6e973db098b82b7169c03c99908c8580e2fe8bf5f1b638648276d440",
    V4_PREFIX + "_PACKAGE_MANIFEST_V1.json": "6b95631a2adc707707e55af68045c47440a2ca0fd3b8fd75c20e8d24a3ca9362",
    V4_PREFIX + "_TEST_MATRIX_V1.csv": "80835ad9c0d95f668b23f703b36defa4dfdbc59801d2d0b518a31149bd5dffb0",
    (
        "scripts/validate_treatment_framework_signed_review_state_"
        "persistence_migration_0010_active_restore_runner_v3_sanitized_"
        "runtime_binding_evidence_collection_and_review_v4_execution_"
        "authorization_v1.py"
    ): "75db3110bb2996a186ebe42c8e78985972ed37b6a1f775041d7dc9ef399be2c9",
}
V4_VALIDATOR = next(
    relative
    for relative in V4_PROTECTED_HASHES
    if relative.endswith("_v4_execution_authorization_v1.py")
)
CENTRAL_V5_STEM = (
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_"
    "COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_"
    "ADAPTER_PREPARATION"
)
CENTRAL_V5_OWNED_ASSIGNMENTS = (
    "SRBE_V5_SANITIZED_CHILD_ENV_ITEMS",
    "SRBE_V5_CONTRACT_ADAPTER_PREPARATION_EFFECTIVE_CURRENT_HOLD",
    "SRBE_V5_CONTRACT_ADAPTER_PREPARATION_EFFECTIVE_CURRENT_COMPLETENESS",
    "SRBE_V5_CONTRACT_ADAPTER_PREPARATION_EFFECTIVE_CURRENT_NEXT_STEP",
    CENTRAL_V5_STEM + "_VALIDATOR",
    CENTRAL_V5_STEM + "_VALIDATOR_SHA256",
    CENTRAL_V5_STEM + "_MANIFEST",
    CENTRAL_V5_STEM + "_MANIFEST_SHA256",
    CENTRAL_V5_STEM + "_PASS_MARKER",
)
CENTRAL_V5_NORMALIZED_ASSIGNMENTS = (
    CENTRAL_V5_STEM + "_VALIDATOR_SHA256",
    CENTRAL_V5_STEM + "_MANIFEST_SHA256",
)
CENTRAL_V5_INTEGRATION_BEGIN = (
    "# >>> pmai_p0_04_v5_contract_adapter_preparation_integration_owned_v1"
)
CENTRAL_V5_INTEGRATION_END = (
    "# <<< pmai_p0_04_v5_contract_adapter_preparation_integration_owned_v1"
)
CENTRAL_V5_OUTPUT_BEGIN = (
    "# >>> pmai_p0_04_v5_contract_adapter_preparation_output_owned_v1"
)
CENTRAL_V5_OUTPUT_END = (
    "# <<< pmai_p0_04_v5_contract_adapter_preparation_output_owned_v1"
)
CENTRAL_V4_INTEGRATION_END = (
    "# <<< pmai_p0_04_v4_execution_authorization_integration_owned_v1"
)
EXPECTED_V5_ENV_ITEMS = (
    ("GIT_CONFIG_GLOBAL", "/dev/null"),
    ("GIT_CONFIG_NOSYSTEM", "1"),
    ("GIT_NO_REPLACE_OBJECTS", "1"),
    ("GIT_OPTIONAL_LOCKS", "0"),
    ("GIT_TERMINAL_PROMPT", "0"),
    ("LANG", "C"),
    ("LC_ALL", "C"),
    ("PATH", "/usr/local/bin:/usr/bin:/bin"),
)
EXPECTED_V5_OUTPUT_EXPRESSIONS = (
    '"v4_controlled_execution_confirmation_superseded=true"',
    '"v4_collection_attempts_consumed=0"',
    '"v5_contract_correction_and_operational_adapter_preparation_complete=true"',
    '"v5_live_execution_authorized=false"',
    '"v5_current_attempts_authorized=0"',
    '"repository_patch_consumes_no_collection_attempt=true"',
    '"v5_live_preconditions_complete=false"',
    '"v5_execution_harness_present=false"',
    '"v5_concrete_render_port_present=false"',
    '"v5_concrete_database_port_present=false"',
    '"v5_authenticated_attempt_ledger_present=false"',
    '"v5_crash_safe_cleanup_supervisor_present=false"',
    '"v5_independent_attestation_origin_present=false"',
    '"render_access=false"',
    '"database_connection=false"',
    '"credential_access=false"',
    '"allowlist_mutation_execution=false"',
    '"srbe_v5_contract_adapter_preparation_effective_evidence_completeness=" + SRBE_V5_CONTRACT_ADAPTER_PREPARATION_EFFECTIVE_CURRENT_COMPLETENESS',
    '"srbe_v5_contract_adapter_preparation_effective_decision=" + SRBE_V5_CONTRACT_ADAPTER_PREPARATION_EFFECTIVE_CURRENT_HOLD',
    '"srbe_v5_contract_adapter_preparation_effective_next_step=" + SRBE_V5_CONTRACT_ADAPTER_PREPARATION_EFFECTIVE_CURRENT_NEXT_STEP',
)
REQUIRED_SUCCESSOR_TEST_SEMANTICS = (
    ("T252", "CURRENT_MAIN_COMMIT_TREE_PR_AND_CI_ANCHORS_EXACT", "repository anchor validation", "PASS"),
    ("T253", "HELD_DA4D347_NOT_REPLACEMENT_ANCESTOR", "repository ancestry validation", "PASS"),
    ("T254", "CURRENT_V4_VALIDATOR_MANIFEST_AND_SIX_IMMUTABLE_MEMBERS_EXACT", "protected byte hash validation", "PASS"),
    ("T255", "V4_OWNED_PROJECTION_PRESERVED_UNDER_V5_SUCCESSOR", "pinned V4 projection validation", "PASS"),
    ("T256", "LEGITIMATE_V5_SUCCESSOR_NOT_COUNTED_AS_SECOND_V4_REPAIR", "pinned V4 history validation", "PASS"),
    ("T257", "SUCCESSOR_COMMIT_MESSAGE_NO_TERMINAL_LF_ACCEPTED", "pinned V4 synthetic validation", "PASS"),
    ("T258", "SUCCESSOR_COMMIT_MESSAGE_SINGLE_TERMINAL_LF_ACCEPTED", "pinned V4 synthetic validation", "PASS"),
    ("T259", "MULTIPLE_TERMINAL_LF_REJECTED", "pinned V4 synthetic mutation", "HOLD"),
    ("T260", "CR_CRLF_NUL_AND_INVALID_UTF8_REJECTED", "pinned V4 synthetic mutation", "HOLD"),
    ("T261", "EXTRA_BODY_TRAILER_BOUNDARY_WHITESPACE_AND_CONTROL_REJECTED", "pinned V4 synthetic mutation", "HOLD"),
    ("T262", "SECOND_V4_REPAIR_OR_IMMUTABLE_PACKAGE_MUTATION_REJECTED", "pinned V4 history mutation", "HOLD"),
    ("T263", "UNAUTHORIZED_V4_CLOSURE_OR_PROJECTION_CHANGE_REJECTED", "pinned V4 closure mutation", "HOLD"),
    ("T264", "V5_HOOK_ORDER_ISOLATION_ENVIRONMENT_AND_MARKER_VIOLATION_REJECTED", "V5 AST projection mutation", "HOLD"),
    ("T265", "V5_MANIFEST_PIN_OR_OWNED_PROJECTION_MISMATCH_REJECTED", "V5 closure mutation", "HOLD"),
    ("T266", "HISTORY_PARENT_TREE_PATH_SUBJECT_PARALLEL_PENDING_OR_HELD_ANCESTOR_AMBIGUITY_REJECTED", "pinned V4 and V5 history mutation", "HOLD"),
    ("T267", "TRANSPARENT_SUCCESSOR_PUBLICATION_MERGE_POSITIVE_CONTROL", "pinned V4 synthetic validation", "PASS"),
)

SUCCESS_KEYS = {
    "adapter_contract_sha256",
    "attempt_binding_sha256",
    "attempt_ledger_receipt_sha256",
    "authorization_record_sha256",
    "cleanup_receipt_sha256",
    "cleanup_supervisor_armed_receipt_sha256",
    "cleanup_supervisor_final_receipt_sha256",
    "collection_attempt_consumed",
    "database_execution_evidence_sha256",
    "database_observation_sha256",
    "evidence_complete",
    "expected_post_restore_schema_manifest_sha256",
    "expected_pre_restore_schema_manifest_sha256",
    "final_inbound_ip_rule_set_empty",
    "fixed_sql_trace_sha256",
    "fixture_only",
    "forbidden_production_provider_identity_sha256",
    "forbidden_staging_provider_identity_sha256",
    "initial_inbound_ip_rule_set_empty",
    "instrumentation_receipt_sha256",
    "operational_collection_procedure_contract_sha256",
    "outcome",
    "post_restore_schema_evidence_collected",
    "pre_restore_readonly_collection_complete",
    "pre_restore_schema_manifest_sha256",
    "provider_observation_sha256",
    "public_external_access_blocked",
    "raw_connection_values_disclosed",
    "reviewer_sha256",
    "runtime_binding_contract_complete",
    "runtime_provenance_observation_receipt_sha256",
    "schema",
    "srbe_collection_evidence_complete",
    "target_application_attachment_count_zero",
    "target_connection_binding_sha256",
    "target_database_observed_identity_sha256",
    "target_lifecycle_within_72h",
    "target_open_connection_count_zero",
    "target_provider_identity_sha256",
    "target_status_available",
    "tls_readonly_contract_sha256",
}
FAILURE_KEYS = {
    "attempt_state",
    "attempt_reserved",
    "cleanup_completed",
    "cleanup_required",
    "collection_attempt_consumed",
    "error_code",
    "final_network_state_verified",
    "hold",
    "outcome",
    "raw_connection_values_disclosed",
    "runtime_evidence_emitted",
    "schema",
    "state_provenance",
    "stage_code",
}
ERROR_CODES = {
    "ALLOWLIST_ADD_FAILED",
    "ALLOWLIST_RECHECK_FAILED",
    "ALLOWLIST_REMOVE_FAILED",
    "ANTI_ROLLBACK_WITNESS_UNAVAILABLE",
    "ARGUMENT_CONTRACT_MISMATCH",
    "ATTEMPT_ALREADY_CONSUMED",
    "ATTEMPT_LEDGER_UNAVAILABLE",
    "ATTEMPT_LEDGER_UNCERTAIN",
    "AUTHORIZATION_BINDING_MISMATCH",
    "AUTHORIZATION_INVALID",
    "CLEANUP_SUPERVISOR_UNAVAILABLE",
    "CLEANUP_SUPERVISOR_UNCERTAIN",
    "CLEANUP_UNCERTAIN",
    "CONNECTION_MATERIAL_INVALID",
    "CONTROLLED_EXECUTION_HOLD",
    "DATABASE_CLOSE_FAILED",
    "DATABASE_CONNECT_FAILED",
    "DATABASE_OBSERVATION_INVALID",
    "DATABASE_READONLY_CONTRACT_FAILED",
    "FINAL_ALLOWLIST_NOT_EMPTY",
    "FINAL_PUBLIC_ACCESS_NOT_BLOCKED",
    "FIXED_SQL_TRACE_INVALID",
    "IDENTITY_DOMAIN_MISMATCH",
    "IDENTITY_SEPARATION_FAILED",
    "INDEPENDENT_ATTESTATION_INVALID",
    "INITIAL_ALLOWLIST_NOT_EMPTY",
    "INSTRUMENTATION_INCOMPLETE",
    "INTERNAL_FAILURE",
    "LEDGER_AUTHENTICATION_FAILED",
    "LIVE_PORTS_NOT_INJECTED",
    "PORT_IMPLEMENTATION_UNBOUND",
    "PUBLIC_ACCESS_NOT_BLOCKED",
    "RUNTIME_COMPONENT_BINDING_MISMATCH",
    "RUNTIME_PROVENANCE_INVALID",
    "RUNTIME_PROVENANCE_UNAVAILABLE",
    "SCHEMA_MANIFEST_MISMATCH",
    "TARGET_ATTACHMENTS_NONZERO",
    "TARGET_CONNECTIONS_NONZERO",
    "TARGET_NOT_AVAILABLE",
    "TARGET_TOO_OLD",
    "TLS_EVIDENCE_INVALID",
    "TLS_NEGOTIATION_INVALID",
}
STAGE_CODES = {
    "ALLOWLIST_ADD",
    "ALLOWLIST_REMOVE",
    "ALLOWLIST_REVALIDATION",
    "ANTI_ROLLBACK_WITNESS",
    "ATTEMPT_FINALIZATION",
    "ATTEMPT_RESERVATION",
    "CLEANUP_SUPERVISOR",
    "CLEANUP_SUPERVISOR_ARM",
    "CLEANUP_SUPERVISOR_FINALIZE",
    "COMPLETE",
    "CONNECTION_MATERIAL",
    "DATABASE_CLOSE",
    "DATABASE_CONNECT",
    "DATABASE_IDENTITY",
    "DATABASE_READONLY_SETUP",
    "FINAL_NETWORK_REVALIDATION",
    "INDEPENDENT_ATTESTATION",
    "OUTPUT_VALIDATION",
    "PRECHECK",
    "PROVIDER_INITIAL_REVALIDATION",
    "RUNTIME_PROVENANCE",
    "SCHEMA_MANIFEST",
}
EXPECTED_FIXED_SQL = {
    "SQL_SET_SESSION_READ_ONLY": (
        "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"
    ),
    "SQL_BEGIN_READ_ONLY": "BEGIN READ ONLY",
    "SQL_SET_SEARCH_PATH": "SET LOCAL search_path TO pg_catalog",
    "SQL_SET_STATEMENT_TIMEOUT": "SET LOCAL statement_timeout TO '5000ms'",
    "SQL_SET_LOCK_TIMEOUT": "SET LOCAL lock_timeout TO '1000ms'",
    "SQL_SET_IDLE_TIMEOUT": (
        "SET LOCAL idle_in_transaction_session_timeout TO '5000ms'"
    ),
    "SQL_VERIFY_READ_ONLY": (
        "SELECT pg_catalog.current_setting('transaction_read_only', true)::text "
        "AS transaction_read_only"
    ),
    "SQL_DATABASE_IDENTITY": (
        "SELECT pg_catalog.current_database()::text AS database_name, "
        "pg_catalog.inet_server_addr()::text AS server_address, "
        "pg_catalog.inet_server_port()::integer AS server_port"
    ),
    "SQL_STRUCTURAL_MANIFEST": (
        "SELECT n.nspname::text AS namespace_name, "
        "c.relname::text AS relation_name, c.relkind::text AS relation_kind, "
        "a.attname::text AS column_name, a.attnum::integer AS ordinal_position, "
        "a.atttypid::integer AS type_oid, a.attnotnull::boolean AS not_null "
        "FROM pg_catalog.pg_class AS c "
        "JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace "
        "LEFT JOIN pg_catalog.pg_attribute AS a "
        "ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped "
        "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
        "AND n.nspname NOT LIKE 'pg_toast%' "
        "AND c.relkind IN ('r','p','v','m','f','S') "
        "ORDER BY n.nspname, c.relname, c.relkind, a.attnum"
    ),
}
EXPECTED_FIXED_SQL_ORDER = (
    "SET_SESSION_READ_ONLY",
    "BEGIN_READ_ONLY",
    "SET_SEARCH_PATH",
    "SET_STATEMENT_TIMEOUT",
    "SET_LOCK_TIMEOUT",
    "SET_IDLE_TIMEOUT",
    "VERIFY_READ_ONLY",
    "DATABASE_IDENTITY",
    "STRUCTURAL_MANIFEST",
)


class ValidationError(RuntimeError):
    pass


def need(condition: bool, label: str) -> None:
    if not condition:
        raise ValidationError(label)


def path(relative: str) -> Path:
    candidate = ROOT / relative
    need(candidate.resolve().is_relative_to(ROOT.resolve()), "unsafe path " + relative)
    return candidate


def digest(relative: str) -> str:
    return hashlib.sha256(path(relative).read_bytes()).hexdigest()


def text(relative: str) -> str:
    return path(relative).read_text(encoding="utf-8")


def json_no_duplicates(relative: str) -> object:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            need(key not in result, "duplicate JSON key " + relative)
            result[key] = value
        return result

    return json.loads(text(relative), object_pairs_hook=pairs)


def sanitized_subprocess_env() -> dict[str, str]:
    """Return a minimal environment with no Git, Python, or receipt injection."""

    return {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": SAFE_PATH,
    }


def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    need(
        GIT_EXECUTABLE.is_file()
        and not GIT_EXECUTABLE.is_symlink()
        and os.access(GIT_EXECUTABLE, os.X_OK),
        "locked git executable",
    )
    result = subprocess.run(
        [str(GIT_EXECUTABLE), *arguments],
        cwd=ROOT,
        env=sanitized_subprocess_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    if check:
        need(result.returncode == 0, "git " + " ".join(arguments))
        need(result.stderr == "", "git stderr " + " ".join(arguments))
    return result


def git_value(*arguments: str) -> str:
    return git(*arguments).stdout.rstrip("\n")


def git_lines(*arguments: str) -> list[str]:
    value = git(*arguments).stdout
    return value.splitlines() if value else []


def parse_git_nul_paths(payload: bytes) -> list[str]:
    if payload == b"":
        return []
    if not payload.endswith(b"\0"):
        raise ValueError("HISTORY_AMBIGUITY")
    raw_paths = payload[:-1].split(b"\0")
    if any(value == b"" for value in raw_paths):
        raise ValueError("HISTORY_AMBIGUITY")
    try:
        values = [value.decode("utf-8", errors="strict") for value in raw_paths]
    except UnicodeDecodeError:
        raise ValueError("HISTORY_AMBIGUITY") from None
    if len(values) != len(set(values)):
        raise ValueError("HISTORY_AMBIGUITY")
    return values


def git_paths(*arguments: str) -> list[str]:
    need("-z" in arguments, "git path command NUL mode")
    result = subprocess.run(
        [str(GIT_EXECUTABLE), *arguments],
        cwd=ROOT,
        env=sanitized_subprocess_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    need(result.returncode == 0, "git path command exit")
    need(result.stderr == b"", "git path command stderr")
    try:
        return parse_git_nul_paths(result.stdout)
    except ValueError as error:
        need(False, str(error))
        return []


def current_changed_paths() -> list[str]:
    staged = set(
        git_paths(
            "diff",
            "--cached",
            "--name-only",
            "--no-renames",
            "-z",
            "HEAD",
        )
    )
    unstaged = set(
        git_paths("diff", "--name-only", "--no-renames", "-z")
    )
    untracked = set(
        git_paths("ls-files", "-z", "--others", "--exclude-standard")
    )
    need(
        not (staged & untracked) and not (unstaged & untracked),
        "HISTORY_AMBIGUITY",
    )
    values = staged | unstaged | untracked
    return sorted(values, key=lambda item: item.encode("utf-8"))


def changed_path_sha256(values: Sequence[str]) -> str:
    payload = "".join(value + "\n" for value in values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def base_has_path(relative: str) -> bool:
    result = git("cat-file", "-e", BASE_COMMIT + ":" + relative, check=False)
    return result.returncode == 0


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
        [str(GIT_EXECUTABLE), "cat-file", "commit", commit],
        cwd=ROOT,
        env=sanitized_subprocess_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    need(result.returncode == 0, "git commit object " + commit)
    need(result.stderr == b"", "git commit object stderr " + commit)
    parts = result.stdout.split(b"\n\n", 1)
    need(
        len(parts) == 2 and parts[0].startswith(b"tree "),
        "git commit object format",
    )
    try:
        return canonical_commit_message_body(parts[1])
    except ValueError as error:
        need(False, str(error))
        return ""


def git_is_ancestor(ancestor: str, descendant: str) -> bool:
    result = git("merge-base", "--is-ancestor", ancestor, descendant, check=False)
    need(result.returncode in {0, 1}, "git ancestry status")
    need(result.stdout == "" and result.stderr == "", "git ancestry output")
    return result.returncode == 0


def git_blob_bytes(commit: str, relative: str) -> bytes:
    result = subprocess.run(
        [str(GIT_EXECUTABLE), "show", commit + ":" + relative],
        cwd=ROOT,
        env=sanitized_subprocess_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    need(result.returncode == 0, "git blob " + relative)
    need(result.stderr == b"", "git blob stderr " + relative)
    return result.stdout


def git_blob_text(commit: str, relative: str) -> str:
    try:
        return git_blob_bytes(commit, relative).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        need(False, "git blob UTF-8 " + relative)
        return ""


def strict_json_bytes(payload: bytes) -> object:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise ValueError("MANIFEST_STRUCTURE_MISMATCH")
            result[key] = value
        return result

    try:
        source = payload.decode("utf-8", errors="strict")
        return json.loads(source, object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("MANIFEST_STRUCTURE_MISMATCH") from None


def manifest_closure_valid(commit: str, manifest_bytes: bytes) -> bool:
    try:
        value = strict_json_bytes(manifest_bytes)
        if type(value) is not dict or type(value.get("files")) is not list:
            return False
        files = value["files"]
        if len(files) != len(MANIFEST_MEMBERS):
            return False
        for entry, relative in zip(files, MANIFEST_MEMBERS, strict=True):
            if type(entry) is not dict or set(entry) != {"path", "bytes", "sha256"}:
                return False
            blob = git_blob_bytes(commit, relative)
            if (
                entry["path"] != relative
                or type(entry["bytes"]) is not int
                or entry["bytes"] != len(blob)
                or entry["sha256"] != hashlib.sha256(blob).hexdigest()
            ):
                return False
        return all(
            git_blob_bytes(commit, relative)
            == git_blob_bytes(PUBLISHED_MERGE_COMMIT, relative)
            for relative in IMMUTABLE_PACKAGE_PATHS
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        return False


def normalized_manifest_correction_bytes(payload: bytes) -> bytes:
    pattern = re.compile(
        rb'("path": "'
        + re.escape(VALIDATOR.encode("utf-8"))
        + rb'",\n      "bytes": )[0-9]+(,\n      "sha256": ")'
        rb'[0-9a-f]{64}("\n    })'
    )
    normalized, count = pattern.subn(
        rb"\1<NORMALIZED_BYTES>\2<NORMALIZED_SHA256>\3", payload
    )
    if count != 1:
        raise ValueError("MANIFEST_STRUCTURE_MISMATCH")
    return normalized


def normalized_central_v5_pin_bytes(payload: bytes) -> bytes:
    normalized = payload
    for name in CENTRAL_V5_NORMALIZED_ASSIGNMENTS:
        pattern = re.compile(
            rb"("
            + re.escape(name.encode("utf-8"))
            + rb"\s*=\s*\(\s*[\"'])[0-9a-f]{64}([\"']\s*\))"
        )
        normalized, count = pattern.subn(
            rb"\1<NORMALIZED_SHA256>\2", normalized, count=1
        )
        if count != 1:
            raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
    return normalized


def commit_v5_bindings_valid(commit: str, central_source: str) -> bool:
    try:
        _, values = unique_top_level_literals(
            central_source, CENTRAL_V5_OWNED_ASSIGNMENTS
        )
        validator_bytes = git_blob_bytes(commit, VALIDATOR)
        manifest_bytes = git_blob_bytes(commit, MANIFEST)
        if (
            values[CENTRAL_V5_STEM + "_VALIDATOR_SHA256"]
            != hashlib.sha256(validator_bytes).hexdigest()
            or values[CENTRAL_V5_STEM + "_MANIFEST_SHA256"]
            != hashlib.sha256(manifest_bytes).hexdigest()
            or not manifest_closure_valid(commit, manifest_bytes)
        ):
            return False
    except (KeyError, TypeError, ValueError, ValidationError, SyntaxError):
        return False
    return True


def commit_pin_only_delta_valid(commit: str, baseline: str) -> bool:
    try:
        candidate_manifest = git_blob_bytes(commit, MANIFEST)
        baseline_manifest = git_blob_bytes(baseline, MANIFEST)
        candidate_central = git_blob_bytes(commit, CENTRAL)
        baseline_central = git_blob_bytes(baseline, CENTRAL)
        return (
            normalized_manifest_correction_bytes(candidate_manifest)
            == normalized_manifest_correction_bytes(baseline_manifest)
            and normalized_central_v5_pin_bytes(candidate_central)
            == normalized_central_v5_pin_bytes(baseline_central)
        )
    except (ValueError, ValidationError):
        return False


def correction_delta_valid(commit: str) -> bool:
    return commit_pin_only_delta_valid(commit, PUBLISHED_MERGE_COMMIT)


def discipline_delta_valid(commit: str) -> bool:
    return commit_pin_only_delta_valid(
        commit,
        FIRST_COMPATIBILITY_PUBLICATION_MERGE,
    )


def working_pin_only_delta_valid(baseline: str) -> bool:
    try:
        candidate_manifest = path(MANIFEST).read_bytes()
        baseline_manifest = git_blob_bytes(baseline, MANIFEST)
        candidate_central = path(CENTRAL).read_bytes()
        baseline_central = git_blob_bytes(baseline, CENTRAL)
        return (
            normalized_manifest_correction_bytes(candidate_manifest)
            == normalized_manifest_correction_bytes(baseline_manifest)
            and normalized_central_v5_pin_bytes(candidate_central)
            == normalized_central_v5_pin_bytes(baseline_central)
        )
    except (OSError, ValueError, ValidationError):
        return False


def working_correction_delta_valid() -> bool:
    return working_pin_only_delta_valid(PUBLISHED_MERGE_COMMIT)


def working_discipline_delta_valid() -> bool:
    return working_pin_only_delta_valid(
        FIRST_COMPATIBILITY_PUBLICATION_MERGE
    )


def exact_marker_block(source: str, begin: str, end: str) -> tuple[str, int, int]:
    lines = source.splitlines(keepends=True)
    begin_indexes = [
        index for index, line in enumerate(lines) if line.rstrip("\n").strip() == begin
    ]
    end_indexes = [
        index for index, line in enumerate(lines) if line.rstrip("\n").strip() == end
    ]
    need(len(begin_indexes) == 1 and len(end_indexes) == 1, "central marker uniqueness " + begin)
    start, stop = begin_indexes[0], end_indexes[0]
    need(start < stop, "central marker order " + begin)
    return "".join(lines[start : stop + 1]), start + 1, stop + 1


def unique_top_level_literals(source: str, names: Sequence[str]) -> tuple[ast.Module, dict[str, object]]:
    tree = ast.parse(source, filename=CENTRAL)
    values: dict[str, object] = {}
    for name in names:
        assignments = [
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ]
        need(len(assignments) == 1, "central owned assignment " + name)
        stores = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and node.id == name
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ]
        need(len(stores) == 1, "central owned assignment mutation " + name)
        try:
            values[name] = ast.literal_eval(assignments[0].value)
        except (ValueError, TypeError) as exc:
            raise ValidationError("central nonliteral assignment " + name) from exc
    return tree, values


def central_v5_owned_projection(source: str) -> str:
    tree, values = unique_top_level_literals(source, CENTRAL_V5_OWNED_ASSIGNMENTS)
    need(
        values["SRBE_V5_SANITIZED_CHILD_ENV_ITEMS"] == EXPECTED_V5_ENV_ITEMS,
        "central V5 sanitized environment tuple",
    )
    for name in CENTRAL_V5_NORMALIZED_ASSIGNMENTS:
        value = values[name]
        need(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "central V5 normalized pin " + name,
        )
        values[name] = "<NORMALIZED_SHA256>"
    integration, integration_begin, integration_end = exact_marker_block(
        source, CENTRAL_V5_INTEGRATION_BEGIN, CENTRAL_V5_INTEGRATION_END
    )
    output, output_begin, output_end = exact_marker_block(
        source, CENTRAL_V5_OUTPUT_BEGIN, CENTRAL_V5_OUTPUT_END
    )
    _, _, v4_end = exact_marker_block(
        source,
        "# >>> pmai_p0_04_v4_execution_authorization_integration_owned_v1",
        CENTRAL_V4_INTEGRATION_END,
    )
    require_line = next(
        (index + 1 for index, line in enumerate(source.splitlines()) if line.strip() == "if args.require_complete:"),
        0,
    )
    all_pass_line = next(
        (
            index + 1
            for index, line in enumerate(source.splitlines())
            if '"ALL PASS: PMAI-P0-04 V4 target provisioned and network locked governance"' in line
        ),
        0,
    )
    need(
        0 < v4_end < integration_begin < integration_end < require_line < output_begin < output_end < all_pass_line,
        "central V4 V5 guard output order",
    )
    main_function = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"),
        None,
    )
    need(main_function is not None, "central main function")
    statements = [
        statement
        for statement in main_function.body
        if statement.lineno > integration_begin
        and getattr(statement, "end_lineno", statement.lineno) < integration_end
    ]
    need(len(statements) == 11, "central V5 successor hook statement count")
    need(integration.count("env=dict(SRBE_V5_SANITIZED_CHILD_ENV_ITEMS)") == 1, "central V5 isolated environment")
    need("SRBE_V4_SANITIZED_CHILD_ENV_ITEMS" not in integration, "central V5 aliases V4 environment")
    for required in (
        '"-I"',
        '"-B"',
        "stdin=subprocess.DEVNULL",
        "stdout=subprocess.PIPE",
        "stderr=subprocess.PIPE",
        "timeout=120",
        "check=False",
    ):
        need(integration.count(required) == 1, "central V5 hook " + required)
    output_lines = tuple(
        line.strip().removesuffix(",")
        for line in output.splitlines()[1:-1]
        if line.strip()
    )
    need(output_lines == EXPECTED_V5_OUTPUT_EXPRESSIONS, "central V5 output projection")
    payload = {
        "schema": "PMAI_P0_04_V5_ADAPTER_PREPARATION_CENTRAL_PROJECTION_V1",
        "v4_owned_projection_sha256": CENTRAL_V4_OWNED_PROJECTION_SHA256,
        "integration_markers": [CENTRAL_V5_INTEGRATION_BEGIN, CENTRAL_V5_INTEGRATION_END],
        "output_markers": [CENTRAL_V5_OUTPUT_BEGIN, CENTRAL_V5_OUTPUT_END],
        "assignments": [[name, values[name]] for name in CENTRAL_V5_OWNED_ASSIGNMENTS],
        "integration_ast": [
            ast.dump(statement, annotate_fields=True, include_attributes=False)
            for statement in statements
        ],
        "output_expressions": list(output_lines),
    }
    canonical = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def expect_projection_failure(source: str, label: str) -> None:
    try:
        central_v5_owned_projection(source)
    except (ValidationError, SyntaxError, ValueError):
        return
    raise ValidationError("central V5 negative projection " + label)


def expect_projection_mismatch(source: str, label: str) -> None:
    try:
        value = central_v5_owned_projection(source)
    except (ValidationError, SyntaxError, ValueError):
        return
    need(
        value != CENTRAL_V5_OWNED_PROJECTION_SHA256,
        "central V5 projection mutation " + label,
    )


def validate_v5_projection_synthetic_tests(source: str) -> None:
    indented_begin = "    " + CENTRAL_V5_INTEGRATION_BEGIN
    v5_pass_marker_name = CENTRAL_V5_STEM + "_PASS_MARKER"
    v4_pass_marker_name = (
        "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_"
        "COLLECTION_AND_REVIEW_V4_EXECUTION_AUTHORIZATION_PASS_MARKER"
    )
    v5_command = (
        "        [\n"
        "            sys.executable,\n"
        '            "-I",\n'
        '            "-B",\n'
        "            str(srbe_v5_adapter_preparation_validator_path),\n"
        "        ],\n"
    )
    v5_pass_check = (
        "            " + v5_pass_marker_name + "\n"
        "        )\n"
        "        == 1,"
    )
    safe_exit_label = (
        '"V5 SRBE contract-correction/adapter-preparation validator exit"'
    )
    v5_returncode_check = (
        "        srbe_v5_adapter_preparation_result.returncode == 0,"
    )
    v5_stderr_check = (
        '        srbe_v5_adapter_preparation_result.stderr == "",'
    )
    need(source.count(v5_command) == 1, "central V5 invocation command anchor")
    need(source.count(v5_pass_check) == 1, "central V5 PASS binding anchor")
    need(source.count(safe_exit_label) == 1, "central V5 failure label anchor")
    need(source.count(v5_returncode_check) == 1, "central V5 exit binding anchor")
    need(source.count(v5_stderr_check) == 1, "central V5 stderr binding anchor")
    expect_projection_failure(
        source.replace(indented_begin, indented_begin + "\n" + indented_begin, 1),
        "duplicate marker",
    )
    expect_projection_failure(
        source.replace("env=dict(SRBE_V5_SANITIZED_CHILD_ENV_ITEMS)", "env={}", 1),
        "environment alias",
    )
    expect_projection_failure(
        source.replace('        "v5_live_execution_authorized=false",\n', "", 1),
        "output omission",
    )
    expect_projection_failure(
        source.replace(CENTRAL_V5_INTEGRATION_END, CENTRAL_V5_INTEGRATION_BEGIN, 1),
        "marker ambiguity",
    )
    expect_projection_failure(
        source.replace(v5_command, v5_command.replace('            "-I",\n', "", 1), 1),
        "missing isolated flag",
    )
    expect_projection_failure(
        source.replace(v5_command, v5_command.replace('            "-B",\n', "", 1), 1),
        "missing no-bytecode flag",
    )
    expect_projection_mismatch(
        source.replace(
            "str(srbe_v5_adapter_preparation_validator_path)",
            '"/tmp/unbound-validator.py"',
            1,
        ),
        "validator path escape",
    )
    expect_projection_mismatch(
        source.replace(
            v5_pass_check,
            v5_pass_check.replace(v5_pass_marker_name, v4_pass_marker_name),
            1,
        ),
        "PASS marker alias",
    )
    expect_projection_mismatch(
        source.replace(
            v5_pass_check,
            v5_pass_check.replace(v5_pass_marker_name, json.dumps(PASS_MARKER)),
            1,
        ),
        "unbound PASS marker",
    )
    expect_projection_mismatch(
        source.replace(
            safe_exit_label,
            safe_exit_label + " + srbe_v5_adapter_preparation_result.stderr",
            1,
        ),
        "sensitive failure message",
    )
    expect_projection_mismatch(
        source.replace(
            v5_returncode_check,
            v5_returncode_check.replace("== 0", "in {0, 1}"),
            1,
        ),
        "nonzero child accepted",
    )
    expect_projection_mismatch(
        source.replace(
            v5_stderr_check,
            v5_stderr_check.replace('== ""', 'in {"", "x"}'),
            1,
        ),
        "child stderr accepted",
    )
    expect_projection_mismatch(
        source.replace(
            v5_pass_check,
            v5_pass_check.replace("== 1", ">= 1"),
            1,
        ),
        "duplicate PASS marker accepted",
    )
    expect_projection_failure(
        source.replace(
            "    # <<< pmai_p0_04_v5_contract_adapter_preparation_integration_owned_v1",
            "        print(os.environ)\n"
            "    # <<< pmai_p0_04_v5_contract_adapter_preparation_integration_owned_v1",
            1,
        ),
        "sensitive output",
    )


def run_pinned_v4_validator() -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(path(V4_VALIDATOR))],
        cwd=ROOT,
        env=sanitized_subprocess_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
        check=False,
    )
    need(result.returncode == 0 and result.stderr == "", "pinned V4 validator")
    need(
        result.stdout.splitlines().count(
            "active_restore_runner_v3_sanitized_runtime_binding_evidence_"
            "collection_and_review_v4_execution_authorization=PASS"
        )
        == 1,
        "pinned V4 validator marker",
    )


def validate_invocation() -> None:
    need(sys.flags.isolated == 1, "validator not isolated")
    need(sys.flags.ignore_environment == 1, "validator reads Python environment")
    need(sys.flags.no_user_site == 1, "validator user site enabled")
    need(sys.flags.dont_write_bytecode == 1, "validator bytecode enabled")
    need(getattr(sys.flags, "safe_path", False) is True, "validator unsafe path")
    need(sys.flags.optimize == 0, "validator optimized invocation")
    need(len(sys.argv) == 1, "validator argument contract")
    need("" not in sys.path, "validator empty sys.path")
    need(str(ROOT) not in sys.path, "validator repository on sys.path")
    need(str(ROOT / "scripts") not in sys.path, "validator scripts on sys.path")


def validate_repository_identity() -> None:
    """Bind Git commands to this exact linked worktree, not inherited Git env."""

    root = ROOT.resolve(strict=True)
    need(git_value("rev-parse", "--show-toplevel") == str(root), "git worktree root")
    dot_git = root / ".git"
    need(not dot_git.is_symlink(), "worktree git metadata symlink")
    if dot_git.is_file():
        raw = dot_git.read_bytes()
        need(0 < len(raw) <= 4096 and raw.endswith(b"\n"), "linked worktree git file bytes")
        try:
            marker = raw.decode("utf-8")
        except UnicodeError as exc:
            raise ValidationError("linked worktree git file encoding") from exc
        need(marker.startswith("gitdir: ") and marker.count("\n") == 1, "linked worktree gitdir marker")
        lexical_git_dir = Path(marker.removeprefix("gitdir: ").rstrip("\n"))
        need(lexical_git_dir.is_absolute(), "linked worktree absolute gitdir")
        git_dir = lexical_git_dir.resolve(strict=True)
        linked = True
    else:
        need(dot_git.is_dir(), "worktree git metadata")
        git_dir = dot_git.resolve(strict=True)
        linked = False
    need(git_dir.is_dir() and not git_dir.is_symlink(), "worktree gitdir")
    need(
        git_value("rev-parse", "--path-format=absolute", "--git-dir")
        == str(git_dir),
        "gitdir identity",
    )
    common_dir = Path(
        git_value("rev-parse", "--path-format=absolute", "--git-common-dir")
    ).resolve(strict=True)
    need(common_dir.is_dir() and not common_dir.is_symlink(), "git common-dir")
    if linked:
        need(git_dir.parent == common_dir / "worktrees", "linked worktree common-dir relation")
    else:
        need(git_dir == common_dir, "ordinary worktree common-dir relation")
    need(
        git_value("rev-parse", "--show-object-format") == "sha1",
        "git object format",
    )


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
    correction_delta_valid: bool
    discipline_delta_valid: bool = False
    ephemeral_pr_test_merge: bool = False


@dataclass(frozen=True)
class HistoryDecision:
    compatibility_correction: str
    publication_merge: str | None
    discipline_correction: str | None
    discipline_publication_merge: str | None
    successor_central_commits: tuple[str, ...]
    successor_publication_merges: tuple[str, ...]
    history_lineage: tuple[str, ...]
    pending_successor: str | None
    ephemeral_pr_test_merge: str | None


@dataclass(frozen=True)
class RepositoryPathSnapshot:
    relative: str
    mode: str
    sha256: str
    head_entry: str
    index_entry: str
    worktree_entry: str


@dataclass(frozen=True)
class RepositorySnapshot:
    head: str
    tree: str
    branch: str
    changed_paths: tuple[str, ...]
    path_snapshots: tuple[RepositoryPathSnapshot, ...]


@dataclass(frozen=True)
class RepositoryValidationState:
    phase: str
    initial_snapshot: RepositorySnapshot


def declared_scope_projection(
    observed_paths: tuple[str, ...],
    declared_paths: tuple[str, ...],
    expected_sequence_sha256: str,
    error: str,
) -> tuple[str, ...]:
    try:
        observed_bytes = tuple(
            relative.encode("utf-8", errors="strict")
            for relative in observed_paths
        )
        declared_bytes = tuple(
            relative.encode("utf-8", errors="strict")
            for relative in declared_paths
        )
    except UnicodeEncodeError:
        raise ValueError("HISTORY_AMBIGUITY") from None
    if (
        any(b"\0" in relative for relative in (*observed_bytes, *declared_bytes))
        or len(observed_paths) != len(set(observed_paths))
        or len(declared_paths) != len(set(declared_paths))
    ):
        raise ValueError("HISTORY_AMBIGUITY")
    if (
        len(observed_paths) != len(declared_paths)
        or set(observed_paths) != set(declared_paths)
        or changed_path_sha256(declared_paths) != expected_sequence_sha256
    ):
        raise ValueError(error)
    return declared_paths


def phase_declared_paths(phase: str) -> tuple[str, ...]:
    if phase in {
        LEGACY_COMPAT_CORRECTION_PRECOMMIT,
        DISCIPLINE_CORRECTION_PRECOMMIT,
    }:
        return CORRECTION_PATHS
    if phase == SUCCESSOR_PRECOMMIT_CANDIDATE:
        return FUTURE_EXACT_7_PATHS
    if phase == POSTCOMMIT_CLEAN:
        return ()
    raise ValueError("INVALID")


def git_blob_oid(payload: bytes) -> str:
    result = subprocess.run(
        [str(GIT_EXECUTABLE), "hash-object", "--stdin"],
        cwd=ROOT,
        env=sanitized_subprocess_env(),
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    need(result.returncode == 0, "git hash-object exit")
    need(result.stderr == b"", "git hash-object stderr")
    try:
        oid = result.stdout.decode("ascii", errors="strict").rstrip("\n")
    except UnicodeDecodeError:
        need(False, "git hash-object encoding")
        return ""
    need(re.fullmatch(r"[0-9a-f]{40}", oid) is not None, "git hash-object output")
    return oid


def repository_path_snapshot(relative: str) -> RepositoryPathSnapshot:
    candidate = path(relative)
    need(
        candidate.is_file() and not candidate.is_symlink(),
        "precommit snapshot file " + relative,
    )
    mode = f"{stat.S_IFREG | stat.S_IMODE(candidate.stat().st_mode):06o}"
    candidate_bytes = candidate.read_bytes()
    head_lines = git_lines("ls-tree", "HEAD", "--", relative)
    need(len(head_lines) <= 1, "precommit HEAD ambiguity " + relative)
    head_entry = "UNTRACKED"
    if head_lines:
        metadata, separator, head_path = head_lines[0].partition("\t")
        fields = metadata.split()
        need(
            separator == "\t"
            and head_path == relative
            and len(fields) == 3
            and fields[1] == "blob"
            and re.fullmatch(r"100(?:644|755)", fields[0]) is not None
            and re.fullmatch(r"[0-9a-f]{40}", fields[2]) is not None,
            "precommit HEAD entry " + relative,
        )
        head_entry = fields[0] + " " + fields[2]
    index_lines = git_lines("ls-files", "--stage", "--", relative)
    need(len(index_lines) <= 1, "precommit index ambiguity " + relative)
    index_entry = "UNTRACKED"
    if index_lines:
        metadata, separator, indexed_path = index_lines[0].partition("\t")
        fields = metadata.split()
        need(
            separator == "\t"
            and indexed_path == relative
            and len(fields) == 3
            and fields[2] == "0"
            and re.fullmatch(r"100(?:644|755) [0-9a-f]{40} 0", metadata)
            is not None,
            "precommit index entry " + relative,
        )
        index_entry = fields[0] + " " + fields[1]
    return RepositoryPathSnapshot(
        relative=relative,
        mode=mode,
        sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        head_entry=head_entry,
        index_entry=index_entry,
        worktree_entry=mode + " " + git_blob_oid(candidate_bytes),
    )


def validate_precommit_index_regime(
    path_snapshots: tuple[RepositoryPathSnapshot, ...],
) -> None:
    if not path_snapshots:
        return
    index_matches_head = all(
        snapshot.index_entry == snapshot.head_entry
        for snapshot in path_snapshots
    )
    index_matches_worktree = all(
        snapshot.index_entry == snapshot.worktree_entry
        for snapshot in path_snapshots
    )
    if not (index_matches_head or index_matches_worktree):
        raise ValueError("PRECOMMIT_INDEX_WORKTREE_REGIME_MISMATCH")


def capture_repository_snapshot(phase: str) -> RepositorySnapshot:
    need(phase in REPOSITORY_VALIDATION_PHASES[:-1], "validation phase")
    observed_paths = tuple(current_changed_paths())
    declared_paths = phase_declared_paths(phase)
    if phase == POSTCOMMIT_CLEAN:
        need(observed_paths == (), "postcommit worktree dirty")
    else:
        sequence_sha256 = (
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256
            if phase == SUCCESSOR_PRECOMMIT_CANDIDATE
            else DISCIPLINE_CORRECTION_PATH_SEQUENCE_SHA256
        )
        error = (
            "HISTORY_AMBIGUITY"
            if phase == SUCCESSOR_PRECOMMIT_CANDIDATE
            else "UNAUTHORIZED_V5_CLOSURE_CHANGE"
        )
        declared_scope_projection(
            observed_paths,
            declared_paths,
            sequence_sha256,
            error,
        )
    path_snapshots = tuple(
        repository_path_snapshot(relative) for relative in declared_paths
    )
    expected_modes = (
        FUTURE_EXACT_7_MODES
        if phase == SUCCESSOR_PRECOMMIT_CANDIDATE
        else (
            ("100644", "100755", "100755")
            if phase != POSTCOMMIT_CLEAN
            else ()
        )
    )
    need(
        tuple(snapshot.mode for snapshot in path_snapshots) == expected_modes,
        "precommit path mode mismatch",
    )
    try:
        validate_precommit_index_regime(path_snapshots)
    except ValueError as error:
        need(False, str(error))
    return RepositorySnapshot(
        head=git_value("rev-parse", "HEAD"),
        tree=git_value("rev-parse", "HEAD^{tree}"),
        branch=git_value("rev-parse", "--abbrev-ref", "HEAD"),
        changed_paths=observed_paths,
        path_snapshots=path_snapshots,
    )


def compare_repository_snapshots(
    phase: str,
    initial: RepositorySnapshot,
    final: RepositorySnapshot,
) -> None:
    if phase == POSTCOMMIT_CLEAN:
        if initial.changed_paths or final.changed_paths:
            raise ValueError("postcommit worktree dirty")
    elif phase not in REPOSITORY_VALIDATION_PHASES[:-1]:
        raise ValueError("INVALID")
    if initial != final:
        raise ValueError("PRECOMMIT_INITIAL_FINAL_PATH_MODE_OR_CONTENT_DRIFT")


def finalize_repository_state(state: RepositoryValidationState) -> None:
    final_snapshot = capture_repository_snapshot(state.phase)
    try:
        compare_repository_snapshots(
            state.phase,
            state.initial_snapshot,
            final_snapshot,
        )
    except ValueError as error:
        need(False, str(error))


def classify_postpublication_history(
    records: tuple[HistoryRecord, ...],
) -> HistoryDecision:
    correction: HistoryRecord | None = None
    publication_merge: HistoryRecord | None = None
    discipline_correction: HistoryRecord | None = None
    discipline_publication_merge: HistoryRecord | None = None
    published_anchor: HistoryRecord | None = None
    pending_successor: HistoryRecord | None = None
    successors: list[str] = []
    successor_merges: list[str] = []
    lineage: list[str] = []
    ephemeral_pr_test_merge: str | None = None
    immutable = set(IMMUTABLE_PACKAGE_PATHS)
    closure = set(PACKAGE_CLOSURE_PATHS)
    relevant_paths = (
        set(PACKAGE_PATHS) | set(FUTURE_EXACT_7_PATHS) | {CENTRAL}
    )
    for record in records:
        if ephemeral_pr_test_merge is not None:
            raise ValueError("HISTORY_AMBIGUITY")
        changed = set(record.changed_paths)
        second_parent_changed = set(record.second_parent_changed_paths)
        if (
            len(changed) != len(record.changed_paths)
            or len(second_parent_changed) != len(record.second_parent_changed_paths)
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
                    record.parents != (PUBLISHED_MERGE_COMMIT, correction.oid)
                    or (merge_subject is None and not ephemeral_subject_valid)
                    or record.tree != correction.tree
                    or record.changed_paths != CORRECTION_PATHS
                    or second_parent_changed
                    or record.central_projection_sha256
                    != CENTRAL_V5_OWNED_PROJECTION_SHA256
                    or not record.bindings_valid
                    or not record.correction_delta_valid
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
                correction is not None
                and publication_merge is not None
                and discipline_correction is not None
                and discipline_publication_merge is None
                and pending_successor is None
            ):
                merge_subject = re.fullmatch(
                    r"Merge pull request #[1-9][0-9]* from pet-med-ai/"
                    + re.escape(DISCIPLINE_CORRECTION_BRANCH)
                    + r"\n\n"
                    + re.escape(DISCIPLINE_CORRECTION_SUBJECT),
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
                    != (
                        FIRST_COMPATIBILITY_PUBLICATION_MERGE,
                        discipline_correction.oid,
                    )
                    or (merge_subject is None and not ephemeral_subject_valid)
                    or record.tree != discipline_correction.tree
                    or record.changed_paths != CORRECTION_PATHS
                    or second_parent_changed
                    or record.central_projection_sha256
                    != CENTRAL_V5_OWNED_PROJECTION_SHA256
                    or not record.bindings_valid
                    or not record.discipline_delta_valid
                ):
                    raise ValueError("HISTORY_AMBIGUITY")
                if ephemeral_subject_valid:
                    ephemeral_pr_test_merge = record.oid
                    continue
                discipline_publication_merge = record
                published_anchor = record
                lineage.append(record.oid)
                continue
            if (
                correction is None
                or publication_merge is None
                or discipline_correction is None
                or discipline_publication_merge is None
                or published_anchor is None
                or pending_successor is None
            ):
                raise ValueError("HISTORY_AMBIGUITY")
            successor_branch_pattern = (
                re.escape(FUTURE_EXACT_7_BRANCH)
                if not successor_merges
                else r"pmai-p0-04-[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?"
            )
            successor_merge_subject = re.fullmatch(
                r"Merge pull request #[1-9][0-9]* from pet-med-ai/"
                + successor_branch_pattern
                + r"\n\n"
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
            if (
                record.parents != (pending_successor.parents[0], pending_successor.oid)
                or (successor_merge_subject is None and not ephemeral_subject_valid)
                or record.tree != pending_successor.tree
                or record.changed_paths != pending_successor.changed_paths
                or second_parent_changed
                or record.central_projection_sha256
                != CENTRAL_V5_OWNED_PROJECTION_SHA256
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
            raise ValueError("IMMUTABLE_V5_PACKAGE_MEMBER_MUTATION")
        if changed & closure:
            if correction is None:
                if (
                    record.parents != (PUBLISHED_MERGE_COMMIT,)
                    or record.subject != COMPATIBILITY_CORRECTION_SUBJECT
                    or record.changed_paths != CORRECTION_PATHS
                ):
                    raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
                if (
                    record.central_projection_sha256
                    != CENTRAL_V5_OWNED_PROJECTION_SHA256
                ):
                    raise ValueError("UNAUTHORIZED_V5_PROJECTION_CHANGE")
                if not record.bindings_valid:
                    raise ValueError("MANIFEST_HASH_MISMATCH")
                if not record.correction_delta_valid:
                    raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
                correction = record
                published_anchor = record
                lineage.append(record.oid)
                continue
            if record.subject == COMPATIBILITY_CORRECTION_SUBJECT:
                raise ValueError("SECOND_COMPATIBILITY_CORRECTION")
            if record.subject == DISCIPLINE_CORRECTION_SUBJECT:
                if discipline_correction is not None:
                    raise ValueError("SECOND_DISCIPLINE_CORRECTION")
                if (
                    publication_merge is None
                    or publication_merge.oid
                    != FIRST_COMPATIBILITY_PUBLICATION_MERGE
                    or published_anchor is None
                    or published_anchor.oid
                    != FIRST_COMPATIBILITY_PUBLICATION_MERGE
                    or pending_successor is not None
                    or record.parents
                    != (FIRST_COMPATIBILITY_PUBLICATION_MERGE,)
                    or record.changed_paths != CORRECTION_PATHS
                ):
                    raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
                if (
                    record.central_projection_sha256
                    != CENTRAL_V5_OWNED_PROJECTION_SHA256
                ):
                    raise ValueError("UNAUTHORIZED_V5_PROJECTION_CHANGE")
                if not record.bindings_valid:
                    raise ValueError("MANIFEST_HASH_MISMATCH")
                if not record.discipline_delta_valid:
                    raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
                discipline_correction = record
                published_anchor = record
                lineage.append(record.oid)
                continue
            raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
        if CENTRAL in changed:
            if record.subject == COMPATIBILITY_CORRECTION_SUBJECT:
                raise ValueError("SECOND_COMPATIBILITY_CORRECTION")
            if record.subject == DISCIPLINE_CORRECTION_SUBJECT:
                raise ValueError("SECOND_DISCIPLINE_CORRECTION")
            if not canonical_single_line_commit_subject(record.subject):
                raise ValueError("HISTORY_AMBIGUITY")
            if (
                correction is None
                or publication_merge is None
                or discipline_correction is None
                or discipline_publication_merge is None
                or published_anchor is None
                or pending_successor is not None
                or (
                    not successor_merges
                    and record.parents != (published_anchor.oid,)
                )
            ):
                raise ValueError("HISTORY_AMBIGUITY")
            if (
                record.central_projection_sha256
                != CENTRAL_V5_OWNED_PROJECTION_SHA256
            ):
                raise ValueError("UNAUTHORIZED_V5_PROJECTION_CHANGE")
            if not record.bindings_valid:
                raise ValueError("MANIFEST_HASH_MISMATCH")
            if not successor_merges:
                declared_scope_projection(
                    record.changed_paths,
                    FUTURE_EXACT_7_PATHS,
                    FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
                    "HISTORY_AMBIGUITY",
                )
            successors.append(record.oid)
            pending_successor = record
            lineage.append(record.oid)
            continue
        raise ValueError("HISTORY_AMBIGUITY")
    if correction is None:
        raise ValueError("HISTORY_AMBIGUITY")
    return HistoryDecision(
        compatibility_correction=correction.oid,
        publication_merge=(publication_merge.oid if publication_merge else None),
        discipline_correction=(
            discipline_correction.oid if discipline_correction else None
        ),
        discipline_publication_merge=(
            discipline_publication_merge.oid
            if discipline_publication_merge
            else None
        ),
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
    parents = tuple(git_value("show", "-s", "--format=%P", commit).split())
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
    delta_valid = False
    discipline_pin_only_delta_valid = False
    if CENTRAL in set(changed_paths) | set(second_parent_changed_paths):
        central_source = git_blob_text(commit, CENTRAL)
        try:
            projection = central_v5_owned_projection(central_source)
        except (SyntaxError, ValueError, ValidationError):
            projection = "INVALID"
        bindings_valid = commit_v5_bindings_valid(commit, central_source)
        delta_valid = correction_delta_valid(commit)
        discipline_pin_only_delta_valid = discipline_delta_valid(commit)
    return HistoryRecord(
        oid=commit,
        parents=parents,
        subject=git_commit_message(commit),
        tree=git_value("rev-parse", commit + "^{tree}"),
        changed_paths=changed_paths,
        second_parent_changed_paths=second_parent_changed_paths,
        central_projection_sha256=projection,
        bindings_valid=bindings_valid,
        correction_delta_valid=delta_valid,
        discipline_delta_valid=discipline_pin_only_delta_valid,
        ephemeral_pr_test_merge=(
            commit == head
            and len(parents) == 2
            and git_value("rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
            and exact_pr_merge_ref_points_to_head(head)
        ),
    )


def history_record_is_relevant(record: HistoryRecord) -> bool:
    return bool(
        set(record.changed_paths)
        & (set(PACKAGE_PATHS) | set(FUTURE_EXACT_7_PATHS) | {CENTRAL})
    )


def validate_ancestry_merge_orientation(
    records: tuple[HistoryRecord, ...], is_ancestor: Any
) -> None:
    for record in records:
        if len(record.parents) > 1 and not is_ancestor(
            PUBLISHED_MERGE_COMMIT, record.parents[0]
        ):
            raise ValueError("HISTORY_AMBIGUITY")


def working_context(
    head: str,
    branch: str,
    working_paths: tuple[str, ...],
    decision: HistoryDecision | None = None,
) -> str:
    if not working_paths:
        return POSTCOMMIT_CLEAN
    if decision is not None and (
        decision.discipline_correction == head
        or decision.pending_successor == head
    ):
        raise ValueError("postcommit worktree dirty")
    changed = set(working_paths)
    if len(changed) != len(working_paths):
        raise ValueError("HISTORY_AMBIGUITY")
    if head == PUBLISHED_MERGE_COMMIT:
        if (
            branch != COMPATIBILITY_CORRECTION_BRANCH
            or len(working_paths) != len(CORRECTION_PATHS)
            or changed != set(CORRECTION_PATHS)
        ):
            raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
        return LEGACY_COMPAT_CORRECTION_PRECOMMIT
    if head == FIRST_COMPATIBILITY_PUBLICATION_MERGE:
        if (
            branch != DISCIPLINE_CORRECTION_BRANCH
            or declared_scope_projection(
                working_paths,
                CORRECTION_PATHS,
                DISCIPLINE_CORRECTION_PATH_SEQUENCE_SHA256,
                "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            )
            != CORRECTION_PATHS
        ):
            raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
        return DISCIPLINE_CORRECTION_PRECOMMIT
    if branch == FUTURE_EXACT_7_BRANCH:
        declared_scope_projection(
            working_paths,
            FUTURE_EXACT_7_PATHS,
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
            "HISTORY_AMBIGUITY",
        )
        return SUCCESSOR_PRECOMMIT_CANDIDATE
    if head not in {
        PUBLISHED_MERGE_COMMIT,
        FIRST_COMPATIBILITY_PUBLICATION_MERGE,
    }:
        raise ValueError("postcommit worktree dirty")
    if changed.intersection(PACKAGE_PATHS):
        raise ValueError("UNAUTHORIZED_V5_CLOSURE_CHANGE")
    raise ValueError("postcommit worktree dirty")


def validate_working_history_context(
    context: str,
    decision: HistoryDecision,
    head: str,
    branch: str,
) -> None:
    if context == DISCIPLINE_CORRECTION_PRECOMMIT:
        if (
            head != FIRST_COMPATIBILITY_PUBLICATION_MERGE
            or branch != DISCIPLINE_CORRECTION_BRANCH
            or decision.publication_merge
            != FIRST_COMPATIBILITY_PUBLICATION_MERGE
            or decision.discipline_correction is not None
            or decision.discipline_publication_merge is not None
            or decision.pending_successor is not None
        ):
            raise ValueError("HISTORY_AMBIGUITY")
        return
    if context == SUCCESSOR_PRECOMMIT_CANDIDATE:
        if decision.pending_successor == head:
            raise ValueError("postcommit worktree dirty")
        if (
            branch != FUTURE_EXACT_7_BRANCH
            or decision.discipline_correction is None
            or decision.discipline_publication_merge is None
            or head != decision.discipline_publication_merge
            or decision.pending_successor is not None
        ):
            raise ValueError("HISTORY_AMBIGUITY")
        return
    if context != POSTCOMMIT_CLEAN:
        raise ValueError("INVALID")


def pending_successor_branch_valid(
    decision: HistoryDecision,
    branch: str,
) -> bool:
    if not decision.successor_publication_merges:
        return branch == FUTURE_EXACT_7_BRANCH
    return (
        re.fullmatch(
            r"pmai-p0-04-[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?",
            branch,
        )
        is not None
    )


def validate_historical_anchors() -> None:
    need(git_value("rev-parse", BASE_COMMIT + "^{tree}") == BASE_TREE, "base tree")
    need(
        tuple(git_value("show", "-s", "--format=%P", BASE_COMMIT).split())
        == BASE_PARENTS,
        "base parent sequence",
    )
    need(
        hashlib.sha256(git_blob_bytes(BASE_COMMIT, CENTRAL)).hexdigest()
        == BASE_CENTRAL_SHA256,
        "base central hash",
    )
    need(
        git_value("rev-parse", INTRODUCTION_COMMIT + "^{tree}")
        == INTRODUCTION_TREE,
        "introduction tree",
    )
    need(
        tuple(git_value("show", "-s", "--format=%P", INTRODUCTION_COMMIT).split())
        == (BASE_COMMIT,),
        "introduction parent",
    )
    need(
        git_value("rev-list", "--count", BASE_COMMIT + ".." + INTRODUCTION_COMMIT)
        == "1",
        "one introduction commit",
    )
    need(
        git_commit_message(INTRODUCTION_COMMIT) == COMMIT_MESSAGE,
        "introduction commit message",
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
        "introduction exact paths",
    )
    need(
        git_value("rev-parse", PUBLISHED_MERGE_COMMIT + "^{tree}")
        == PUBLISHED_MERGE_TREE,
        "published merge tree",
    )
    need(
        tuple(
            git_value("show", "-s", "--format=%P", PUBLISHED_MERGE_COMMIT).split()
        )
        == PUBLISHED_MERGE_PARENTS,
        "published merge parents",
    )
    need(
        git_commit_message(PUBLISHED_MERGE_COMMIT)
        == (
            "Merge pull request #22 from pet-med-ai/"
            + HEAD_BRANCH
            + "\n\n"
            + COMMIT_MESSAGE
        ),
        "published merge message",
    )
    need(
        git_paths(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            BASE_COMMIT + ".." + PUBLISHED_MERGE_COMMIT,
        )
        == list(EXPECTED_CHANGED_PATHS),
        "published merge first-parent paths",
    )
    need(
        git_paths(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            INTRODUCTION_COMMIT + ".." + PUBLISHED_MERGE_COMMIT,
        )
        == [],
        "published merge second-parent paths",
    )
    need(
        git_lines(
            "rev-list",
            "--reverse",
            "--full-history",
            BASE_COMMIT + ".." + PUBLISHED_MERGE_COMMIT,
            "--",
            *PACKAGE_PATHS,
        )
        == [INTRODUCTION_COMMIT, PUBLISHED_MERGE_COMMIT],
        "unique historical V5 rebuild",
    )
    for relative, expected in (
        (VALIDATOR, PUBLISHED_VALIDATOR_SHA256),
        (MANIFEST, PUBLISHED_MANIFEST_SHA256),
        (CENTRAL, PUBLISHED_CENTRAL_SHA256),
    ):
        need(
            hashlib.sha256(
                git_blob_bytes(PUBLISHED_MERGE_COMMIT, relative)
            ).hexdigest()
            == expected,
            "published protected hash " + relative,
        )
    need(
        git_value(
            "rev-parse", FIRST_COMPATIBILITY_CORRECTION_COMMIT + "^{tree}"
        )
        == FIRST_COMPATIBILITY_CORRECTION_TREE,
        "first compatibility correction tree",
    )
    need(
        tuple(
            git_value(
                "show",
                "-s",
                "--format=%P",
                FIRST_COMPATIBILITY_CORRECTION_COMMIT,
            ).split()
        )
        == (PUBLISHED_MERGE_COMMIT,),
        "first compatibility correction parent",
    )
    need(
        git_commit_message(FIRST_COMPATIBILITY_CORRECTION_COMMIT)
        == COMPATIBILITY_CORRECTION_SUBJECT,
        "first compatibility correction message",
    )
    need(
        tuple(
            git_paths(
                "diff",
                "--name-only",
                "--no-renames",
                "-z",
                PUBLISHED_MERGE_COMMIT
                + ".."
                + FIRST_COMPATIBILITY_CORRECTION_COMMIT,
            )
        )
        == CORRECTION_PATHS,
        "first compatibility correction paths",
    )
    need(
        git_value(
            "rev-parse", FIRST_COMPATIBILITY_PUBLICATION_MERGE + "^{tree}"
        )
        == FIRST_COMPATIBILITY_PUBLICATION_TREE,
        "first compatibility publication tree",
    )
    need(
        tuple(
            git_value(
                "show",
                "-s",
                "--format=%P",
                FIRST_COMPATIBILITY_PUBLICATION_MERGE,
            ).split()
        )
        == FIRST_COMPATIBILITY_PUBLICATION_PARENTS,
        "first compatibility publication parents",
    )
    need(
        git_commit_message(FIRST_COMPATIBILITY_PUBLICATION_MERGE)
        == (
            "Merge pull request #23 from pet-med-ai/"
            + COMPATIBILITY_CORRECTION_BRANCH
            + "\n\n"
            + COMPATIBILITY_CORRECTION_SUBJECT
        ),
        "first compatibility publication message",
    )
    need(
        tuple(
            git_paths(
                "diff",
                "--name-only",
                "--no-renames",
                "-z",
                PUBLISHED_MERGE_COMMIT
                + ".."
                + FIRST_COMPATIBILITY_PUBLICATION_MERGE,
            )
        )
        == CORRECTION_PATHS,
        "first compatibility publication first-parent paths",
    )
    need(
        git_paths(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            FIRST_COMPATIBILITY_CORRECTION_COMMIT
            + ".."
            + FIRST_COMPATIBILITY_PUBLICATION_MERGE,
        )
        == [],
        "first compatibility publication second-parent paths",
    )
    for relative, expected in (
        (VALIDATOR, FIRST_COMPATIBILITY_VALIDATOR_SHA256),
        (MANIFEST, FIRST_COMPATIBILITY_MANIFEST_SHA256),
        (CENTRAL, FIRST_COMPATIBILITY_CENTRAL_SHA256),
    ):
        need(
            hashlib.sha256(
                git_blob_bytes(
                    FIRST_COMPATIBILITY_PUBLICATION_MERGE,
                    relative,
                )
            ).hexdigest()
            == expected,
            "first compatibility protected hash " + relative,
        )
    need(
        hashlib.sha256(
            normalized_central_v5_pin_bytes(
                git_blob_bytes(
                    FIRST_COMPATIBILITY_PUBLICATION_MERGE,
                    CENTRAL,
                )
            )
        ).hexdigest()
        == CENTRAL_TWO_PIN_NORMALIZED_SHA256,
        "first compatibility normalized central two-pin hash",
    )
    held_presence = git(
        "cat-file", "-e", HELD_V5_COMMIT + "^{commit}", check=False
    )
    if held_presence.returncode == 0:
        need(
            git_value("rev-parse", HELD_V5_COMMIT + "^{tree}") == HELD_V5_TREE,
            "held V5 tree",
        )
        need(
            git_value("rev-parse", HELD_V5_COMMIT + "^") == HELD_V5_PARENT,
            "held V5 parent",
        )
        need(
            not git_is_ancestor(HELD_V5_COMMIT, "HEAD"),
            "held V5 is ancestor",
        )


def validate_commit_path_modes(
    commit: str,
    relatives: tuple[str, ...],
    expected_modes: tuple[str, ...],
    label: str,
) -> None:
    need(len(relatives) == len(expected_modes), label + " mode count")
    for relative, expected_mode in zip(
        relatives,
        expected_modes,
        strict=True,
    ):
        lines = git_lines("ls-tree", commit, "--", relative)
        need(len(lines) == 1, label + " tree entry " + relative)
        metadata, separator, observed_path = lines[0].partition("\t")
        fields = metadata.split()
        need(
            separator == "\t"
            and observed_path == relative
            and len(fields) == 3
            and fields[0] == expected_mode
            and fields[1] == "blob"
            and re.fullmatch(r"[0-9a-f]{40}", fields[2]) is not None,
            label + " tree mode " + relative,
        )


def validate_repository_history() -> RepositoryValidationState:
    validate_historical_anchors()
    head = git_value("rev-parse", "HEAD")
    need(
        git_is_ancestor(PUBLISHED_MERGE_COMMIT, head),
        "published merge is not ancestor",
    )
    working_paths = current_changed_paths()
    current_branch = git_value("rev-parse", "--abbrev-ref", "HEAD")
    if head == PUBLISHED_MERGE_COMMIT:
        try:
            context = working_context(
                head,
                current_branch,
                tuple(working_paths),
            )
        except ValueError as error:
            need(False, str(error))
            raise AssertionError("unreachable") from error
        need(
            context == LEGACY_COMPAT_CORRECTION_PRECOMMIT,
            "legacy compatibility correction phase",
        )
        initial_snapshot = capture_repository_snapshot(context)
        need(
            initial_snapshot.head == head
            and initial_snapshot.branch == current_branch
            and initial_snapshot.changed_paths == tuple(working_paths),
            "precommit initial repository snapshot",
        )
        need(
            working_correction_delta_valid(),
            "unauthorized V5 compatibility correction delta",
        )
        return RepositoryValidationState(context, initial_snapshot)
    ancestry_commits = git_lines(
        "rev-list",
        "--reverse",
        "--topo-order",
        "--ancestry-path",
        PUBLISHED_MERGE_COMMIT + ".." + head,
    )
    ancestry_records = tuple(
        history_record(commit, head) for commit in ancestry_commits
    )
    try:
        validate_ancestry_merge_orientation(ancestry_records, git_is_ancestor)
        decision = classify_postpublication_history(
            tuple(
                record
                for record in ancestry_records
                if history_record_is_relevant(record)
            )
        )
        context = working_context(
            head,
            current_branch,
            tuple(working_paths),
            decision,
        )
        validate_working_history_context(
            context,
            decision,
            head,
            current_branch,
        )
        initial_snapshot = capture_repository_snapshot(context)
        need(
            initial_snapshot.head == head
            and initial_snapshot.branch == current_branch
            and initial_snapshot.changed_paths == tuple(working_paths),
            "precommit initial repository snapshot",
        )
        validate_history_ancestry(decision, git_is_ancestor)
    except ValueError as error:
        need(False, str(error))
        raise AssertionError("unreachable") from error
    need(
        decision.compatibility_correction
        == FIRST_COMPATIBILITY_CORRECTION_COMMIT,
        "first compatibility correction history anchor",
    )
    need(
        decision.publication_merge
        == FIRST_COMPATIBILITY_PUBLICATION_MERGE,
        "first compatibility publication history anchor",
    )
    history_anchor = decision.history_lineage[-1]
    need(git_is_ancestor(history_anchor, head), "V5 history anchor is not ancestor")
    if decision.publication_merge is None:
        need(
            (
                head == decision.compatibility_correction
                and current_branch == COMPATIBILITY_CORRECTION_BRANCH
            )
            or decision.ephemeral_pr_test_merge == head,
            "unpublished compatibility correction context",
        )
    if (
        decision.discipline_correction is None
        and context == POSTCOMMIT_CLEAN
    ):
        need(
            head == FIRST_COMPATIBILITY_PUBLICATION_MERGE,
            "discipline correction missing from clean successor history",
        )
    if (
        decision.discipline_correction is not None
        and decision.discipline_publication_merge is None
    ):
        need(
            (
                head == decision.discipline_correction
                and current_branch == DISCIPLINE_CORRECTION_BRANCH
            )
            or decision.ephemeral_pr_test_merge == head,
            "unpublished discipline correction context",
        )
    if decision.pending_successor is not None:
        need(
            (
                head == decision.pending_successor
                and pending_successor_branch_valid(
                    decision,
                    current_branch,
                )
            )
            or decision.ephemeral_pr_test_merge == head,
            "unpublished successor context",
        )
    validate_commit_path_modes(
        decision.compatibility_correction,
        CORRECTION_PATHS,
        ("100644", "100755", "100755"),
        "compatibility correction",
    )
    if decision.discipline_correction is not None:
        validate_commit_path_modes(
            decision.discipline_correction,
            CORRECTION_PATHS,
            ("100644", "100755", "100755"),
            "discipline correction",
        )
    if decision.successor_central_commits:
        validate_commit_path_modes(
            decision.successor_central_commits[0],
            FUTURE_EXACT_7_PATHS,
            FUTURE_EXACT_7_MODES,
            "first successor",
        )
    if context == DISCIPLINE_CORRECTION_PRECOMMIT:
        need(
            working_discipline_delta_valid(),
            "unauthorized V5 discipline correction delta",
        )
    return RepositoryValidationState(context, initial_snapshot)


def validate_git_scope() -> RepositoryValidationState:
    need(
        hashlib.sha256(PACKAGE_RECORD_ID.encode("utf-8")).hexdigest()
        == PACKAGE_RECORD_ID_SHA256,
        "package record ID hash",
    )
    need(
        hashlib.sha256(AUTHORIZATION_ID.encode("utf-8")).hexdigest()
        == AUTHORIZATION_ID_SHA256,
        "authorization ID hash",
    )
    need(
        hashlib.sha256(
            COMPATIBILITY_CORRECTION_AUTHORIZATION_ID.encode("utf-8")
        ).hexdigest()
        == COMPATIBILITY_CORRECTION_AUTHORIZATION_ID_SHA256,
        "compatibility correction authorization ID hash",
    )
    need(
        hashlib.sha256(
            DISCIPLINE_CORRECTION_AUTHORIZATION_ID.encode("utf-8")
        ).hexdigest()
        == DISCIPLINE_CORRECTION_AUTHORIZATION_ID_SHA256,
        "discipline correction authorization ID hash",
    )
    need(
        tuple(sorted(EXPECTED_CHANGED_PATHS, key=lambda item: item.encode("utf-8")))
        == EXPECTED_CHANGED_PATHS,
        "declared path order",
    )
    need(len(EXPECTED_CHANGED_PATHS) == 13, "changed path count")
    need(len(PACKAGE_PATHS) == 12, "package path count")
    need(len(MANIFEST_MEMBERS) == 11, "manifest member count")
    need(
        changed_path_sha256(EXPECTED_CHANGED_PATHS)
        == EXPECTED_PATH_SEQUENCE_SHA256,
        "path sequence hash",
    )
    need(
        changed_path_sha256(CORRECTION_PATHS)
        == COMPATIBILITY_CORRECTION_PATH_SEQUENCE_SHA256,
        "correction path sequence hash",
    )
    need(
        COMPATIBILITY_CORRECTION_PATH_SEQUENCE_SHA256
        == DISCIPLINE_CORRECTION_PATH_SEQUENCE_SHA256,
        "discipline correction path sequence binding",
    )
    need(len(FUTURE_EXACT_7_PATHS) == 7, "future exact-7 path count")
    need(
        len(FUTURE_EXACT_7_PATHS) == len(set(FUTURE_EXACT_7_PATHS)),
        "future exact-7 path uniqueness",
    )
    need(
        changed_path_sha256(FUTURE_EXACT_7_PATHS)
        == FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
        "future exact-7 declared path sequence hash",
    )
    need(
        tuple(
            sorted(
                FUTURE_EXACT_7_PATHS,
                key=lambda item: item.encode("utf-8"),
            )
        )
        != FUTURE_EXACT_7_PATHS,
        "future exact-7 declared order must remain non-sorted",
    )
    for relative in PACKAGE_PATHS:
        need(not base_has_path(relative), "package path existed at base " + relative)
    need(base_has_path(CENTRAL), "central absent at base")
    return validate_repository_history()


def history_variant(record: HistoryRecord, **changes: object) -> HistoryRecord:
    values = dict(record.__dict__)
    values.update(changes)
    return HistoryRecord(**values)


def expect_contract_error(
    action: Any, expected: str, label: str
) -> None:
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
        canonical_commit_message_body(b"title\nbody\n") == "title\nbody",
        "commit message internal newline preservation",
    )
    for payload, expected_error, label in (
        (
            correction_subject_bytes + b"\n\n",
            "git commit message terminal newline ambiguity",
            "multiple terminal LF",
        ),
        (correction_subject_bytes + b"\r", "git commit message bytes", "bare CR"),
        (correction_subject_bytes + b"\r\n", "git commit message bytes", "CRLF"),
        (correction_subject_bytes + b"\0", "git commit message bytes", "NUL"),
        (b"\xff", "git commit message UTF-8", "invalid UTF-8"),
    ):
        expect_contract_error(
            lambda value=payload: canonical_commit_message_body(value),
            expected_error,
            "commit message " + label,
        )

    projection = CENTRAL_V5_OWNED_PROJECTION_SHA256
    sorted_future_paths = tuple(
        sorted(FUTURE_EXACT_7_PATHS, key=lambda value: value.encode("utf-8"))
    )
    need(
        declared_scope_projection(
            sorted_future_paths,
            FUTURE_EXACT_7_PATHS,
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
            "HISTORY_AMBIGUITY",
        )
        == FUTURE_EXACT_7_PATHS,
        "future exact-7 count-set then declared-order projection",
    )
    for observed, declared, sequence, expected, label in (
        (
            sorted_future_paths[:-1],
            FUTURE_EXACT_7_PATHS,
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
            "HISTORY_AMBIGUITY",
            "missing authorized path",
        ),
        (
            (*sorted_future_paths, "scripts/unexpected.py"),
            FUTURE_EXACT_7_PATHS,
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
            "HISTORY_AMBIGUITY",
            "unauthorized extra path",
        ),
        (
            (*sorted_future_paths[:-1], sorted_future_paths[0]),
            FUTURE_EXACT_7_PATHS,
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
            "HISTORY_AMBIGUITY",
            "duplicate path",
        ),
        (
            sorted_future_paths,
            tuple(reversed(FUTURE_EXACT_7_PATHS)),
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
            "HISTORY_AMBIGUITY",
            "declared order sequence hash mismatch",
        ),
        (
            (*sorted_future_paths[:-1], "bad\0path"),
            FUTURE_EXACT_7_PATHS,
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
            "HISTORY_AMBIGUITY",
            "NUL path",
        ),
        (
            (*sorted_future_paths[:-1], "bad\udcffpath"),
            FUTURE_EXACT_7_PATHS,
            FUTURE_EXACT_7_PATH_SEQUENCE_SHA256,
            "HISTORY_AMBIGUITY",
            "invalid UTF-8 path",
        ),
    ):
        expect_contract_error(
            lambda actual=observed, declared_values=declared, expected_sha=sequence: (
                declared_scope_projection(
                    actual,
                    declared_values,
                    expected_sha,
                    "HISTORY_AMBIGUITY",
                )
            ),
            expected,
            label,
        )

    correction = HistoryRecord(
        oid=FIRST_COMPATIBILITY_CORRECTION_COMMIT,
        parents=(PUBLISHED_MERGE_COMMIT,),
        subject=COMPATIBILITY_CORRECTION_SUBJECT,
        tree=FIRST_COMPATIBILITY_CORRECTION_TREE,
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256=projection,
        bindings_valid=True,
        correction_delta_valid=True,
    )
    correction_decision = classify_postpublication_history((correction,))
    need(
        correction_decision.compatibility_correction == correction.oid
        and correction_decision.publication_merge is None,
        "exact compatibility correction positive control",
    )
    need(
        working_context(
            PUBLISHED_MERGE_COMMIT,
            COMPATIBILITY_CORRECTION_BRANCH,
            CORRECTION_PATHS,
        )
        == LEGACY_COMPAT_CORRECTION_PRECOMMIT,
        "legacy compatibility correction dirty precommit",
    )
    for altered, expected, label in (
        (
            history_variant(correction, parents=("0" * 40,)),
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "wrong original correction parent",
        ),
        (
            history_variant(correction, changed_paths=(MANIFEST, VALIDATOR)),
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "missing original correction central path",
        ),
        (
            history_variant(correction, central_projection_sha256="0" * 64),
            "UNAUTHORIZED_V5_PROJECTION_CHANGE",
            "original V5 projection drift",
        ),
        (
            history_variant(correction, bindings_valid=False),
            "MANIFEST_HASH_MISMATCH",
            "original manifest hash mismatch",
        ),
        (
            history_variant(correction, correction_delta_valid=False),
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "original central non-pin change",
        ),
    ):
        expect_contract_error(
            lambda record=altered: classify_postpublication_history((record,)),
            expected,
            label,
        )

    publication_merge = HistoryRecord(
        oid=FIRST_COMPATIBILITY_PUBLICATION_MERGE,
        parents=(PUBLISHED_MERGE_COMMIT, correction.oid),
        subject=(
            "Merge pull request #23 from pet-med-ai/"
            + COMPATIBILITY_CORRECTION_BRANCH
            + "\n\n"
            + COMPATIBILITY_CORRECTION_SUBJECT
        ),
        tree=correction.tree,
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256=projection,
        bindings_valid=True,
        correction_delta_valid=True,
    )
    published_records = (correction, publication_merge)
    published_decision = classify_postpublication_history(published_records)
    need(
        published_decision.publication_merge == publication_merge.oid,
        "compatibility publication merge positive control",
    )
    immutable_change = HistoryRecord(
        oid="1" * 40,
        parents=(publication_merge.oid,),
        subject="PMAI-P0-04: Synthetic immutable mutation",
        tree="synthetic-immutable-tree",
        changed_paths=(DOC,),
        second_parent_changed_paths=(),
        central_projection_sha256=None,
        bindings_valid=True,
        correction_delta_valid=False,
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (*published_records, immutable_change)
        ),
        "IMMUTABLE_V5_PACKAGE_MEMBER_MUTATION",
        "dirty old V5 immutable member",
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (
                *published_records,
                history_variant(
                    correction,
                    oid="2" * 40,
                    parents=(publication_merge.oid,),
                ),
            )
        ),
        "SECOND_COMPATIBILITY_CORRECTION",
        "second original compatibility correction",
    )

    discipline = HistoryRecord(
        oid="3" * 40,
        parents=(FIRST_COMPATIBILITY_PUBLICATION_MERGE,),
        subject=DISCIPLINE_CORRECTION_SUBJECT,
        tree="synthetic-discipline-tree",
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256=projection,
        bindings_valid=True,
        correction_delta_valid=False,
        discipline_delta_valid=True,
    )
    discipline_records = (*published_records, discipline)
    discipline_decision = classify_postpublication_history(discipline_records)
    need(
        discipline_decision.discipline_correction == discipline.oid
        and discipline_decision.discipline_publication_merge is None,
        "clean discipline correction commit positive control",
    )
    need(
        working_context(
            FIRST_COMPATIBILITY_PUBLICATION_MERGE,
            DISCIPLINE_CORRECTION_BRANCH,
            CORRECTION_PATHS,
        )
        == DISCIPLINE_CORRECTION_PRECOMMIT,
        "exact discipline dirty precommit positive control",
    )
    for paths, branch, expected, label in (
        (
            (DOC, CENTRAL),
            DISCIPLINE_CORRECTION_BRANCH,
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "dirty old V5 immutable member",
        ),
        (
            (MANIFEST, CENTRAL),
            DISCIPLINE_CORRECTION_BRANCH,
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "dirty old V5 manifest outside exact correction",
        ),
        (
            (VALIDATOR, CENTRAL),
            DISCIPLINE_CORRECTION_BRANCH,
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "dirty old V5 validator outside exact correction",
        ),
        (
            (MANIFEST, VALIDATOR),
            DISCIPLINE_CORRECTION_BRANCH,
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "discipline correction missing central",
        ),
        (
            CORRECTION_PATHS,
            "pmai-p0-04-wrong-discipline-branch",
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "wrong discipline branch",
        ),
    ):
        expect_contract_error(
            lambda observed=paths, observed_branch=branch: working_context(
                FIRST_COMPATIBILITY_PUBLICATION_MERGE,
                observed_branch,
                observed,
            ),
            expected,
            label,
        )
    validate_working_history_context(
        DISCIPLINE_CORRECTION_PRECOMMIT,
        published_decision,
        FIRST_COMPATIBILITY_PUBLICATION_MERGE,
        DISCIPLINE_CORRECTION_BRANCH,
    )
    validate_working_history_context(
        POSTCOMMIT_CLEAN,
        discipline_decision,
        discipline.oid,
        DISCIPLINE_CORRECTION_BRANCH,
    )
    expect_contract_error(
        lambda: working_context(
            discipline.oid,
            DISCIPLINE_CORRECTION_BRANCH,
            (MANIFEST,),
            discipline_decision,
        ),
        "postcommit worktree dirty",
        "committed discipline correction dirty worktree",
    )
    for altered, expected, label in (
        (
            history_variant(discipline, parents=("0" * 40,)),
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "wrong discipline parent",
        ),
        (
            history_variant(discipline, subject="PMAI-P0-04: Wrong discipline"),
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "wrong discipline subject",
        ),
        (
            history_variant(discipline, changed_paths=(MANIFEST, VALIDATOR)),
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "missing discipline central path",
        ),
        (
            history_variant(discipline, central_projection_sha256="4" * 64),
            "UNAUTHORIZED_V5_PROJECTION_CHANGE",
            "discipline V5 projection drift",
        ),
        (
            history_variant(discipline, bindings_valid=False),
            "MANIFEST_HASH_MISMATCH",
            "discipline manifest member hash mismatch",
        ),
        (
            history_variant(discipline, discipline_delta_valid=False),
            "UNAUTHORIZED_V5_CLOSURE_CHANGE",
            "discipline central non-pin or manifest order change",
        ),
    ):
        expect_contract_error(
            lambda record=altered: classify_postpublication_history(
                (*published_records, record)
            ),
            expected,
            label,
        )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (*discipline_records, history_variant(discipline, oid="4" * 40))
        ),
        "SECOND_DISCIPLINE_CORRECTION",
        "second discipline correction",
    )

    discipline_merge = HistoryRecord(
        oid="5" * 40,
        parents=(FIRST_COMPATIBILITY_PUBLICATION_MERGE, discipline.oid),
        subject=(
            "Merge pull request #24 from pet-med-ai/"
            + DISCIPLINE_CORRECTION_BRANCH
            + "\n\n"
            + DISCIPLINE_CORRECTION_SUBJECT
        ),
        tree=discipline.tree,
        changed_paths=CORRECTION_PATHS,
        second_parent_changed_paths=(),
        central_projection_sha256=projection,
        bindings_valid=True,
        correction_delta_valid=False,
        discipline_delta_valid=True,
    )
    discipline_published_records = (*discipline_records, discipline_merge)
    discipline_published_decision = classify_postpublication_history(
        discipline_published_records
    )
    need(
        discipline_published_decision.discipline_publication_merge
        == discipline_merge.oid,
        "discipline publication merge positive control",
    )
    ephemeral_discipline_merge = history_variant(
        discipline_merge,
        oid="6" * 40,
        subject=(
            "Merge "
            + discipline.oid
            + " into "
            + FIRST_COMPATIBILITY_PUBLICATION_MERGE
        ),
        ephemeral_pr_test_merge=True,
    )
    ephemeral_discipline_decision = classify_postpublication_history(
        (*discipline_records, ephemeral_discipline_merge)
    )
    need(
        ephemeral_discipline_decision.discipline_publication_merge is None
        and ephemeral_discipline_decision.ephemeral_pr_test_merge
        == ephemeral_discipline_merge.oid,
        "discipline synthetic PR merge positive control",
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (
                *discipline_records,
                history_variant(
                    ephemeral_discipline_merge,
                    oid="e" * 40,
                    subject=(
                        "Merge "
                        + "0" * 40
                        + " into "
                        + FIRST_COMPATIBILITY_PUBLICATION_MERGE
                    ),
                ),
            )
        ),
        "HISTORY_AMBIGUITY",
        "discipline synthetic PR merge wrong head prefix",
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (
                *discipline_records,
                ephemeral_discipline_merge,
                history_variant(
                    discipline,
                    oid="f" * 40,
                    parents=(ephemeral_discipline_merge.oid,),
                    subject="PMAI-P0-04: Follow-on after ephemeral merge",
                    changed_paths=(CENTRAL,),
                    discipline_delta_valid=False,
                ),
            )
        ),
        "HISTORY_AMBIGUITY",
        "follow-on after discipline synthetic PR merge",
    )
    for altered, label in (
        (
            history_variant(
                discipline_merge,
                parents=(discipline.oid, FIRST_COMPATIBILITY_PUBLICATION_MERGE),
            ),
            "discipline merge reversed parents",
        ),
        (
            history_variant(discipline_merge, tree="wrong-tree"),
            "discipline merge tree",
        ),
        (
            history_variant(
                discipline_merge,
                changed_paths=tuple(reversed(CORRECTION_PATHS)),
            ),
            "discipline merge path order",
        ),
        (
            history_variant(
                discipline_merge,
                second_parent_changed_paths=(CENTRAL,),
            ),
            "discipline merge second-parent diff",
        ),
        (
            history_variant(
                discipline_merge,
                parents=(*discipline_merge.parents, "7" * 40),
            ),
            "discipline octopus merge",
        ),
    ):
        expect_contract_error(
            lambda record=altered: classify_postpublication_history(
                (*discipline_records, record)
            ),
            "HISTORY_AMBIGUITY",
            label,
        )

    expect_contract_error(
        lambda: validate_working_history_context(
            SUCCESSOR_PRECOMMIT_CANDIDATE,
            published_decision,
            publication_merge.oid,
            FUTURE_EXACT_7_BRANCH,
        ),
        "HISTORY_AMBIGUITY",
        "future exact-7 before discipline publication",
    )
    validate_working_history_context(
        SUCCESSOR_PRECOMMIT_CANDIDATE,
        discipline_published_decision,
        discipline_merge.oid,
        FUTURE_EXACT_7_BRANCH,
    )
    need(
        working_context(
            discipline_merge.oid,
            FUTURE_EXACT_7_BRANCH,
            sorted_future_paths,
        )
        == SUCCESSOR_PRECOMMIT_CANDIDATE,
        "exact authorized 7-path dirty successor precommit candidate",
    )
    expect_contract_error(
        lambda: working_context(
            discipline_merge.oid,
            "pmai-p0-04-generic-successor",
            (CENTRAL,),
        ),
        "postcommit worktree dirty",
        "branch regex plus central presence is not authorization",
    )

    successor = HistoryRecord(
        oid="8" * 40,
        parents=(discipline_merge.oid,),
        subject="PMAI-P0-04: Synthetic exact-7 successor",
        tree="synthetic-successor-tree",
        changed_paths=sorted_future_paths,
        second_parent_changed_paths=(),
        central_projection_sha256=projection,
        bindings_valid=True,
        correction_delta_valid=False,
    )
    successor_records = (*discipline_published_records, successor)
    successor_decision = classify_postpublication_history(successor_records)
    need(
        successor_decision.pending_successor == successor.oid
        and successor_decision.successor_central_commits == (successor.oid,),
        "clean exact-7 successor commit positive control",
    )
    expect_contract_error(
        lambda: validate_working_history_context(
            SUCCESSOR_PRECOMMIT_CANDIDATE,
            successor_decision,
            successor.oid,
            FUTURE_EXACT_7_BRANCH,
        ),
        "postcommit worktree dirty",
        "committed successor dirty worktree",
    )
    expect_contract_error(
        lambda: working_context(
            successor.oid,
            FUTURE_EXACT_7_BRANCH,
            (CENTRAL,),
            successor_decision,
        ),
        "postcommit worktree dirty",
        "committed successor incomplete dirty scope",
    )
    for altered, expected, label in (
        (
            history_variant(
                successor,
                changed_paths=tuple(
                    relative
                    for relative in sorted_future_paths
                    if relative != CENTRAL
                ),
            ),
            "HISTORY_AMBIGUITY",
            "successor missing central path",
        ),
        (
            history_variant(
                successor,
                changed_paths=sorted_future_paths[1:],
            ),
            "HISTORY_AMBIGUITY",
            "successor missing path",
        ),
        (
            history_variant(successor, central_projection_sha256="9" * 64),
            "UNAUTHORIZED_V5_PROJECTION_CHANGE",
            "successor V5 projection drift",
        ),
        (
            history_variant(successor, bindings_valid=False),
            "MANIFEST_HASH_MISMATCH",
            "successor manifest hash mismatch",
        ),
        (
            history_variant(
                successor,
                subject=COMPATIBILITY_CORRECTION_SUBJECT,
            ),
            "SECOND_COMPATIBILITY_CORRECTION",
            "successor reserved compatibility subject",
        ),
        (
            history_variant(
                successor,
                subject=DISCIPLINE_CORRECTION_SUBJECT,
            ),
            "SECOND_DISCIPLINE_CORRECTION",
            "successor reserved discipline subject",
        ),
    ):
        expect_contract_error(
            lambda record=altered: classify_postpublication_history(
                (*discipline_published_records, record)
            ),
            expected,
            label,
        )
    for invalid_subject, label in (
        ("", "empty successor subject"),
        (" " + successor.subject, "successor subject leading whitespace"),
        (successor.subject + " ", "successor subject trailing whitespace"),
        (successor.subject + "\nbody", "successor subject extra body"),
        (successor.subject + "\x7f", "successor subject control character"),
    ):
        expect_contract_error(
            lambda subject=invalid_subject: classify_postpublication_history(
                (
                    *discipline_published_records,
                    history_variant(successor, subject=subject),
                )
            ),
            "HISTORY_AMBIGUITY",
            label,
        )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (
                *successor_records,
                history_variant(
                    successor,
                    oid="9" * 40,
                    parents=(successor.oid,),
                ),
            )
        ),
        "HISTORY_AMBIGUITY",
        "parallel pending successor",
    )

    successor_merge = HistoryRecord(
        oid="a" * 40,
        parents=(discipline_merge.oid, successor.oid),
        subject=(
            "Merge pull request #25 from pet-med-ai/"
            + FUTURE_EXACT_7_BRANCH
            + "\n\n"
            + successor.subject
        ),
        tree=successor.tree,
        changed_paths=successor.changed_paths,
        second_parent_changed_paths=(),
        central_projection_sha256=projection,
        bindings_valid=True,
        correction_delta_valid=False,
    )
    successor_published_records = (*successor_records, successor_merge)
    merged_decision = classify_postpublication_history(
        successor_published_records
    )
    need(
        merged_decision.successor_publication_merges == (successor_merge.oid,)
        and merged_decision.pending_successor is None,
        "clean successor publication merge positive control",
    )
    lineage_ancestry_pairs = {
        (PUBLISHED_MERGE_COMMIT, merged_decision.history_lineage[0]),
        *zip(
            merged_decision.history_lineage,
            merged_decision.history_lineage[1:],
        ),
    }
    validate_history_ancestry(
        merged_decision,
        lambda ancestor, descendant: (
            ancestor,
            descendant,
        )
        in lineage_ancestry_pairs,
    )
    missing_ancestry_pair = tuple(
        zip(
            merged_decision.history_lineage,
            merged_decision.history_lineage[1:],
        )
    )[-1]
    expect_contract_error(
        lambda: validate_history_ancestry(
            merged_decision,
            lambda ancestor, descendant: (
                ancestor,
                descendant,
            )
            in lineage_ancestry_pairs
            and (ancestor, descendant) != missing_ancestry_pair,
        ),
        "HISTORY_AMBIGUITY",
        "parallel successor ancestry",
    )
    for altered, label in (
        (
            history_variant(
                successor_merge,
                subject=(
                    "Merge pull request #25 from pet-med-ai/"
                    "pmai-p0-04-wrong-successor\n\n"
                    + successor.subject
                ),
            ),
            "successor merge branch",
        ),
        (
            history_variant(successor_merge, tree="wrong-successor-tree"),
            "successor merge tree",
        ),
        (
            history_variant(
                successor_merge,
                second_parent_changed_paths=(CENTRAL,),
            ),
            "successor merge second-parent diff",
        ),
        (
            history_variant(
                successor_merge,
                parents=(successor.oid, discipline_merge.oid),
            ),
            "successor merge parent order",
        ),
    ):
        expect_contract_error(
            lambda record=altered: classify_postpublication_history(
                (*successor_records, record)
            ),
            "HISTORY_AMBIGUITY",
            label,
        )
    ephemeral_successor_merge = history_variant(
        successor_merge,
        oid="b" * 40,
        subject="Merge " + successor.oid + " into " + discipline_merge.oid,
        ephemeral_pr_test_merge=True,
    )
    ephemeral_successor_decision = classify_postpublication_history(
        (*successor_records, ephemeral_successor_merge)
    )
    need(
        ephemeral_successor_decision.pending_successor == successor.oid
        and ephemeral_successor_decision.ephemeral_pr_test_merge
        == ephemeral_successor_merge.oid,
        "successor synthetic PR merge positive control",
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (
                *successor_records,
                history_variant(
                    ephemeral_successor_merge,
                    oid="1" * 40,
                    subject=(
                        "Merge "
                        + successor.oid
                        + " into "
                        + "0" * 40
                    ),
                ),
            )
        ),
        "HISTORY_AMBIGUITY",
        "successor synthetic PR merge wrong base prefix",
    )
    expect_contract_error(
        lambda: classify_postpublication_history(
            (
                *successor_records,
                ephemeral_successor_merge,
                history_variant(
                    successor,
                    oid="2" * 40,
                    parents=(ephemeral_successor_merge.oid,),
                    subject="PMAI-P0-04: Follow-on after ephemeral successor",
                    changed_paths=(CENTRAL,),
                ),
            )
        ),
        "HISTORY_AMBIGUITY",
        "follow-on after successor synthetic PR merge",
    )
    later_successor = HistoryRecord(
        oid="c" * 40,
        parents=("d" * 40,),
        subject="PMAI-P0-04: Synthetic later central evolution",
        tree="synthetic-later-successor-tree",
        changed_paths=(CENTRAL,),
        second_parent_changed_paths=(),
        central_projection_sha256=projection,
        bindings_valid=True,
        correction_delta_valid=False,
    )
    later_decision = classify_postpublication_history(
        (*successor_published_records, later_successor)
    )
    need(
        later_decision.pending_successor == later_successor.oid
        and pending_successor_branch_valid(
            successor_decision,
            FUTURE_EXACT_7_BRANCH,
        )
        and not pending_successor_branch_valid(
            successor_decision,
            "pmai-p0-04-generic-successor",
        )
        and pending_successor_branch_valid(
            later_decision,
            "pmai-p0-04-generic-successor",
        ),
        "legitimate later central evolution remains compatible",
    )

    clean_snapshot = RepositorySnapshot(
        head="d" * 40,
        tree="e" * 40,
        branch=DISCIPLINE_CORRECTION_BRANCH,
        changed_paths=(),
        path_snapshots=(),
    )
    compare_repository_snapshots(
        POSTCOMMIT_CLEAN,
        clean_snapshot,
        clean_snapshot,
    )
    dirty_postcommit_snapshot = RepositorySnapshot(
        head=clean_snapshot.head,
        tree=clean_snapshot.tree,
        branch=clean_snapshot.branch,
        changed_paths=(CENTRAL,),
        path_snapshots=(),
    )
    expect_contract_error(
        lambda: compare_repository_snapshots(
            POSTCOMMIT_CLEAN,
            clean_snapshot,
            dirty_postcommit_snapshot,
        ),
        "postcommit worktree dirty",
        "postcommit dirty worktree",
    )
    path_snapshot = RepositoryPathSnapshot(
        relative=MANIFEST,
        mode="100644",
        sha256="f" * 64,
        head_entry="100644 " + "0" * 40,
        index_entry="100644 " + "0" * 40,
        worktree_entry="100644 " + "1" * 40,
    )
    unstaged_central_snapshot = RepositoryPathSnapshot(
        relative=CENTRAL,
        mode="100755",
        sha256="e" * 64,
        head_entry="100755 " + "2" * 40,
        index_entry="100755 " + "2" * 40,
        worktree_entry="100755 " + "3" * 40,
    )
    validate_precommit_index_regime(
        (path_snapshot, unstaged_central_snapshot)
    )
    staged_path_snapshot = RepositoryPathSnapshot(
        **{
            **path_snapshot.__dict__,
            "index_entry": path_snapshot.worktree_entry,
        }
    )
    staged_central_snapshot = RepositoryPathSnapshot(
        **{
            **unstaged_central_snapshot.__dict__,
            "index_entry": unstaged_central_snapshot.worktree_entry,
        }
    )
    validate_precommit_index_regime(
        (staged_path_snapshot, staged_central_snapshot)
    )
    expect_contract_error(
        lambda: validate_precommit_index_regime(
            (path_snapshot, staged_central_snapshot)
        ),
        "PRECOMMIT_INDEX_WORKTREE_REGIME_MISMATCH",
        "mixed staged and unstaged index regime",
    )
    expect_contract_error(
        lambda: validate_precommit_index_regime(
            (
                RepositoryPathSnapshot(
                    **{
                        **path_snapshot.__dict__,
                        "index_entry": "100644 " + "9" * 40,
                    }
                ),
            )
        ),
        "PRECOMMIT_INDEX_WORKTREE_REGIME_MISMATCH",
        "third index blob",
    )
    dirty_snapshot = RepositorySnapshot(
        head="1" * 40,
        tree="2" * 40,
        branch=DISCIPLINE_CORRECTION_BRANCH,
        changed_paths=CORRECTION_PATHS,
        path_snapshots=(path_snapshot,),
    )
    compare_repository_snapshots(
        DISCIPLINE_CORRECTION_PRECOMMIT,
        dirty_snapshot,
        dirty_snapshot,
    )
    for altered, label in (
        (
            RepositorySnapshot(
                **{
                    **dirty_snapshot.__dict__,
                    "changed_paths": tuple(reversed(CORRECTION_PATHS)),
                }
            ),
            "path sequence",
        ),
        (
            RepositorySnapshot(
                **{**dirty_snapshot.__dict__, "head": "3" * 40}
            ),
            "head",
        ),
        (
            RepositorySnapshot(
                **{**dirty_snapshot.__dict__, "branch": "wrong-branch"}
            ),
            "branch",
        ),
        (
            RepositorySnapshot(
                **{
                    **dirty_snapshot.__dict__,
                    "path_snapshots": (
                        RepositoryPathSnapshot(
                            **{**path_snapshot.__dict__, "mode": "100755"}
                        ),
                    ),
                }
            ),
            "mode",
        ),
        (
            RepositorySnapshot(
                **{
                    **dirty_snapshot.__dict__,
                    "path_snapshots": (
                        RepositoryPathSnapshot(
                            **{**path_snapshot.__dict__, "sha256": "4" * 64}
                        ),
                    ),
                }
            ),
            "content hash",
        ),
        (
            RepositorySnapshot(
                **{
                    **dirty_snapshot.__dict__,
                    "path_snapshots": (
                        RepositoryPathSnapshot(
                            **{
                                **path_snapshot.__dict__,
                                "index_entry": "UNTRACKED",
                            }
                        ),
                    ),
                }
            ),
            "index entry",
        ),
    ):
        expect_contract_error(
            lambda final=altered: compare_repository_snapshots(
                DISCIPLINE_CORRECTION_PRECOMMIT,
                dirty_snapshot,
                final,
            ),
            "PRECOMMIT_INITIAL_FINAL_PATH_MODE_OR_CONTENT_DRIFT",
            "precommit snapshot " + label + " drift",
        )
    expect_contract_error(
        lambda: compare_repository_snapshots(
            INVALID,
            clean_snapshot,
            clean_snapshot,
        ),
        "INVALID",
        "invalid repository phase",
    )


def validate_modes() -> None:
    for relative in PACKAGE_PATHS:
        candidate = path(relative)
        need(candidate.is_file() and not candidate.is_symlink(), "unsafe file " + relative)
        expected_mode = 0o755 if relative in {ADAPTER, VALIDATOR, REVIEWER} else 0o644
        need(stat.S_IMODE(candidate.stat().st_mode) == expected_mode, "file mode " + relative)
    central_path = path(CENTRAL)
    need(central_path.is_file() and not central_path.is_symlink(), "unsafe central")
    need(stat.S_IMODE(central_path.stat().st_mode) == 0o755, "central mode")


def validate_v4_protection() -> None:
    for relative, expected in V4_PROTECTED_HASHES.items():
        candidate = path(relative)
        need(candidate.is_file() and not candidate.is_symlink(), "protected V4 path " + relative)
        need(digest(relative) == expected, "protected V4 hash " + relative)
    need(not path(ACTIVE_RUNNER).exists(), "active runner present")
    need(
        not list((ROOT / "backend/migrations/versions").glob("0010*.py")),
        "active migration 0010 present",
    )


def validate_successor_test_matrix() -> None:
    raw = path(TEST_MATRIX).read_bytes()
    need(len(raw) > LEGACY_TEST_MATRIX_PREFIX_BYTES, "successor test matrix length")
    legacy = raw[:LEGACY_TEST_MATRIX_PREFIX_BYTES]
    need(legacy.endswith(b"\n"), "legacy test matrix terminal LF")
    need(
        hashlib.sha256(legacy).hexdigest() == LEGACY_TEST_MATRIX_PREFIX_SHA256,
        "legacy T001 through T251 semantic bytes",
    )
    expected_suffix = "".join(
        ",".join(
            (
                "PMAI-P0-04-ARR-V3-SRBE-V5-PREP-" + test_id,
                scenario,
                method,
                expected,
                "DESIGNED",
                "HOLD_NO_COMMIT",
            )
        )
        + "\n"
        for test_id, scenario, method, expected in REQUIRED_SUCCESSOR_TEST_SEMANTICS
    ).encode("utf-8")
    need(raw[LEGACY_TEST_MATRIX_PREFIX_BYTES:] == expected_suffix, "T252 through T267 exact semantics")
    with path(TEST_MATRIX).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    need(len(rows) == 268, "test matrix exact row count")
    need(
        [row[0] for row in rows[1:]]
        == [
            f"PMAI-P0-04-ARR-V3-SRBE-V5-PREP-T{index:03d}"
            for index in range(1, 268)
        ],
        "test matrix contiguous IDs",
    )
    expected_rows = [
        [
            "PMAI-P0-04-ARR-V3-SRBE-V5-PREP-" + test_id,
            scenario,
            method,
            expected,
            "DESIGNED",
            "HOLD_NO_COMMIT",
        ]
        for test_id, scenario, method, expected in REQUIRED_SUCCESSOR_TEST_SEMANTICS
    ]
    need(rows[252:] == expected_rows, "test matrix semantic row mapping")
    v4_source = text(V4_VALIDATOR)
    for semantic_token in (
        "commit message no terminal LF positive control",
        "commit message single terminal LF positive control",
        "multiple terminal LF",
        "bare CR",
        "CRLF",
        "invalid UTF-8",
        "SECOND_REPAIR_PACKAGE_MUTATION",
        "UNAUTHORIZED_CLOSURE_CHANGE",
        "UNAUTHORIZED_V4_PROJECTION_CHANGE",
        "LEGITIMATE_SUCCESSOR_CENTRAL_EVOLUTION_NOT_COUNTED_AS_V4_REPAIR",
        "parallel successor ancestry",
        "transparent successor publication merge positive control",
    ):
        need(semantic_token in v4_source, "pinned V4 semantic coverage " + semantic_token)


def validate_contract_artifacts() -> None:
    document = text(DOC)
    required_document_values = (
        "package_record_id=" + PACKAGE_RECORD_ID,
        "package_record_id_sha256=" + PACKAGE_RECORD_ID_SHA256,
        "package_recorded_date=2026-08-29",
        "base_commit=" + BASE_COMMIT,
        "base_tree_sha=" + BASE_TREE,
        "source_pull_request=" + str(SOURCE_PULL_REQUEST),
        "base_github_ci_run_id=" + str(SOURCE_CI_RUN_ID),
        "base_github_ci_run_number=" + str(SOURCE_CI_RUN_NUMBER),
        "base_github_ci_event=" + SOURCE_CI_EVENT,
        "base_github_ci_run_attempt=" + str(SOURCE_CI_ATTEMPT),
        "base_github_ci_terminal_status=" + SOURCE_CI_STATUS,
        "base_github_ci_conclusion=" + SOURCE_CI_CONCLUSION,
        "head_branch=" + HEAD_BRANCH,
        "commit_message=" + COMMIT_MESSAGE,
        "authorization_id=" + AUTHORIZATION_ID,
        "authorization_id_sha256=" + AUTHORIZATION_ID_SHA256,
        "current_v4_owned_central_projection_sha256=" + CENTRAL_V4_OWNED_PROJECTION_SHA256,
        "held_v5_commit_must_not_be_replacement_ancestor=true",
        "changed_path_sequence_sha256=" + EXPECTED_PATH_SEQUENCE_SHA256,
        "expected_pre_restore_empty_schema_manifest_sha256=" + EXPECTED_EMPTY_SCHEMA_SHA256,
        "expected_post_restore_schema_manifest_sha256=UNBOUND",
        "prior_v4_collection_attempts_consumed=0",
        "prior_v4_confirmation_superseded_for_all_future_live_execution=true",
        "v5_live_execution_authorized=false",
        "v5_current_attempts_authorized=0",
        "repository_patch_consumes_no_collection_attempt=true",
        "repository_commit_oid",
        "repository_tree_oid",
        "operator_run_id_sha256",
        "operator_ipv4_cidr_32_sha256",
        "expected_target_provider_identity_sha256",
        "expected_production_provider_identity_sha256",
        "expected_staging_provider_identity_sha256",
        "execution_harness_sha256",
        "independent_attestation_hmac_key_id_sha256",
        "HOLD_NO_LIVE_EXECUTION",
        "Render_access=false",
        "database_connection=false",
        "credential_access=false",
        "pull_request_creation=false",
        "merge=false",
    )
    for value in required_document_values:
        need(document.count(value) >= 1, "document value " + value)

    procedure_match = re.search(
        r"operational_collection_procedure_contract_begin\n\n~~~text\n"
        r"(.*?)~~~\n\noperational_collection_procedure_contract_end",
        document,
        flags=re.DOTALL,
    )
    need(procedure_match is not None, "procedure contract fence")
    procedure_bytes = procedure_match.group(1).encode("utf-8")
    need(procedure_bytes.endswith(b"\n"), "procedure trailing LF")
    need(hashlib.sha256(procedure_bytes).hexdigest() == PROCEDURE_CONTRACT_SHA256, "procedure hash")

    pointer = json_no_duplicates(POINTER)
    need(isinstance(pointer, dict), "pointer object")
    expected_pointer = {
        "active_package_record_id": PACKAGE_RECORD_ID,
        "active_package_record_id_sha256": PACKAGE_RECORD_ID_SHA256,
        "package_recorded_date": "2026-08-29",
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "source_pull_request": SOURCE_PULL_REQUEST,
        "base_github_ci_run_id": SOURCE_CI_RUN_ID,
        "base_github_ci_run_number": SOURCE_CI_RUN_NUMBER,
        "base_github_ci_status": "PASS",
        "base_github_ci_event": SOURCE_CI_EVENT,
        "base_github_ci_run_attempt": SOURCE_CI_ATTEMPT,
        "base_github_ci_terminal_status": SOURCE_CI_STATUS,
        "base_github_ci_conclusion": SOURCE_CI_CONCLUSION,
        "head_branch": HEAD_BRANCH,
        "commit_message": COMMIT_MESSAGE,
        "authorization_id": AUTHORIZATION_ID,
        "authorization_id_sha256": AUTHORIZATION_ID_SHA256,
        "base_central_validator_sha256": BASE_CENTRAL_SHA256,
        "current_v4_owned_central_projection_sha256": CENTRAL_V4_OWNED_PROJECTION_SHA256,
        "held_v5_commit_must_not_be_replacement_ancestor": True,
        "changed_path_sequence_sha256": EXPECTED_PATH_SEQUENCE_SHA256,
        "prior_v4_confirmation_external_access_started": False,
        "prior_v4_collection_attempts_consumed": 0,
        "prior_v4_confirmation_superseded_for_all_future_live_execution": True,
        "prior_v4_attempt_entitlement_carried_forward": False,
        "prior_v4_confirmation_reuse_allowed": False,
        "preserve_current_v4_immutable_package_members_byte_exact": True,
        "v5_live_execution_authorized": False,
        "v5_current_attempts_authorized": 0,
        "repository_patch_consumes_no_collection_attempt": True,
        "expected_pre_restore_empty_schema_manifest_sha256": EXPECTED_EMPTY_SCHEMA_SHA256,
        "expected_post_restore_schema_manifest_sha256": "UNBOUND",
        "operational_collection_procedure_contract_sha256": PROCEDURE_CONTRACT_SHA256,
        "tls_readonly_contract_sha256": TLS_READONLY_CONTRACT_SHA256,
        "post_merge_new_ci_and_new_v5_single_use_live_confirmation_required": True,
    }
    for key, expected in expected_pointer.items():
        need(pointer.get(key) == expected, "pointer " + key)

    baseline = json_no_duplicates(BASELINE)
    need(isinstance(baseline, dict), "baseline object")
    need(baseline.get("current_execution_decision") == "HOLD_NO_LIVE_EXECUTION", "baseline decision")
    repository_anchor = baseline.get("repository_anchor")
    authorization = baseline.get("authorization")
    v4_disposition = baseline.get("v4_disposition")
    held_v5_disposition = baseline.get("held_v5_disposition")
    v5_execution = baseline.get("v5_execution_state")
    identity = baseline.get("identity_contract")
    schema = baseline.get("schema_contract")
    output = baseline.get("output_contract")
    operational = baseline.get("operational_contract")
    prohibitions = baseline.get("repository_only_prohibitions")
    for value in (
        repository_anchor,
        authorization,
        v4_disposition,
        held_v5_disposition,
        v5_execution,
        identity,
        schema,
        output,
        operational,
        prohibitions,
    ):
        need(isinstance(value, dict), "baseline nested object")
    need(repository_anchor["base_commit"] == BASE_COMMIT, "baseline base commit")
    need(repository_anchor["base_tree_sha"] == BASE_TREE, "baseline base tree")
    need(tuple(repository_anchor[key] for key in ("base_parent_1", "base_parent_2")) == BASE_PARENTS, "baseline base parents")
    need(repository_anchor["source_pull_request"] == SOURCE_PULL_REQUEST, "baseline source PR")
    need(repository_anchor["base_github_ci_run_id"] == SOURCE_CI_RUN_ID, "baseline CI run")
    need(repository_anchor["base_github_ci_run_number"] == SOURCE_CI_RUN_NUMBER, "baseline CI number")
    need(repository_anchor["base_github_ci_event"] == SOURCE_CI_EVENT, "baseline CI event")
    need(repository_anchor["base_github_ci_run_attempt"] == SOURCE_CI_ATTEMPT, "baseline CI attempt")
    need(repository_anchor["base_github_ci_terminal_status"] == SOURCE_CI_STATUS, "baseline CI terminal status")
    need(repository_anchor["base_github_ci_conclusion"] == SOURCE_CI_CONCLUSION, "baseline CI conclusion")
    need(repository_anchor["base_central_validator_sha256"] == BASE_CENTRAL_SHA256, "baseline central hash")
    need(repository_anchor["head_branch"] == HEAD_BRANCH, "baseline branch")
    need(repository_anchor["commit_message"] == COMMIT_MESSAGE, "baseline commit message")
    need(authorization["authorization_id"] == AUTHORIZATION_ID, "baseline authorization")
    need(authorization["authorization_id_sha256"] == AUTHORIZATION_ID_SHA256, "baseline authorization hash")
    need(authorization["changed_path_sequence_sha256"] == EXPECTED_PATH_SEQUENCE_SHA256, "baseline path hash")
    need(authorization["maximum_changed_path_count"] == 13, "baseline path count")
    need(authorization["package_path_count"] == 12, "baseline package count")
    need(authorization["manifest_member_count"] == 11, "baseline manifest count")
    need(authorization["manifest_self_excluded"] is True, "baseline manifest self")
    need(authorization["maximum_fast_forward_push_count"] == 0, "baseline no push count")
    need(authorization["repository_push_authorized"] is False, "baseline no push")
    need(authorization["bundle_export_authorized"] is False, "baseline no bundle")
    need(v4_disposition["prior_v4_collection_attempts_consumed"] == 0, "baseline V4 attempts")
    need(v4_disposition["prior_v4_confirmation_superseded_for_all_future_live_execution"] is True, "baseline V4 superseded")
    need(v4_disposition["preserve_current_v4_immutable_package_members_byte_exact"] is True, "baseline V4 preserve")
    need(v4_disposition["historical_repair_commit"] == "e410804fd21aa0c7bf57040b088543190d442fc9", "baseline unique repair")
    need(v4_disposition["compatibility_correction_commit"] == BASE_PARENTS[1], "baseline compatibility correction")
    need(v4_disposition["compatibility_merge_commit"] == BASE_COMMIT, "baseline compatibility merge")
    need(v4_disposition["current_validator_sha256"] == V4_PROTECTED_HASHES[V4_VALIDATOR], "baseline V4 validator hash")
    need(v4_disposition["current_manifest_sha256"] == V4_PROTECTED_HASHES[V4_PREFIX + "_PACKAGE_MANIFEST_V1.json"], "baseline V4 manifest hash")
    need(v4_disposition["current_owned_central_projection_sha256"] == CENTRAL_V4_OWNED_PROJECTION_SHA256, "baseline V4 projection")
    need(held_v5_disposition == {
        "branch": "pmai-p0-04-arr-v3-srbe-v5-operational-adapter-prep",
        "commit": HELD_V5_COMMIT,
        "tree": HELD_V5_TREE,
        "parent": HELD_V5_PARENT,
        "result": "HOLD_NO_AMEND_NO_RETRY_NO_PUSH",
        "attempt_consumed": True,
        "entitlement_carried_forward": False,
        "reuse_allowed": False,
        "commit_must_not_be_replacement_ancestor": True,
        "preserve_commit_and_tree_byte_exact": True,
    }, "baseline held V5 disposition")
    need(v5_execution["v5_live_execution_authorized"] is False, "baseline V5 live")
    need(v5_execution["v5_current_attempts_authorized"] == 0, "baseline V5 attempts")
    need(v5_execution["repository_patch_consumes_no_collection_attempt"] is True, "baseline attempt consumption")
    need(identity["target_production_staging_provider_identity_domain"] == "PROVIDER_CONNECTION_TUPLE_V5", "baseline provider domain")
    need(identity["database_observed_identity_domain"] == "DATABASE_OBSERVED_IDENTITY_V5", "baseline database domain")
    need(identity["database_observed_identity_may_substitute_provider_identity"] is False, "baseline domain substitution")
    need(identity["tls_readonly_contract_sha256"] == TLS_READONLY_CONTRACT_SHA256, "baseline TLS hash")
    need(schema["expected_pre_restore_empty_schema_manifest_sha256"] == EXPECTED_EMPTY_SCHEMA_SHA256, "baseline empty schema")
    need(schema["expected_post_restore_schema_manifest_sha256"] == "UNBOUND", "baseline postrestore")
    for key in (
        "post_restore_schema_evidence_collected",
        "runtime_binding_contract_complete",
        "srbe_collection_evidence_complete",
        "evidence_complete",
    ):
        need(schema[key] is False, "baseline schema flag " + key)
    need(output["success_and_failure_envelopes_mutually_exclusive"] is True, "baseline envelopes")
    need(operational["operational_collection_procedure_contract_sha256"] == PROCEDURE_CONTRACT_SHA256, "baseline procedure")
    for key in (
        "Render_access",
        "database_connection",
        "credential_access",
        "allowlist_mutation_execution",
        "dependency_install_or_lockfile_change",
        "runner_creation_activation_import_or_execution",
        "backup_access",
        "restore_execution",
        "migration_creation_or_execution",
        "deployment",
        "target_deletion",
    ):
        need(prohibitions[key] is False, "baseline prohibition " + key)

    for relative, expected_header, expected_status in (
        (
            CHECKLIST,
            ["item_id", "control", "required", "repository_observation", "current_status", "decision_if_failed"],
            {"PASS", "DESIGNED", "HOLD_LIVE"},
        ),
        (
            GO_NO_GO,
            ["gate_id", "gate", "required", "current", "status", "decision_if_failed"],
            {"PASS", "DESIGNED", "HOLD_LIVE"},
        ),
        (
            TEST_MATRIX,
            ["test_id", "scenario", "method", "expected", "status", "decision_if_failed"],
            {"DESIGNED"},
        ),
    ):
        with path(relative).open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        need(len(rows) >= 2 and rows[0] == expected_header, "CSV header " + relative)
        need(all(len(row) == 6 for row in rows), "CSV width " + relative)
        need(len({row[0] for row in rows[1:]}) == len(rows) - 1, "CSV ids " + relative)
        need(all(row[4] in expected_status for row in rows[1:]), "CSV status " + relative)


def expected_hold_state_all_of() -> list[dict[str, object]]:
    return [
        {
            "if": {
                "required": ["state_provenance"],
                "properties": {
                    "state_provenance": {"const": "UNVERIFIED_REVIEW_INPUT"}
                },
            },
            "then": {
                "properties": {
                    "attempt_state": {"const": "UNCERTAIN"},
                    "attempt_reserved": {"const": True},
                    "collection_attempt_consumed": {"const": True},
                    "cleanup_required": {"const": True},
                    "cleanup_completed": {"const": False},
                    "final_network_state_verified": {"const": False},
                }
            },
        },
        {
            "if": {
                "required": ["state_provenance"],
                "properties": {
                    "state_provenance": {"const": "ADAPTER_STATE_MACHINE"}
                },
            },
            "then": {
                "oneOf": [
                    {
                        "properties": {
                            "attempt_state": {"const": "KNOWN_NOT_STARTED"},
                            "attempt_reserved": {"const": False},
                            "collection_attempt_consumed": {"const": False},
                            "cleanup_required": {"const": False},
                            "cleanup_completed": {"const": False},
                            "final_network_state_verified": {"const": False},
                        }
                    },
                    {
                        "allOf": [
                            {
                                "properties": {
                                    "attempt_state": {"const": "CONSUMED"},
                                    "attempt_reserved": {"const": True},
                                    "collection_attempt_consumed": {"const": True},
                                }
                            },
                            {
                                "oneOf": [
                                    {
                                        "properties": {
                                            "cleanup_required": {"const": False},
                                            "cleanup_completed": {"const": False},
                                            "final_network_state_verified": {"const": False},
                                        }
                                    },
                                    {
                                        "properties": {
                                            "cleanup_required": {"const": True},
                                            "cleanup_completed": {"const": True},
                                            "final_network_state_verified": {"const": True},
                                        }
                                    },
                                    {
                                        "properties": {
                                            "cleanup_required": {"const": True},
                                            "cleanup_completed": {"const": False},
                                            "final_network_state_verified": {"const": False},
                                        }
                                    },
                                ]
                            },
                        ]
                    },
                    {
                        "properties": {
                            "attempt_state": {"const": "UNCERTAIN"},
                            "attempt_reserved": {"const": True},
                            "collection_attempt_consumed": {"const": True},
                            "cleanup_required": {"const": True},
                            "cleanup_completed": {"const": False},
                            "final_network_state_verified": {"const": False},
                        }
                    },
                ]
            },
        },
    ]


def validate_json_schemas() -> None:
    runtime = json_no_duplicates(RUNTIME_SCHEMA)
    result = json_no_duplicates(RESULT_SCHEMA)
    need(isinstance(runtime, dict) and isinstance(result, dict), "schema objects")
    need(runtime.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "runtime draft")
    need(runtime.get("$id") == RUNTIME_SCHEMA_URN, "runtime id")
    need(
        runtime.get("title")
        == "PMAI P0-04 SRBE V5 sanitized runtime observation",
        "runtime title",
    )
    need(runtime.get("type") == "object", "runtime type")
    need(runtime.get("additionalProperties") is False, "runtime additional properties")
    runtime_required = runtime.get("required")
    runtime_properties = runtime.get("properties")
    need(isinstance(runtime_required, list) and isinstance(runtime_properties, dict), "runtime keys")
    need(set(runtime_required) == set(runtime_properties), "runtime required/property closure")
    need(set(runtime_required) == SUCCESS_KEYS - {"outcome"}, "runtime success key relation")

    need(result.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "result draft")
    need(result.get("$id") == RESULT_SCHEMA_URN, "result id")
    need(
        result.get("title") == "PMAI P0-04 SRBE V5 sanitized collection result",
        "result title",
    )
    need(result.get("oneOf") == [{"$ref": "#/$defs/successEnvelope"}, {"$ref": "#/$defs/holdEnvelope"}], "result oneOf")
    definitions = result.get("$defs")
    need(isinstance(definitions, dict), "result definitions")
    success = definitions.get("successEnvelope")
    failure = definitions.get("holdEnvelope")
    need(isinstance(success, dict) and isinstance(failure, dict), "result envelopes")
    for envelope, expected in ((success, SUCCESS_KEYS), (failure, FAILURE_KEYS)):
        need(envelope.get("type") == "object", "envelope type")
        need(envelope.get("additionalProperties") is False, "envelope additional properties")
        required = envelope.get("required")
        properties = envelope.get("properties")
        need(isinstance(required, list) and isinstance(properties, dict), "envelope keys")
        need(set(required) == set(properties) == expected, "envelope key closure")

    success_properties = success["properties"]
    failure_properties = failure["properties"]
    need(success_properties["schema"].get("const") == RESULT_SCHEMA_ID, "success schema")
    need(success_properties["outcome"].get("const") == "SUCCESS", "success outcome")
    need(failure_properties["schema"].get("const") == RESULT_SCHEMA_ID, "failure schema")
    need(failure_properties["outcome"].get("const") == "HOLD", "failure outcome")
    need(
        failure_properties["attempt_state"].get("enum")
        == ["KNOWN_NOT_STARTED", "CONSUMED", "UNCERTAIN"],
        "failure attempt state enum",
    )
    need(
        failure_properties["state_provenance"].get("enum")
        == ["ADAPTER_STATE_MACHINE", "UNVERIFIED_REVIEW_INPUT"],
        "failure provenance enum",
    )
    need(failure.get("allOf") == expected_hold_state_all_of(), "failure state invariants")
    need(success_properties["expected_pre_restore_schema_manifest_sha256"].get("const") == EXPECTED_EMPTY_SCHEMA_SHA256, "success expected empty")
    need(success_properties["pre_restore_schema_manifest_sha256"].get("const") == EXPECTED_EMPTY_SCHEMA_SHA256, "success observed empty")
    need(success_properties["expected_post_restore_schema_manifest_sha256"].get("const") == "UNBOUND", "success postrestore")
    for key in (
        "post_restore_schema_evidence_collected",
        "runtime_binding_contract_complete",
        "srbe_collection_evidence_complete",
        "evidence_complete",
        "raw_connection_values_disclosed",
        "fixture_only",
    ):
        need(success_properties[key].get("const") is False, "success false " + key)
    need(success_properties["pre_restore_readonly_collection_complete"].get("const") is True, "success pre-restore complete")
    need(failure_properties["hold"].get("const") is True, "failure hold")
    need(failure_properties["runtime_evidence_emitted"].get("const") is False, "failure evidence")
    need(failure_properties["raw_connection_values_disclosed"].get("const") is False, "failure raw")
    error_values = failure_properties["error_code"].get("enum")
    stage_values = failure_properties["stage_code"].get("enum")
    need(
        isinstance(error_values, list)
        and len(error_values) == len(ERROR_CODES)
        and set(error_values) == ERROR_CODES,
        "failure exact error codes",
    )
    need(
        isinstance(stage_values, list)
        and len(stage_values) == len(STAGE_CODES)
        and set(stage_values) == STAGE_CODES,
        "failure exact stage codes",
    )


def assigned_literal(tree: ast.AST, name: str) -> object:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValidationError("missing literal " + name)


def top_level_assignment_value(tree: ast.Module, name: str) -> ast.expr:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return node.value
    raise ValidationError("missing top-level assignment " + name)


def function_contract_dict(
    tree: ast.Module,
    name: str,
    named_values: Mapping[str, object],
) -> dict[str, object]:
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == name
        ),
        None,
    )
    need(function is not None and len(function.body) == 1, "contract function " + name)
    statement = function.body[0]
    need(isinstance(statement, ast.Return), "contract function return " + name)
    outer = statement.value
    need(
        isinstance(outer, ast.Call)
        and isinstance(outer.func, ast.Name)
        and outer.func.id == "sha256_bytes"
        and len(outer.args) == 1
        and not outer.keywords,
        "contract outer hash " + name,
    )
    canonical = outer.args[0]
    need(
        isinstance(canonical, ast.Call)
        and isinstance(canonical.func, ast.Name)
        and canonical.func.id == "canonical_json_bytes"
        and len(canonical.args) == 1
        and not canonical.keywords
        and isinstance(canonical.args[0], ast.Dict),
        "contract canonical dict " + name,
    )
    result: dict[str, object] = {}
    for key_node, value_node in zip(
        canonical.args[0].keys,
        canonical.args[0].values,
        strict=True,
    ):
        need(
            isinstance(key_node, ast.Constant)
            and isinstance(key_node.value, str),
            "contract key " + name,
        )
        if isinstance(value_node, ast.Constant):
            value = value_node.value
        elif isinstance(value_node, ast.Name) and value_node.id in named_values:
            value = named_values[value_node.id]
        else:
            raise ValidationError("contract value " + name + " " + key_node.value)
        need(key_node.value not in result, "contract duplicate key " + name)
        result[key_node.value] = value
    return result


def assigned_string_set(tree: ast.AST, name: str) -> set[str]:
    need(isinstance(tree, ast.Module), "string set module " + name)

    def evaluate(value_node: ast.expr, resolving: frozenset[str]) -> set[str]:
        if (
            isinstance(value_node, ast.Call)
            and isinstance(value_node.func, ast.Name)
            and value_node.func.id == "frozenset"
            and len(value_node.args) == 1
            and not value_node.keywords
        ):
            return evaluate(value_node.args[0], resolving)
        if isinstance(value_node, ast.Name):
            need(
                value_node.id not in resolving,
                "cyclic string set " + value_node.id,
            )
            return evaluate(
                top_level_assignment_value(tree, value_node.id),
                resolving | {value_node.id},
            )
        if isinstance(value_node, ast.BinOp) and isinstance(
            value_node.op,
            (ast.BitOr, ast.Sub),
        ):
            left = evaluate(value_node.left, resolving)
            right = evaluate(value_node.right, resolving)
            return left | right if isinstance(value_node.op, ast.BitOr) else left - right
        if isinstance(value_node, (ast.Set, ast.List, ast.Tuple)):
            items: list[str] = []
            for element in value_node.elts:
                need(
                    isinstance(element, ast.Constant)
                    and isinstance(element.value, str),
                    "string set literal " + name,
                )
                items.append(element.value)
            need(len(set(items)) == len(items), "duplicate string set member " + name)
            return set(items)
        raise ValidationError("unsupported string set expression " + name)

    return evaluate(top_level_assignment_value(tree, name), frozenset({name}))


def validate_python_sources() -> None:
    allowed_imports = {
        ADAPTER: {
            "__future__",
            "argparse",
            "dataclasses",
            "datetime",
            "hashlib",
            "hmac",
            "ipaddress",
            "json",
            "os",
            "pathlib",
            "re",
            "stat",
            "sys",
            "tempfile",
            "typing",
            "unicodedata",
        },
        REVIEWER: {
            "__future__",
            "argparse",
            "hashlib",
            "hmac",
            "json",
            "os",
            "pathlib",
            "re",
            "stat",
            "sys",
            "tempfile",
            "typing",
        },
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "breakpoint"}
    banned_modules = {
        "asyncpg",
        "ctypes",
        "http",
        "importlib",
        "psycopg",
        "psycopg2",
        "requests",
        "socket",
        "sqlalchemy",
        "subprocess",
        "urllib",
    }
    for relative, allowed in allowed_imports.items():
        source = text(relative)
        tree = ast.parse(source, filename=relative)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                need(node.level == 0 and node.module is not None, "relative import " + relative)
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                need(node.func.id not in banned_calls, "dynamic call " + relative)
        need(imports == allowed, "exact imports " + relative)
        need(not (imports & banned_modules), "banned import " + relative)
        need("time.sleep" not in source and "backoff" not in source, "retry primitive " + relative)
        need("validate_isolated_invocation" in source or "validate_invocation_contract" in source, "isolated invocation " + relative)

    adapter_source = text(ADAPTER)
    adapter_tree = ast.parse(adapter_source, filename=ADAPTER)
    reviewer_source = text(REVIEWER)
    reviewer_tree = ast.parse(reviewer_source, filename=REVIEWER)
    need(set(assigned_literal(adapter_tree, "SUCCESS_KEYS")) == SUCCESS_KEYS, "adapter success keys")
    need(set(assigned_literal(adapter_tree, "FAILURE_KEYS")) == FAILURE_KEYS, "adapter failure keys")
    need(assigned_string_set(adapter_tree, "ERROR_CODES") == ERROR_CODES, "adapter exact error codes")
    need(assigned_string_set(adapter_tree, "STAGE_CODES") == STAGE_CODES, "adapter exact stage codes")
    for script_name, script_tree in (
        ("adapter", adapter_tree),
        ("reviewer", reviewer_tree),
    ):
        for sql_name, expected_sql in EXPECTED_FIXED_SQL.items():
            need(
                assigned_literal(script_tree, sql_name) == expected_sql,
                script_name + " exact fixed SQL " + sql_name,
            )
    need(
        tuple(assigned_literal(adapter_tree, "FIXED_SQL_ORDER"))
        == EXPECTED_FIXED_SQL_ORDER,
        "adapter fixed SQL order",
    )
    adapter_sql_map = top_level_assignment_value(adapter_tree, "FIXED_SQL")
    need(isinstance(adapter_sql_map, ast.Dict), "adapter fixed SQL map")
    observed_adapter_sql_map: dict[str, str] = {}
    for key_node, value_node in zip(
        adapter_sql_map.keys,
        adapter_sql_map.values,
        strict=True,
    ):
        need(
            isinstance(key_node, ast.Constant)
            and isinstance(key_node.value, str)
            and isinstance(value_node, ast.Name),
            "adapter fixed SQL map entry",
        )
        observed_adapter_sql_map[key_node.value] = value_node.id
    expected_sql_name_map = {
        statement_id: "SQL_" + statement_id
        for statement_id in EXPECTED_FIXED_SQL_ORDER
    }
    need(
        observed_adapter_sql_map == expected_sql_name_map,
        "adapter fixed SQL map closure",
    )
    reviewer_sql_sequence = top_level_assignment_value(reviewer_tree, "FIXED_SQL")
    need(
        isinstance(reviewer_sql_sequence, ast.Tuple)
        and len(reviewer_sql_sequence.elts) == len(EXPECTED_FIXED_SQL_ORDER),
        "reviewer fixed SQL sequence",
    )
    for item, statement_id in zip(
        reviewer_sql_sequence.elts,
        EXPECTED_FIXED_SQL_ORDER,
        strict=True,
    ):
        need(
            isinstance(item, ast.Tuple)
            and len(item.elts) == 2
            and isinstance(item.elts[0], ast.Constant)
            and item.elts[0].value == statement_id
            and isinstance(item.elts[1], ast.Name)
            and item.elts[1].id == "SQL_" + statement_id,
            "reviewer fixed SQL order " + statement_id,
        )
    fixed_sql_trace = {
        "schema": "PMAI_P0_04_SRBE_V5_FIXED_SQL_TRACE_V1",
        "statements": [
            {
                "sql_sha256": hashlib.sha256(
                    EXPECTED_FIXED_SQL["SQL_" + statement_id].encode("ascii")
                ).hexdigest(),
                "statement_id": statement_id,
            }
            for statement_id in EXPECTED_FIXED_SQL_ORDER
        ],
    }
    fixed_sql_trace_bytes = json.dumps(
        fixed_sql_trace,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    need(
        hashlib.sha256(fixed_sql_trace_bytes).hexdigest()
        == FIXED_SQL_TRACE_SHA256,
        "fixed SQL trace hash",
    )
    expected_tls_contract = {
        "begin_read_only": True,
        "connect_timeout_seconds": 10,
        "idle_transaction_timeout_ms": 5000,
        "lock_timeout_ms": 1000,
        "schema": "PMAI_P0_04_SRBE_V5_TLS_READONLY_CONTRACT_V2",
        "search_path": "pg_catalog",
        "session_default_read_only": True,
        "sslmode": "verify-full",
        "statement_timeout_ms": 5000,
        "verify_certificate": True,
        "verify_hostname": True,
    }
    need(
        assigned_literal(adapter_tree, "CONNECT_TIMEOUT_SECONDS") == 10,
        "adapter connect timeout",
    )
    need(
        function_contract_dict(
            adapter_tree,
            "tls_readonly_contract_sha256",
            {"CONNECT_TIMEOUT_SECONDS": 10},
        )
        == expected_tls_contract,
        "adapter TLS contract",
    )
    need(
        function_contract_dict(
            reviewer_tree,
            "tls_readonly_contract_sha256",
            {},
        )
        == expected_tls_contract,
        "reviewer TLS contract",
    )
    tls_contract_bytes = json.dumps(
        expected_tls_contract,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    need(
        hashlib.sha256(tls_contract_bytes).hexdigest()
        == TLS_READONLY_CONTRACT_SHA256,
        "TLS read-only contract hash",
    )
    need("SHOW transaction_read_only" not in adapter_source, "unlocked readonly SQL")
    need("class RenderPort(Protocol)" in adapter_source, "RenderPort protocol")
    need("class DatabasePort(Protocol)" in adapter_source, "DatabasePort protocol")
    need("class AttemptLedgerPort(Protocol)" in adapter_source, "AttemptLedgerPort protocol")
    need("class CleanupSupervisorPort(Protocol)" in adapter_source, "CleanupSupervisorPort protocol")
    need("class RuntimeProvenancePort(Protocol)" in adapter_source, "RuntimeProvenancePort protocol")
    need(
        "class SyntheticReferenceFileAttemptLedger:" in adapter_source
        and "never a future live ledger implementation" in adapter_source,
        "synthetic-only ledger boundary",
    )
    need("class FileAttemptLedger:" not in adapter_source, "live-usable unauthenticated ledger absent")
    need("receipt.authenticated is True" in adapter_source, "authenticated receipt requirement")
    need("os.O_EXCL" in adapter_source and "os.fsync" in adapter_source and "0o600" in adapter_source, "synthetic crash ledger model")
    need("PMAI_P0_04_SRBE_V5_ATTEMPT_BINDING_V2" in adapter_source, "attempt binding V2")
    need("runtime_provenance_observation_receipt_sha256" in adapter_source, "runtime provenance binding")
    need("runtime_provenance_hmac_key_id_sha256" in adapter_source, "runtime provenance key binding")
    need("hmac.compare_digest" in adapter_source, "runtime provenance HMAC verification")
    need(
        "len(set(hmac_key_ids)) == len(hmac_key_ids)" in adapter_source,
        "adapter HMAC key ID separation",
    )
    need("operator_run_id_sha256" in adapter_source, "operator run binding")
    need("operator_ipv4_cidr_32_sha256" in adapter_source, "operator CIDR hash binding")
    need("expected_target_provider_identity_sha256" in adapter_source, "expected target identity binding")
    need("RUNTIME_OBSERVATION_KEYS = SUCCESS_KEYS - {\"outcome\"}" in adapter_source, "runtime observation contract")
    collect_function = next(
        node
        for node in adapter_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "collect_once"
    )
    collect_argument_names = [argument.arg for argument in collect_function.args.args]
    collect_argument_names.extend(argument.arg for argument in collect_function.args.kwonlyargs)
    need("now_utc" not in collect_argument_names and "clock" not in collect_argument_names, "public clock injection")
    need("finally:" in adapter_source, "outer cleanup")
    add_calls = 0
    remove_calls = 0
    execute_calls = 0
    for node in ast.walk(adapter_tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_operator_ipv4_cidr_32":
                add_calls += 1
            elif node.func.attr == "remove_operator_ipv4_cidr_32":
                remove_calls += 1
            elif node.func.attr == "execute_fixed":
                execute_calls += 1
    need(add_calls == 1 and remove_calls == 1, "single allowlist call sites")
    need(execute_calls == 1, "single DB execution call site")

    need(assigned_string_set(reviewer_tree, "SUCCESS_KEYS") == SUCCESS_KEYS, "reviewer success keys")
    need(assigned_string_set(reviewer_tree, "FAILURE_KEYS") == FAILURE_KEYS, "reviewer failure keys")
    need(assigned_string_set(reviewer_tree, "ERROR_CODES") == ERROR_CODES, "reviewer exact error codes")
    need(assigned_string_set(reviewer_tree, "STAGE_CODES") == STAGE_CODES, "reviewer exact stage codes")
    reviewer_key_id_fields = {
        "ledger_hmac_key_id_sha256",
        "runtime_provenance_hmac_key_id_sha256",
        "independent_attestation_hmac_key_id_sha256",
    }
    reviewer_key_separation = False
    for node in ast.walk(reviewer_tree):
        if not (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == 3
            and isinstance(node.left, ast.Call)
            and isinstance(node.left.func, ast.Name)
            and node.left.func.id == "len"
            and len(node.left.args) == 1
            and isinstance(node.left.args[0], ast.Set)
        ):
            continue
        fields: set[str] = set()
        for element in node.left.args[0].elts:
            if (
                isinstance(element, ast.Subscript)
                and isinstance(element.value, ast.Name)
                and element.value.id == "attestation"
                and isinstance(element.slice, ast.Constant)
                and isinstance(element.slice.value, str)
            ):
                fields.add(element.slice.value)
        if fields == reviewer_key_id_fields:
            reviewer_key_separation = True
            break
    need(reviewer_key_separation, "reviewer HMAC key ID separation")
    for value in (
        "PMAI_P0_04_V5_INDEPENDENT_ATTESTATION_HMAC_KEY_FD",
        "PMAI_P0_04_SRBE_V5_INDEPENDENT_RUNTIME_ATTESTATION_V1",
        "--independent-attestation-file",
        "hmac.compare_digest",
        "stat.S_ISFIFO",
        "UNVERIFIED_REVIEW_INPUT",
        '"attempt_state": "UNCERTAIN"',
        '"attempt_reserved": True',
        '"collection_attempt_consumed": True',
        '"cleanup_required": True',
    ):
        need(value in reviewer_source, "reviewer authenticated boundary " + value)
    need(
        "PMAI_P0_04_V5_INDEPENDENT_INSTRUMENTATION_RECEIPT_SHA256"
        not in reviewer_source
        and "PMAI_P0_04_V5_INDEPENDENT_CLEANUP_RECEIPT_SHA256"
        not in reviewer_source,
        "legacy unauthenticated reviewer environment",
    )


def parse_single_json_line(value: bytes) -> Mapping[str, object]:
    need(value.endswith(b"\n") and value.count(b"\n") == 1, "single JSON line")
    need(len(value) <= 4096, "sanitized output size")
    raw = value[:-1].decode("utf-8", errors="strict")
    result = json.loads(raw)
    need(isinstance(result, dict), "sanitized output object")
    canonical = json.dumps(
        result,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    need(canonical == value, "canonical sanitized output")
    need(set(result) == FAILURE_KEYS, "offline output failure keys")
    need(result["schema"] == RESULT_SCHEMA_ID and result["outcome"] == "HOLD", "offline HOLD")
    need(result["raw_connection_values_disclosed"] is False, "offline raw disclosure")
    need(result["runtime_evidence_emitted"] is False, "offline runtime evidence")
    validate_failure_state(result)
    return result


def validate_failure_state(record: Mapping[str, object]) -> None:
    state = (
        record["attempt_state"],
        record["attempt_reserved"],
        record["collection_attempt_consumed"],
        record["cleanup_required"],
        record["cleanup_completed"],
        record["final_network_state_verified"],
    )
    if record["state_provenance"] == "UNVERIFIED_REVIEW_INPUT":
        need(
            state == ("UNCERTAIN", True, True, True, False, False),
            "unverified conservative failure state",
        )
        return
    need(
        record["state_provenance"] == "ADAPTER_STATE_MACHINE",
        "failure state provenance",
    )
    allowed_adapter_states = {
        ("KNOWN_NOT_STARTED", False, False, False, False, False),
        ("CONSUMED", True, True, False, False, False),
        ("CONSUMED", True, True, True, True, True),
        ("CONSUMED", True, True, True, False, False),
        ("UNCERTAIN", True, True, True, False, False),
    }
    need(state in allowed_adapter_states, "adapter failure state invariant")


def run_offline(command: Sequence[str], expected_exit: int) -> bytes:
    result = subprocess.run(
        list(command),
        cwd=ROOT,
        env=sanitized_subprocess_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    need(result.returncode == expected_exit, "offline command exit")
    need(result.stderr == b"", "offline command stderr")
    return result.stdout


def validate_offline_execution() -> None:
    cases = (
        ([sys.executable, "-I", "-B", str(path(ADAPTER)), "--dry-run"], 0, "CONTROLLED_EXECUTION_HOLD", "ADAPTER_STATE_MACHINE"),
        ([sys.executable, "-I", "-B", str(path(ADAPTER)), "--self-test"], 0, "CONTROLLED_EXECUTION_HOLD", "ADAPTER_STATE_MACHINE"),
        ([sys.executable, "-I", "-B", str(path(ADAPTER)), "--collect-once"], 1, "LIVE_PORTS_NOT_INJECTED", "ADAPTER_STATE_MACHINE"),
        ([sys.executable, "-P", "-E", "-s", "-B", str(path(ADAPTER)), "--dry-run"], 1, "ARGUMENT_CONTRACT_MISMATCH", "ADAPTER_STATE_MACHINE"),
        ([sys.executable, "-I", "-B", str(path(REVIEWER)), "--self-test"], 0, "CONTROLLED_EXECUTION_HOLD", "UNVERIFIED_REVIEW_INPUT"),
        ([sys.executable, "-P", "-E", "-s", "-B", str(path(REVIEWER)), "--self-test"], 1, "ARGUMENT_CONTRACT_MISMATCH", "UNVERIFIED_REVIEW_INPUT"),
    )
    before = current_changed_paths()
    for command, expected_exit, expected_error, expected_provenance in cases:
        first = run_offline(command, expected_exit)
        second = run_offline(command, expected_exit)
        need(first == second, "offline deterministic output")
        record = parse_single_json_line(first)
        need(record["error_code"] == expected_error, "offline fixed error")
        need(
            record["state_provenance"] == expected_provenance,
            "offline fixed state provenance",
        )
    need(current_changed_paths() == before, "offline test repository mutation")


def validate_manifest() -> None:
    value = json_no_duplicates(MANIFEST)
    need(isinstance(value, dict), "manifest object")
    expected_keys = {
        "schema",
        "stage_id",
        "substage",
        "repository",
        "replacement_revision",
        "package_record_id",
        "package_record_id_sha256",
        "package_recorded_date",
        "authorization_id",
        "authorization_id_sha256",
        "base_commit",
        "base_tree_sha",
        "source_pull_request",
        "base_github_ci_run_id",
        "base_github_ci_run_number",
        "base_github_ci_status",
        "base_github_ci_event",
        "base_github_ci_run_attempt",
        "base_github_ci_terminal_status",
        "base_github_ci_conclusion",
        "base_central_validator_sha256",
        "head_branch",
        "commit_message",
        "current_v4_validator_sha256",
        "current_v4_manifest_sha256",
        "current_v4_owned_central_projection_sha256",
        "central_v5_owned_projection_sha256",
        "held_v5_commit",
        "held_v5_tree",
        "held_v5_commit_must_not_be_replacement_ancestor",
        "authorized_changed_path_count",
        "authorized_changed_path_sequence_sha256",
        "package_path_count",
        "manifest_member_count",
        "manifest_self_excluded",
        "ci_static_checks_changed",
        "smoke_petmed_changed",
        "github_workflow_changed",
        "files",
    }
    need(set(value) == expected_keys, "manifest keys")
    need(value["schema"] == "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_SRBE_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_PACKAGE_MANIFEST_V1", "manifest schema")
    need(value["stage_id"] == "PMAI-P0-04", "manifest stage")
    need(value["repository"] == "pet-med-ai/Pet-med-ai", "manifest repository")
    need(value["replacement_revision"] == 2, "manifest revision")
    need(value["package_record_id"] == PACKAGE_RECORD_ID, "manifest package record")
    need(value["package_record_id_sha256"] == PACKAGE_RECORD_ID_SHA256, "manifest package record hash")
    need(value["package_recorded_date"] == "2026-08-29", "manifest package date")
    need(value["authorization_id"] == AUTHORIZATION_ID, "manifest authorization")
    need(value["authorization_id_sha256"] == AUTHORIZATION_ID_SHA256, "manifest authorization hash")
    need(value["base_commit"] == BASE_COMMIT and value["base_tree_sha"] == BASE_TREE, "manifest base")
    need(value["source_pull_request"] == SOURCE_PULL_REQUEST, "manifest source PR")
    need(value["base_github_ci_run_id"] == SOURCE_CI_RUN_ID, "manifest CI run")
    need(value["base_github_ci_run_number"] == SOURCE_CI_RUN_NUMBER, "manifest CI number")
    need(value["base_github_ci_status"] == "PASS", "manifest CI status")
    need(value["base_github_ci_event"] == SOURCE_CI_EVENT, "manifest CI event")
    need(value["base_github_ci_run_attempt"] == SOURCE_CI_ATTEMPT, "manifest CI attempt")
    need(value["base_github_ci_terminal_status"] == SOURCE_CI_STATUS, "manifest CI terminal status")
    need(value["base_github_ci_conclusion"] == SOURCE_CI_CONCLUSION, "manifest CI conclusion")
    need(value["base_central_validator_sha256"] == BASE_CENTRAL_SHA256, "manifest base central")
    need(value["head_branch"] == HEAD_BRANCH and value["commit_message"] == COMMIT_MESSAGE, "manifest publication")
    need(value["current_v4_validator_sha256"] == V4_PROTECTED_HASHES[V4_VALIDATOR], "manifest V4 validator")
    need(value["current_v4_manifest_sha256"] == V4_PROTECTED_HASHES[V4_PREFIX + "_PACKAGE_MANIFEST_V1.json"], "manifest V4 manifest")
    need(value["current_v4_owned_central_projection_sha256"] == CENTRAL_V4_OWNED_PROJECTION_SHA256, "manifest V4 projection")
    need(value["central_v5_owned_projection_sha256"] == CENTRAL_V5_OWNED_PROJECTION_SHA256, "manifest V5 projection")
    need(value["held_v5_commit"] == HELD_V5_COMMIT and value["held_v5_tree"] == HELD_V5_TREE, "manifest held V5")
    need(value["held_v5_commit_must_not_be_replacement_ancestor"] is True, "manifest held ancestry")
    need(value["authorized_changed_path_count"] == 13, "manifest changed count")
    need(value["authorized_changed_path_sequence_sha256"] == EXPECTED_PATH_SEQUENCE_SHA256, "manifest path hash")
    need(value["package_path_count"] == 12, "manifest package count")
    need(value["manifest_member_count"] == 11, "manifest member count")
    need(value["manifest_self_excluded"] is True, "manifest self excluded")
    for key in ("ci_static_checks_changed", "smoke_petmed_changed", "github_workflow_changed"):
        need(value[key] is False, "manifest unchanged " + key)
    files = value["files"]
    need(isinstance(files, list) and len(files) == 11, "manifest files")
    need([entry.get("path") for entry in files if isinstance(entry, dict)] == list(MANIFEST_MEMBERS), "manifest order")
    for entry, relative in zip(files, MANIFEST_MEMBERS, strict=True):
        need(isinstance(entry, dict) and set(entry) == {"path", "bytes", "sha256"}, "manifest entry")
        candidate = path(relative)
        need(entry["path"] == relative, "manifest path")
        need(entry["bytes"] == candidate.stat().st_size, "manifest bytes " + relative)
        need(entry["sha256"] == digest(relative), "manifest hash " + relative)


def validate_central() -> None:
    source = text(CENTRAL)
    actual_values: dict[str, str] = {}
    for name in CENTRAL_V5_NORMALIZED_ASSIGNMENTS:
        capture = re.search(
            r"" + re.escape(name) + r"\s*=\s*\(\s*[\"']([0-9a-f]{64})[\"']\s*\)",
            source,
        )
        need(capture is not None, "central SHA field " + name)
        actual_values[name] = capture.group(1)
    need(
        actual_values[CENTRAL_V5_STEM + "_VALIDATOR_SHA256"] == digest(VALIDATOR),
        "central validator hash",
    )
    need(
        actual_values[CENTRAL_V5_STEM + "_MANIFEST_SHA256"] == digest(MANIFEST),
        "central manifest hash",
    )
    actual_projection = central_v5_owned_projection(source)
    need(actual_projection == CENTRAL_V5_OWNED_PROJECTION_SHA256, "central V5 owned projection")
    validate_v5_projection_synthetic_tests(source)


def main() -> int:
    validate_invocation()
    validate_repository_identity()
    repository_state = validate_git_scope()
    validate_modes()
    validate_v4_protection()
    run_pinned_v4_validator()
    validate_successor_compatibility_synthetic_tests()
    validate_successor_test_matrix()
    validate_contract_artifacts()
    validate_json_schemas()
    validate_python_sources()
    validate_offline_execution()
    validate_manifest()
    validate_central()
    need(
        repository_state.phase in REPOSITORY_VALIDATION_PHASES[:-1],
        "validation phase",
    )
    finalize_repository_state(repository_state)
    print(PASS_MARKER)
    print(FINAL_PASS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
