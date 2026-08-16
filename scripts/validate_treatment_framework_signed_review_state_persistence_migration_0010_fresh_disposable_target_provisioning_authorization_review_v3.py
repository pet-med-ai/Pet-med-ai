#!/usr/bin/env python3
"""Validate PMAI-P0-04 Fresh Disposable Target Provisioning Authorization Review V3."""

from __future__ import annotations

import ast
import csv
import hashlib
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3.md"
CHECKLIST = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3_CHECKLIST_V1.csv"
GO_NO_GO = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3_GO_NO_GO_V1.csv"
TEST_MATRIX = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3_TEST_MATRIX_V1.csv"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_review_v3.py"
PREPARATION_DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V3.md"
DESIGN_CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
IMPLEMENTATION_CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_CANDIDATE_V1.py.txt"
CI = "scripts/ci_static_checks.sh"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"

EXPECTED_HEAD = "4d787ebd51f610d8f92e679ab5caa22191924ac4"
EXPECTED_PARENT = "6a11b484f4506caccd2e27be1558bcf455a8538a"
EXPECTED_ISOLATED = "8d1dc8814ed8f80d8bc965b494c1c320fc08f228"
EXPECTED_PRIOR_CI_SHA256 = "8c23f683f89965f4b90bd2925a575d2ac5ee5340ece340cc12b02ec923dcce55"
EXPECTED_FINAL_CI_SHA256 = "4c91905018f71da785a3ec77fd20da7c31c8e495862fb6e30259e60658756706"
EXPECTED_CI_TARGETS_SHA256 = "bbaf1559159f1882bd922581c1bb95f157fe01020fb0b8c327bd849413dfd7bc"
EXPECTED_CI_COMMANDS_SHA256 = "fbef4bae5e5291fcb84bbe1d2aa1f2f58c904d954402d9dbdf4e13103fb827f6"
EXPECTED_LOCKED_RUNNER_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_DESIGN_CANDIDATE_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256 = "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
EXPECTED_TARGET_CONTRACT_SHA256 = "e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744"
EXPECTED_NEXT_SUBJECT = "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXTERNAL_EXECUTION_AUTHORIZATION_V3"

PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
CONTRACT_KEYS = (
    "authorization_record_id",
    "target_logical_name",
    "target_provider",
    "target_provider_account_scope",
    "target_region",
    "target_engine_family",
    "target_server_major_version",
    "target_instance_type",
    "target_storage_gb",
    "target_storage_autoscaling",
    "target_read_replica_count",
    "target_high_availability",
    "target_connection_pooling",
    "target_application_attachment_count",
    "target_network_scope",
    "target_cost_ceiling_usd",
    "target_max_lifetime_hours",
    "target_delete_within_hours_after_evidence",
    "target_deletion_owner",
)
EXPECTED_CONTRACT = {
    "authorization_record_id": "PMAI-P0-04-FDTP-AUTH-REVIEW-V3-20260815",
    "target_logical_name": "pet-med-ai-db-p0-04-fresh-disposable-restore-v3-ohio",
    "target_provider": "Render",
    "target_provider_account_scope": "PROJECT_OWNER_EXISTING_RENDER_ACCOUNT",
    "target_region": "Ohio (US East)",
    "target_engine_family": "PostgreSQL",
    "target_server_major_version": "18",
    "target_instance_type": "Basic-256mb",
    "target_storage_gb": "1",
    "target_storage_autoscaling": "false",
    "target_read_replica_count": "0",
    "target_high_availability": "false",
    "target_connection_pooling": "false",
    "target_application_attachment_count": "0",
    "target_network_scope": "UNATTACHED_NO_APPLICATION_TRAFFIC",
    "target_cost_ceiling_usd": "1.00",
    "target_max_lifetime_hours": "72",
    "target_delete_within_hours_after_evidence": "24",
    "target_deletion_owner": "PROJECT_OWNER_OPERATOR",
}
FALSE_MARKERS = {
    "current_fresh_disposable_target_provisioning_authorized",
    "external_target_provisioning_execution_authorized",
    "one_time_external_provisioning_confirmation_present",
    "fresh_disposable_target_selected",
    "fresh_disposable_target_created",
    "restore_runner_v3_implementation_promoted",
    "active_restore_runner_created",
    "restore_runner_v3_activation_authorized",
    "restore_runner_v3_execution_authorized",
    "archive_file_opened",
    "backup_archive_listing_invoked",
    "backup_archive_member_headers_read",
    "backup_archive_member_payload_read",
    "backup_archive_extracted",
    "backup_archive_copied",
    "backup_archive_uploaded",
    "backup_archive_modified",
    "backup_archive_repackaged",
    "fresh_disposable_target_provisioning_authorized",
    "render_target_created",
    "render_target_deleted",
    "restore_runner_activated",
    "restore_runner_executed",
    "locked_runner_invoked",
    "credential_collection_performed",
    "connection_url_collected",
    "database_connection",
    "database_write",
    "restore_execution",
    "pg_restore_invoked",
    "psql_invoked",
    "alembic_invoked",
    "migration_created",
    "migration_executed",
    "application_deployment",
    "resource_deleted",
    "files_staged",
    "files_committed",
    "files_pushed",
    "backup_restoreability_verified",
    "disposable_restore_rehearsal_complete",
    "p0_04_execution_authorized",
    "staging_0010_apply_authorized",
}


