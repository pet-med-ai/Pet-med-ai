#!/usr/bin/env python3
"""Validate the PMAI-P0-04 V4 SRBE execution-authorization package."""

from __future__ import annotations

import ast
import csv
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
EXPECTED_CHANGED_PATHS = (*PACKAGE_PATHS, CENTRAL)

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
CENTRAL_NORMALIZED_SHA256 = "0902f01ee07cbf1e7923f76aa3585204c863e5473396e1717de0b38baa4ae65c"

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


def rows(relative: str, fieldnames: list[str]) -> list[dict[str, str]]:
    with safe_path(relative).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        need(reader.fieldnames == fieldnames, "CSV header " + relative)
        value = list(reader)
    need(all(set(row) == set(fieldnames) for row in value), "CSV row schema " + relative)
    return value


def marker(source: str, key: str) -> str:
    values = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", source)
    need(values and len(set(values)) == 1, "marker consistency " + key)
    return values[0]


def contract_sha256(lines: tuple[str, ...]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
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


def path_sequence_sha256(paths: list[str] | tuple[str, ...]) -> str:
    return hashlib.sha256(("\n".join(paths) + "\n").encode("utf-8")).hexdigest()


def current_changed_paths() -> list[str]:
    tracked = git_lines("diff", "--name-only", BASE_COMMIT)
    untracked = git_lines("ls-files", "--others", "--exclude-standard")
    return sorted(set(tracked + untracked), key=lambda value: value.encode("utf-8"))


def introduction_commit() -> str | None:
    head = git("rev-parse", "HEAD")
    need(git("rev-parse", BASE_COMMIT + "^{tree}") == BASE_TREE, "base tree")
    if head == BASE_COMMIT:
        need(current_changed_paths() == list(EXPECTED_CHANGED_PATHS), "working changed paths")
        return None
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_COMMIT, head],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    need(ancestor.returncode == 0, "base is not ancestor")
    introductions = git_lines("rev-list", "--reverse", BASE_COMMIT + ".." + head, "--", DOC)
    need(len(introductions) == 1, "execution authorization introduction commit count")
    introduction = introductions[0]
    parents = git_lines("show", "-s", "--format=%P", introduction)
    need(len(parents) == 1 and parents[0] == BASE_COMMIT, "introduction parent")
    paths = git_lines("diff", "--name-only", BASE_COMMIT + ".." + introduction)
    need(paths == list(EXPECTED_CHANGED_PATHS), "introduction changed paths")
    if head != introduction:
        first_parent = git_lines("rev-list", "--first-parent", BASE_COMMIT + ".." + head)
        need(introduction not in first_parent, "linear additional commit after introduction")
        protected = git_lines("diff", "--name-only", introduction + ".." + head, "--", *PACKAGE_PATHS)
        need(not protected, "execution authorization package changed after introduction")
    return introduction


def git_blob_text(commit: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "show", commit + ":" + relative],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    need(result.returncode == 0 and result.stderr == "", "git blob " + relative)
    return result.stdout


def literal_assignments(source: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    tree = ast.parse(source, filename=CENTRAL)
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = value
    return values


def contract_lines(source: str, begin: str, end: str) -> tuple[str, ...]:
    lines = source.splitlines()
    need(lines.count(begin) == 1 and lines.count(end) == 1, "contract markers " + begin)
    start = lines.index(begin)
    stop = lines.index(end)
    need(start < stop, "contract order " + begin)
    value = lines[start + 1 : stop]
    while value and value[0] == "":
        value.pop(0)
    while value and value[-1] == "":
        value.pop()
    if value and value[0] == "~~~text":
        value.pop(0)
    if value and value[-1] == "~~~":
        value.pop()
    while value and value[0] == "":
        value.pop(0)
    while value and value[-1] == "":
        value.pop()
    return tuple(value)


def require_document_value(source: str, key: str, expected: str) -> None:
    need(
        source.splitlines().count(key + "=" + expected) >= 1,
        "document marker " + key,
    )


def run_validator(relative: str, pass_marker: str, label: str) -> None:
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / relative)],
        cwd=ROOT,
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
        require_document_value(source, key, expected)
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
        require_document_value(source, key, expected)
    for key in UNBOUND_FIELDS:
        require_document_value(source, key, "UNBOUND")
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
        require_document_value(source, key, "false")
    for key in true_fields:
        require_document_value(source, key, "true")
    for key in EXECUTION_FALSE_FIELDS:
        require_document_value(source, key, "false")
    schema_block = "\n".join(OUTPUT_SCHEMA_LINES) + "\n"
    procedure_block = "\n".join(PROCEDURE_LINES) + "\n"
    need(contract_sha256(OUTPUT_SCHEMA_LINES) == OUTPUT_SCHEMA_SHA256, "validator output schema hash")
    need(contract_sha256(PROCEDURE_LINES) == PROCEDURE_SHA256, "validator procedure hash")
    need(source.count(schema_block) == 1, "document exact collection phase output schema block")
    need(source.count(procedure_block) == 1, "document exact operational collection procedure block")


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
    manifest = read_json(MANIFEST)
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
    need(type(files) is list and len(files) == 7, "manifest member count")
    need([item["path"] for item in files] == list(MANIFEST_MEMBERS), "manifest member sequence")
    for item in files:
        need(type(item) is dict and set(item) == {"path", "bytes", "sha256"}, "manifest member schema")
        relative = item["path"]
        need(relative in MANIFEST_MEMBERS, "manifest member path")
        path = safe_path(relative)
        need(item["bytes"] == path.stat().st_size, "manifest member bytes " + relative)
        need(item["sha256"] == digest(relative), "manifest member hash " + relative)
    need(MANIFEST not in {item["path"] for item in files}, "manifest self exclusion")
    need(CENTRAL not in {item["path"] for item in files}, "central manifest exclusion")


