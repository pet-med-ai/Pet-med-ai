#!/usr/bin/env python3
"""Validate PMAI-P0-04 disposable target authorization preparation V1."""

from __future__ import annotations

import ast
import csv
import hashlib
from pathlib import Path
import re
import sys


REPO = Path(__file__).resolve().parents[1]
DOC = REPO / 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1.md'
CHECKLIST = REPO / 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_CHECKLIST_V1.csv'
GO_NO_GO = REPO / 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = REPO / 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_TEST_MATRIX_V1.csv'
LOCKED_RUNNER = REPO / 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
PREVIOUS_GOVERNANCE = REPO / 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_REHEARSAL_GOVERNANCE_V1.md'
CI = REPO / 'scripts/ci_static_checks.sh'
PRIOR_VALIDATOR = REPO / 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'

EXPECTED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
CI_COMMAND = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py || exit 1'
EXPECTED_PRIOR_CI_SHA256 = '27579b1d054a50223f76590c15bf310c4cc950341d1018e89c54a4849f62d0c2'
EXPECTED_PRE_ROLLOVER_CI_SHA256 = '9d07238bc0831d43c1b4ee7dfea73d2a92016eca68af4f5bdb210032ab071d50'
EXPECTED_FINAL_CI_SHA256 = '0ddbb7e54bfdeaad96fa11911b747a0a17dd146fb72d6ed11ff9fb70942e2800'

FALSE_KEYS = ('disposable_restore_target_provisioning_authorized', 'disposable_restore_execution_authorized', 'disposable_restore_database_created', 'disposable_restore_database_write_authorized', 'restore_runner_created', 'restore_runner_execution_enabled', 'restore_runner_executed_by_ci', 'backup_restoreability_verified', 'disposable_restore_rehearsal_complete', 'corrected_migration_implementation_authorized', 'p0_04_execution_authorized', 'staging_0010_apply_authorized', 'active_0010_migration_file_created', 'staging_0010_migration_executed', 'production_migration_authorized', 'production_migration_executed', 'network_access', 'database_connection', 'database_write', 'restore_execution', 'pg_restore_invoked', 'psql_invoked', 'alembic_invoked', 'migration_created', 'migration_executed')

REQUIRED_DOC_MARKERS = (
    "stage_id=PMAI-P0-04",
    "package_status=PREPARATION_ONLY",
    "repository_only=true",
    "evidence_completeness=PENDING_DRY_RUN_REVIEW_VALIDATION_AND_SEPARATE_AUTHORIZATION",
    "decision=HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW",
    "local_main=3124087025522892d9e9a887af977ab03e244c73",
    "origin_main=3124087025522892d9e9a887af977ab03e244c73",
    "local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228",
    "remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228",
    "production_runtime=d659aefb",
    "staging_runtime=8d1dc881",
    "production_database_revision=0009_diag_data",
    "staging_database_revision=0009_diag_data",
    "baseline_source=operator_handoff_not_network_reverified_by_this_package",
    "ready_for_separate_disposable_target_provisioning_authorization_review=true",
    "disposable_restore_target_provisioning_authorized=false",
    "protected_hash_rollover_required=true",
    "prior_validator_target_scope_extended=true",
    "prior_validator_hash_scope_extended=true",
    "ci_target_scope_extended=true",
    "approved_ci_validator_count=2",
    "protected_hash_rollover_complete=true",
    "post_rollover_ci_sha256=8068312d6aa24e667f344b3eea9082f0a9b3688bc664dee0984d3e3dd251f25c",
)

