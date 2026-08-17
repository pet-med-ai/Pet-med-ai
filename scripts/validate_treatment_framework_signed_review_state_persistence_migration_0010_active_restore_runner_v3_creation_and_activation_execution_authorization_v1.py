#!/usr/bin/env python3
"""Validate the P0-04 active-runner V3 execution-authorization record."""

from __future__ import annotations

import ast
import csv
import hashlib
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_"
DOC = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1.md"
CHECKLIST = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1_CHECKLIST_V1.csv"
GO_NO_GO = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1_GO_NO_GO_V1.csv"
TEST_MATRIX = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1_TEST_MATRIX_V1.csv"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_creation_and_activation_execution_authorization_v1.py"
REVIEW_DOC = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_AUTHORIZATION_REVIEW_V1.md"
TARGET_EVIDENCE_DOC = "docs/clinical_data/" + PREFIX + "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3.md"
DESIGN_CANDIDATE = "docs/clinical_data/" + PREFIX + "DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
IMPLEMENTATION_CANDIDATE = "docs/clinical_data/" + PREFIX + "DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_CANDIDATE_V1.py.txt"
ACTIVE_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_v3.py"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"
CI = "scripts/ci_static_checks.sh"

EXPECTED_HEAD = "41cebde19b7990aff5beb27899e7892876e4a698"
EXPECTED_PARENT = "41b94ef7e5e337538fa6ef22ebc0a225112c5c59"
EXPECTED_ISOLATED = "8d1dc8814ed8f80d8bc965b494c1c320fc08f228"
EXPECTED_PRIOR_CI_SHA256 = "2aa57fb16b2513954b8ab8f9f86646a3d961174576ea6aa3539e683636620b6c"
EXPECTED_FINAL_CI_SHA256 = "a433a4790a1ea2a638640906dd43e8402bfccaa463967968eb0e1eda915ad6d4"
EXPECTED_DESIGN_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_IMPLEMENTATION_SHA256 = "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
EXPECTED_LOCKED_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_TARGET_CONTRACT_SHA256 = "e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744"
EXPECTED_TARGET_COUNT = 152
EXPECTED_COMMAND_COUNT = 31
EXPECTED_AUTHORIZATION_RECORD_ID = "PMAI-P0-04-ARR-V3-CA-EXEC-AUTH-V1-20260816"
EXPECTED_NEXT_ACTION = "REQUEST_SEPARATE_ONE_TIME_CREATION_AND_ACTIVATION_EXECUTION_CONFIRMATION"
PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}

FALSE_FLAGS = {
    "EXECUTION_ENABLED", "ARCHIVE_ACCESS_ENABLED", "ARCHIVE_LISTING_ENABLED",
    "MEMBER_HEADER_READ_ENABLED", "MEMBER_PAYLOAD_READ_ENABLED", "ARCHIVE_EXTRACTION_ENABLED",
    "TARGET_PREFLIGHT_ENABLED", "DATABASE_CONNECTION_ENABLED", "DATABASE_WRITE_ENABLED",
    "RESTORE_PROCESS_ENABLED", "RESTORE_EXECUTION_ENABLED", "PG_RESTORE_INVOCATION_ENABLED",
    "PSQL_INVOCATION_ENABLED", "AUTOMATIC_RETRY_ENABLED", "MANUAL_RETRY_ENABLED",
    "MIGRATION_0010_ENABLED", "DEPLOYMENT_ENABLED", "RESOURCE_DELETION_ENABLED",
}
UNBOUND_BINDINGS = {
    "ACTIVATION_AUTHORIZATION_RECORD_ID", "EXPECTED_ACTIVE_SOURCE_SHA256",
    "EXPECTED_TARGET_IDENTITY_SHA256", "FORBIDDEN_PRODUCTION_IDENTITY_SHA256",
    "FORBIDDEN_STAGING_IDENTITY_SHA256", "EXPECTED_SCHEMA_MANIFEST_SHA256",
}


def need(condition: bool, message: str) -> None:
    if not condition:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(rel: str) -> str:
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + rel)
    return path.read_text(encoding="utf-8")


