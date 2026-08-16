#!/usr/bin/env python3
"""Validate PMAI-P0-04 Active Restore Runner V3 creation/activation preparation."""

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
DOC = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION_V1.md"
CHECKLIST = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION_V1_CHECKLIST_V1.csv"
GO_NO_GO = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION_V1_GO_NO_GO_V1.csv"
TEST_MATRIX = "docs/clinical_data/" + PREFIX + "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION_V1_TEST_MATRIX_V1.csv"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_creation_and_activation_preparation_v1.py"
EVIDENCE_DOC = "docs/clinical_data/" + PREFIX + "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3.md"
DESIGN_CANDIDATE = "docs/clinical_data/" + PREFIX + "DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
IMPLEMENTATION_CANDIDATE = "docs/clinical_data/" + PREFIX + "DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_CANDIDATE_V1.py.txt"
ACTIVE_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_v3.py"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"
CI = "scripts/ci_static_checks.sh"

EXPECTED_HEAD = "b13a790b9f1803a52e51598523c17779a4a7397a"
EXPECTED_PARENT = "6673d3b4bb4052f57f4f7d456a09ac82b20ea281"
EXPECTED_PRIOR_CI_SHA256 = "4c91905018f71da785a3ec77fd20da7c31c8e495862fb6e30259e60658756706"
EXPECTED_FINAL_CI_SHA256 = "4c91905018f71da785a3ec77fd20da7c31c8e495862fb6e30259e60658756706"
EXPECTED_DESIGN_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_IMPLEMENTATION_SHA256 = "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
EXPECTED_LOCKED_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_TARGET_CONTRACT_SHA256 = "e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744"
EXPECTED_TARGET_COUNT = 142
EXPECTED_COMMAND_COUNT = 29
EXPECTED_NEXT = "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_AUTHORIZATION_REVIEW_V1"
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
    match = re.search(r"(?m)^" + re.escape(key) + r"=(.*)$", source)
    need(match is not None, "marker " + key)
    return match.group(1)

def rows(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

def assignments(source: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return result

def ci_targets(source: str) -> list[str]:
    match = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)\s*$", source)
    need(match is not None, "CI TARGETS block")
    return re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)

def python_lines(source: str) -> list[str]:
    return [line.strip() for line in source.splitlines() if line.strip().startswith("python3 ") and not line.strip().startswith("python3 -m py_compile ")]

def main() -> int:
    doc = read(DOC)
    evidence = read(EVIDENCE_DOC)
    ci = read(CI)
    required = {
        "stage_id": "PMAI-P0-04",
        "substage": "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION_V1",
        "package_status": "ACTIVE_RUNNER_CREATION_AND_ACTIVATION_PREPARATION_ONLY",
        "current_substage": "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3",
        "restore_runner_v3_implementation_authorized": "true",
        "fresh_disposable_target_provisioning_verified": "true",
        "target_status": "AVAILABLE",
        "active_runner_creation_and_activation_preparation_complete": "true",
        "active_restore_runner_created": "false",
        "restore_runner_activated": "false",
        "restore_runner_executed": "false",
        "restore_runner_v3_creation_authorized": "false",
        "restore_runner_v3_activation_authorized": "false",
        "restore_runner_v3_execution_authorized": "false",
        "planned_active_runner_path_present": "false",
        "planned_active_source_sha256": "UNBOUND",
        "expected_runtime_target_identity_sha256": "UNBOUND",
        "repository_only": "true",
        "provider_control_plane_opened": "false",
        "archive_file_opened": "false",
        "backup_archive_listing_invoked": "false",
        "credential_collection_performed": "false",
        "database_connection": "false",
        "restore_execution": "false",
        "migration_created": "false",
        "migration_executed": "false",
        "target_modified": "false",
        "target_deleted": "false",
        "files_staged": "false",
        "files_committed": "false",
        "files_pushed": "false",
        "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "p0_04_execution_authorized": "false",
        "staging_0010_apply_authorized": "false",
        "decision": "GO_TO_SEPARATE_" + EXPECTED_NEXT,
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)
    need(marker(doc, "local_main") == EXPECTED_HEAD, "entry head")
    need(marker(doc, "main_parent") == EXPECTED_PARENT, "entry parent")
    need(marker(doc, "github_ci_gate_number") == "212", "CI Gate number")
    need(marker(doc, "github_ci_gate_status") == "PASS", "CI Gate status")
    need(marker(doc, "prior_ci_sha256") == EXPECTED_PRIOR_CI_SHA256, "prior CI hash")
    need(marker(doc, "final_ci_sha256") == EXPECTED_FINAL_CI_SHA256, "final CI hash marker")
    need(marker(evidence, "decision") == "GO_TO_SEPARATE_ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION", "evidence decision")
    need(marker(evidence, "target_contract_identity_sha256") == EXPECTED_TARGET_CONTRACT_SHA256, "target contract")
    need(marker(evidence, "target_status") == "AVAILABLE", "target status evidence")
    need(sha256_path(ROOT / DESIGN_CANDIDATE) == EXPECTED_DESIGN_SHA256, "design candidate hash")
    need(sha256_path(ROOT / IMPLEMENTATION_CANDIDATE) == EXPECTED_IMPLEMENTATION_SHA256, "implementation candidate hash")
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_SHA256, "locked runner hash")
    candidate = ROOT / IMPLEMENTATION_CANDIDATE
    need(not candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), "implementation candidate executable")
    need(not (ROOT / IMPLEMENTATION_CANDIDATE.removesuffix(".txt")).exists(), "implementation candidate active twin")
    values = assignments(candidate.read_text(encoding="utf-8"))
    for name in FALSE_FLAGS:
        need(values.get(name) is False, "candidate flag " + name)
    for name in UNBOUND_BINDINGS:
        need(values.get(name) == "UNBOUND", "candidate binding " + name)
    need(not (ROOT / ACTIVE_RUNNER).exists(), "planned active runner already exists")
    need(not list((ROOT / "backend/migrations/versions").glob("0010*.py")), "active 0010 migration")
    checklist, gates, tests = rows(CHECKLIST), rows(GO_NO_GO), rows(TEST_MATRIX)
    need(len(checklist) == 47 and all(row["status"] == "PASS" for row in checklist), "checklist")
    need(len(gates) == 17 and {row["status"] for row in gates} == {"PASS", "HOLD"}, "go/no-go")
    need(len(tests) == 39 and all(row["status"] == "DESIGNED" for row in tests), "test matrix")
    targets = ci_targets(ci)
    commands = python_lines(ci)
    need(len(targets) == EXPECTED_TARGET_COUNT and len(set(targets)) == EXPECTED_TARGET_COUNT, "CI target cardinality")
    need(PACKAGE_PATHS <= set(targets), "CI package targets")
    need(len(commands) == EXPECTED_COMMAND_COUNT, "CI command cardinality")
    need(commands[-1] == "python3 " + VALIDATOR + " || exit 1", "CI command order")
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, "CI file hash")
    print("PASS: PMAI-P0-04 Active Restore Runner V3 Creation and Activation Preparation V1")
    print("stage_id=PMAI-P0-04")
    print("substage=ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION_V1")
    print("active_runner_creation_and_activation_preparation_complete=true")
    print("active_restore_runner_created=false")
    print("restore_runner_activated=false")
    print("restore_runner_executed=false")
    print("archive_file_opened=false")
    print("credential_collection_performed=false")
    print("database_connection=false")
    print("restore_execution=false")
    print("decision=GO_TO_SEPARATE_" + EXPECTED_NEXT)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
