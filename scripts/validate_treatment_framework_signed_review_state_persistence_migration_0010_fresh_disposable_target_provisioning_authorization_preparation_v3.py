#!/usr/bin/env python3
"""Validate PMAI-P0-04 Fresh Disposable Target Provisioning Authorization Preparation V3."""

from __future__ import annotations

import ast
import csv
import hashlib
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3.md"
CHECKLIST = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3_CHECKLIST_V1.csv"
GO_NO_GO = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3_GO_NO_GO_V1.csv"
TEST_MATRIX = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3_TEST_MATRIX_V1.csv"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_preparation_v3.py"
PRIOR_REVIEW_DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_IMPLEMENTATION_AUTHORIZATION_REVIEW_V1.md"
DESIGN_CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
IMPLEMENTATION_CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_CANDIDATE_V1.py.txt"
CI = "scripts/ci_static_checks.sh"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"

EXPECTED_HEAD = "6a11b484f4506caccd2e27be1558bcf455a8538a"
EXPECTED_PARENT = "a2f117eb55208bf5022d04482d005137a2f26874"
EXPECTED_ISOLATED = "8d1dc8814ed8f80d8bc965b494c1c320fc08f228"
EXPECTED_PRIOR_CI_SHA256 = "55dd1eb17ed1fb19d030759ae9ff5926a2bda5ee545461a980a99b58a5c474f1"
EXPECTED_FINAL_CI_SHA256 = "4b50f28b230853bd57a983a7034aff170e11531bd276964a8c4b93769803c80c"
EXPECTED_LOCKED_RUNNER_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_DESIGN_CANDIDATE_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256 = "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
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
EXPECTED_NEXT_SUBJECT = "FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3"

PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
FALSE_MARKERS = {
    "fresh_disposable_target_provisioning_authorized", "fresh_disposable_target_created",
    "active_restore_runner_created", "restore_runner_v3_activation_authorized",
    "restore_runner_v3_execution_authorized", "one_time_restore_execution_authorized",
    "archive_file_opened", "backup_archive_listing_invoked",
    "backup_archive_member_headers_read", "backup_archive_member_payload_read",
    "backup_archive_extracted", "backup_archive_copied", "backup_archive_uploaded",
    "backup_archive_modified", "backup_archive_repackaged", "credential_collection_performed",
    "connection_url_collected", "database_connection", "database_write", "restore_execution",
    "pg_restore_invoked", "psql_invoked", "alembic_invoked", "migration_created",
    "migration_executed", "application_deployment", "resource_deleted", "files_staged",
    "files_committed", "files_pushed", "backup_restoreability_verified",
    "disposable_restore_rehearsal_complete", "p0_04_execution_authorized",
    "staging_0010_apply_authorized",
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


def marker(source: str, key: str) -> str:
    match = re.search(r"(?m)^" + re.escape(key) + r"=(.*)$", source)
    need(match is not None, "marker " + key)
    return match.group(1)


def ci_targets(source: str) -> list[str]:
    match = re.search(r'(?ms)^TARGETS=\(\n(.*?)^\)\s*$', source)
    need(match is not None, "CI TARGETS block")
    return re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)


def python_lines(source: str) -> list[str]:
    return [line.strip() for line in source.splitlines() if line.strip().startswith("python3 ") and not line.strip().startswith("python3 -m py_compile ")]


def candidate_assignments(source: str) -> dict[str, object]:
    tree = ast.parse(source, filename=IMPLEMENTATION_CANDIDATE)
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