REQUIRED_TEST_IDS = {
    "PMAI-P0-04-DTPA-T001",
    "PMAI-P0-04-DTPA-T002",
    "PMAI-P0-04-DTPA-T003",
    "PMAI-P0-04-DTPA-T004",
    "PMAI-P0-04-DTPA-T005",
    "PMAI-P0-04-DTPA-T006",
    "PMAI-P0-04-DTPA-T007",
    "PMAI-P0-04-DTPA-T008",
    "PMAI-P0-04-DTPA-T009",
    "PMAI-P0-04-DTPA-T010",
    "PMAI-P0-04-DTPA-T011",
    "PMAI-P0-04-DTPA-T012",
    "PMAI-P0-04-DTPA-T013",
    "PMAI-P0-04-DTPA-T014",
    "PMAI-P0-04-DTPA-T015",
    "PMAI-P0-04-DTPA-T016",
    "PMAI-P0-04-DTPA-T017",
    "PMAI-P0-04-DTPA-T018",
    "PMAI-P0-04-DTPA-T019",
    "PMAI-P0-04-DTPA-T020",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    failures: list[str] = []
    required_files = (
        DOC,
        CHECKLIST,
        GO_NO_GO,
        TEST_MATRIX,
        LOCKED_RUNNER,
        PREVIOUS_GOVERNANCE,
        PRIOR_VALIDATOR,
        CI,
    )
    for path in required_files:
        if not path.is_file():
            failures.append(f"missing required file: {path.relative_to(REPO)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    doc = DOC.read_text(encoding="utf-8")
    package_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX)
    )

    for marker in REQUIRED_DOC_MARKERS:
        if marker not in doc:
            failures.append(f"required document marker missing: {marker}")

    for key in FALSE_KEYS:
        false_pattern = re.compile(rf"(?m)^{re.escape(key)}=false$")
        true_pattern = re.compile(rf"(?im)^{re.escape(key)}\s*=\s*true$")
        if not false_pattern.search(doc):
            failures.append(f"required false safety marker missing: {key}")
        if true_pattern.search(package_text):
            failures.append(f"forbidden true safety marker: {key}")

    secret_patterns = (
        re.compile(r"(?i)postgres(?:ql)?://[^\s`]+"),
        re.compile(r"(?im)^\s*(?:export\s+)?DATABASE_URL\s*="),
        re.compile(r"(?im)^\s*(?:export\s+)?SECRET_KEY\s*="),
        re.compile(r"(?im)^\s*(?:password|passwd|pwd)\s*[:=]"),
    )
    for pattern in secret_patterns:
        if pattern.search(package_text):
            failures.append(f"forbidden secret or connection pattern: {pattern.pattern}")

    executable_db_command = re.compile(
        r"(?im)^\s*(?:\$\s*)?(?:sudo\s+)?(?:pg_restore|psql|alembic)(?:\s|$)"
    )
    if executable_db_command.search(package_text):
        failures.append("executable database/restore/migration command found")

    checklist = read_csv(CHECKLIST)
    checklist_by_control = {row.get("control", ""): row for row in checklist}
    for key in (
        "network_access",
        "database_connection",
        "database_write",
        "restore_execution",
        "pg_restore_invoked",
        "psql_invoked",
        "alembic_invoked",
        "migration_created",
        "migration_executed",
        "disposable_restore_target_provisioning_authorized",
        "disposable_restore_execution_authorized",
        "p0_04_execution_authorized",
        "staging_0010_apply_authorized",
        "production_migration_authorized",
    ):
        row = checklist_by_control.get(key)
        if not row or row.get("expected") != "false" or row.get("current") != "false":
            failures.append(f"checklist false control invalid: {key}")

    for key in (
        "protected_hash_rollover_required",
        "protected_hash_scope_extended",
        "protected_hash_rollover_complete",
    ):
        row = checklist_by_control.get(key)
        if not row or row.get("expected") != "true" or row.get("current") != "true":
            failures.append(f"checklist true control invalid: {key}")

    decision_rows = read_csv(GO_NO_GO)
    if len(decision_rows) != 1:
        failures.append("Go/No-Go must contain exactly one decision row")
    else:
        decision = decision_rows[0]
        if decision.get("authorized") != "false":
            failures.append("Go/No-Go authorized must be false")
        if decision.get("decision") != (
            "HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_"
            "AUTHORIZATION_REVIEW"
        ):
            failures.append("Go/No-Go decision is not the required HOLD")

    test_rows = read_csv(TEST_MATRIX)
    actual_test_ids = {row.get("test_id", "") for row in test_rows}
    if actual_test_ids != REQUIRED_TEST_IDS:
        failures.append("test matrix IDs differ from the exact required set")

    runner_hash = sha256_path(LOCKED_RUNNER)
    if runner_hash != EXPECTED_RUNNER_SHA256:
        failures.append(
            f"locked runner SHA-256 mismatch: expected={EXPECTED_RUNNER_SHA256} "
            f"actual={runner_hash}"
        )

    final_ci_hash = sha256_path(CI)
    if final_ci_hash != EXPECTED_FINAL_CI_SHA256:
        failures.append(
            f"post-rollover CI SHA-256 mismatch: expected={EXPECTED_FINAL_CI_SHA256} "
            f"actual={final_ci_hash}"
        )

    prior_source = PRIOR_VALIDATOR.read_text(encoding="utf-8")
    try:
        prior_tree = ast.parse(prior_source)
        assignments = {}
        for node in prior_tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id in {"TARGETS", "HASHES"}:
                    assignments[target.id] = ast.literal_eval(node.value)
        prior_targets = assignments.get("TARGETS")
        prior_hashes = assignments.get("HASHES")
    except (SyntaxError, ValueError) as exc:
        failures.append(f"prior validator literal parsing failed: {exc}")
        prior_targets = None
        prior_hashes = None

    package_paths = {
        'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1.md',
        'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_CHECKLIST_V1.csv',
        'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_GO_NO_GO_V1.csv',
        'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1_TEST_MATRIX_V1.csv',
        'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py',
    }
    if not isinstance(prior_targets, list) or not package_paths.issubset(set(prior_targets)):
        failures.append("prior validator TARGETS does not protect the full package")
    if not isinstance(prior_hashes, dict):
        failures.append("prior validator HASHES is unavailable")
    else:
        if prior_hashes.get('scripts/ci_static_checks.sh') != EXPECTED_FINAL_CI_SHA256:
            failures.append("prior validator does not protect the final CI hash")
        for rel in package_paths:
            path = REPO / rel
            expected = prior_hashes.get(rel)
            if not expected or not path.is_file() or sha256_path(path) != expected:
                failures.append(f"prior validator protected package hash invalid: {rel}")

    ci_text = CI.read_text(encoding="utf-8")
    target_block = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)\s*$", ci_text)
    if target_block is None or not isinstance(prior_targets, list):
        failures.append("CI/prior validator target scope cannot be compared")
    else:
        ci_targets = re.findall(r'^\s*"([^"]+)"\s*$', target_block.group(1), flags=re.M)
        if ci_targets != prior_targets:
            failures.append("CI TARGETS differs from prior validator TARGETS")

    active_migrations = sorted(
        path.relative_to(REPO).as_posix()
        for path in REPO.glob("backend/**/0010*.py")
        if path.is_file()
    )
    if active_migrations:
        failures.append(
            "active backend 0010 migration file(s) present: "
            + ", ".join(active_migrations)
        )

    ci_lines = CI.read_text(encoding="utf-8").splitlines()
    if ci_lines.count(CI_COMMAND) != 1:
        failures.append("fail-closed CI validator command must appear exactly once")

    for path in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line != line.rstrip():
                failures.append(
                    f"trailing whitespace: {path.relative_to(REPO)}:{line_no}"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("PASS: PMAI-P0-04 Disposable Target Provisioning Authorization Preparation V1")
    print("stage_id=PMAI-P0-04")
    print("package_status=PREPARATION_ONLY")
    print("protected_hash_rollover_complete=true")
    print("post_rollover_ci_sha256=8068312d6aa24e667f344b3eea9082f0a9b3688bc664dee0984d3e3dd251f25c")
    print("repository_only=true")
    print("network_access=false")
    print("database_connection=false")
    print("database_write=false")
    print("restore_execution=false")
    print("migration_created=false")
    print("migration_executed=false")
    print("disposable_restore_target_provisioning_authorized=false")
    print("disposable_restore_execution_authorized=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("decision=HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
