#!/usr/bin/env python3
"""Validate PMAI-P0-04 Restore Runner V3 Implementation Authorization Review V1."""

from __future__ import annotations

import ast
import csv
import hashlib
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1.md"
CHECKLIST = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1_CHECKLIST_V1.csv"
GO_NO_GO = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1_GO_NO_GO_V1.csv"
TEST_MATRIX = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1_TEST_MATRIX_V1.csv"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_authorization_review_v1.py"
PREPARATION_DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1.md"
DESIGN_CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
IMPLEMENTATION_CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_CANDIDATE_V1.py.txt"
CI = "scripts/ci_static_checks.sh"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"

EXPECTED_HEAD = "a2f117eb55208bf5022d04482d005137a2f26874"
EXPECTED_PARENT = "40f263be59d8732589ba78c4aa985d8c1b1b0a98"
EXPECTED_ISOLATED = "8d1dc8814ed8f80d8bc965b494c1c320fc08f228"
EXPECTED_PRIOR_CI_SHA256 = "33d0cc12675211d7761ab1f1c7a909709c24df56854d31fad1d67638e555614f"
EXPECTED_FINAL_CI_SHA256 = "4b50f28b230853bd57a983a7034aff170e11531bd276964a8c4b93769803c80c"
EXPECTED_LOCKED_RUNNER_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_DESIGN_CANDIDATE_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256 = "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
EXPECTED_FUNCTION_SOURCE_SHA256 = {'build_extraction_plan': '0056cfeaac81cf8045a36c42c1a567517e6b7ef9300b38260527c34dc25aa1cb',
 'build_metadata_contract': '3236ddf177ecdb22529c145e55360c53e456e3fadb9475c8ce01c3b9d17e34fe',
 'build_restore_argv': 'd053afa2f5bc1417bb42890eac9c4af054f3efa875423561183b3374a30fa48c',
 'execute_authorized_restore': 'c5be4a7390002ea9010ab6e875ac15072ec8dad7963fdc66b887b794d59ec92b',
 'extract_logical_root_once': '8e1e2dfa793be2cf41decaf713d8a092624f08ee170e3f261857629107e1a8d8',
 'extract_member_safely': '4de62faf2bf2f53110da7cd7eb11e44c627674d281ea39df204916fd30b3efa5',
 'future_bindings_complete': '58e1bf6541c463536170b87d957715d74a75665a4e3c026c5461a8ffd8850d8b',
 'main': '8345e68c057e2693aef1aa48a6c5640ff8c320cfdfc43f6eccd2b3ad09ef4fe7',
 'normalize_member_name': '3a2ccc4dcf9e204faee10784e8dee4d91da76d2a4a25ac13ee27fb7ceee12681',
 'open_private_directory': '0d85c888806e2ae864a793e9abed363053711e98291d9b07a36bcaae42c145d5',
 'read_only_target_preflight': '4b3b67bfb574dce068713f14d85f7707df63cfb7ec0211cb1a99b08b4f56881e',
 'reserve_attempt_once': '53094e64b9df7f9003a298eec6186001e8203fd0b0bc59938fdd1e7665cc96cf',
 'restore_once': '397b2e8f06485ed1a3ebd620c25840b6910e4c14bfd8fb9291813edb0b7bc43c',
 'run_child_once': '8d54a4fd25aee75ea30e106a8f837a6d9125826482341b886cf1bb6ecc571ecf',
 'sanitized_postcheck': 'c5fe2bf78869f7ab80a61a04b2f3cc4da3f4faef48979e52bf1a379b3b86cf50',
 'write_private_libpq_files': '12724bc762f8a7e1f8f3ca97d2792e07912422d18e366315e6fbe927e7127582'}
EXPECTED_COMMANDS = ['python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_execution_evidence_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_restore_governance_decision_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_authorization_review_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_execution_evidence_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_structural_predicate_review_governance_decision_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_preparation_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_authorization_review_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_execution_evidence_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_post_execution_structural_review_governance_decision_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v3_preparation_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v3_authorization_review_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v3_execution_evidence_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_design_preparation_v3.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_authorization_review_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_preparation_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_authorization_review_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_preparation_v3.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_review_v3.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_external_execution_authorization_v3.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_execution_evidence_v3.py '
 '|| exit 1']
EXPECTED_NEXT_SUBJECT = "FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3"

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


def text(rel: str) -> str:
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + rel)
    return path.read_text(encoding="utf-8")


def rows(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def assignments(tree: ast.Module) -> dict[str, object]:
    result: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return result


def source_function_hashes(source: str) -> dict[str, str]:
    critical = set(EXPECTED_FUNCTION_SOURCE_SHA256)
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    found: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name not in critical:
            continue
        start = min([node.lineno] + [item.lineno for item in node.decorator_list])
        body = "".join(lines[start - 1:node.end_lineno])
        found[node.name] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return found


def ci_targets(source: str) -> list[str]:
    match = re.search(r'(?ms)^TARGETS=\(\n(.*?)^\)\s*$', source)
    need(match is not None, "CI TARGETS block")
    return re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)


def python_lines(source: str) -> list[str]:
    return [line.strip() for line in source.splitlines() if line.strip().startswith("python3 ") and not line.strip().startswith("python3 -m py_compile ")]


def marker(source: str, key: str) -> str:
    match = re.search(r'(?m)^' + re.escape(key) + r'=(.*)$', source)
    need(match is not None, "marker " + key)
    return match.group(1)