def marker(source: str, key: str) -> str:
    found = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", source)
    need(found and len(set(found)) == 1, "marker consistency " + key)
    return found[0]


def rows(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def assignments(source: str) -> dict[str, object]:
    values: dict[str, object] = {}
    tree = ast.parse(source, filename=IMPLEMENTATION_CANDIDATE)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        values[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            try:
                values[node.target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return values


def ci_targets(source: str) -> list[str]:
    match = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)\s*$", source)
    need(match is not None, "CI TARGETS block")
    return re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)


def python_lines(source: str) -> list[str]:
    return [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith("python3 ")
        and not line.strip().startswith("python3 -m py_compile ")
    ]


def validate_candidate() -> None:
    path = ROOT / IMPLEMENTATION_CANDIDATE
    need(IMPLEMENTATION_CANDIDATE.endswith(".py.txt"), "implementation candidate suffix")
    need(path.is_file() and not path.is_symlink(), "implementation candidate missing")
    need(sha256_path(path) == EXPECTED_IMPLEMENTATION_SHA256, "implementation candidate hash")
    need(not path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), "implementation candidate executable")
    need(not (ROOT / IMPLEMENTATION_CANDIDATE.removesuffix(".txt")).exists(), "implementation candidate active twin")
    source = path.read_text(encoding="utf-8")
    values = assignments(source)
    for name in FALSE_FLAGS:
        need(values.get(name) is False, "candidate fail-closed flag " + name)
    for name in UNBOUND_BINDINGS:
        need(values.get(name) == "UNBOUND", "candidate future binding " + name)
    need("shell=True" not in source and "shell = True" not in source, "shell true")
    need("extractall(" not in source and ".extract(" not in source, "unsafe tar extraction API")
    need("eval(" not in source and "exec(" not in source, "unsafe dynamic execution")


