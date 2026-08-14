#!/usr/bin/env python3
"""Validate PMAI-P0-04 Restore Runner V3 Implementation Preparation V1."""

from __future__ import annotations

import ast
import csv
import hashlib
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1.md"
CHECKLIST = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1_CHECKLIST_V1.csv"
GO_NO_GO = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1_GO_NO_GO_V1.csv"
TEST_MATRIX = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1_TEST_MATRIX_V1.csv"
CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_CANDIDATE_V1.py.txt"
DESIGN_CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_preparation_v1.py"
CI = "scripts/ci_static_checks.sh"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"

EXPECTED_HEAD = "40f263be59d8732589ba78c4aa985d8c1b1b0a98"
EXPECTED_PARENT = "190de64deac0eef19c9ffcaafc8ecbdcc12f7278"
EXPECTED_ISOLATED = "8d1dc8814ed8f80d8bc965b494c1c320fc08f228"
EXPECTED_PRIOR_CI_SHA256 = "9a8c3a96466a783c576c28d66b6e7db3cc05c86c018bcd750343c3d99f323104"
EXPECTED_FINAL_CI_SHA256 = "55dd1eb17ed1fb19d030759ae9ff5926a2bda5ee545461a980a99b58a5c474f1"
EXPECTED_LOCKED_RUNNER_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_DESIGN_CANDIDATE_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_CANDIDATE_SHA256 = "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
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
 '|| exit 1']
PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, CANDIDATE, VALIDATOR}


def need(condition: bool, message: str) -> None:
    if not condition:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_text(rel: str) -> str:
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + rel)
    return path.read_text(encoding="utf-8")


