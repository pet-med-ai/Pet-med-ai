#!/usr/bin/env python3
"""Validate the PMAI-P0-04 V4 runner/SRBE authorization review package."""

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
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_"
    "AUTHORIZATION_REVIEW_V1"
)
WORK_BUNDLE = "PMAI-P0-04-ARR-V3-ACT-SRBE-REBIND-V4-AUTH-REVIEW"
REVIEW_RECORD = "PMAI-P0-04-ARR-V3-ACT-SRBE-REBIND-V4-AUTH-REV-20260827"
BASE_COMMIT = "98be892b5018058e6020f43caf6dd4d84a0f06b8"
BASE_TREE = "a03646e32d147ce5e78653305eb263149b1104b9"
HEAD_BRANCH = "pmai-p0-04-arr-v3-srbe-rebind-v4-auth-review"
SOURCE_HEAD = "195ac8990f64e062ca32ec3379035255de78d0df"
SOURCE_MERGE = BASE_COMMIT
SOURCE_TREE = BASE_TREE
SOURCE_CI_RUN_ID = 33071543545
SOURCE_CI_RUN_NUMBER = 224
EXPECTED_PATH_SEQUENCE_SHA256 = (
    "3f0504a0eaaf5c8679ae2da1593680371ba5c544cd072cf8f2fc0520af9cf33f"
)
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
NEXT_SUBJECT = (
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_"
    "AND_REVIEW_V4_EXECUTION_AUTHORIZATION_V1"
)
DECISION = "GO_TO_SEPARATE_" + NEXT_SUBJECT
PASS_MARKER = (
    "active_restore_runner_v3_activation_and_srbe_contract_rebind_"
    "v4_authorization_review=PASS"
)
FINAL_PASS = "ALL PASS: PMAI-P0-04 V4 runner activation and SRBE rebind authorization review"

PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
    "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_"
    "AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_V1"
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
    "migration_0010_active_restore_runner_v3_activation_and_srbe_contract_"
    "rebind_v4_authorization_review_v1.py"
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

PREP_PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
    "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_"
    "AND_SRBE_CONTRACT_REBIND_V4_PREPARATION_V1"
)
PREP_BASELINE = PREP_PREFIX + "_LOCKED_BASELINE_V1.json"
PREP_POINTER = PREP_PREFIX + "_ACTIVE_POINTER_V1.json"
PREP_MANIFEST = PREP_PREFIX + "_PACKAGE_MANIFEST_V1.json"
PREP_COLLECTOR = PREP_PREFIX + "_COLLECTOR_CANDIDATE_V1.py.txt"
PREP_RUNTIME_TEMPLATE = PREP_PREFIX + "_RUNTIME_OBSERVATION_TEMPLATE_V1.json"
PREP_SANITIZED_TEMPLATE = PREP_PREFIX + "_SANITIZED_COLLECTOR_OUTPUT_TEMPLATE_V1.json"
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
    PREP_BASELINE: "dff8cb0d90dfb7c68be8afb7a21c62ac4d6dea14cd600b89409e0a5e93586f6c",
    PREP_POINTER: "5fb6082e7f9a3a0d0e33eef37b4e136a42c7b8b57ee1c5a4bc7bd44a67171ece",
    PREP_MANIFEST: "4e1e3b895f522e58917052d8af3e8bcdd6127ef9db2b4fc0cccff95124e2641c",
    PREP_VALIDATOR: "7178853124e403080cdcc0c3bed63ec31c9acf5f791f5352fdd62373acdc770d",
    PREP_REVIEWER: "c655571668758332f6501cb44b3d074600a405be7984c6110d4db30190f4ef87",
    PREP_COLLECTOR: "753f4eb9f1cef9c98b4fca934bbbc430b77aab028fd71f77d345f695ed383fb6",
    PREP_RUNTIME_TEMPLATE: "580a485ae62221ef4d2e3e598321bb9197e5083d0cb0926fdc85a1766544f1b2",
    PREP_SANITIZED_TEMPLATE: "f65411c98bebc8f7773724d0ee9088faeac6f3b620c853079233c360921ceee8",
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
REVIEW_EFFECTIVE_NEXT = "PREPARE_" + NEXT_SUBJECT
CENTRAL_NORMALIZED_SHA256 = (
    "54167766b86da69a0f0a8bf3e889d674962197dd8d7a8f3eb107abd2e79e7baa"
)