def main() -> int:
    doc = read(DOC)
    review = read(REVIEW_DOC)
    target_evidence = read(TARGET_EVIDENCE_DOC)
    ci = read(CI)

    required = {
        "stage_id": "PMAI-P0-04",
        "substage": "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1",
        "package_status": "ACTIVE_RUNNER_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_RECORD_ONLY",
        "authorization_record_id": EXPECTED_AUTHORIZATION_RECORD_ID,
        "current_turn_scope": "REPOSITORY_ONLY_DESIGN_AND_DRY_RUN",
        "authorization_scope": "ONE_ATOMIC_CREATE_NEW_AND_NONEXECUTING_ACTIVATION_ACTION_ONLY",
        "current_active_restore_runner_creation_authorized": "false",
        "current_restore_runner_v3_activation_authorized": "false",
        "current_creation_and_activation_execution_authorized": "false",
        "post_effective_gate_creation_and_activation_execution_eligible": "true",
        "post_effective_gate_creation_and_activation_execution_authorized": "false",
        "one_time_creation_and_activation_confirmation_present": "false",
        "current_creation_and_activation_attempts_authorized": "0",
        "post_confirmation_creation_and_activation_attempts_authorized": "1",
        "creation_and_activation_attempts_consumed": "0",
        "automatic_retry": "false",
        "manual_retry_authorized": "false",
        "authorization_reuse_allowed": "false",
        "active_restore_runner_created": "false",
        "restore_runner_activated": "false",
        "restore_runner_executed": "false",
        "selected_route": "ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3",
        "design_candidate_sha256": EXPECTED_DESIGN_SHA256,
        "implementation_candidate_sha256": EXPECTED_IMPLEMENTATION_SHA256,
        "implementation_candidate_modified_by_authorization": "false",
        "target_contract_identity_sha256": EXPECTED_TARGET_CONTRACT_SHA256,
        "target_status_from_published_evidence": "AVAILABLE",
        "target_status_rechecked_by_authorization": "false",
        "planned_active_runner_path_present": "false",
        "active_0010_migration_present": "false",
        "activation_authorization_record_id_binding": "UNBOUND_UNTIL_ONE_TIME_CONFIRMATION",
        "expected_active_source_sha256_binding": "UNBOUND_UNTIL_ONE_TIME_CONFIRMATION",
        "expected_target_identity_sha256_binding": "UNBOUND_UNTIL_ONE_TIME_CONFIRMATION",
        "forbidden_production_identity_sha256_binding": "UNBOUND_UNTIL_ONE_TIME_CONFIRMATION",
        "forbidden_staging_identity_sha256_binding": "UNBOUND_UNTIL_ONE_TIME_CONFIRMATION",
        "expected_schema_manifest_sha256_binding": "UNBOUND_UNTIL_ONE_TIME_CONFIRMATION",
        "runtime_binding_contract_complete": "false",
        "binding_values_collected_by_current_package": "false",
        "execution_action": "ATOMIC_CREATE_NEW_ACTIVE_RUNNER_SOURCE_AND_SET_REVIEWED_NONEXECUTING_MODE_ONLY",
        "execution_attempt_limit": "1",
        "execution_attempts_consumed": "0",
        "activation_may_import_runner": "false",
        "activation_may_execute_runner": "false",
        "activation_may_access_archive": "false",
        "activation_may_read_credentials": "false",
        "activation_may_access_target": "false",
        "activation_may_connect_database": "false",
        "activation_may_restore": "false",
        "restore_runner_v3_execution_authorized": "false",
        "one_time_restore_execution_authorized": "false",
        "restore_attempts_authorized": "0",
        "repository_only": "true",
        "network_access": "false",
        "provider_control_plane_opened": "false",
        "archive_file_opened": "false",
        "backup_archive_listing_invoked": "false",
        "credential_collection_performed": "false",
        "target_accessed": "false",
        "target_modified": "false",
        "target_deleted": "false",
        "database_connection": "false",
        "restore_execution": "false",
        "migration_created": "false",
        "migration_executed": "false",
        "application_deployment": "false",
        "resource_deleted": "false",
        "files_staged": "false",
        "files_committed": "false",
        "files_pushed": "false",
        "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "p0_04_execution_authorized": "false",
        "staging_0010_apply_authorized": "false",
        "decision": "GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY",
        "next_action": EXPECTED_NEXT_ACTION,
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)

    baseline = {
        "local_main": EXPECTED_HEAD,
        "origin_main": EXPECTED_HEAD,
        "main_parent": EXPECTED_PARENT,
        "github_ci_gate_number": "214",
        "github_ci_gate_status": "PASS",
        "github_ci_gate_commit": EXPECTED_HEAD,
        "prior_ci_sha256": EXPECTED_PRIOR_CI_SHA256,
        "final_ci_sha256": EXPECTED_FINAL_CI_SHA256,
        "local_isolated_branch": EXPECTED_ISOLATED,
        "remote_isolated_branch": EXPECTED_ISOLATED,
        "completed_commit": EXPECTED_HEAD,
        "completed_parent": EXPECTED_PARENT,
        "completed_ci_gate": "214",
        "completed_ci_status": "PASS",
    }
    for key, expected in baseline.items():
        need(marker(doc, key) == expected, "baseline marker " + key)

    review_required = {
        "substage": "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_AUTHORIZATION_REVIEW_V1",
        "authorization_scope_recorded": "true",
        "post_effective_gate_creation_and_activation_eligible": "true",
        "post_effective_gate_creation_and_activation_execution_authorized": "false",
        "runtime_binding_contract_complete": "false",
        "active_restore_runner_created": "false",
        "restore_runner_activated": "false",
        "restore_runner_executed": "false",
        "decision": "GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY",
        "next_subject": "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1",
    }
    for key, expected in review_required.items():
        need(marker(review, key) == expected, "authorization review marker " + key)

    need(marker(target_evidence, "target_contract_identity_sha256") == EXPECTED_TARGET_CONTRACT_SHA256, "target evidence contract")
    need(marker(target_evidence, "target_status") == "AVAILABLE", "target evidence status")
    need(sha256_path(ROOT / DESIGN_CANDIDATE) == EXPECTED_DESIGN_SHA256, "design candidate hash")
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_SHA256, "locked runner hash")
    validate_candidate()
    need(not (ROOT / ACTIVE_RUNNER).exists(), "planned active runner already exists")
    need(not list((ROOT / "backend/migrations/versions").glob("0010*.py")), "active 0010 migration")

    checklist, gates, tests = rows(CHECKLIST), rows(GO_NO_GO), rows(TEST_MATRIX)
    need(len(checklist) == 60 and len({row["control_id"] for row in checklist}) == 60, "checklist cardinality")
    need(all(row["status"] == "PASS" for row in checklist), "checklist status")
    need(len(gates) == 31 and len({row["gate_id"] for row in gates}) == 31, "go/no-go cardinality")
    need({row["status"] for row in gates} == {"PASS", "HOLD"}, "go/no-go status set")
    by_gate = {row["gate"]: row for row in gates}
    need(by_gate["one time confirmation present"]["status"] == "HOLD", "confirmation gate")
    need(by_gate["runtime binding contract complete"]["status"] == "HOLD", "binding gate")
    need(by_gate["repository apply authority"]["status"] == "HOLD", "apply gate")
    need(by_gate["Git publication authority"]["status"] == "HOLD", "publication gate")
    need(by_gate["authorization package internally ready"]["status"] == "PASS", "internal readiness gate")
    need(len(tests) == 52 and len({row["test_id"] for row in tests}) == 52, "test matrix cardinality")
    need(all(row["status"] == "DESIGNED" for row in tests), "test matrix status")

    targets = ci_targets(ci)
    commands = python_lines(ci)
    need(len(targets) == EXPECTED_TARGET_COUNT and len(set(targets)) == EXPECTED_TARGET_COUNT, "CI target cardinality")
    need(PACKAGE_PATHS <= set(targets), "CI package targets")
    need(len(commands) == EXPECTED_COMMAND_COUNT, "CI command cardinality")
    preparation_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_creation_and_activation_preparation_v1.py || exit 1"
    review_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_creation_and_activation_authorization_review_v1.py || exit 1"
    authorization_command = "python3 " + VALIDATOR + " || exit 1"
    need(commands[-3:] == [preparation_command, review_command, authorization_command], "CI command order")
    need(ci.splitlines().count("# PMAI-P0-04 active restore runner V3 creation and activation execution authorization v1") == 1, "CI marker count")
    need(ci.splitlines().count(authorization_command) == 1, "CI authorization command count")
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, "CI file hash")

    unsafe_patterns = ("postgres://", "postgresql://", "dashboard.render.com/", "dpg-", "srv-")
    for rel in PACKAGE_PATHS:
        value = read(rel)
        need(value.endswith("\n"), "final newline " + rel)
        if rel != VALIDATOR:
            need(not any(pattern in value for pattern in unsafe_patterns), "raw external identifier in " + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), "trailing whitespace {}:{}".format(rel, line_no))

    print("PASS: PMAI-P0-04 Active Restore Runner V3 Creation and Activation Execution Authorization V1")
    print("stage_id=PMAI-P0-04")
    print("substage=ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1")
    print("authorization_record_id=" + EXPECTED_AUTHORIZATION_RECORD_ID)
    print("authorization_scope_recorded=true")
    print("current_active_restore_runner_creation_authorized=false")
    print("current_restore_runner_v3_activation_authorized=false")
    print("current_creation_and_activation_execution_authorized=false")
    print("post_effective_gate_creation_and_activation_execution_eligible=true")
    print("post_effective_gate_creation_and_activation_execution_authorized=false")
    print("one_time_creation_and_activation_confirmation_present=false")
    print("runtime_binding_contract_complete=false")
    print("current_creation_and_activation_attempts_authorized=0")
    print("post_confirmation_creation_and_activation_attempts_authorized=1")
    print("active_restore_runner_created=false")
    print("restore_runner_activated=false")
    print("restore_runner_executed=false")
    print("archive_file_opened=false")
    print("credential_collection_performed=false")
    print("target_accessed=false")
    print("database_connection=false")
    print("restore_execution=false")
    print("decision=GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY")
    print("next_action=" + EXPECTED_NEXT_ACTION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
