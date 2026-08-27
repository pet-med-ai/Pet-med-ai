#!/usr/bin/env python3
"""Validate the PMAI-P0-04 V4 runner/SRBE rebind preparation package."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Mapping, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "PMAI-P0-04"
SUBSTAGE = (
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_"
    "V4_PREPARATION_V1"
)
WORK_BUNDLE = "PMAI-P0-04-ARR-V3-ACT-SRBE-REBIND-V4-PREP"
PREPARATION_RECORD = "PMAI-P0-04-ARR-V3-ACT-SRBE-REBIND-V4-PREP-20260827"
AUTHORIZATION = (
    "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_"
    "REBIND_V4_PREPARATION_REPOSITORY_PATCH_CONTROLLED_EXECUTION_V1"
)
BASE_COMMIT = "c5b272d13ece67e2f86482eeac6023d8cd969049"
BASE_TREE = "91c3fd0aa7dc9b02d1aceacd73a3b786bb04f204"
HEAD_BRANCH = "pmai-p0-04-arr-v3-srbe-rebind-v4-prep"
EXPECTED_COMMIT_MESSAGE = (
    "PMAI-P0-04: Prepare V4 runner activation and SRBE contract rebind"
)
EXPECTED_PATH_SEQUENCE_SHA256 = (
    "448efcf5ccafa9f93b46f2d2bd705068103637a6e11632c423993b2d4d03d529"
)
SOURCE_V4_PR = 17
SOURCE_V4_HEAD = "b34b60b79a3dbd17ace576eb4dfa09d56a877968"
SOURCE_V4_POINTER_SHA256 = (
    "916bc762d99959879afe82e2154f47264530e65fc64cf158993db8361a0691ac"
)
SOURCE_V4_MANIFEST_SHA256 = (
    "f64d2b3c5a0f91475778306adf2f96c78bc60ce9a51e1d474e5c978066709554"
)
SOURCE_V4_VALIDATOR_SHA256 = (
    "cf065999ec6b43f875dc3cdb20c6bc503b9426b5d29fc0c380b4dc15118f1728"
)
SOURCE_V4_PASS_MARKER = (
    "fresh_disposable_target_provisioning_execution_evidence_v4=PASS"
)
SOURCE_V4_EVIDENCE_RECORD = "PMAI-P0-04-FDTP-EXEC-EVID-V4-20260826"
REVIEW_RECORD = "PMAI-P0-04-FDTP-AUTH-REVIEW-V4-20260823"
TARGET_NAME = "pet-med-ai-db-p0-04-fresh-disposable-restore-v4-ohio"
TARGET_CONTRACT_SHA256 = (
    "e1cba6bc207fa4654d3155ef4abd8d818d8fd4323ce990446bc680fd15522529"
)
TARGET_SERVICE_SHA256 = (
    "3f0ed4e1cb1bbef10babb4d3ba7fa9ec03e048d7d30595389f30d0871bcdb4fe"
)
PRIOR_V3_TARGET_CONTRACT_SHA256 = (
    "e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744"
)
PRIOR_V3_AUTHORIZATION_RECORD = "PMAI-P0-04-ARR-V3-CA-EXEC-AUTH-V1-20260816"
PRIOR_V3_AUTHORIZATION_DOC_SHA256 = (
    "3f518dc9735060f4c74d9c0832f7228f0860cd244947573c80037e5962a384c1"
)
PRIOR_V3_SRBE_BASELINE_SHA256 = (
    "152fb13e8feb5c019263a56d4a28fc6bcc6a6ad2b0c537385aea4f22c7b08fc8"
)
PRIOR_V3_SRBE_MANIFEST_SHA256 = (
    "4439e3a4d86b9e8017ac29260631d7a0c16b9182bd7833a0cbc2e8c6e38d1855"
)
IMPLEMENTATION_CANDIDATE_SHA256 = (
    "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
)
COLLECTOR_CONTRACT_SHA256 = (
    "1d4ce179cbd4ead48b6af7e3165bf7dd4e94eeef306c64cdcd40fa7788150a54"
)
DECISION = (
    "GO_TO_SEPARATE_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_"
    "REBIND_V4_AUTHORIZATION_REVIEW"
)
NEXT_SUBJECT = (
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_"
    "V4_AUTHORIZATION_REVIEW"
)
PASS_MARKER = (
    "active_restore_runner_v3_activation_and_srbe_contract_rebind_"
    "v4_preparation=PASS"
)
LEGACY_CURRENT_HOLD = (
    "HOLD_PMAI_P0_04_V4_TARGET_AVAILABLE_AND_NETWORK_LOCKED_PENDING_"
    "ACTIVE_RUNNER_AND_SRBE_CONTRACT_REBIND_V4"
)
LEGACY_CURRENT_COMPLETENESS = (
    "V4_TARGET_PROVISIONING_AND_NETWORK_LOCKDOWN_EVIDENCE_COMPLETE_PENDING_"
    "ACTIVE_RUNNER_SRBE_V4_REBIND_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION"
)
LEGACY_CURRENT_NEXT_STEP = (
    "PREPARE_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4"
)
EFFECTIVE_CURRENT_HOLD = (
    "HOLD_PMAI_P0_04_PENDING_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_"
    "CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW"
)
EFFECTIVE_CURRENT_COMPLETENESS = (
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_"
    "PREPARATION_COMPLETE_PENDING_AUTHORIZATION_REVIEW_RESTORE_REHEARSAL_"
    "AND_EXTERNAL_EXECUTION"
)
EFFECTIVE_CURRENT_NEXT_STEP = (
    "PREPARE_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_"
    "V4_AUTHORIZATION_REVIEW"
)

PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_"
    "REBIND_V4_PREPARATION_V1"
)
DOC = PREFIX + ".md"
POINTER = PREFIX + "_ACTIVE_POINTER_V1.json"
CHECKLIST = PREFIX + "_CHECKLIST_V1.csv"
GO_NO_GO = PREFIX + "_GO_NO_GO_V1.csv"
BASELINE = PREFIX + "_LOCKED_BASELINE_V1.json"
MANIFEST = PREFIX + "_PACKAGE_MANIFEST_V1.json"
RUNTIME_TEMPLATE = PREFIX + "_RUNTIME_OBSERVATION_TEMPLATE_V1.json"
COLLECTOR_TEMPLATE = PREFIX + "_SANITIZED_COLLECTOR_OUTPUT_TEMPLATE_V1.json"
COLLECTOR = PREFIX + "_COLLECTOR_CANDIDATE_V1.py.txt"
TEST_MATRIX = PREFIX + "_TEST_MATRIX_V1.csv"
VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_activation_and_srbe_contract_"
    "rebind_v4_preparation_v1.py"
)
REVIEWER = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_activation_and_srbe_contract_"
    "rebind_v4_evidence_review_v1.py"
)
CENTRAL = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_staging_migration_apply.py"
)
ACTIVE_RUNNER = (
    "scripts/run_treatment_framework_signed_review_state_persistence_"
    "migration_0010_disposable_restore_v3.py"
)
IMPLEMENTATION_CANDIDATE = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_"
    "CANDIDATE_V1.py.txt"
)
SOURCE_V4_POINTER = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_"
    "EVIDENCE_V4_ACTIVE_POINTER_V1.json"
)
SOURCE_V4_MANIFEST = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_"
    "EVIDENCE_V4_PACKAGE_MANIFEST_V1.json"
)
SOURCE_V4_VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_fresh_disposable_target_provisioning_execution_"
    "evidence_v4.py"
)
PRIOR_V3_AUTHORIZATION_DOC = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_"
    "EXECUTION_AUTHORIZATION_V1.md"
)
PRIOR_V3_SRBE_BASELINE = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_PREPARATION_V1_LOCKED_BASELINE_V1.json"
)
PRIOR_V3_SRBE_MANIFEST = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_PREPARATION_V1_PACKAGE_MANIFEST_V1.json"
)
CI = "scripts/ci_static_checks.sh"
SMOKE = "scripts/smoke_petmed.sh"
WORKFLOW_CI = ".github/workflows/ci-gate.yml"
WORKFLOW_KB = ".github/workflows/validate-kb.yml"

PACKAGE_PATHS = tuple(sorted((
    DOC,
    POINTER,
    CHECKLIST,
    GO_NO_GO,
    BASELINE,
    MANIFEST,
    RUNTIME_TEMPLATE,
    COLLECTOR_TEMPLATE,
    COLLECTOR,
    TEST_MATRIX,
    VALIDATOR,
    REVIEWER,
)))
MANIFEST_MEMBERS = tuple(sorted(set(PACKAGE_PATHS) - {MANIFEST}))
AUTHORIZED_CHANGED_PATHS = set((*PACKAGE_PATHS, CENTRAL))

PROTECTED_HASHES = {
    SOURCE_V4_POINTER: SOURCE_V4_POINTER_SHA256,
    SOURCE_V4_MANIFEST: SOURCE_V4_MANIFEST_SHA256,
    SOURCE_V4_VALIDATOR: SOURCE_V4_VALIDATOR_SHA256,
    PRIOR_V3_AUTHORIZATION_DOC: PRIOR_V3_AUTHORIZATION_DOC_SHA256,
    PRIOR_V3_SRBE_BASELINE: PRIOR_V3_SRBE_BASELINE_SHA256,
    PRIOR_V3_SRBE_MANIFEST: PRIOR_V3_SRBE_MANIFEST_SHA256,
    IMPLEMENTATION_CANDIDATE: IMPLEMENTATION_CANDIDATE_SHA256,
    CI: "a26f17997b73dffc542faa369c447431d97f36a84d4979fe26c3994dddcaee9b",
    SMOKE: "538f774e50514e8baec49a3b8acff99650b087ceb05b25bc0ba59d0f73f87652",
    WORKFLOW_CI: "08d71f8ed906e196ac505e7b94d591c081c0efb88b38f093e933332a7010fe2c",
    WORKFLOW_KB: "7c50df3e738e5103672f011fc8ffa742411ead6a5b415790758cfce14c875c00",
}

RUNTIME_HASH_KEYS = {
    "expected_active_source_sha256",
    "expected_schema_manifest_sha256",
    "expected_target_identity_sha256",
    "forbidden_production_identity_sha256",
    "forbidden_staging_identity_sha256",
}
AUTHORIZATION_HASH_KEYS = {
    "collection_execution_authorization_record_sha256",
    "successor_activation_authorization_record_sha256",
}
EVIDENCE_HASH_KEYS = {
    "source_observation_bundle_sha256",
    "target_application_attachment_recheck_evidence_sha256",
    "target_available_recheck_evidence_sha256",
    "target_lifecycle_evidence_sha256",
    "target_network_lockdown_recheck_evidence_sha256",
    "target_open_connection_recheck_evidence_sha256",
}
COLLECTOR_HASH_KEYS = RUNTIME_HASH_KEYS | AUTHORIZATION_HASH_KEYS | EVIDENCE_HASH_KEYS | {
    "collector_contract_sha256"
}
COLLECTOR_BOOLEAN_KEYS = {
    "collection_execution_authorized",
    "evidence_complete",
    "final_service_inbound_ip_rule_set_empty",
    "fixture_only",
    "public_external_access_blocked",
    "raw_connection_values_disclosed",
    "target_application_attachment_count_zero",
    "target_lifecycle_within_72h",
    "target_open_connection_count_zero",
    "target_status_available",
}
COLLECTOR_BOUNDARY_KEYS = {
    "archive_accessed",
    "backup_accessed",
    "credential_accessed",
    "database_connected",
    "deployment_performed",
    "filesystem_input_read",
    "filesystem_output_written",
    "git_write_performed",
    "migration_created",
    "migration_executed",
    "network_accessed",
    "provider_control_plane_accessed",
    "resource_deleted",
    "restore_executed",
    "runner_activated",
    "runner_created",
    "runner_executed",
    "runner_imported",
    "runtime_evidence_collected",
    "target_accessed",
}
REVIEWER_BOUNDARY_KEYS = {
    "archive_accessed",
    "backup_accessed",
    "credential_accessed",
    "database_connected",
    "deployment_performed",
    "external_input_read",
    "external_output_written",
    "git_write_performed",
    "migration_created",
    "migration_executed",
    "network_accessed",
    "provider_control_plane_accessed",
    "resource_deleted",
    "restore_executed",
    "runner_activated",
    "runner_created",
    "runner_executed",
    "runner_imported",
    "runtime_evidence_reviewed",
    "target_accessed",
}
BOUNDARY_KEYS = COLLECTOR_BOUNDARY_KEYS | REVIEWER_BOUNDARY_KEYS
ALLOWED_COLLECTOR_IMPORTS = {
    "__future__", "argparse", "hashlib", "json", "re", "sys", "typing"
}
ALLOWED_REVIEWER_IMPORTS = set(ALLOWED_COLLECTOR_IMPORTS)
FORBIDDEN_IMPORT_ROOTS = {
    "asyncpg", "boto3", "http", "os", "pathlib", "psycopg", "psycopg2",
    "requests", "socket", "sqlite3", "subprocess", "tarfile", "urllib"
}
FORBIDDEN_CALL_NAMES = {
    "Path", "__import__", "compile", "delattr", "eval", "exec", "getattr",
    "globals", "input", "locals", "open", "setattr", "vars"
}
MAX_FILE_BYTES = 1024 * 1024
CENTRAL_NORMALIZED_SHA256 = "7fd657b6a29297dd3dc0c7c99205afc11b21880c36507c2f01e9e63502c3b293"


def need(condition: bool, message: str) -> None:
    if not condition:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def safe_path(relative: str) -> Path:
    path = ROOT / relative
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + relative)
    need(path.resolve().is_relative_to(ROOT.resolve()), "path escape " + relative)
    need(path.stat().st_size <= MAX_FILE_BYTES, "file too large " + relative)
    return path


def text(relative: str) -> str:
    try:
        return safe_path(relative).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        need(False, "invalid UTF-8 " + relative)
        raise AssertionError from exc


def digest(relative: str) -> str:
    return hashlib.sha256(safe_path(relative).read_bytes()).hexdigest()


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def marker(source: str, key: str) -> str:
    matches = re.findall(r"(?m)^" + re.escape(key) + r"=(.*)$", source)
    need(len(matches) == 1, "marker cardinality " + key)
    return matches[0]


def read_json(relative: str) -> dict[str, object]:
    try:
        value = json.loads(text(relative))
    except json.JSONDecodeError as exc:
        need(False, "invalid JSON " + relative)
        raise AssertionError from exc
    need(type(value) is dict, "JSON object required " + relative)
    return value


def rows(relative: str, expected_header: Sequence[str]) -> list[dict[str, str]]:
    with safe_path(relative).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        need(reader.fieldnames == list(expected_header), "CSV header " + relative)
        data = list(reader)
    need(all(set(row) == set(expected_header) for row in data), "CSV row schema " + relative)
    return data


def literal_assignments(source: str) -> dict[str, object]:
    try:
        tree = ast.parse(source, filename="<governance-source>")
    except SyntaxError as exc:
        need(False, "Python source parse")
        raise AssertionError from exc
    assignments: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            assignments[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
    return assignments


def git_result(*arguments: str, text_mode: bool = True) -> subprocess.CompletedProcess[object]:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text_mode,
        timeout=30,
        check=False,
    )


def git_lines(*arguments: str) -> list[str]:
    result = git_result(*arguments)
    need(result.returncode == 0, "git inspection " + " ".join(arguments))
    need(isinstance(result.stdout, str), "git text output")
    return [line for line in result.stdout.splitlines() if line]


def git_blob_text(commit: str, relative: str) -> str:
    result = git_result("show", commit + ":" + relative)
    need(result.returncode == 0, "git blob inspection " + relative)
    need(isinstance(result.stdout, str), "git blob text " + relative)
    return result.stdout


def base_path_exists(relative: str) -> bool:
    result = git_result("cat-file", "-e", BASE_COMMIT + ":" + relative)
    return result.returncode == 0


def changed_path_hash(paths: Sequence[str]) -> str:
    payload = "".join(path + "\n" for path in sorted(paths)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_authorized_scope() -> str | None:
    need(len(PACKAGE_PATHS) == 12, "package path cardinality")
    need(len(MANIFEST_MEMBERS) == 11, "manifest member cardinality")
    need(len(AUTHORIZED_CHANGED_PATHS) == 13, "authorized path cardinality")
    need(git_lines("rev-parse", BASE_COMMIT + "^{tree}") == [BASE_TREE], "base tree drift")
    for relative in PACKAGE_PATHS:
        need(not base_path_exists(relative), "package path existed at base " + relative)
        need(safe_path(relative).stat().st_mode & 0o777 == 0o644, "package file mode " + relative)
    need(base_path_exists(CENTRAL), "central missing at base")
    need(safe_path(CENTRAL).stat().st_mode & 0o777 == 0o755, "central file mode")

    introductions = git_lines("log", "--diff-filter=A", "--format=%H", "--", VALIDATOR)
    if introductions:
        need(len(introductions) == 1, "validator introduction commit count")
        introduction = introductions[0]
        need(git_lines("rev-parse", introduction + "^") == [BASE_COMMIT], "introduction parent")
        need(
            git_lines("rev-list", "--count", BASE_COMMIT + ".." + introduction) == ["1"],
            "one introduction commit",
        )
        need(git_lines("merge-base", introduction, "HEAD") == [introduction], "introduction ancestor")
        head = git_lines("rev-parse", "HEAD")[0]
        if head != introduction:
            first_parent_history = set(git_lines("rev-list", "--first-parent", "HEAD"))
            need(
                introduction not in first_parent_history,
                "unauthorized linear descendant after introduction",
            )
            need(
                not git_lines("diff", "--name-only", introduction + "..HEAD", "--", *PACKAGE_PATHS),
                "package member drift after merged introduction",
            )
        need(
            git_lines("show", "-s", "--format=%B", introduction)
            == [EXPECTED_COMMIT_MESSAGE],
            "introduction commit message",
        )
        changed = git_lines(
            "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", introduction
        )
    else:
        introduction = None
        need(git_lines("branch", "--show-current") == [HEAD_BRANCH], "head branch drift")
        need(git_lines("rev-parse", "HEAD") == [BASE_COMMIT], "uncommitted HEAD baseline")
        changed_set = set(git_lines("diff", "--name-only", BASE_COMMIT + "...HEAD"))
        changed_set.update(git_lines("diff", "--name-only"))
        changed_set.update(git_lines("diff", "--cached", "--name-only"))
        changed_set.update(git_lines("ls-files", "--others", "--exclude-standard"))
        changed = sorted(changed_set)
    need(set(changed) == AUTHORIZED_CHANGED_PATHS, "exact changed path scope")
    need(len(changed) == 13, "changed path count")
    need(changed_path_hash(changed) == EXPECTED_PATH_SEQUENCE_SHA256, "changed path sequence hash")
    new_paths = {relative for relative in changed if not base_path_exists(relative)}
    modified_paths = set(changed) - new_paths
    need(new_paths == set(PACKAGE_PATHS), "exact twelve new paths")
    need(modified_paths == {CENTRAL}, "exact single existing-file modification")
    return introduction


def validate_protected_history() -> None:
    for relative, expected in PROTECTED_HASHES.items():
        need(digest(relative) == expected, "protected historical hash " + relative)
    need(PRIOR_V3_AUTHORIZATION_DOC_SHA256 != hashlib.sha256(PRIOR_V3_AUTHORIZATION_RECORD.encode("utf-8")).hexdigest(), "V3 record and document identity distinction")
    need(TARGET_CONTRACT_SHA256 != TARGET_SERVICE_SHA256, "contract and service identity distinction")
    need(not (ROOT / ACTIVE_RUNNER).exists(), "planned active runner path present")
    need(
        not list((ROOT / "backend/migrations/versions").glob("0010*.py")),
        "active 0010 migration present",
    )


def validate_previous_v4_evidence() -> None:
    result = subprocess.run(
        [sys.executable, "-B", str(safe_path(SOURCE_V4_VALIDATOR))],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    need(result.returncode == 0, "source V4 evidence validator exit")
    need(result.stderr == "", "source V4 evidence validator stderr")
    need(
        result.stdout.splitlines().count(SOURCE_V4_PASS_MARKER) == 1,
        "source V4 evidence validator PASS marker",
    )


def validate_document() -> None:
    source = text(DOC)
    required = {
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "preparation_record_id": PREPARATION_RECORD,
        "stage_status": "IN_PROGRESS",
        "package_status": "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_ONLY",
        "preparation_status": "COMPLETE_REPOSITORY_ONLY_ALL_SUCCESSOR_BINDINGS_UNBOUND",
        "current_execution_decision": "HOLD_NO_RUNNER_SRBE_OR_EXTERNAL_EXECUTION",
        "authorization_record_id": AUTHORIZATION,
        "repository": "pet-med-ai/Pet-med-ai",
        "expected_github_login": "zhaohaisheng967-dotcom",
        "expected_repository_permission": "write",
        "pre_patch_remote_readonly_revalidation": "true",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "expected_local_head_branch_absent_at_precheck": "true",
        "expected_remote_head_branch_absent_at_precheck": "true",
        "create_isolated_branch_from_expected_base": "true",
        "risk_lane": "YELLOW_REPOSITORY_ONLY",
        "changed_path_scope": "EXACT_13_PATHS",
        "maximum_changed_path_count": "13",
        "package_path_count": "12",
        "manifest_member_count": "11",
        "maximum_commit_count": "1",
        "maximum_push_count": "1",
        "branch_deletion_authorized": "false",
        "force_push_authorized": "false",
        "additional_commit_authorized": "false",
        "ci_retry_authorized": "false",
        "library_master_directory_update": "false",
        "authorization_single_use": "true",
        "source_v4_evidence_pr": "17",
        "source_v4_evidence_head_commit": SOURCE_V4_HEAD,
        "source_v4_evidence_merge_commit": BASE_COMMIT,
        "source_v4_evidence_tree_sha": BASE_TREE,
        "source_v4_evidence_record_id": SOURCE_V4_EVIDENCE_RECORD,
        "source_v4_evidence_active_pointer_sha256": SOURCE_V4_POINTER_SHA256,
        "source_v4_evidence_manifest_sha256": SOURCE_V4_MANIFEST_SHA256,
        "source_v4_evidence_validator_sha256": SOURCE_V4_VALIDATOR_SHA256,
        "review_record_id": REVIEW_RECORD,
        "target_logical_name": TARGET_NAME,
        "target_contract_identity_sha256": TARGET_CONTRACT_SHA256,
        "target_service_identifier_sha256": TARGET_SERVICE_SHA256,
        "target_status_from_merged_evidence": "AVAILABLE",
        "target_application_attachment_count_from_merged_evidence": "0",
        "target_open_connection_count_from_merged_evidence": "0",
        "final_service_inbound_ip_rule_set_from_merged_evidence": "[]",
        "public_external_access_blocked_from_merged_evidence": "true",
        "target_live_metadata_revalidation": "false",
        "target_live_revalidation_required_before_future_external_action": "true",
        "prior_v3_target_contract_identity_sha256": PRIOR_V3_TARGET_CONTRACT_SHA256,
        "prior_v3_target_state": "RETIRED_ABSENCE_VERIFIED_HISTORICAL",
        "prior_v3_activation_authorization_record_id": PRIOR_V3_AUTHORIZATION_RECORD,
        "prior_v3_activation_authorization_doc_sha256": PRIOR_V3_AUTHORIZATION_DOC_SHA256,
        "prior_v3_srbe_locked_baseline_sha256": PRIOR_V3_SRBE_BASELINE_SHA256,
        "prior_v3_srbe_package_manifest_sha256": PRIOR_V3_SRBE_MANIFEST_SHA256,
        "prior_v3_activation_or_srbe_authorization_reuse": "false",
        "existing_v3_and_v4_historical_files_byte_exact": "true",
        "restore_runner_v3_implementation_candidate_sha256": IMPLEMENTATION_CANDIDATE_SHA256,
        "planned_active_runner_path": ACTIVE_RUNNER,
        "planned_active_runner_path_present": "false",
        "active_0010_migration_present": "false",
        "successor_activation_authorization_record_id": "UNBOUND",
        "collection_execution_authorization_record_id": "UNBOUND",
        "expected_active_source_sha256": "UNBOUND",
        "expected_target_identity_sha256": "UNBOUND",
        "forbidden_production_identity_sha256": "UNBOUND",
        "forbidden_staging_identity_sha256": "UNBOUND",
        "expected_schema_manifest_sha256": "UNBOUND",
        "runtime_binding_contract_complete": "false",
        "collector_contract_sha256": COLLECTOR_CONTRACT_SHA256,
        "authorization_record_hash_normalization": "SHA256_UTF8_EXACT_RECORD_ID_NO_LF",
        "future_target_application_attachment_count_zero": "false",
        "future_target_open_connection_count_zero": "false",
        "future_final_service_inbound_ip_rule_set_empty": "false",
        "future_public_external_access_blocked": "false",
        "legacy_ci_validator_cutover_authorized": "false",
        "render_readonly_access": "false",
        "database_connection": "false",
        "runtime_evidence_collection": "false",
        "runner_creation": "false",
        "runner_activation": "false",
        "runner_execution": "false",
        "restore_execution": "false",
        "migration_creation_or_execution": "false",
        "deployment": "false",
        "target_deletion": "false",
        "manual_retry": "false",
        "automatic_retry": "false",
        "decision": DECISION,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in required.items():
        need(marker(source, key) == expected, "document marker " + key)


def validate_baseline() -> None:
    baseline = read_json(BASELINE)
    need(
        set(baseline)
        == {
            "schema", "stage_id", "substage", "work_bundle", "preparation_record_id",
            "stage_status", "package_status", "preparation_status",
            "current_execution_decision", "repository", "base_branch", "base_commit",
            "base_tree_sha", "head_branch", "authorization", "source_v4_evidence",
            "historical_v3_anchors", "successor_rebind_contract", "inert_tooling",
            "legacy_ci_boundary", "execution_boundaries", "decision", "sole_next_subject",
        },
        "baseline exact top-level schema",
    )
    expected_scalars = {
        "schema": "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_V1_LOCKED_BASELINE_V1",
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "preparation_record_id": PREPARATION_RECORD,
        "stage_status": "IN_PROGRESS",
        "package_status": "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_ONLY",
        "preparation_status": "COMPLETE_REPOSITORY_ONLY_ALL_SUCCESSOR_BINDINGS_UNBOUND",
        "current_execution_decision": "HOLD_NO_RUNNER_SRBE_OR_EXTERNAL_EXECUTION",
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "decision": DECISION,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in expected_scalars.items():
        need(baseline.get(key) == expected, "baseline scalar " + key)
    need(
        baseline["authorization"]
        == {
            "authorization_id": AUTHORIZATION,
            "authorization_single_use": True,
            "risk_lane": "YELLOW_REPOSITORY_ONLY",
            "expected_github_login": "zhaohaisheng967-dotcom",
            "expected_repository_permission": "write",
            "pre_patch_remote_readonly_revalidation": True,
            "expected_local_head_branch_absent_at_precheck": True,
            "expected_remote_head_branch_absent_at_precheck": True,
            "create_isolated_branch_from_expected_base": True,
            "changed_path_scope": "EXACT_13_PATHS",
            "changed_path_sequence_sha256": EXPECTED_PATH_SEQUENCE_SHA256,
            "maximum_changed_path_count": 13,
            "maximum_new_file_count": 12,
            "maximum_existing_file_modification_count": 1,
            "package_path_count": 12,
            "manifest_member_count": 11,
            "manifest_self_excluded": True,
            "maximum_commit_count": 1,
            "maximum_push_count": 1,
            "pull_request_creation_authorized": False,
            "merge_authorized": False,
            "branch_deletion_authorized": False,
            "force_push_authorized": False,
            "additional_commit_authorized": False,
            "ci_retry_authorized": False,
            "library_master_directory_update": False,
            "manual_retry": False,
            "automatic_retry": False,
        },
        "baseline exact authorization",
    )
    source = baseline["source_v4_evidence"]
    need(type(source) is dict, "baseline V4 source object")
    expected_source = {
        "pull_request": SOURCE_V4_PR,
        "head_commit": SOURCE_V4_HEAD,
        "merge_commit": BASE_COMMIT,
        "tree_sha": BASE_TREE,
        "evidence_record_id": SOURCE_V4_EVIDENCE_RECORD,
        "active_pointer_sha256": SOURCE_V4_POINTER_SHA256,
        "manifest_sha256": SOURCE_V4_MANIFEST_SHA256,
        "validator_sha256": SOURCE_V4_VALIDATOR_SHA256,
        "review_record_id": REVIEW_RECORD,
        "target_logical_name": TARGET_NAME,
        "target_contract_identity_sha256": TARGET_CONTRACT_SHA256,
        "target_service_identifier_sha256": TARGET_SERVICE_SHA256,
        "target_status_from_merged_evidence": "AVAILABLE",
        "target_application_attachment_count_from_merged_evidence": 0,
        "target_open_connection_count_from_merged_evidence": 0,
        "final_service_inbound_ip_rule_set_from_merged_evidence": [],
        "public_external_access_blocked_from_merged_evidence": True,
        "live_metadata_revalidated_by_preparation": False,
        "live_revalidation_required_before_future_external_action": True,
    }
    need(source == expected_source, "baseline exact V4 evidence source")
    need(
        baseline["historical_v3_anchors"]
        == {
            "target_contract_identity_sha256": PRIOR_V3_TARGET_CONTRACT_SHA256,
            "target_state": "RETIRED_ABSENCE_VERIFIED_HISTORICAL",
            "activation_authorization_record_id": PRIOR_V3_AUTHORIZATION_RECORD,
            "activation_authorization_doc_sha256": PRIOR_V3_AUTHORIZATION_DOC_SHA256,
            "srbe_locked_baseline_sha256": PRIOR_V3_SRBE_BASELINE_SHA256,
            "srbe_package_manifest_sha256": PRIOR_V3_SRBE_MANIFEST_SHA256,
            "authorization_reusable": False,
            "files_byte_exact": True,
        },
        "baseline exact V3 anchors",
    )
    successor = baseline["successor_rebind_contract"]
    need(type(successor) is dict, "successor contract object")
    need(successor["implementation_candidate_sha256"] == IMPLEMENTATION_CANDIDATE_SHA256, "candidate hash")
    need(successor["planned_active_runner_path"] == ACTIVE_RUNNER, "planned active path")
    need(successor["authorization_record_hash_normalization"] == "SHA256_UTF8_EXACT_RECORD_ID_NO_LF", "authorization record normalization")
    for key in (
        "successor_activation_authorization_record_id",
        "collection_execution_authorization_record_id",
        "expected_active_source_sha256",
        "expected_target_identity_sha256",
        "forbidden_production_identity_sha256",
        "forbidden_staging_identity_sha256",
        "expected_schema_manifest_sha256",
    ):
        need(successor[key] == "UNBOUND", "successor binding not UNBOUND " + key)
    for key in (
        "planned_active_runner_path_present", "active_0010_migration_present",
        "runtime_binding_contract_complete", "target_contract_hash_may_substitute_runtime_identity",
        "service_identifier_hash_may_substitute_runtime_identity",
        "future_target_application_attachment_count_zero",
        "future_target_open_connection_count_zero",
        "future_final_service_inbound_ip_rule_set_empty",
        "future_public_external_access_blocked",
    ):
        need(successor[key] is False, "successor false boundary " + key)
    inert = baseline["inert_tooling"]
    need(type(inert) is dict, "inert tooling object")
    need(inert["collector_candidate_created"] is True, "collector candidate created")
    need(inert["collector_contract_sha256"] == COLLECTOR_CONTRACT_SHA256, "collector contract hash")
    need(inert["reviewer_created"] is True, "reviewer created")
    need(inert["reviewer_synthetic_fixture_tests_only"] is True, "reviewer synthetic only")
    need(inert["dynamic_output_types"] == ["boolean", "lowercase_sha256"], "dynamic output types")
    for key, value in inert.items():
        if key in {"collector_candidate_created", "collector_contract_sha256", "reviewer_created", "reviewer_synthetic_fixture_tests_only", "dynamic_output_types"}:
            continue
        need(value is False, "inert tooling false boundary " + key)
    legacy = baseline["legacy_ci_boundary"]
    need(type(legacy) is dict, "legacy boundary object")
    need(legacy["validator_cutover_required_before_active_path_creation"] is True, "legacy cutover required")
    for key in ("ci_entrypoint_changed", "github_workflow_changed", "smoke_entrypoint_changed", "validator_cutover_authorized"):
        need(legacy[key] is False, "legacy boundary false " + key)
    boundaries = baseline["execution_boundaries"]
    need(type(boundaries) is dict and boundaries, "execution boundaries object")
    need(all(value is False for value in boundaries.values()), "execution boundary enabled")


def validate_pointer() -> None:
    pointer = read_json(POINTER)
    need(pointer["schema"] == "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_V1_ACTIVE_POINTER_V1", "pointer schema")
    need(pointer["stage_id"] == STAGE_ID, "pointer stage")
    need(pointer["substage"] == SUBSTAGE, "pointer substage")
    need(pointer["work_bundle"] == WORK_BUNDLE, "pointer work bundle")
    need(pointer["preparation_record_id"] == PREPARATION_RECORD, "pointer record")
    need(pointer["pointer_version"] == 1, "pointer version")
    need(pointer["supersedes_pointer_path"] == SOURCE_V4_POINTER, "pointer predecessor path")
    need(pointer["supersedes_pointer_sha256"] == SOURCE_V4_POINTER_SHA256, "pointer predecessor hash")
    need(pointer["active_locked_baseline_path"] == BASELINE, "pointer baseline path")
    need(pointer["active_locked_baseline_sha256"] == digest(BASELINE), "pointer baseline digest")
    need(pointer["target_contract_identity_sha256"] == TARGET_CONTRACT_SHA256, "pointer contract hash")
    need(pointer["target_service_identifier_sha256"] == TARGET_SERVICE_SHA256, "pointer service hash")
    need(pointer["target_state_source"] == "MERGED_SANITIZED_V4_EVIDENCE_NOT_LIVE_REVALIDATION", "pointer target source")
    for key in (
        "successor_activation_authorization_record_id",
        "collection_execution_authorization_record_id",
        "expected_active_source_sha256",
        "expected_target_identity_sha256",
        "forbidden_production_identity_sha256",
        "forbidden_staging_identity_sha256",
        "expected_schema_manifest_sha256",
    ):
        need(pointer[key] == "UNBOUND", "pointer binding not UNBOUND " + key)
    for key in (
        "runtime_binding_contract_complete", "active_runner_created", "active_runner_activated",
        "planned_active_runner_path_present", "active_0010_migration_present",
        "legacy_ci_validator_cutover_authorized", "runtime_evidence_collected",
        "external_execution_authorized",
    ):
        need(pointer[key] is False, "pointer false boundary " + key)
    need(pointer["collector_state"] == "INERT_SYNTHETIC_ONLY", "pointer collector state")
    need(pointer["reviewer_state"] == "OFFLINE_SYNTHETIC_ONLY", "pointer reviewer state")
    need(pointer["current_execution_decision"] == "HOLD_NO_RUNNER_SRBE_OR_EXTERNAL_EXECUTION", "pointer current hold")
    need(pointer["decision"] == DECISION, "pointer decision")
    need(pointer["sole_next_subject"] == NEXT_SUBJECT, "pointer next subject")


def validate_templates() -> None:
    runtime = read_json(RUNTIME_TEMPLATE)
    need(runtime.get("schema") == "PMAI_P0_04_ARR_V3_V4_REBIND_RUNTIME_OBSERVATION_TEMPLATE_V1", "runtime template schema")
    runtime_values = {key: value for key, value in runtime.items() if key != "schema"}
    need(runtime_values, "runtime template values")
    need(all(value == "UNBOUND" or value is False for value in runtime_values.values()), "runtime template not inert")
    sanitized = read_json(COLLECTOR_TEMPLATE)
    need(set(sanitized) == COLLECTOR_HASH_KEYS | COLLECTOR_BOOLEAN_KEYS, "collector template keys")
    need(all(sanitized[key] == "UNBOUND" for key in COLLECTOR_HASH_KEYS), "collector template hash bound")
    need(all(sanitized[key] is False for key in COLLECTOR_BOOLEAN_KEYS), "collector template boolean true")
    for value in (*runtime_values.values(), *sanitized.values()):
        need(value == "UNBOUND" or value is False, "template live value")


def imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def validate_inert_script(relative: str, allowed_imports: set[str], collector: bool) -> None:
    path = safe_path(relative)
    source = text(relative)
    try:
        tree = ast.parse(source, filename="<inert-governance-tool>")
    except SyntaxError as exc:
        need(False, "inert tool parse " + relative)
        raise AssertionError from exc
    roots = imported_roots(tree)
    need(roots <= allowed_imports, "inert tool import allowlist " + relative)
    need(not (roots & FORBIDDEN_IMPORT_ROOTS), "external capability import " + relative)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            need(node.func.id not in FORBIDDEN_CALL_NAMES, "forbidden call " + relative)
        if isinstance(node, ast.Attribute):
            need(
                node.attr
                not in {
                    "FileType", "Popen", "__class__", "__dict__", "__globals__",
                    "__subclasses__", "connect", "glob", "iterdir", "mkdir", "modules",
                    "open", "popen", "read", "read_bytes", "read_text", "recv", "remove",
                    "rename", "replace", "request", "run", "send", "socket", "system",
                    "touch", "unlink", "urlopen", "walk", "write", "write_bytes", "write_text",
                },
                "forbidden attribute capability " + relative,
            )
    argument_names: list[str] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            continue
        need(len(node.args) == 1 and isinstance(node.args[0], ast.Constant), "CLI positional contract " + relative)
        need(type(node.args[0].value) is str, "CLI argument name type " + relative)
        argument_names.append(node.args[0].value)
        keyword_values = {item.arg: item.value for item in node.keywords if item.arg is not None}
        need(set(keyword_values) == {"action"}, "CLI keyword contract " + relative)
        need(
            isinstance(keyword_values["action"], ast.Constant)
            and keyword_values["action"].value == "store_true",
            "CLI action contract " + relative,
        )
    need(sorted(argument_names) == ["--dry-run", "--self-test"], "exact CLI arguments " + relative)
    for token in ("__class__", "__dict__", "__subclasses__", "importlib", "sys.modules", "sys.path"):
        need(token not in source, "dynamic capability token " + relative)
    for token in ("--collect", "--input", "--live", "--output", "--review"):
        need(token not in source, "operational CLI token " + relative)
    need(source.count('modes.add_argument("--dry-run"') == 1, "dry-run mode cardinality " + relative)
    need(source.count('modes.add_argument("--self-test"') == 1, "self-test mode cardinality " + relative)
    need("CANDIDATE_FORBIDDEN_BINDING_KEYS" in source, "candidate binding-domain guard " + relative)
    need("expected_active_source_sha256" in source, "active source field " + relative)
    need("IMPLEMENTATION_CANDIDATE_BINDING_DOMAIN_MISMATCH" in source, "candidate substitution guard " + relative)
    if collector:
        need(relative.endswith(".py.txt"), "collector suffix")
        need(path.stat().st_mode & 0o111 == 0, "collector executable bit")
        need("live_collection_adapter_present" in source, "collector live-adapter boundary")
    else:
        assignments = literal_assignments(source)
        need(assignments.get("EXPECTED_COLLECTOR_CONTRACT_SHA256") == COLLECTOR_CONTRACT_SHA256, "reviewer collector contract")
        need("OPERATIONAL_REVIEW_NOT_AUTHORIZED_BY_PREPARATION" in source, "reviewer operational hold")


def run_inert_json(relative: str, arguments: Sequence[str], expected_returncode: int) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-B", str(safe_path(relative)), *arguments],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        check=False,
    )
    need(result.returncode == expected_returncode, "inert tool exit " + relative)
    need(result.stderr == "", "inert tool stderr " + relative)
    lines = result.stdout.splitlines()
    need(len(lines) == 1, "inert tool output cardinality " + relative)
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        need(False, "inert tool JSON output " + relative)
        raise AssertionError from exc
    need(type(value) is dict and value, "inert tool output object " + relative)
    if relative == COLLECTOR and expected_returncode != 0:
        expected_keys = COLLECTOR_BOUNDARY_KEYS | {"error_code_sha256", "hold"}
    elif relative == REVIEWER and expected_returncode != 0:
        expected_keys = REVIEWER_BOUNDARY_KEYS | {"error_code_sha256", "hold"}
    elif relative == COLLECTOR and list(arguments) == ["--dry-run"]:
        expected_keys = COLLECTOR_BOUNDARY_KEYS | {
            "collector_contract_sha256", "hold", "live_collection_adapter_present",
            "runtime_binding_contract_complete", "self_test_only",
            "target_contract_provenance_sha256", "target_service_provenance_sha256",
        }
    elif relative == COLLECTOR and list(arguments) == ["--self-test"]:
        expected_keys = (
            COLLECTOR_BOUNDARY_KEYS
            | COLLECTOR_HASH_KEYS
            | COLLECTOR_BOOLEAN_KEYS
            | {"candidate_target_substitution_rejected", "hold", "release_eligible", "self_test"}
        )
    elif relative == REVIEWER and list(arguments) == ["--dry-run"]:
        expected_keys = REVIEWER_BOUNDARY_KEYS | {
            "hold", "operational_review_cli_present", "runtime_binding_contract_complete",
            "synthetic_fixture_tests_only", "target_contract_provenance_sha256",
            "target_service_provenance_sha256", "template_contract_sha256",
        }
    elif relative == REVIEWER and list(arguments) == ["--self-test"]:
        expected_keys = REVIEWER_BOUNDARY_KEYS | {
            "candidate_target_substitution_rejected", "contract_substitution_rejected",
            "fixture_record_sha256", "hold", "operational_release_rejected",
            "release_eligible", "self_test", "synthetic_values_persisted",
        }
    else:
        need(False, "unrecognized inert execution contract " + relative)
        raise AssertionError
    need(set(value) == expected_keys, "inert tool exact output keys " + relative)
    need(all(type(item) is bool or is_sha256(item) for item in value.values()), "inert tool output type " + relative)
    need(value.get("hold") is True, "inert tool HOLD output " + relative)
    return value


def validate_inert_tooling() -> None:
    validate_inert_script(COLLECTOR, ALLOWED_COLLECTOR_IMPORTS, collector=True)
    validate_inert_script(REVIEWER, ALLOWED_REVIEWER_IMPORTS, collector=False)
    collector_dry = run_inert_json(COLLECTOR, ["--dry-run"], 0)
    collector_test = run_inert_json(COLLECTOR, ["--self-test"], 0)
    reviewer_dry = run_inert_json(REVIEWER, ["--dry-run"], 0)
    reviewer_test = run_inert_json(REVIEWER, ["--self-test"], 0)
    run_inert_json(COLLECTOR, [], 1)
    run_inert_json(COLLECTOR, ["--collect"], 1)
    run_inert_json(REVIEWER, [], 1)
    run_inert_json(REVIEWER, ["--review"], 1)
    need(collector_dry.get("collector_contract_sha256") == COLLECTOR_CONTRACT_SHA256, "collector contract hash")
    for result, expected_boundaries in (
        (collector_dry, COLLECTOR_BOUNDARY_KEYS),
        (collector_test, COLLECTOR_BOUNDARY_KEYS),
        (reviewer_dry, REVIEWER_BOUNDARY_KEYS),
        (reviewer_test, REVIEWER_BOUNDARY_KEYS),
    ):
        need(all(result[key] is False for key in expected_boundaries), "inert boundary true or missing")
    for result in (collector_test, reviewer_test):
        need(result.get("self_test") is True, "self-test marker")
        need(result.get("release_eligible") is False, "synthetic release eligibility")
        need(result.get("candidate_target_substitution_rejected") is True, "candidate target substitution rejection")
    need(collector_test.get("collection_execution_authorized") is False, "collector synthetic authorization")
    need(collector_test.get("evidence_complete") is False, "collector synthetic evidence completeness")
    need(collector_test.get("fixture_only") is True, "collector fixture marker")
    need(collector_test.get("target_status_available") is False, "collector target status")
    need(collector_test.get("target_lifecycle_within_72h") is False, "collector lifecycle")
    need(reviewer_test.get("operational_release_rejected") is True, "reviewer operational rejection")
    need(reviewer_test.get("contract_substitution_rejected") is True, "reviewer contract rejection")


def validate_csvs() -> None:
    checklist = rows(CHECKLIST, ["item_id", "control", "current_state", "required_state", "status"])
    gates = rows(GO_NO_GO, ["gate_id", "gate", "current_state", "required_state", "decision"])
    tests = rows(TEST_MATRIX, ["test_id", "area", "test_case", "expected_result", "runtime_access", "status"])
    need([row["item_id"] for row in checklist] == [f"ARRV4-C{i:03d}" for i in range(1, 38)], "checklist IDs")
    need(all(row["status"] == "PASS" for row in checklist), "checklist status")
    need([row["gate_id"] for row in gates] == [f"ARRV4-G{i:03d}" for i in range(1, 21)], "gate IDs")
    expected_gate_decisions = (
        ["GO_PREPARATION"] * 5
        + ["HOLD_EXPECTED"] * 6
        + ["GO_PREPARATION"]
        + ["HOLD_EXPECTED"] * 5
        + ["GO_PREPARATION"] * 2
        + ["HOLD_EXPECTED"]
    )
    need([row["decision"] for row in gates] == expected_gate_decisions, "gate decision sequence")
    need([row["test_id"] for row in tests] == [f"ARRV4-T{i:03d}" for i in range(1, 41)], "test IDs")
    need(all(row["runtime_access"] == "none" for row in tests), "test runtime access")
    need(all(row["status"] == "DESIGNED" for row in tests), "test design status")


def validate_manifest() -> None:
    manifest = read_json(MANIFEST)
    expected_keys = {
        "schema", "stage_id", "substage", "work_bundle", "preparation_record_id",
        "repository", "base_branch", "base_commit", "base_tree_sha", "head_branch",
        "authorized_changed_path_count", "authorized_changed_path_sequence_sha256",
        "package_path_count", "manifest_member_count", "manifest_self_excluded",
        "central_integration_path", "ci_entrypoint_changed", "github_workflow_changed",
        "smoke_entrypoint_changed", "files",
    }
    need(set(manifest) == expected_keys, "manifest exact schema")
    expected_metadata: dict[str, object] = {
        "schema": "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_V1_PACKAGE_MANIFEST_V1",
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "preparation_record_id": PREPARATION_RECORD,
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "authorized_changed_path_count": 13,
        "authorized_changed_path_sequence_sha256": EXPECTED_PATH_SEQUENCE_SHA256,
        "package_path_count": 12,
        "manifest_member_count": 11,
        "manifest_self_excluded": True,
        "central_integration_path": CENTRAL,
        "ci_entrypoint_changed": False,
        "github_workflow_changed": False,
        "smoke_entrypoint_changed": False,
    }
    for key, expected in expected_metadata.items():
        need(type(manifest[key]) is type(expected) and manifest[key] == expected, "manifest metadata " + key)
    files = manifest["files"]
    need(type(files) is list and len(files) == 11, "manifest member count")
    need([item["path"] for item in files] == list(MANIFEST_MEMBERS), "manifest member sequence")
    for item in files:
        need(type(item) is dict and set(item) == {"path", "bytes", "sha256"}, "manifest member schema")
        relative = item["path"]
        need(type(relative) is str and relative in MANIFEST_MEMBERS, "manifest member path")
        path = safe_path(relative)
        need(item["bytes"] == path.stat().st_size, "manifest member byte count " + relative)
        need(item["sha256"] == digest(relative), "manifest member digest " + relative)
    need(MANIFEST not in {item["path"] for item in files}, "manifest self exclusion")
    need(CENTRAL not in {item["path"] for item in files}, "central manifest exclusion")


def validate_central_hook(introduction: str | None) -> None:
    source = text(CENTRAL)
    assignments = literal_assignments(source)
    expected = {
        "CURRENT_HOLD": LEGACY_CURRENT_HOLD,
        "CURRENT_COMPLETENESS": LEGACY_CURRENT_COMPLETENESS,
        "CURRENT_NEXT_STEP": LEGACY_CURRENT_NEXT_STEP,
        "EFFECTIVE_CURRENT_HOLD": EFFECTIVE_CURRENT_HOLD,
        "EFFECTIVE_CURRENT_COMPLETENESS": EFFECTIVE_CURRENT_COMPLETENESS,
        "EFFECTIVE_CURRENT_NEXT_STEP": EFFECTIVE_CURRENT_NEXT_STEP,
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_VALIDATOR": VALIDATOR,
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_VALIDATOR_SHA256": digest(VALIDATOR),
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_MANIFEST": MANIFEST,
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_MANIFEST_SHA256": digest(MANIFEST),
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_PASS_MARKER": PASS_MARKER,
    }
    for key, expected_value in expected.items():
        need(assignments.get(key) == expected_value, "central constant " + key)
    need(source.count('"decision=" + CURRENT_HOLD') == 1, "legacy decision source cardinality")
    need(source.count('"next_step=" + CURRENT_NEXT_STEP') == 1, "legacy next-step source cardinality")
    need(source.count('"effective_decision=" + EFFECTIVE_CURRENT_HOLD') == 1, "effective decision output")
    need(source.count('"effective_next_step=" + EFFECTIVE_CURRENT_NEXT_STEP') == 1, "effective next-step output")
    need(source.count('"effective_evidence_completeness=" + EFFECTIVE_CURRENT_COMPLETENESS') == 1, "effective completeness output")
    need(source.count("v4_rebind_preparation_result = subprocess.run(") == 1, "central preparation subprocess count")
    need(source.count('[sys.executable, "-B", str(v4_rebind_preparation_validator_path)]') == 1, "central preparation command")
    need(source.count("ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_PASS_MARKER") >= 3, "central preparation PASS checks")
    need(source.index("v4_evidence_result = subprocess.run(") < source.index("v4_rebind_preparation_result = subprocess.run("), "central hook order")
    for line in (
        '"v4_runner_srbe_rebind_preparation_complete=true"',
        '"runtime_binding_contract_complete=false"',
        '"restore_runner_created=false"',
        '"p0_04_execution_authorized=false"',
        '"staging_0010_apply_authorized=false"',
        '"active_0010_migration_file_created=false"',
        '"database_write=false"',
        '"migration_executed=false"',
    ):
        need(source.count(line) >= 1, "central safety output " + line)
    normalized = source if introduction is None else git_blob_text(introduction, CENTRAL)
    for name in (
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_VALIDATOR_SHA256",
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_MANIFEST_SHA256",
    ):
        pattern = (
            r"(" + re.escape(name) + r"\s*=\s*\(\s*[\"'])"
            r"[0-9a-f]{64}"
            r"([\"']\s*\))"
        )
        normalized, count = re.subn(pattern, r"\1<NORMALIZED_SHA256>\2", normalized)
        need(count == 1, "central normalized hash field " + name)
    need(
        hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        == CENTRAL_NORMALIZED_SHA256,
        "central normalized full-file hash",
    )


def validate_no_sensitive_material() -> None:
    combined = "\n".join(text(relative) for relative in (*PACKAGE_PATHS, CENTRAL))
    forbidden = {
        "provider or external URL": r"(?i)\bhttps?://",
        "database URI": r"(?i)\bpostgres(?:ql)?://",
        "raw provider resource identifier": r"(?i)\b(?:dpg|srv)-[a-z0-9]{6,}\b",
        "email address": r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "credential assignment": (
            r"(?i)\b(?:password|secret|database_url|access_token)\s*[:=]\s*"
            r"[^\s,}\]]+"
        ),
    }
    for label, pattern in forbidden.items():
        need(re.search(pattern, combined) is None, "forbidden " + label)


def main() -> int:
    for relative in PACKAGE_PATHS:
        safe_path(relative)
    introduction = validate_authorized_scope()
    validate_protected_history()
    validate_document()
    validate_baseline()
    validate_pointer()
    validate_templates()
    validate_inert_tooling()
    validate_csvs()
    validate_manifest()
    validate_central_hook(introduction)
    validate_previous_v4_evidence()
    validate_no_sensitive_material()
    for line in (
        PASS_MARKER,
        "stage_id=" + STAGE_ID,
        "work_bundle=" + WORK_BUNDLE,
        "base_commit=" + BASE_COMMIT,
        "base_tree_sha=" + BASE_TREE,
        "source_v4_evidence_pr=17",
        "source_v4_evidence_merge_commit=" + BASE_COMMIT,
        "target_contract_identity_sha256=" + TARGET_CONTRACT_SHA256,
        "target_service_identifier_sha256=" + TARGET_SERVICE_SHA256,
        "target_state_source=MERGED_SANITIZED_V4_EVIDENCE_NOT_LIVE_REVALIDATION",
        "successor_activation_authorization_record_id=UNBOUND",
        "expected_active_source_sha256=UNBOUND",
        "expected_target_identity_sha256=UNBOUND",
        "expected_schema_manifest_sha256=UNBOUND",
        "runtime_binding_contract_complete=false",
        "planned_active_runner_path_present=false",
        "active_0010_migration_present=false",
        "legacy_ci_validator_cutover_authorized=false",
        "render_readonly_access=false",
        "database_connection=false",
        "runtime_evidence_collection=false",
        "runner_creation=false",
        "runner_activation=false",
        "runner_execution=false",
        "restore_execution=false",
        "migration_creation_or_execution=false",
        "deployment=false",
        "target_deletion=false",
        "decision=" + DECISION,
        "sole_next_subject=" + NEXT_SUBJECT,
        "ALL PASS: PMAI-P0-04 V4 runner activation and SRBE rebind preparation",
    ):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