def validate_central(introduction: str | None) -> None:
    source = text(CENTRAL)
    assignments = literal_assignments(source)
    stem = "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V4_EXECUTION_AUTHORIZATION"
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
    }
    for key, expected_value in expected.items():
        need(assignments.get(key) == expected_value, "central constant " + key)
    prep_hook = "v4_rebind_preparation_result = subprocess.run("
    review_hook = "v4_rebind_authorization_review_result = subprocess.run("
    execution_hook = "srbe_v4_execution_authorization_result = subprocess.run("
    need(source.count(prep_hook) == 1, "preparation subprocess count")
    need(source.count(review_hook) == 1, "review subprocess count")
    need(source.count(execution_hook) == 1, "execution authorization subprocess count")
    need(source.index(prep_hook) < source.index(review_hook) < source.index(execution_hook), "central hook order")
    need(source.count('[sys.executable, "-B", str(srbe_v4_execution_authorization_validator_path)]') == 1, "execution authorization command")
    required_outputs = (
        '"v4_runner_srbe_collection_review_execution_authorization_complete=true"',
        '"srbe_collection_evidence_complete=false"',
        '"current_collection_execution_authorized=false"',
        '"current_external_execution_authorized=false"',
        '"post_effective_gate_srbe_collection_and_review_execution_authorized=false"',
        '"srbe_execution_authorization_effective_evidence_completeness=" + SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_COMPLETENESS',
        '"srbe_execution_authorization_effective_decision=" + SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_HOLD',
        '"srbe_execution_authorization_effective_next_step=" + SRBE_EXECUTION_AUTHORIZATION_EFFECTIVE_CURRENT_NEXT_STEP',
        '"runtime_binding_contract_complete=false"',
        '"restore_runner_created=false"',
        '"p0_04_execution_authorized=false"',
        '"active_0010_migration_file_created=false"',
        '"database_write=false"',
        '"migration_executed=false"',
    )
    for line in required_outputs:
        need(source.count(line) >= 1, "central safety output " + line)
    normalized = source if introduction is None else git_blob_text(introduction, CENTRAL)
    for name in (stem + "_VALIDATOR_SHA256", stem + "_MANIFEST_SHA256"):
        pattern = (
            r"(" + re.escape(name) + r"\s*=\s*\(\s*[\"'])"
            r"[0-9a-f]{64}"
            r"([\"']\s*\))"
        )
        normalized, count = re.subn(pattern, r"\1<NORMALIZED_SHA256>\2", normalized)
        need(count == 1, "central normalized field " + name)
    need(hashlib.sha256(normalized.encode("utf-8")).hexdigest() == CENTRAL_NORMALIZED_SHA256, "central normalized hash")


def validate_no_sensitive_material() -> None:
    combined = "\n".join(text(relative) for relative in (*PACKAGE_PATHS, CENTRAL))
    forbidden = {
        "external URL": r"(?i)\bhttps?://",
        "database URI": r"(?i)\bpostgres(?:ql)?://",
        "raw provider identifier": r"(?i)\b(?:dpg|srv)-[a-z0-9]{6,}\b",
        "email address": r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "credential assignment": r"(?i)\b(?:password|secret|database_url|access_token)\s*[:=]\s*[^\s,}\]]+",
    }
    for label, pattern in forbidden.items():
        need(re.search(pattern, combined) is None, "forbidden " + label)


def main() -> int:
    for relative in PACKAGE_PATHS:
        safe_path(relative)
    need(
        list(EXPECTED_CHANGED_PATHS)
        == sorted(EXPECTED_CHANGED_PATHS, key=lambda value: value.encode("utf-8")),
        "changed path sort",
    )
    need(path_sequence_sha256(EXPECTED_CHANGED_PATHS) == EXPECTED_PATH_SEQUENCE_SHA256, "changed path sequence hash")
    introduction = introduction_commit()
    validate_source_anchors()
    validate_document()
    validate_baseline_and_pointer()
    validate_csvs()
    validate_manifest()
    validate_central(introduction)
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