def need(condition: bool, message: str) -> None:
    if not condition:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def text(rel: str) -> str:
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + rel)
    return path.read_text(encoding="utf-8")


def rows(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def marker(source: str, key: str) -> str:
    matches = re.findall(r"(?m)^" + re.escape(key) + r"=(.*)$", source)
    need(matches and len(set(matches)) == 1, "marker " + key)
    return matches[0]


def ci_targets(source: str) -> list[str]:
    match = re.search(r'(?ms)^TARGETS=\(\n(.*?)^\)\s*$', source)
    need(match is not None, "CI TARGETS block")
    return re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)


def python_lines(source: str) -> list[str]:
    return [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith("python3 ")
        and not line.strip().startswith("python3 -m py_compile ")
    ]


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


def canonical_contract_sha256(doc: str) -> str:
    canonical = "".join(key + "=" + marker(doc, key) + "\n" for key in CONTRACT_KEYS)
    return sha256_bytes(canonical.encode("utf-8"))


def sequence_sha256(values: list[str]) -> str:
    return sha256_bytes(("\n".join(values) + "\n").encode("utf-8"))


def main() -> int:
    doc = text(DOC)
    preparation = text(PREPARATION_DOC)
    ci = text(CI)
    required = {
        "stage_id": "PMAI-P0-04",
        "substage": "FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3",
        "package_status": "FRESH_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_RECORD_ONLY",
        "review_status": "PROPOSED_APPROVE_EXACT_FRESH_TARGET_CONTRACT_V3",
        "authorization_scope": "ONE_NEW_EMPTY_ISOLATED_DISPOSABLE_POSTGRES_SERVICE_ONLY",
        "authorization_scope_recorded": "true",
        "post_effective_gate_fresh_disposable_target_contract_authorized": "true",
        "post_effective_gate_fresh_disposable_target_provisioning_eligible": "true",
        "selected_route": "ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3",
        "fresh_disposable_target_provisioning_authorization_preparation_complete": "true",
        "restore_runner_v3_implementation_authorized": "true",
        "root_contract_resolved": "true",
        "root_layout_classification": "PG_DIRECTORY_ROOT_DEEP_WRAPPED",
        "wrapper_depth": "2",
        "cumulative_archive_listing_attempts_consumed": "3",
        "cumulative_archive_listing_attempts_remaining": "0",
        "target_contract_bound": "true",
        "target_contract_identity_sha256": EXPECTED_TARGET_CONTRACT_SHA256,
        "target_service_identifier": "UNBOUND_UNTIL_CREATED",
        "actual_target_identity_sha256": "UNBOUND_UNTIL_CREATED",
        "target_created_at": "UNBOUND_UNTIL_CREATED",
        "target_expiry_at": "DERIVE_FROM_CREATED_AT_PLUS_72_HOURS",
        "target_is_disposable": "true",
        "target_must_be_new": "true",
        "target_must_be_empty": "true",
        "target_production_identity_excluded": "true",
        "target_staging_identity_excluded": "true",
        "target_prior_retired_identity_reuse_forbidden": "true",
        "target_prior_authorization_reuse_forbidden": "true",
        "target_application_traffic_disabled": "true",
        "target_cleanup_evidence_required": "true",
        "source_postgresql_major_version": "18",
        "restore_client_version": "18.4",
        "required_target_postgresql_major_version": "18",
        "version_compatibility_review": "PASS_CONDITIONAL_ON_EXECUTION_TIME_EXACT_MAJOR_RECHECK",
        "provider_pricing_network_reverified": "false",
        "repository_only": "true",
        "network_access": "false",
        "external_execution": "false",
        "sole_next_subject": EXPECTED_NEXT_SUBJECT,
        "decision": "GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY",
    }
    required.update(EXPECTED_CONTRACT)
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == "false", "false boundary marker " + key)
    need(marker(doc, "local_main") == EXPECTED_HEAD, "entry head")
    need(marker(doc, "origin_main") == EXPECTED_HEAD, "origin head")
    need(marker(doc, "main_parent") == EXPECTED_PARENT, "entry parent")
    need(marker(doc, "github_ci_gate_number") == "209", "Gate number")
    need(marker(doc, "github_ci_gate_status") == "PASS", "Gate status")
    need(marker(doc, "github_ci_gate_commit") == EXPECTED_HEAD, "Gate commit")
    need(marker(doc, "prior_ci_sha256") == EXPECTED_PRIOR_CI_SHA256, "prior CI hash")
    need(marker(doc, "final_ci_sha256") == EXPECTED_FINAL_CI_SHA256, "final CI hash")
    need(marker(doc, "local_isolated_branch") == EXPECTED_ISOLATED, "isolated local")
    need(marker(doc, "remote_isolated_branch") == EXPECTED_ISOLATED, "isolated remote")
    need(marker(preparation, "ready_for_separate_fresh_disposable_target_provisioning_authorization_review_v3") == "true", "preparation readiness")
    need(marker(preparation, "fresh_disposable_target_selected") == "false", "preparation target selection")
    need(marker(preparation, "fresh_disposable_target_created") == "false", "preparation target creation")
    need(marker(preparation, "final_ci_sha256") == EXPECTED_FINAL_CI_SHA256, "preparation final CI hash")
    need(canonical_contract_sha256(doc) == EXPECTED_TARGET_CONTRACT_SHA256, "target contract hash")
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, "locked runner hash")
    need(sha256_path(ROOT / DESIGN_CANDIDATE) == EXPECTED_DESIGN_CANDIDATE_SHA256, "design candidate hash")
    candidate = ROOT / IMPLEMENTATION_CANDIDATE
    need(candidate.is_file() and not candidate.is_symlink(), "implementation candidate")
    need(sha256_path(candidate) == EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256, "implementation candidate hash")
    need(IMPLEMENTATION_CANDIDATE.endswith(".py.txt"), "implementation candidate suffix")
    need(not candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), "implementation candidate executable")
    need(not (ROOT / IMPLEMENTATION_CANDIDATE.removesuffix(".txt")).exists(), "active implementation twin")
    assignments = candidate_assignments(candidate.read_text(encoding="utf-8"))
    for name in (
        "EXECUTION_ENABLED",
        "ARCHIVE_ACCESS_ENABLED",
        "ARCHIVE_LISTING_ENABLED",
        "DATABASE_CONNECTION_ENABLED",
        "RESTORE_EXECUTION_ENABLED",
    ):
        need(assignments.get(name) is False, "candidate gate " + name)
    package_text = "\n".join(text(rel) for rel in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX))
    forbidden = [
        r"(?i)postgres(?:ql)?://[^\s`]+",
        r"(?im)^\s*(?:export\s+)?DATABASE_URL\s*=",
        r"(?im)^\s*(?:export\s+)?SECRET_KEY\s*=",
        r"(?im)^\s*(?:password|passwd|pwd)\s*[:=]",
    ]
    need(not any(re.search(pattern, package_text) for pattern in forbidden), "secret or connection material")
    checklist = rows(CHECKLIST)
    go_no_go = rows(GO_NO_GO)
    tests = rows(TEST_MATRIX)
    need(len(checklist) == 69 and all(row["status"] == "PASS" for row in checklist), "checklist")
    need(len(go_no_go) == 40 and {row["status"] for row in go_no_go} == {"PASS", "HOLD"}, "go/no-go")
    need(len(tests) == 62 and all(row["status"] == "DESIGNED" for row in tests), "test matrix")
    targets = ci_targets(ci)
    commands = python_lines(ci)
    need(len(targets) == 142 and len(set(targets)) == 142, "CI target cardinality")
    need(PACKAGE_PATHS <= set(targets), "CI package targets")
    need(sequence_sha256(targets) == EXPECTED_CI_TARGETS_SHA256, "CI target contract")
    need(len(commands) == 29, "CI command cardinality")
    need(sequence_sha256(commands) == EXPECTED_CI_COMMANDS_SHA256, "CI command contract")
    need(
        commands[-5:-1]
        == [
            "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_preparation_v3.py || exit 1",
            "python3 " + VALIDATOR + " || exit 1",
            "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_external_execution_authorization_v3.py || exit 1",
            "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_execution_evidence_v3.py || exit 1",
        ],
        "CI command order",
    )
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, "CI file hash")
    need(not list((ROOT / "backend/migrations/versions").glob("0010*.py")), "active 0010 migration")
    print("PASS: PMAI-P0-04 Fresh Disposable Target Provisioning Authorization Review V3")
    print("stage_id=PMAI-P0-04")
    print("substage=FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3")
    print("package_status=FRESH_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_RECORD_ONLY")
    print("authorization_scope_recorded=true")
    print("target_contract_bound=true")
    print("target_contract_identity_sha256=" + EXPECTED_TARGET_CONTRACT_SHA256)
    print("post_effective_gate_fresh_disposable_target_contract_authorized=true")
    print("post_effective_gate_fresh_disposable_target_provisioning_eligible=true")
    print("fresh_disposable_target_provisioning_authorized=false")
    print("external_target_provisioning_execution_authorized=false")
    print("one_time_external_provisioning_confirmation_present=false")
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
    print("decision=GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY")
    print("next_subject=" + EXPECTED_NEXT_SUBJECT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