UNBOUND_FIELDS = (
    "successor_activation_authorization_record_id",
    "collection_execution_authorization_record_id",
    "successor_activation_authorization_record_sha256",
    "collection_execution_authorization_record_sha256",
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
FALSE_FIELDS = (
    "runtime_binding_contract_complete",
    "collection_execution_authorized",
    "runtime_evidence_collected",
    "evidence_complete",
    "external_execution_authorized",
    "planned_active_runner_path_present",
    "active_0010_migration_present",
    "legacy_ci_validator_cutover_authorized",
    "target_live_metadata_revalidation",
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
    "manual_retry",
    "automatic_retry",
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
    need(len(introductions) == 1, "authorization review introduction commit count")
    introduction = introductions[0]
    parents = git_lines("show", "-s", "--format=%P", introduction)
    need(len(parents) == 1 and parents[0] == BASE_COMMIT, "introduction parent")
    paths = git_lines("diff", "--name-only", BASE_COMMIT + ".." + introduction)
    need(paths == list(EXPECTED_CHANGED_PATHS), "introduction changed paths")
    if head != introduction:
        first_parent = git_lines("rev-list", "--first-parent", BASE_COMMIT + ".." + head)
        need(introduction not in first_parent, "linear additional commit after introduction")
        protected = git_lines("diff", "--name-only", introduction + ".." + head, "--", *PACKAGE_PATHS)
        need(not protected, "authorization review package changed after introduction")
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
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = value
    return values


def validate_source_anchors() -> None:
    for relative, expected in PREP_HASHES.items():
        need(digest(relative) == expected, "preparation protected hash " + relative)
    candidate = safe_path(IMPLEMENTATION_CANDIDATE)
    need(digest(IMPLEMENTATION_CANDIDATE) == CANDIDATE_SHA256, "implementation candidate hash")
    need(not candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), "candidate executable")
    need(not (ROOT / PLANNED_ACTIVE_RUNNER).exists(), "planned active runner path present")
    migrations = ROOT / MIGRATIONS
    need(not list(migrations.glob("0010*.py")), "active 0010 migration present")
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / PREP_VALIDATOR)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=45,
        check=False,
    )
    need(result.returncode == 0, "preparation validator exit")
    need(result.stderr == "", "preparation validator stderr")
    need(result.stdout.splitlines().count(PREP_PASS_MARKER) == 1, "preparation validator PASS marker")