def validate_candidate() -> None:
    path = ROOT / IMPLEMENTATION_CANDIDATE
    need(path.is_file() and not path.is_symlink(), "implementation candidate missing")
    need(IMPLEMENTATION_CANDIDATE.endswith(".py.txt"), "implementation candidate suffix")
    need(not bool(path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)), "implementation candidate executable")
    need(not (ROOT / IMPLEMENTATION_CANDIDATE.removesuffix(".txt")).exists(), "active candidate twin exists")
    need(sha256_path(path) == EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256, "implementation candidate hash")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=IMPLEMENTATION_CANDIDATE)
    values = assignments(tree)
    for name in FALSE_FLAGS:
        need(values.get(name) is False, "external flag " + name)
    for name in UNBOUND_BINDINGS:
        need(values.get(name) == "UNBOUND", "future binding " + name)
    need(source_function_hashes(source) == EXPECTED_FUNCTION_SOURCE_SHA256, "critical function source hashes")
    need("shell=True" not in source and "shell = True" not in source, "shell true")
    need("extractall(" not in source and ".extract(" not in source, "unsafe tar extraction API")
    need("eval(" not in source and "exec(" not in source, "unsafe dynamic execution")


def main() -> int:
    doc = text(DOC)
    preparation = text(PREPARATION_DOC)
    ci = text(CI)
    required = {
        "stage_id": "PMAI-P0-04",
        "substage": "RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1",
        "package_status": "EXACT_INERT_IMPLEMENTATION_IDENTITY_AUTHORIZATION_REVIEW_ONLY",
        "current_restore_runner_v3_implementation_authorized": "false",
        "proposed_post_effective_gate_restore_runner_v3_implementation_authorized": "true",
        "authorized_scope": "EXACT_HASH_BOUND_INERT_IMPLEMENTATION_IDENTITY_ONLY",
        "implementation_candidate_sha256": EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256,
        "implementation_candidate_modified_by_review": "false",
        "candidate_promotion_authorized": "false",
        "active_restore_runner_created": "false",
        "restore_runner_v3_activation_authorized": "false",
        "restore_runner_v3_execution_authorized": "false",
        "fresh_disposable_target_authorized": "false",
        "repository_only": "true",
        "archive_file_opened": "false",
        "backup_archive_listing_invoked": "false",
        "backup_archive_member_headers_read": "false",
        "backup_archive_member_payload_read": "false",
        "database_connection": "false",
        "restore_execution": "false",
        "migration_created": "false",
        "migration_executed": "false",
        "files_staged": "false",
        "files_committed": "false",
        "files_pushed": "false",
        "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "p0_04_execution_authorized": "false",
        "staging_0010_apply_authorized": "false",
        "decision": "GO_TO_SEPARATE_" + EXPECTED_NEXT_SUBJECT,
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)
    need(marker(doc, "local_main") == EXPECTED_HEAD, "entry head")
    need(marker(doc, "main_parent") == EXPECTED_PARENT, "entry parent")
    need(marker(doc, "github_ci_gate_number") == "207", "Gate number")
    need(marker(doc, "github_ci_gate_status") == "PASS", "Gate status")
    need(marker(doc, "prior_ci_sha256") == EXPECTED_PRIOR_CI_SHA256, "prior CI marker")
    need(marker(doc, "final_ci_sha256") == EXPECTED_FINAL_CI_SHA256, "final CI marker")
    need(marker(preparation, "implementation_candidate_sha256") == EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256, "preparation candidate pointer")
    need(marker(preparation, "restore_runner_v3_implementation_authorized") == "false", "preparation authority pointer")
    need(sha256_path(ROOT / DESIGN_CANDIDATE) == EXPECTED_DESIGN_CANDIDATE_SHA256, "design candidate hash")
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, "locked runner hash")
    validate_candidate()
    checklist = rows(CHECKLIST)
    go_no_go = rows(GO_NO_GO)
    tests = rows(TEST_MATRIX)
    need(len(checklist) == 48 and all(row["status"] == "PASS" for row in checklist), "checklist")
    need(len(go_no_go) == 28 and {row["status"] for row in go_no_go} == {"PASS", "HOLD"}, "go/no-go")
    need(len(tests) == 44 and all(row["status"] == "DESIGNED" for row in tests), "test matrix")
    targets = ci_targets(ci)
    commands = python_lines(ci)
    need(len(targets) == 137 and len(set(targets)) == 137, "CI target cardinality")
    need(PACKAGE_PATHS <= set(targets), "CI package targets")
    need(len(commands) == 28 and commands == EXPECTED_COMMANDS, "CI command contract")
    fresh_target_preparation_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_preparation_v3.py || exit 1"
    fresh_target_authorization_review_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_review_v3.py || exit 1"
    fresh_target_external_execution_authorization_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_external_execution_authorization_v3.py || exit 1"
    fresh_target_execution_evidence_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_execution_evidence_v3.py || exit 1"
    need(commands[-5:] == ["python3 " + VALIDATOR + " || exit 1", fresh_target_preparation_command, fresh_target_authorization_review_command, fresh_target_external_execution_authorization_command, fresh_target_execution_evidence_command], "CI command order")
    need(all(IMPLEMENTATION_CANDIDATE not in command for command in commands), "candidate executed by CI")
    need(not list((ROOT / "backend/migrations/versions").glob("0010*.py")), "active 0010 migration")
    print("PASS: PMAI-P0-04 Restore Runner V3 Implementation Authorization Review V1")
    print("stage_id=PMAI-P0-04")
    print("substage=RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1")
    print("implementation_candidate_integrity_review_complete=true")
    print("current_restore_runner_v3_implementation_authorized=false")
    print("proposed_post_effective_gate_restore_runner_v3_implementation_authorized=true")
    print("active_restore_runner_created=false")
    print("restore_runner_v3_activation_authorized=false")
    print("restore_runner_v3_execution_authorized=false")
    print("archive_file_opened=false")
    print("database_connection=false")
    print("restore_execution=false")
    print("decision=GO_TO_SEPARATE_" + EXPECTED_NEXT_SUBJECT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
