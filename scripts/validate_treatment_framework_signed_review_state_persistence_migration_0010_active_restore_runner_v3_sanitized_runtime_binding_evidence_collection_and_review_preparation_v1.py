#!/usr/bin/env python3
"""Validate the PMAI-P0-04 sanitized-evidence preparation package offline."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType
from typing import Mapping, NoReturn, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
DOC_PREFIX = (
    "docs/clinical_data/"
    "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_"
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_"
    "COLLECTION_AND_REVIEW_PREPARATION_V1"
)
REVIEWER_REL = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_review_v1.py"
)
VALIDATOR_REL = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_collection_and_review_preparation_v1.py"
)
MANIFEST_PATH = ROOT / (DOC_PREFIX + "_PACKAGE_MANIFEST_V1.json")
BASELINE_PATH = ROOT / (DOC_PREFIX + "_LOCKED_BASELINE_V1.json")
COLLECTOR_PATH = ROOT / (DOC_PREFIX + "_COLLECTOR_CANDIDATE_V1.py.txt")
REVIEWER_PATH = ROOT / REVIEWER_REL
OBSERVATION_TEMPLATE_PATH = ROOT / (DOC_PREFIX + "_RUNTIME_OBSERVATION_TEMPLATE_V1.json")
COLLECTOR_TEMPLATE_PATH = ROOT / (DOC_PREFIX + "_SANITIZED_COLLECTOR_OUTPUT_TEMPLATE_V1.json")
CHECKLIST_PATH = ROOT / (DOC_PREFIX + "_CHECKLIST_V1.csv")
TEST_MATRIX_PATH = ROOT / (DOC_PREFIX + "_TEST_MATRIX_V1.csv")
DOCUMENT_PATH = ROOT / (DOC_PREFIX + ".md")
CANDIDATE_PATH = ROOT / (
    "docs/clinical_data/"
    "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_"
    "DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_CANDIDATE_V1.py.txt"
)
LOCKED_RUNNER_PATH = ROOT / (
    "scripts/run_treatment_framework_signed_review_state_persistence_"
    "migration_0010_staging_migration_apply.py"
)
ACTIVE_RUNNER_PATH = ROOT / (
    "scripts/run_treatment_framework_signed_review_state_persistence_"
    "migration_0010_disposable_restore_v3.py"
)

EXPECTED_CANDIDATE_SHA256 = (
    "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
)
EXPECTED_BASE_COMMIT = "ec5fd93108adf13e3570a18f37465b852f2b1484"
EXPECTED_CI_GATE = 215
EXPECTED_SOURCE_PACKAGE_SHA256 = (
    "f4f708aa0f5550eaeb5377e9c6787faf36349beb23958ca861420ba098524e93"
)
EXPECTED_LOCKED_RUNNER_SHA256 = (
    "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
)
MAX_FILE_BYTES = 1024 * 1024
PAYLOAD_PATHS = {
    DOC_PREFIX + ".md",
    DOC_PREFIX + "_CHECKLIST_V1.csv",
    DOC_PREFIX + "_COLLECTOR_CANDIDATE_V1.py.txt",
    DOC_PREFIX + "_LOCKED_BASELINE_V1.json",
    DOC_PREFIX + "_RUNTIME_OBSERVATION_TEMPLATE_V1.json",
    DOC_PREFIX + "_SANITIZED_COLLECTOR_OUTPUT_TEMPLATE_V1.json",
    DOC_PREFIX + "_TEST_MATRIX_V1.csv",
    REVIEWER_REL,
    VALIDATOR_REL,
}
ALLOWED_COLLECTOR_IMPORTS = {
    "__future__",
    "argparse",
    "datetime",
    "hashlib",
    "json",
    "re",
    "sys",
    "typing",
}
ALLOWED_REVIEWER_IMPORTS = {
    "__future__",
    "argparse",
    "hashlib",
    "json",
    "os",
    "pathlib",
    "re",
    "sys",
    "typing",
}
FORBIDDEN_CALL_NAMES = {"__import__", "compile", "eval", "exec"}
FORBIDDEN_IMPORT_ROOTS = {
    "asyncpg",
    "boto3",
    "http",
    "psycopg",
    "psycopg2",
    "requests",
    "socket",
    "sqlite3",
    "subprocess",
    "tarfile",
    "urllib",
}


class Hold(RuntimeError):
    """Fixed stop code whose digest can be emitted without leaking paths."""


class HashBooleanArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise Hold("ARGUMENT_CONTRACT_MISMATCH")


def need(condition: bool, code: str) -> None:
    if not condition:
        raise Hold(code)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def read_json(path: Path, label: str) -> dict[str, object]:
    need(path.is_file() and not path.is_symlink(), label + "_MISSING_OR_UNSAFE")
    need(path.stat().st_size <= MAX_FILE_BYTES, label + "_TOO_LARGE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Hold(label + "_INVALID_JSON") from exc
    need(isinstance(value, dict), label + "_NOT_OBJECT")
    return value


def validate_manifest() -> None:
    manifest = read_json(MANIFEST_PATH, "PACKAGE_MANIFEST")
    need(
        manifest.get("schema")
        == "PMAI_P0_04_ARR_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_PREPARATION_REPOSITORY_PACKAGE_MANIFEST_V1",
        "PACKAGE_MANIFEST_SCHEMA_MISMATCH",
    )
    files = manifest.get("files")
    need(isinstance(files, list), "PACKAGE_MANIFEST_FILES_INVALID")
    paths: list[str] = []
    for item in files:
        need(isinstance(item, dict), "PACKAGE_MANIFEST_ENTRY_INVALID")
        need(set(item) == {"bytes", "path", "sha256"}, "PACKAGE_MANIFEST_ENTRY_KEYS")
        path_value = item["path"]
        need(
            isinstance(path_value, str)
            and re.fullmatch(r"[A-Za-z0-9_./-]+", path_value) is not None
            and not path_value.startswith("/")
            and ".." not in Path(path_value).parts,
            "PACKAGE_MANIFEST_PATH_INVALID",
        )
        need(is_sha256(item["sha256"]), "PACKAGE_MANIFEST_SHA256_INVALID")
        need(type(item["bytes"]) is int and item["bytes"] >= 0, "PACKAGE_MANIFEST_SIZE_INVALID")
        path = ROOT / path_value
        need(path.is_file() and not path.is_symlink(), "PACKAGE_FILE_MISSING_OR_UNSAFE")
        need(path.stat().st_size == item["bytes"], "PACKAGE_FILE_SIZE_MISMATCH")
        need(sha256_path(path) == item["sha256"], "PACKAGE_FILE_HASH_MISMATCH")
        paths.append(path_value)
    need(paths == sorted(paths), "PACKAGE_MANIFEST_NOT_SORTED")
    need(len(paths) == len(set(paths)), "PACKAGE_MANIFEST_DUPLICATE_PATH")
    need(set(paths) == PAYLOAD_PATHS, "PACKAGE_MANIFEST_SCOPE_MISMATCH")


def validate_baseline() -> None:
    baseline = read_json(BASELINE_PATH, "BASELINE")
    need(
        baseline.get("schema")
        == "PMAI_P0_04_ARR_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_PREPARATION_BASELINE_V1",
        "BASELINE_SCHEMA_MISMATCH",
    )
    need(baseline.get("repository") == "pet-med-ai/Pet-med-ai", "REPOSITORY_MISMATCH")
    need(baseline.get("base_commit") == EXPECTED_BASE_COMMIT, "BASE_COMMIT_MISMATCH")
    need(baseline.get("github_ci_gate") == EXPECTED_CI_GATE, "CI_GATE_MISMATCH")
    need(baseline.get("github_ci_gate_conclusion") == "success", "CI_CONCLUSION_MISMATCH")
    need(
        baseline.get("implementation_candidate_sha256") == EXPECTED_CANDIDATE_SHA256,
        "BASELINE_CANDIDATE_HASH_MISMATCH",
    )
    need(
        baseline.get("source_preparation_package_sha256")
        == EXPECTED_SOURCE_PACKAGE_SHA256,
        "SOURCE_PACKAGE_HASH_MISMATCH",
    )
    need(CANDIDATE_PATH.is_file() and not CANDIDATE_PATH.is_symlink(), "CANDIDATE_MISSING_OR_UNSAFE")
    need(CANDIDATE_PATH.stat().st_size <= MAX_FILE_BYTES, "CANDIDATE_TOO_LARGE")
    need(sha256_path(CANDIDATE_PATH) == EXPECTED_CANDIDATE_SHA256, "CANDIDATE_HASH_MISMATCH")
    need(
        LOCKED_RUNNER_PATH.is_file()
        and not LOCKED_RUNNER_PATH.is_symlink()
        and sha256_path(LOCKED_RUNNER_PATH) == EXPECTED_LOCKED_RUNNER_SHA256,
        "LOCKED_RUNNER_HASH_MISMATCH",
    )
    need(not ACTIVE_RUNNER_PATH.exists(), "ACTIVE_RUNNER_FORBIDDEN")
    need(
        not list((ROOT / "backend/migrations/versions").glob("0010*.py")),
        "ACTIVE_0010_MIGRATION_FORBIDDEN",
    )
    source = CANDIDATE_PATH.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename="<locked-implementation-candidate>")
    except (SyntaxError, UnicodeError) as exc:
        raise Hold("CANDIDATE_PARSE_FAILED") from exc
    assignments: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
        ):
            assignments[node.targets[0].id] = node.value.value
    for name in (
        "ACTIVATION_AUTHORIZATION_RECORD_ID",
        "EXPECTED_ACTIVE_SOURCE_SHA256",
        "EXPECTED_TARGET_IDENTITY_SHA256",
        "FORBIDDEN_PRODUCTION_IDENTITY_SHA256",
        "FORBIDDEN_STAGING_IDENTITY_SHA256",
        "EXPECTED_SCHEMA_MANIFEST_SHA256",
    ):
        need(assignments.get(name) == "UNBOUND", "CANDIDATE_BINDING_NOT_UNBOUND")
    need("def read_only_target_preflight(" in source, "CANDIDATE_PREFLIGHT_MISSING")
    need("def sanitized_postcheck(" in source, "CANDIDATE_POSTCHECK_MISSING")


def imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def validate_script_ast(path: Path, allowed_imports: set[str], collector: bool) -> None:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename="<preparation-script>")
    except (SyntaxError, UnicodeError) as exc:
        raise Hold("PREPARATION_SCRIPT_PARSE_FAILED") from exc
    roots = imported_roots(tree)
    need(roots <= allowed_imports, "PREPARATION_IMPORT_ALLOWLIST_FAILED")
    need(not (roots & FORBIDDEN_IMPORT_ROOTS), "FORBIDDEN_IMPORT_DETECTED")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            need(node.func.id not in FORBIDDEN_CALL_NAMES, "FORBIDDEN_DYNAMIC_CALL_DETECTED")
    if collector:
        need('"--dry-run"' in source and '"--self-test"' in source, "COLLECTOR_SAFE_MODES_MISSING")
        need('"--collect"' not in source and '"--review"' not in source, "COLLECTOR_LIVE_CLI_DETECTED")
        need("def collect_from_observation(" in source, "COLLECTOR_CORE_MISSING")
    else:
        need('"--review"' in source, "REVIEWER_MODE_MISSING")
        need("CANONICAL_REPOSITORY" in source, "REVIEWER_REPOSITORY_WRITE_GUARD_MISSING")


def validate_csv_files() -> None:
    with CHECKLIST_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    need(len(rows) == 26, "CHECKLIST_ROW_COUNT_MISMATCH")
    need(
        set(rows[0]) == {"id", "gate", "current_state", "required_state", "fail_closed_result"},
        "CHECKLIST_HEADER_MISMATCH",
    )
    need(len({row["id"] for row in rows}) == len(rows), "CHECKLIST_ID_DUPLICATE")
    need(all(row["fail_closed_result"] == "HOLD" for row in rows), "CHECKLIST_NOT_FAIL_CLOSED")

    with TEST_MATRIX_PATH.open("r", encoding="utf-8", newline="") as handle:
        tests = list(csv.DictReader(handle))
    need(len(tests) == 35, "TEST_MATRIX_ROW_COUNT_MISMATCH")
    need(
        set(tests[0]) == {"id", "area", "case", "expected_result", "runtime_access"},
        "TEST_MATRIX_HEADER_MISMATCH",
    )
    need(len({row["id"] for row in tests}) == len(tests), "TEST_MATRIX_ID_DUPLICATE")
    need(all(row["runtime_access"] == "none" for row in tests), "TEST_MATRIX_RUNTIME_ACCESS")


def validate_document() -> None:
    need(DOCUMENT_PATH.is_file() and not DOCUMENT_PATH.is_symlink(), "DOCUMENT_MISSING_OR_UNSAFE")
    text = DOCUMENT_PATH.read_text(encoding="utf-8")
    for marker in (
        "stage_id=PMAI-P0-04",
        "substage=ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_PREPARATION_V1",
        "base_commit=" + EXPECTED_BASE_COMMIT,
        "github_ci_gate=215",
        "source_preparation_package_sha256=" + EXPECTED_SOURCE_PACKAGE_SHA256,
        "preparation_complete=true",
        "runtime_evidence_collection_authorized=false",
        "runtime_evidence_collected=false",
        "runtime_evidence_reviewed=false",
        "runtime_binding_contract_complete=false",
        "creation_and_activation_execution_authorized=false",
        "decision=HOLD_PENDING_SEPARATE_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_EXECUTION_AUTHORIZATION",
    ):
        need(marker in text, "DOCUMENT_MARKER_MISSING")


def load_module(path: Path, name: str) -> ModuleType:
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    need(spec is not None and spec.loader is not None, "MODULE_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_hold(callback: object) -> None:
    held = False
    try:
        callback()
    except Exception:
        held = True
    need(held, "NEGATIVE_CASE_DID_NOT_HOLD")


def validate_collector_negative_cases(module: ModuleType) -> None:
    observation, now = module.synthetic_observation()
    record = module.collect_from_observation(observation, now)
    module.validate_hash_boolean_output(record)

    mutations = []
    extra = dict(observation)
    extra["extra"] = False
    mutations.append(extra)

    credential = dict(observation)
    credential["target_identity"] = dict(observation["target_identity"])
    credential["target_identity"]["password"] = "forbidden"
    mutations.append(credential)

    empty = dict(observation)
    empty["target_identity"] = dict(observation["target_identity"])
    empty["target_identity"]["database"] = ""
    mutations.append(empty)

    bad_port = dict(observation)
    bad_port["target_identity"] = dict(observation["target_identity"])
    bad_port["target_identity"]["port"] = "05432"
    mutations.append(bad_port)

    duplicate_identity = dict(observation)
    duplicate_identity["production_identity"] = dict(observation["target_identity"])
    mutations.append(duplicate_identity)

    no_relations = dict(observation)
    no_relations["schema_manifest_relations"] = []
    mutations.append(no_relations)

    duplicate_relation = dict(observation)
    duplicate_relation["schema_manifest_relations"] = ["public.alpha", "public.alpha"]
    mutations.append(duplicate_relation)

    raw_disclosure = dict(observation)
    raw_disclosure["raw_connection_values_disclosed"] = True
    mutations.append(raw_disclosure)

    stale = dict(observation)
    stale["target_available_recheck_evidence"] = dict(
        observation["target_available_recheck_evidence"]
    )
    stale["target_available_recheck_evidence"]["observed_at_utc"] = (
        "2026-08-16T00:00:00Z"
    )
    mutations.append(stale)

    for value in mutations:
        expect_hold(lambda value=value: module.collect_from_observation(value, now))


def validate_reviewer_negative_cases(module: ModuleType) -> None:
    base = module.synthetic_record()
    eligible = dict(base)
    eligible["collection_execution_authorized"] = True
    eligible["fixture_only"] = False
    module.validate_collector_record(eligible, release=True)
    downstream = module.build_downstream_evidence(eligible)
    need(
        downstream["reviewed_sanitized_evidence_bundle_sha256"]
        == module.sha256_bytes(module.canonical_json_bytes(eligible)),
        "REVIEWED_BUNDLE_HASH_NOT_MECHANICAL",
    )

    mutations: list[dict[str, object]] = []
    for key, value in (
        ("expected_target_identity_sha256", "UNBOUND"),
        ("expected_target_identity_sha256", "0" * 64),
        ("expected_target_identity_sha256", str(eligible["expected_target_identity_sha256"]).upper()),
        ("expected_target_identity_sha256", eligible["forbidden_production_identity_sha256"]),
        ("expected_target_identity_sha256", module.TARGET_CONTRACT_IDENTITY_SHA256),
        (
            "expected_schema_manifest_sha256",
            "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081",
        ),
        ("target_status_available", False),
        ("target_lifecycle_within_72h", False),
        ("collection_execution_authorized", False),
        ("fixture_only", True),
        ("raw_connection_values_disclosed", True),
    ):
        changed = dict(eligible)
        changed[key] = value
        mutations.append(changed)
    extra = dict(eligible)
    extra["extra"] = False
    mutations.append(extra)
    for value in mutations:
        expect_hold(lambda value=value: module.validate_collector_record(value, release=True))


def validate_console_result(output: str) -> None:
    lines = output.splitlines()
    need(len(lines) == 1, "CONSOLE_LINE_COUNT_MISMATCH")
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise Hold("CONSOLE_JSON_INVALID") from exc
    need(isinstance(value, dict) and bool(value), "CONSOLE_OBJECT_INVALID")
    need(
        all(type(item) is bool or is_sha256(item) for item in value.values()),
        "CONSOLE_VALUE_TYPE_FORBIDDEN",
    )


def run_safe_mode(path: Path, mode: str) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, str(path), mode],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
        env=environment,
    )
    need(result.returncode == 0, "SAFE_MODE_FAILED")
    need(result.stderr == "", "SAFE_MODE_STDERR_NOT_EMPTY")
    validate_console_result(result.stdout.rstrip("\r\n"))


def boundary_status() -> dict[str, bool]:
    return {
        "archive_accessed": False,
        "backup_accessed": False,
        "credential_accessed": False,
        "database_connected": False,
        "deployment_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_stage_performed": False,
        "migration_created": False,
        "migration_executed": False,
        "network_accessed": False,
        "provider_control_plane_accessed": False,
        "resource_deleted": False,
        "restore_executed": False,
        "runner_activated": False,
        "runner_created": False,
        "runner_executed": False,
        "runner_imported": False,
        "target_accessed": False,
    }


def emit_hash_boolean(value: Mapping[str, object]) -> None:
    need(
        all(type(item) is bool or is_sha256(item) for item in value.values()),
        "CONSOLE_VALUE_TYPE_FORBIDDEN",
    )
    print(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    )


def payload_snapshot() -> dict[str, str]:
    paths = [ROOT / value for value in PAYLOAD_PATHS]
    paths.append(MANIFEST_PATH)
    return {str(path.relative_to(ROOT)): sha256_path(path) for path in paths}


def dry_run() -> int:
    before = payload_snapshot()
    validate_manifest()
    validate_baseline()
    validate_document()
    validate_script_ast(COLLECTOR_PATH, ALLOWED_COLLECTOR_IMPORTS, collector=True)
    validate_script_ast(REVIEWER_PATH, ALLOWED_REVIEWER_IMPORTS, collector=False)
    validate_csv_files()
    read_json(OBSERVATION_TEMPLATE_PATH, "OBSERVATION_TEMPLATE")
    read_json(COLLECTOR_TEMPLATE_PATH, "COLLECTOR_TEMPLATE")

    collector = load_module(COLLECTOR_PATH, "pmai_srbe_collector_validation")
    reviewer = load_module(REVIEWER_PATH, "pmai_srbe_reviewer_validation")
    validate_collector_negative_cases(collector)
    validate_reviewer_negative_cases(reviewer)
    for script, mode in (
        (COLLECTOR_PATH, "--dry-run"),
        (COLLECTOR_PATH, "--self-test"),
        (REVIEWER_PATH, "--dry-run"),
        (REVIEWER_PATH, "--self-test"),
    ):
        run_safe_mode(script, mode)
    after = payload_snapshot()
    need(before == after, "DRY_RUN_PACKAGE_WRITE_DETECTED")

    result: dict[str, object] = {
        "candidate_sha256": sha256_path(CANDIDATE_PATH),
        "collector_negative_matrix_pass": True,
        "collector_safe_modes_pass": True,
        "dry_run": True,
        "hold": True,
        "package_manifest_sha256": sha256_path(MANIFEST_PATH),
        "preparation_complete": True,
        "reviewer_negative_matrix_pass": True,
        "reviewer_safe_modes_pass": True,
        "runtime_evidence_collected": False,
        "runtime_evidence_reviewed": False,
    }
    result.update(boundary_status())
    emit_hash_boolean(result)
    return 0


def parser() -> HashBooleanArgumentParser:
    value = HashBooleanArgumentParser(add_help=False, description=__doc__)
    value.add_argument("--dry-run", action="store_true", required=True)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser().parse_args(argv)
    return dry_run()


def entrypoint() -> int:
    try:
        return main()
    except Exception as exc:
        result: dict[str, object] = {
            "error_code_sha256": sha256_bytes(str(exc).encode("utf-8")),
            "hold": True,
            "preparation_complete": False,
            "runtime_evidence_collected": False,
            "runtime_evidence_reviewed": False,
        }
        result.update(boundary_status())
        try:
            emit_hash_boolean(result)
        except Exception:
            print('{"hold":true}')
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