def main() -> int:
    doc = text(DOC)
    prior = text(PRIOR_REVIEW_DOC)
    ci = text(CI)
    required = {
        "stage_id": "PMAI-P0-04",
        "substage": "FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3",
        "package_status": "FRESH_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_ONLY",
        "selected_route": "ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3",
        "restore_runner_v3_implementation_authorized": "true",
        "fresh_disposable_target_provisioning_authorization_preparation_complete": "true",
        "ready_for_separate_fresh_disposable_target_provisioning_authorization_review_v3": "true",
        "current_fresh_disposable_target_provisioning_authorized": "false",
        "proposed_fresh_disposable_target_provisioning_authorized": "false",
        "fresh_disposable_target_selected": "false",
        "fresh_disposable_target_created": "false",
        "root_contract_resolved": "true",
        "root_layout_classification": "PG_DIRECTORY_ROOT_DEEP_WRAPPED",
        "wrapper_depth": "2",
        "cumulative_archive_listing_attempts_consumed": "3",
        "cumulative_archive_listing_attempts_remaining": "0",
        "candidate_scope": "ONE_NEW_EMPTY_ISOLATED_DISPOSABLE_POSTGRES_SERVICE_ONLY",
        "candidate_provider": "UNBOUND",
        "candidate_region": "UNBOUND",
        "candidate_service_identifier": "UNBOUND",
        "candidate_target_identity_sha256": "UNBOUND",
        "candidate_server_major_version": "UNBOUND",
        "candidate_cost_ceiling": "UNBOUND",
        "candidate_expiry_at": "UNBOUND",
        "candidate_deletion_owner": "UNBOUND",
        "candidate_prior_retired_target_reuse_forbidden": "true",
        "candidate_prior_authorization_reuse_forbidden": "true",
        "repository_only": "true",
        "decision": "GO_TO_SEPARATE_" + EXPECTED_NEXT_SUBJECT,
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == "false", "false boundary marker " + key)
    need(marker(doc, "local_main") == EXPECTED_HEAD, "entry head")
    need(marker(doc, "origin_main") == EXPECTED_HEAD, "origin head")
    need(marker(doc, "main_parent") == EXPECTED_PARENT, "entry parent")
    need(marker(doc, "github_ci_gate_number") == "208", "Gate number")
    need(marker(doc, "github_ci_gate_status") == "PASS", "Gate status")
    need(marker(doc, "prior_ci_sha256") == EXPECTED_PRIOR_CI_SHA256, "prior CI hash")
    need(marker(doc, "final_ci_sha256") == EXPECTED_FINAL_CI_SHA256, "final CI hash")
    need(marker(prior, "proposed_post_effective_gate_restore_runner_v3_implementation_authorized") == "true", "prior effective identity proposal")
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, "locked runner hash")
    need(sha256_path(ROOT / DESIGN_CANDIDATE) == EXPECTED_DESIGN_CANDIDATE_SHA256, "design candidate hash")
    candidate = ROOT / IMPLEMENTATION_CANDIDATE
    need(candidate.is_file() and not candidate.is_symlink(), "implementation candidate")
    need(sha256_path(candidate) == EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256, "implementation candidate hash")
    need(IMPLEMENTATION_CANDIDATE.endswith(".py.txt"), "implementation candidate suffix")
    need(not candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), "implementation candidate executable")
    need(not (ROOT / IMPLEMENTATION_CANDIDATE.removesuffix(".txt")).exists(), "active implementation twin")
    assignments = candidate_assignments(candidate.read_text(encoding="utf-8"))
    for name in ("EXECUTION_ENABLED", "ARCHIVE_ACCESS_ENABLED", "ARCHIVE_LISTING_ENABLED", "DATABASE_CONNECTION_ENABLED", "RESTORE_EXECUTION_ENABLED"):
        need(assignments.get(name) is False, "candidate gate " + name)
    package_text = "\n".join(text(rel) for rel in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX))
    forbidden = [
        r"(?i)postgres(?:ql)?://[^\s`]+", r"(?im)^\s*(?:export\s+)?DATABASE_URL\s*=",
        r"(?im)^\s*(?:export\s+)?SECRET_KEY\s*=", r"(?im)^\s*(?:password|passwd|pwd)\s*[:=]",
    ]
    need(not any(re.search(pattern, package_text) for pattern in forbidden), "secret or connection material")
    checklist = rows(CHECKLIST)
    go_no_go = rows(GO_NO_GO)
    tests = rows(TEST_MATRIX)
    need(len(checklist) == 55 and all(row["status"] == "PASS" for row in checklist), "checklist")
    need(len(go_no_go) == 32 and {row["status"] for row in go_no_go} == {"PASS", "HOLD"}, "go/no-go")
    need(len(tests) == 53 and all(row["status"] == "DESIGNED" for row in tests), "test matrix")
    targets = ci_targets(ci)
    commands = python_lines(ci)
    need(len(targets) == 137 and len(set(targets)) == 137, "CI target cardinality")
    need(PACKAGE_PATHS <= set(targets), "CI package targets")
    need(len(commands) == 28 and commands == EXPECTED_COMMANDS, "CI command contract")
    fresh_target_authorization_review_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_review_v3.py || exit 1"
    fresh_target_external_execution_authorization_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_external_execution_authorization_v3.py || exit 1"
    fresh_target_execution_evidence_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_execution_evidence_v3.py || exit 1"
    need(commands[-4:] == ["python3 " + VALIDATOR + " || exit 1", fresh_target_authorization_review_command, fresh_target_external_execution_authorization_command, fresh_target_execution_evidence_command], "CI command order")
    need(not list((ROOT / "backend/migrations/versions").glob("0010*.py")), "active 0010 migration")
    print("PASS: PMAI-P0-04 Fresh Disposable Target Provisioning Authorization Preparation V3")
    print("stage_id=PMAI-P0-04")
    print("substage=FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3")
    print("package_status=FRESH_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_ONLY")
    print("restore_runner_v3_implementation_authorized=true")
    print("fresh_disposable_target_provisioning_authorization_preparation_complete=true")
    print("ready_for_separate_fresh_disposable_target_provisioning_authorization_review_v3=true")
    print("fresh_disposable_target_provisioning_authorized=false")
    print("fresh_disposable_target_selected=false")
    print("fresh_disposable_target_created=false")
    print("active_restore_runner_created=false")
    print("restore_runner_v3_activation_authorized=false")
    print("restore_runner_v3_execution_authorized=false")
    print("archive_file_opened=false")
    print("database_connection=false")
    print("restore_execution=false")
    print("backup_restoreability_verified=false")
    print("disposable_restore_rehearsal_complete=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("decision=GO_TO_SEPARATE_" + EXPECTED_NEXT_SUBJECT)
    print("next_action=SEPARATE_" + EXPECTED_NEXT_SUBJECT + "_REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