def validate_document() -> None:
    source = text(DOC)
    required = {
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "authorization_review_record_id": REVIEW_RECORD,
        "stage_status": "IN_PROGRESS",
        "package_status": "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_RECORD_ONLY",
        "review_status": "PROPOSED_APPROVE_SEPARATE_SRBE_COLLECTION_AND_REVIEW_EXECUTION_AUTHORIZATION_ELIGIBILITY_ONLY",
        "authorization_review_scope": "REPOSITORY_STATIC_ANCHORS_AND_FUTURE_GATES_ONLY",
        "authorization_review_record_only": "true",
        "current_execution_decision": "HOLD_NO_RUNNER_SRBE_OR_EXTERNAL_EXECUTION",
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "changed_path_scope": "EXACT_9_PATHS",
        "changed_path_sequence_sha256": EXPECTED_PATH_SEQUENCE_SHA256,
        "source_preparation_pr": "18",
        "source_preparation_head_commit": SOURCE_HEAD,
        "source_preparation_merge_commit": SOURCE_MERGE,
        "source_preparation_tree_sha": SOURCE_TREE,
        "source_preparation_ci_run_id": str(SOURCE_CI_RUN_ID),
        "source_preparation_ci_run_number": str(SOURCE_CI_RUN_NUMBER),
        "source_preparation_ci_status": "PASS",
        "target_contract_identity_sha256": TARGET_CONTRACT_SHA256,
        "target_service_identifier_sha256": TARGET_SERVICE_SHA256,
        "target_hashes_are_sanitized_provenance_only": "true",
        "target_contract_hash_may_substitute_runtime_identity": "false",
        "target_service_hash_may_substitute_runtime_identity": "false",
        "target_live_metadata_revalidation": "false",
        "target_live_revalidation_required_before_future_external_action": "true",
        "restore_runner_v3_implementation_candidate_sha256": CANDIDATE_SHA256,
        "planned_active_runner_path": PLANNED_ACTIVE_RUNNER,
        "collector_contract_sha256": COLLECTOR_CONTRACT_SHA256,
        "post_effective_gate_srbe_collection_and_review_execution_authorization_eligible": "true",
        "post_effective_gate_runner_creation_or_activation_authorization_eligible": "false",
        "decision": DECISION,
        "post_review_sole_next_subject": NEXT_SUBJECT,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in required.items():
        need(marker(source, key) == expected, "document marker " + key)
    for key in UNBOUND_FIELDS:
        need(marker(source, key) == "UNBOUND", "document unbound " + key)
    for key in FALSE_FIELDS:
        need(marker(source, key) == "false", "document false " + key)
    for key in EXECUTION_FALSE_FIELDS:
        need(marker(source, key) == "false", "document execution false " + key)


def validate_baseline_and_pointer() -> None:
    baseline = read_json(BASELINE)
    required: dict[str, Any] = {
        "schema": "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_V1_LOCKED_BASELINE_V1",
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "authorization_review_record_id": REVIEW_RECORD,
        "stage_status": "IN_PROGRESS",
        "package_status": "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_RECORD_ONLY",
        "review_status": "PROPOSED_APPROVE_SEPARATE_SRBE_COLLECTION_AND_REVIEW_EXECUTION_AUTHORIZATION_ELIGIBILITY_ONLY",
        "authorization_review_scope": "REPOSITORY_STATIC_ANCHORS_AND_FUTURE_GATES_ONLY",
        "authorization_review_record_only": True,
        "current_execution_decision": "HOLD_NO_RUNNER_SRBE_OR_EXTERNAL_EXECUTION",
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "decision": DECISION,
        "post_review_sole_next_subject": NEXT_SUBJECT,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in required.items():
        need(type(baseline.get(key)) is type(expected) and baseline.get(key) == expected, "baseline " + key)
    source = baseline["source_preparation"]
    need(source["pull_request"] == 18, "baseline source PR")
    need(source["head_commit"] == SOURCE_HEAD, "baseline source head")
    need(source["merge_commit"] == SOURCE_MERGE, "baseline source merge")
    need(source["tree_sha"] == SOURCE_TREE, "baseline source tree")
    need(source["ci_run_id"] == SOURCE_CI_RUN_ID, "baseline source CI ID")
    need(source["ci_run_number"] == SOURCE_CI_RUN_NUMBER, "baseline source CI number")
    need(source["ci_status"] == "PASS", "baseline source CI status")
    runtime = baseline["runtime_binding_state"]
    for key in UNBOUND_FIELDS:
        need(runtime.get(key) == "UNBOUND", "baseline unbound " + key)
    for key in (
        "runtime_binding_contract_complete", "collection_execution_authorized",
        "runtime_evidence_collected", "evidence_complete", "external_execution_authorized",
    ):
        need(runtime.get(key) is False, "baseline runtime false " + key)
    static = baseline["static_provenance"]
    need(static["target_contract_identity_sha256"] == TARGET_CONTRACT_SHA256, "baseline target contract")
    need(static["target_service_identifier_sha256"] == TARGET_SERVICE_SHA256, "baseline target service")
    need(static["implementation_candidate_sha256"] == CANDIDATE_SHA256, "baseline candidate")
    need(static["planned_active_runner_path_present"] is False, "baseline active path")
    need(static["active_0010_migration_present"] is False, "baseline migration")
    for key in EXECUTION_FALSE_FIELDS:
        need(baseline["execution_boundaries"].get(key) is False, "baseline execution false " + key)
    live = baseline["live_observation_state"]
    need(all(value is False for value in live.values()), "baseline live observation state")
    post = baseline["post_effective_boundary"]
    need(post["srbe_collection_and_review_execution_authorization_eligible"] is True, "baseline SRBE eligibility")
    need(post["runner_creation_or_activation_authorization_eligible"] is False, "baseline runner eligibility")
    need(post["authorization_reuse_allowed"] is False, "baseline authorization reuse")

    pointer = read_json(POINTER)
    pointer_required: dict[str, Any] = {
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "authorization_review_record_id": REVIEW_RECORD,
        "pointer_version": 1,
        "supersedes_pointer_sha256": PREP_HASHES[PREP_POINTER],
        "active_locked_baseline_sha256": digest(BASELINE),
        "source_preparation_merge_commit": SOURCE_MERGE,
        "source_preparation_tree_sha": SOURCE_TREE,
        "source_preparation_ci_run_number": SOURCE_CI_RUN_NUMBER,
        "source_preparation_ci_status": "PASS",
        "target_contract_identity_sha256": TARGET_CONTRACT_SHA256,
        "target_service_identifier_sha256": TARGET_SERVICE_SHA256,
        "runtime_binding_contract_complete": False,
        "runtime_evidence_collected": False,
        "external_execution_authorized": False,
        "post_effective_gate_srbe_collection_and_review_execution_authorization_eligible": True,
        "post_effective_gate_runner_creation_or_activation_authorization_eligible": False,
        "active_runner_created": False,
        "active_runner_activated": False,
        "runner_imported": False,
        "runner_executed": False,
        "planned_active_runner_path_present": False,
        "active_0010_migration_present": False,
        "legacy_ci_validator_cutover_authorized": False,
        "current_execution_decision": "HOLD_NO_RUNNER_SRBE_OR_EXTERNAL_EXECUTION",
        "decision": DECISION,
        "post_review_sole_next_subject": NEXT_SUBJECT,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in pointer_required.items():
        need(type(pointer.get(key)) is type(expected) and pointer.get(key) == expected, "pointer " + key)
    for key in (
        "successor_activation_authorization_record_id",
        "collection_execution_authorization_record_id",
        "expected_active_source_sha256",
        "expected_target_identity_sha256",
        "forbidden_production_identity_sha256",
        "forbidden_staging_identity_sha256",
        "expected_schema_manifest_sha256",
    ):
        need(pointer.get(key) == "UNBOUND", "pointer unbound " + key)


def validate_csvs() -> None:
    checklist = rows(CHECKLIST, ["item_id", "control", "current_state", "required_state", "status"])
    gates = rows(GO_NO_GO, ["gate_id", "gate", "current_state", "required_state", "decision"])
    tests = rows(TEST_MATRIX, ["test_id", "area", "test_case", "expected_result", "runtime_access", "status"])
    need([row["item_id"] for row in checklist] == [f"ARRV4AR-C{i:03d}" for i in range(1, 49)], "checklist IDs")
    need(all(row["status"] == "PASS" for row in checklist), "checklist status")
    need([row["gate_id"] for row in gates] == [f"ARRV4AR-G{i:03d}" for i in range(1, 27)], "gate IDs")
    need({row["decision"] for row in gates} <= {"GO_REVIEW", "HOLD_EXPECTED", "HOLD_UNTIL_PUBLICATION"}, "gate decisions")
    by_gate = {row["gate"]: row for row in gates}
    need(by_gate["Runtime binding contract"]["decision"] == "HOLD_EXPECTED", "runtime binding gate")
    need(by_gate["SRBE execution authorization eligibility"]["decision"] == "GO_REVIEW", "SRBE eligibility gate")
    need(by_gate["Runner creation or activation eligibility"]["decision"] == "HOLD_EXPECTED", "runner eligibility gate")
    need([row["test_id"] for row in tests] == [f"ARRV4AR-T{i:03d}" for i in range(1, 49)], "test IDs")
    need(all(row["runtime_access"] == "none" for row in tests), "test runtime access")
    need(all(row["status"] == "DESIGNED" for row in tests), "test status")


def validate_manifest() -> None:
    manifest = read_json(MANIFEST)
    expected_keys = {
        "schema", "stage_id", "substage", "work_bundle", "authorization_review_record_id",
        "repository", "base_branch", "base_commit", "base_tree_sha", "head_branch",
        "authorized_changed_path_count", "authorized_changed_path_sequence_sha256",
        "package_path_count", "manifest_member_count", "manifest_self_excluded",
        "central_integration_path", "ci_entrypoint_changed", "github_workflow_changed",
        "smoke_entrypoint_changed", "files",
    }
    need(set(manifest) == expected_keys, "manifest exact schema")
    metadata: dict[str, Any] = {
        "schema": "PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_V1_PACKAGE_MANIFEST_V1",
        "stage_id": STAGE_ID,
        "substage": SUBSTAGE,
        "work_bundle": WORK_BUNDLE,
        "authorization_review_record_id": REVIEW_RECORD,
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
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_VALIDATOR": VALIDATOR,
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_VALIDATOR_SHA256": digest(VALIDATOR),
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_MANIFEST": MANIFEST,
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_MANIFEST_SHA256": digest(MANIFEST),
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_PASS_MARKER": PASS_MARKER,
    }
    for key, expected_value in expected.items():
        need(assignments.get(key) == expected_value, "central constant " + key)
    need(source.count("v4_rebind_preparation_result = subprocess.run(") == 1, "preparation subprocess count")
    need(source.count("v4_rebind_authorization_review_result = subprocess.run(") == 1, "review subprocess count")
    need(source.index("v4_rebind_preparation_result = subprocess.run(") < source.index("v4_rebind_authorization_review_result = subprocess.run("), "central hook order")
    need(source.count('[sys.executable, "-B", str(v4_rebind_authorization_review_validator_path)]') == 1, "review command")
    need(source.count('"v4_runner_srbe_rebind_authorization_review_complete=true"') == 1, "review complete output")
    need(source.count('"post_effective_gate_srbe_collection_and_review_execution_authorization_eligible=true"') == 1, "SRBE eligibility output")
    need(source.count('"authorization_review_effective_decision=" + AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_HOLD') == 1, "review effective decision output")
    need(source.count('"authorization_review_effective_next_step=" + AUTHORIZATION_REVIEW_EFFECTIVE_CURRENT_NEXT_STEP') == 1, "review effective next output")
    for line in (
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
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_VALIDATOR_SHA256",
        "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_AUTHORIZATION_REVIEW_MANIFEST_SHA256",
    ):
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
    need(list(EXPECTED_CHANGED_PATHS) == sorted(EXPECTED_CHANGED_PATHS, key=lambda value: value.encode("utf-8")), "changed path sort")
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
    print("source_preparation_pr=18")
    print("source_preparation_merge_commit=" + SOURCE_MERGE)
    print("source_preparation_ci_run_number=224")
    print("authorization_review_record_only=true")
    print("current_execution_decision=HOLD_NO_RUNNER_SRBE_OR_EXTERNAL_EXECUTION")
    print("successor_activation_authorization_record_id=UNBOUND")
    print("collection_execution_authorization_record_id=UNBOUND")
    print("expected_active_source_sha256=UNBOUND")
    print("expected_target_identity_sha256=UNBOUND")
    print("expected_schema_manifest_sha256=UNBOUND")
    print("runtime_binding_contract_complete=false")
    print("runtime_evidence_collected=false")
    print("external_execution_authorized=false")
    print("post_effective_gate_srbe_collection_and_review_execution_authorization_eligible=true")
    print("post_effective_gate_runner_creation_or_activation_authorization_eligible=false")
    print("planned_active_runner_path_present=false")
    print("active_0010_migration_present=false")
    print("render_readonly_access=false")
    print("database_connection=false")
    print("runner_creation=false")
    print("runner_activation=false")
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