def read_csv(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def assignments(tree: ast.Module) -> dict[str, object]:
    values: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        values[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    return values


def function_nodes(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def ci_targets(value: str) -> list[str]:
    block = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)\s*$", value)
    need(block is not None, "CI TARGETS block")
    return re.findall(r'^\s*"([^"]+)"\s*$', block.group(1), flags=re.M)


def python_lines(value: str) -> list[str]:
    return [
        line.strip()
        for line in value.splitlines()
        if line.strip().startswith("python3 ")
        and not line.strip().startswith("python3 -m py_compile ")
    ]


class ReferenceHold(RuntimeError):
    pass


def reference_normalize(raw_name: str, is_directory: bool) -> tuple[str, ...]:
    raw = raw_name[:-1] if is_directory and raw_name.endswith("/") else raw_name
    if not raw or len(raw.encode("utf-8")) > 4096 or raw.startswith("/") or "\\" in raw:
        raise ReferenceHold()
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        raise ReferenceHold()
    if raw == ".":
        if not is_directory:
            raise ReferenceHold()
        return ()
    parts = raw.split("/")
    if parts[0] == ".":
        parts = parts[1:]
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ReferenceHold()
    if len(parts[0]) >= 2 and parts[0][1] == ":":
        raise ReferenceHold()
    if len(parts) > 64:
        raise ReferenceHold()
    return tuple(parts)


def validate_reference_fixtures() -> None:
    accepted = [
        (".", True, ()),
        ("./a", False, ("a",)),
        ("a", False, ("a",)),
        ("./a/b", False, ("a", "b")),
        ("a/b/", True, ("a", "b")),
        ("toc.dat", False, ("toc.dat",)),
        ("./x/y/toc.dat", False, ("x", "y", "toc.dat")),
        ("x-y/z_1", False, ("x-y", "z_1")),
    ]
    rejected = [
        ("", False), ("/a", False), ("../a", False), ("a/../b", False),
        ("a\\b", False), ("C:/a", False), ("a//b", False), ("a/./b", False),
        (".", False), ("./", False), ("a\x00b", False), ("a\nb", False),
        ("/", True), ("//a", False), ("./../a", False), ("./a//b", False),
        ("D:x", False), ("a\tb", False), ("a\rb", False), ("a\x7fb", False),
        ("/../a", False), ("./.", False), ("a/..", True), ("a/.", True),
        ("a//", True), ("\\server", False), ("E:\\a", False), ("./C:/a", False),
        ("x" * 4097, False), ("/x" * 65, False), ("a/../../b", False), ("..", False),
    ]
    need(len(accepted) + len(rejected) == 40, "reference fixture count")
    for raw, is_directory, expected in accepted:
        need(reference_normalize(raw, is_directory) == expected, "accepted reference fixture")
    for raw, is_directory in rejected:
        try:
            reference_normalize(raw, is_directory)
        except ReferenceHold:
            continue
        need(False, "rejected reference fixture")


def validate_candidate(source: str) -> None:
    tree = ast.parse(source, filename=CANDIDATE)
    values = assignments(tree)
    false_names = {
        "EXECUTION_ENABLED", "ARCHIVE_ACCESS_ENABLED", "ARCHIVE_LISTING_ENABLED",
        "MEMBER_HEADER_READ_ENABLED", "MEMBER_PAYLOAD_READ_ENABLED",
        "ARCHIVE_EXTRACTION_ENABLED", "TARGET_PREFLIGHT_ENABLED",
        "DATABASE_CONNECTION_ENABLED", "DATABASE_WRITE_ENABLED",
        "RESTORE_PROCESS_ENABLED", "RESTORE_EXECUTION_ENABLED",
        "PG_RESTORE_INVOCATION_ENABLED", "PSQL_INVOCATION_ENABLED",
        "AUTOMATIC_RETRY_ENABLED", "MANUAL_RETRY_ENABLED",
        "MIGRATION_0010_ENABLED", "DEPLOYMENT_ENABLED", "RESOURCE_DELETION_ENABLED",
    }
    need(all(values.get(name) is False for name in false_names), "candidate execution flags")
    unbound = {
        "ACTIVATION_AUTHORIZATION_RECORD_ID", "EXPECTED_ACTIVE_SOURCE_SHA256",
        "EXPECTED_TARGET_IDENTITY_SHA256", "FORBIDDEN_PRODUCTION_IDENTITY_SHA256",
        "FORBIDDEN_STAGING_IDENTITY_SHA256", "EXPECTED_SCHEMA_MANIFEST_SHA256",
    }
    need(all(values.get(name) == "UNBOUND" for name in unbound), "future bindings remain unbound")
    need(values.get("EXPECTED_WRAPPER_DEPTH") == 2, "wrapper depth")
    need(values.get("EXPECTED_ROOT_LAYOUT_CLASSIFICATION") == "PG_DIRECTORY_ROOT_DEEP_WRAPPED", "root layout")
    need(values.get("EXPECTED_DATABASE_REVISION_AFTER_RESTORE") == "0009_diag_data", "revision")
    need(values.get("RESTORE_ARGV_PREFIX") == (
        "pg_restore", "--dbname=service=pmai_p0_04_disposable_restore_v3",
        "--no-owner", "--no-privileges", "--no-tablespaces",
        "--no-publications", "--no-subscriptions", "--single-transaction",
        "--exit-on-error", "--verbose", "--no-password",
    ), "restore argv")
    need("BEGIN READ ONLY" in values.get("TARGET_PREFLIGHT_SQL", ""), "preflight read only")
    need("BEGIN READ ONLY" in values.get("POSTCHECK_SQL", ""), "postcheck read only")
    need("extractall" not in source, "tarfile extractall forbidden")
    need(re.search(r"\.extract\s*\(", source) is None, "TarFile.extract forbidden")
    need("shell=True" not in source and "shell = True" not in source, "shell true forbidden")
    need("os.system" not in source and "os.popen" not in source, "shell helper forbidden")
    need(re.search(r"\b(eval|exec|compile)\s*\(", source) is None, "dynamic execution forbidden")
    need("importlib" not in source and "pickle" not in source, "dynamic loader forbidden")
    functions = function_nodes(tree)
    need(set(EXPECTED_FUNCTION_SOURCE_SHA256) <= set(functions), "critical functions present")
    source_lines = source.splitlines(keepends=True)
    for name, expected in EXPECTED_FUNCTION_SOURCE_SHA256.items():
        function = functions[name]
        start_line = min(
            [function.lineno] + [decorator.lineno for decorator in function.decorator_list]
        )
        function_source = "".join(source_lines[start_line - 1 : function.end_lineno])
        actual = hashlib.sha256(function_source.encode("utf-8")).hexdigest()
        need(actual == expected, "critical function source hash " + name)
    module_calls = [node for node in tree.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)]
    need(not module_calls, "top-level call expression forbidden")
    main_guards = [
        node for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and "__name__" in ast.dump(node.test)
    ]
    need(len(main_guards) == 1, "single main guard")
    run_child = ast.get_source_segment(source, functions["run_child_once"]) or ""
    need("shell=False" in run_child and "start_new_session=True" in run_child, "child process hardening")
    need("TimeoutExpired" in run_child and "killpg" in run_child, "timeout process-group cleanup")
    extraction = ast.get_source_segment(source, functions["extract_member_safely"]) or ""
    need("O_EXCL" in extraction and "O_NOFOLLOW" in extraction and "dir_fd=" in extraction, "safe extraction descriptors")
    reserve = ast.get_source_segment(source, functions["reserve_attempt_once"]) or ""
    need("O_EXCL" in reserve and "automatic_retry" in reserve, "one-attempt reservation")


def main() -> int:
    for rel in PACKAGE_PATHS:
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), "package path " + rel)
        need(path.read_bytes().endswith(b"\n"), "final newline " + rel)
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, "CI hash")
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, "locked runner hash")
    need(sha256_path(ROOT / DESIGN_CANDIDATE) == EXPECTED_DESIGN_CANDIDATE_SHA256, "design candidate hash")
    need(sha256_path(ROOT / CANDIDATE) == EXPECTED_CANDIDATE_SHA256, "implementation candidate hash")
    need(CANDIDATE.endswith(".py.txt"), "candidate suffix")
    need(not (ROOT / CANDIDATE.removesuffix(".txt")).exists(), "active implementation candidate forbidden")
    need(not (ROOT / CANDIDATE).stat().st_mode & 0o111, "candidate executable mode forbidden")
    need(not list((ROOT / "backend/migrations/versions").glob("0010*.py")), "active migration 0010 forbidden")
    candidate_source = read_text(CANDIDATE)
    validate_candidate(candidate_source)
    validate_reference_fixtures()
    doc = read_text(DOC)
    required_markers = {
        "stage_id=PMAI-P0-04",
        "substage=RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1",
        "current_restore_runner_v3_implementation_preparation_authorized=true",
        "restore_runner_v3_implementation_preparation_complete=true",
        "inert_implementation_candidate_created=true",
        "active_restore_runner_created=false",
        "restore_runner_v3_implementation_authorized=false",
        "archive_file_opened=false",
        "database_connection=false",
        "restore_execution=false",
        "backup_restoreability_verified=false",
        "p0_04_execution_authorized=false",
        "staging_0010_apply_authorized=false",
        "decision=GO_TO_SEPARATE_RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1",
    }
    need(all(marker in doc for marker in required_markers), "document markers")
    checklist = read_csv(CHECKLIST)
    go_no_go = read_csv(GO_NO_GO)
    tests = read_csv(TEST_MATRIX)
    need(len(checklist) == 56 and all(row["status"] == "PASS" for row in checklist), "checklist")
    need(len(go_no_go) == 30, "go/no-go count")
    need({row["status"] for row in go_no_go} == {"PASS", "HOLD"}, "go/no-go statuses")
    need(len(tests) == 52 and all(row["status"] == "DESIGNED" for row in tests), "test matrix")
    ci = read_text(CI)
    targets = ci_targets(ci)
    commands = python_lines(ci)
    need(len(targets) == 117 and len(set(targets)) == 117, "CI target cardinality")
    need(len(commands) == 24 and commands == EXPECTED_COMMANDS, "CI command contract")
    need(PACKAGE_PATHS <= set(targets), "CI package targets")
    need(all(CANDIDATE not in command for command in commands), "candidate not executed by CI")
    need(("python3 " + VALIDATOR + " || exit 1") in commands, "validator command")
    print("PASS: PMAI-P0-04 Restore Runner V3 Implementation Preparation V1")
    print("stage_id=PMAI-P0-04")
    print("substage=RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1")
    print("package_status=INERT_IMPLEMENTATION_PREPARATION_ONLY")
    print("implementation_candidate_sha256=" + EXPECTED_CANDIDATE_SHA256)
    print("candidate_ast_valid=true")
    print("candidate_imported=false")
    print("candidate_executed=false")
    print("active_restore_runner_created=false")
    print("archive_file_opened=false")
    print("backup_archive_listing_invoked=false")
    print("database_connection=false")
    print("restore_execution=false")
    print("backup_restoreability_verified=false")
    print("disposable_restore_rehearsal_complete=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("decision=GO_TO_SEPARATE_RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1")
    print("next_action=SEPARATE_RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1_REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
