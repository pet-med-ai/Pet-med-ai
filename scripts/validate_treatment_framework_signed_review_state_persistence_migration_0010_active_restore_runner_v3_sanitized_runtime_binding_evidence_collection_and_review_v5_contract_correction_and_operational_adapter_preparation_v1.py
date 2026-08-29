#!/usr/bin/env python3
"""Fail-closed validator for the PMAI-P0-04 V5 SRBE adapter package."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Mapping, Sequence


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


def current_changed_paths() -> list[str]:
    values = set(git_lines("diff", "--name-only", "HEAD"))
    values.update(git_lines("diff", "--cached", "--name-only", "HEAD"))
    values.update(git_lines("ls-files", "--others", "--exclude-standard"))
    return sorted(values, key=lambda item: item.encode("utf-8"))


def changed_path_sha256(values: Sequence[str]) -> str:
    payload = "".join(value + "\n" for value in values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def base_has_path(relative: str) -> bool:
    result = git("cat-file", "-e", BASE_COMMIT + ":" + relative, check=False)
    return result.returncode == 0


def commit_message_bytes(commit: str) -> bytes:
    raw = git("cat-file", "commit", commit).stdout.encode("utf-8")
    parts = raw.split(b"\n\n", 1)
    need(len(parts) == 2, "commit object message boundary")
    return parts[1]


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


def validate_v5_projection_synthetic_tests(source: str) -> None:
    indented_begin = "    " + CENTRAL_V5_INTEGRATION_BEGIN
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


def validate_git_scope() -> bool:
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
    need(git_value("rev-parse", BASE_COMMIT + "^{tree}") == BASE_TREE, "base tree")
    need(
        tuple(git_value("show", "-s", "--format=%P", BASE_COMMIT).split())
        == BASE_PARENTS,
        "base parent sequence",
    )
    base_central = git("show", BASE_COMMIT + ":" + CENTRAL).stdout.encode("utf-8")
    need(hashlib.sha256(base_central).hexdigest() == BASE_CENTRAL_SHA256, "base central hash")
    held_presence = git("cat-file", "-e", HELD_V5_COMMIT + "^{commit}", check=False)
    if held_presence.returncode == 0:
        need(git_value("rev-parse", HELD_V5_COMMIT + "^{tree}") == HELD_V5_TREE, "held V5 tree")
        need(git_value("rev-parse", HELD_V5_COMMIT + "^") == HELD_V5_PARENT, "held V5 parent")
        need(
            git("merge-base", "--is-ancestor", HELD_V5_COMMIT, "HEAD", check=False).returncode
            != 0,
            "held V5 is replacement ancestor",
        )
    need(tuple(sorted(EXPECTED_CHANGED_PATHS, key=lambda item: item.encode("utf-8"))) == EXPECTED_CHANGED_PATHS, "declared path order")
    need(len(EXPECTED_CHANGED_PATHS) == 13, "changed path count")
    need(len(PACKAGE_PATHS) == 12, "package path count")
    need(len(MANIFEST_MEMBERS) == 11, "manifest member count")
    need(changed_path_sha256(EXPECTED_CHANGED_PATHS) == EXPECTED_PATH_SEQUENCE_SHA256, "path sequence hash")
    for relative in PACKAGE_PATHS:
        need(not base_has_path(relative), "package path existed at base " + relative)
    need(base_has_path(CENTRAL), "central absent at base")

    head = git_value("rev-parse", "HEAD")
    if head == BASE_COMMIT:
        need(git_value("branch", "--show-current") == HEAD_BRANCH, "precommit branch")
        need(current_changed_paths() == list(EXPECTED_CHANGED_PATHS), "precommit exact paths")
        return False

    introductions = git_lines("log", "--diff-filter=A", "--format=%H", "--", DOC)
    need(len(introductions) == 1, "introduction count")
    introduction = introductions[0]
    need(git_value("show", "-s", "--format=%P", introduction) == BASE_COMMIT, "introduction parent")
    need(git_value("rev-list", "--count", BASE_COMMIT + ".." + introduction) == "1", "one introduction commit")
    need(git_value("show", "-s", "--format=%s", introduction) == COMMIT_MESSAGE, "commit message")
    need(commit_message_bytes(introduction) == (COMMIT_MESSAGE + "\n").encode("utf-8"), "exact commit message bytes")
    need(
        git_lines("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", introduction)
        == list(EXPECTED_CHANGED_PATHS),
        "introduction exact paths",
    )
    need(
        git("merge-base", "--is-ancestor", introduction, "HEAD", check=False).returncode
        == 0,
        "introduction not ancestor",
    )
    if git_value("branch", "--show-current") == HEAD_BRANCH:
        need(head == introduction, "authorized branch advanced after introduction")
    if head != introduction:
        need(
            git_lines(
                "diff",
                "--name-only",
                introduction + "..HEAD",
                "--",
                *EXPECTED_CHANGED_PATHS,
            )
            == [],
            "authorized path drift after introduction",
        )
    need(current_changed_paths() == [], "postcommit worktree dirty")
    return True


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
    committed = validate_git_scope()
    validate_modes()
    validate_v4_protection()
    run_pinned_v4_validator()
    validate_successor_test_matrix()
    validate_contract_artifacts()
    validate_json_schemas()
    validate_python_sources()
    validate_offline_execution()
    validate_manifest()
    validate_central()
    need(committed in {True, False}, "validation phase")
    print(PASS_MARKER)
    print(FINAL_PASS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
