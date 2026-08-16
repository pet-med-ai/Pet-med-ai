#!/usr/bin/env python3
"""Validate PMAI-P0-04 fresh disposable target provisioning evidence V3."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_"
DOC = PREFIX + "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3.md"
CHECKLIST = PREFIX + "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3_CHECKLIST_V1.csv"
GO_NO_GO = PREFIX + "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3_GO_NO_GO_V1.csv"
TEST_MATRIX = PREFIX + "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3_TEST_MATRIX_V1.csv"
AUTH_DOC = PREFIX + "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXTERNAL_EXECUTION_AUTHORIZATION_V3.md"
PRIOR_REVIEW_DOC = PREFIX + "FRESH_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V3.md"
DESIGN_CANDIDATE = PREFIX + "DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
IMPLEMENTATION_CANDIDATE = PREFIX + "DISPOSABLE_RESTORE_RUNNER_V3_IMPLEMENTATION_CANDIDATE_V1.py.txt"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_execution_evidence_v3.py"
CI = "scripts/ci_static_checks.sh"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"

EXPECTED_HEAD = "6673d3b4bb4052f57f4f7d456a09ac82b20ea281"
EXPECTED_PARENT = "e3dce86cdc98546e61eb52b573aa8fee112a00b4"
EXPECTED_ISOLATED = "8d1dc8814ed8f80d8bc965b494c1c320fc08f228"
EXPECTED_PRIOR_CI_SHA256 = "87605430bdb1c71d8edf7cace65bc554f5e8e888e6e8eed807ccb33cc32dbe18"
EXPECTED_FINAL_CI_SHA256 = "2aa57fb16b2513954b8ab8f9f86646a3d961174576ea6aa3539e683636620b6c"
EXPECTED_CI_TARGETS_SHA256 = "3a4111dbb58aded4461ac3baba45922b077c1bec44dea7867402bea1d106026a"
EXPECTED_CI_COMMANDS_SHA256 = "7ab6d12a3a94e577df72ed828dcfe8cedcde6bf143d1cab4e509a43236d49819"
EXPECTED_LOCKED_RUNNER_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_DESIGN_CANDIDATE_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256 = "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
EXPECTED_TARGET_CONTRACT_SHA256 = "e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744"
EXPECTED_RESULT_SHA256 = "e786650600fe955d3d1121bb4cf6187acf1fd27e256da4084c09d91348722e4f"
EXPECTED_AUTHORIZATION_RECORD = "PMAI-P0-04-FDTP-EXT-EXEC-AUTH-V3-20260815"
EXPECTED_EVIDENCE_RECORD = "PMAI-P0-04-FDTP-EXEC-EVID-V3-20260816"
EXPECTED_DECISION = "GO_TO_SEPARATE_ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION"

EVIDENCE_HASHES = [
    "58ce6e522b5cfa9d52390bc4304f4e71c7a92bef852122971948715288e16f43",
    "541eeccc2e78d5b7713d31e0a5605de641caf64facd69d58b64d32b115b619e7",
    "676c8e2198bcf764c9d215458c33a70a73a88f5b079d9648b5a29de1a3237e3e",
    "c28d09c4b80ee27d8f6f8affbe18eb100b8fae3552432ddb1d65edc237a6fb2b",
    "4edb074ae2f4cd9363adf5657286b7276d2faaf757636f74f00912b0511776c0",
]

PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
TARGET_CONTRACT = {
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

CURRENT_FALSE_MARKERS = {
    "current_external_target_provisioning_execution_authorized",
    "current_target_creation_authorized",
    "active_restore_runner_created",
    "restore_runner_v3_activation_authorized",
    "restore_runner_v3_execution_authorized",
    "current_provisioning_attempt_authorized",
    "second_provisioning_attempt_authorized",
    "target_creation_retry_allowed",
    "target_prior_retired_identity_reused",
    "exact_timestamp_inference_performed",
    "network_access",
    "external_execution",
    "provider_control_plane_opened",
    "target_selection_performed",
    "target_creation_performed",
    "target_configuration_modified",
    "target_deletion_performed",
    "credential_collection_performed",
    "connection_url_collected",
    "archive_file_opened",
    "backup_archive_listing_invoked",
    "backup_archive_member_headers_read",
    "backup_archive_member_payload_read",
    "backup_archive_extracted",
    "backup_archive_copied",
    "backup_archive_uploaded",
    "backup_archive_modified",
    "backup_archive_repackaged",
    "restore_runner_activated",
    "restore_runner_executed",
    "locked_runner_invoked",
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
    "target_database_connectivity_verified",
    "target_database_empty_state_readback_verified",
    "backup_restoreability_verified",
    "disposable_restore_rehearsal_complete",
    "restore_runner_creation_authorized",
    "restore_runner_activation_authorized",
    "restore_runner_execution_authorized",
    "restore_execution_authorized",
    "target_retirement_authorized",
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


def marker(source: str, key: str) -> str:
    matches = re.findall(r"(?m)^" + re.escape(key) + r"=(.*)$", source)
    need(matches and len(set(matches)) == 1, "marker " + key)
    return matches[0]


def rows(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def sequence_sha256(values: list[str]) -> str:
    return sha256_bytes(("\n".join(values) + "\n").encode("utf-8"))


def canonical_result(source: str) -> tuple[dict[str, object], str]:
    match = re.search(
        r"(?ms)^## 7\. Canonical sanitized provisioning result\n.*?^~~~json\n(.*?)^~~~$",
        source,
    )
    need(match is not None, "canonical JSON block")
    raw = match.group(1).rstrip("\n")
    parsed = json.loads(raw)
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    need(raw == canonical, "canonical JSON formatting")
    return parsed, canonical


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
    auth = text(AUTH_DOC)
    prior_review = text(PRIOR_REVIEW_DOC)
    ci = text(CI)

    required = {
        "stage_id": "PMAI-P0-04",
        "substage": "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3",
        "package_status": "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_RECORD_ONLY",
        "evidence_status": "COMPLETE_SINGLE_TARGET_PROVISIONING_ATTEMPT_TARGET_AVAILABLE",
        "evidence_record_id": EXPECTED_EVIDENCE_RECORD,
        "authorization_record_id": EXPECTED_AUTHORIZATION_RECORD,
        "external_provisioning_execution_performed": "true",
        "external_create_request_submitted": "true",
        "execution_attempt_limit": "1",
        "execution_attempts_consumed": "1",
        "execution_attempts_remaining": "0",
        "automatic_retry": "false",
        "manual_retry_authorized": "false",
        "authorization_reuse_allowed": "false",
        "target_created": "true",
        "target_status": "AVAILABLE",
        "target_contract_match": "true",
        "decision": EXPECTED_DECISION,
        "authorization_package_commit": EXPECTED_HEAD,
        "authorization_package_commit_parent": EXPECTED_PARENT,
        "local_main_at_evidence_entry": EXPECTED_HEAD,
        "origin_main_at_evidence_entry": EXPECTED_HEAD,
        "github_ci_gate_number": "211",
        "github_ci_gate_status": "PASS",
        "github_ci_gate_commit": EXPECTED_HEAD,
        "prior_ci_sha256": EXPECTED_PRIOR_CI_SHA256,
        "final_ci_sha256": EXPECTED_FINAL_CI_SHA256,
        "local_isolated_branch": EXPECTED_ISOLATED,
        "remote_isolated_branch": EXPECTED_ISOLATED,
        "repository_clean_before_execution": "true",
        "repository_clean_after_execution": "true",
        "target_contract_identity_sha256": EXPECTED_TARGET_CONTRACT_SHA256,
        "execution_attempt_number": "1",
        "create_request_submitted": "true",
        "name_absent_preflight": "true",
        "configuration_contract_preflight_passed": "true",
        "cost_ceiling_preflight_passed": "true",
        "target_cost_projection_usd": "0.62",
        "target_is_disposable": "true",
        "target_is_new": "true",
        "target_was_empty_at_creation": "true",
        "target_application_traffic_disabled": "true",
        "target_service_identifier_sha256": "NOT_CAPTURED_PRIVACY_BOUNDARY_ENFORCED",
        "target_service_identifier_capture_status": "INTENTIONALLY_NOT_CAPTURED",
        "target_created_at_utc": "NOT_CAPTURED_EXACTLY_RELATIVE_UI_ONLY",
        "target_expiry_at_utc": "EXTERNAL_OPERATOR_TRACKED_MAX_72_HOURS",
        "sanitized_external_evidence_count": "5",
        "sanitized_provisioning_result_sha256": EXPECTED_RESULT_SHA256,
        "sanitized_result_field_count": "23",
        "repository_only": "true",
        "fresh_disposable_target_provisioning_verified": "true",
        "target_contract_configuration_verified": "true",
        "target_available_control_plane_status_verified": "true",
        "sole_next_subject": "ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION",
    }
    required.update(TARGET_CONTRACT)
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)
    for key in CURRENT_FALSE_MARKERS:
        need(marker(doc, key) == "false", "false boundary marker " + key)

    historical = {
        "recorded_provider_control_plane_opened": "true",
        "recorded_target_form_configured": "true",
        "recorded_external_create_request_submitted": "true",
        "recorded_target_created": "true",
        "recorded_target_available": "true",
        "recorded_execution_attempts_consumed": "1",
        "recorded_credentials_viewed": "false",
        "recorded_connection_values_viewed": "false",
        "recorded_database_connection": "false",
        "recorded_backup_access": "false",
        "recorded_runner_created": "false",
        "recorded_runner_activated": "false",
        "recorded_runner_executed": "false",
        "recorded_restore_execution": "false",
        "recorded_migration_created": "false",
        "recorded_migration_executed": "false",
        "recorded_resource_deleted": "false",
    }
    for key, expected in historical.items():
        need(marker(doc, key) == expected, "recorded boundary marker " + key)

    evidence_markers = [
        "sanitized_configuration_name_evidence_sha256",
        "sanitized_region_version_evidence_sha256",
        "sanitized_plan_storage_evidence_sha256",
        "sanitized_cost_safety_evidence_sha256",
        "sanitized_available_status_evidence_sha256",
    ]
    need([marker(doc, key) for key in evidence_markers] == EVIDENCE_HASHES, "evidence hash set")

    parsed, canonical = canonical_result(doc)
    need(len(parsed) == 23, "sanitized result field count")
    need(sha256_bytes(canonical.encode("utf-8")) == EXPECTED_RESULT_SHA256, "sanitized result hash")
    need(parsed["authorization_record_id"] == EXPECTED_AUTHORIZATION_RECORD, "result authorization record")
    need(parsed["execution_attempt_number"] == 1, "result attempt")
    need(parsed["target_contract_identity_sha256"] == EXPECTED_TARGET_CONTRACT_SHA256, "result contract hash")
    need(parsed["target_status"] == "AVAILABLE", "result status")
    need(parsed["target_service_identifier_sha256"] == "NOT_CAPTURED_PRIVACY_BOUNDARY_ENFORCED", "result identity privacy")
    need(parsed["target_created_at_utc"] == "NOT_CAPTURED_EXACTLY_RELATIVE_UI_ONLY", "result creation precision")
    need(parsed["target_expiry_at_utc"] == "EXTERNAL_OPERATOR_TRACKED_MAX_72_HOURS", "result expiry precision")
    need(parsed["sanitized_external_evidence_sha256_set"] == EVIDENCE_HASHES, "result evidence hashes")

    need(marker(auth, "authorization_record_id") == EXPECTED_AUTHORIZATION_RECORD, "authorization record rollover")
    need(marker(auth, "target_contract_identity_sha256") == EXPECTED_TARGET_CONTRACT_SHA256, "authorization contract rollover")
    need(marker(auth, "post_execution_next_subject") == "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3", "authorization successor")
    need(marker(auth, "subsequent_execution_attempts_consumed") == "1", "authorization pointer attempt")
    need(marker(auth, "subsequent_execution_attempts_remaining") == "0", "authorization pointer remaining")
    need(marker(auth, "subsequent_target_status") == "AVAILABLE", "authorization pointer status")
    need(marker(auth, "subsequent_sanitized_provisioning_result_sha256") == EXPECTED_RESULT_SHA256, "authorization pointer result")
    need(marker(prior_review, "target_contract_identity_sha256") == EXPECTED_TARGET_CONTRACT_SHA256, "prior review contract")

    package_text = "\n".join(text(rel) for rel in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX))
    forbidden = [
        r"(?i)postgres(?:ql)?://[^\s`]+",
        r"(?im)^\s*(?:export\s+)?DATABASE_URL\s*=",
        r"(?im)^\s*(?:export\s+)?SECRET_KEY\s*=",
        r"(?im)^\s*(?:password|passwd|pwd|api_token|access_token)\s*[:=]",
        r"(?i)\bsrv-[a-z0-9]{8,}\b",
    ]
    need(not any(re.search(pattern, package_text) for pattern in forbidden), "secret raw identifier or connection material")
    need("dashboard.render.com/d/" not in package_text, "raw dashboard URL")

    checklist = rows(CHECKLIST)
    go_no_go = rows(GO_NO_GO)
    tests = rows(TEST_MATRIX)
    need(len(checklist) == 60 and all(row["status"] == "PASS" for row in checklist), "checklist")
    need(len(go_no_go) == 40 and {row["status"] for row in go_no_go} == {"PASS", "HOLD"}, "go/no-go")
    need(len(tests) == 55 and all(row["status"] == "DESIGNED" for row in tests), "test matrix")

    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, "locked runner hash")
    need(sha256_path(ROOT / DESIGN_CANDIDATE) == EXPECTED_DESIGN_CANDIDATE_SHA256, "design candidate hash")
    implementation = ROOT / IMPLEMENTATION_CANDIDATE
    need(implementation.is_file() and not implementation.is_symlink(), "implementation candidate")
    need(sha256_path(implementation) == EXPECTED_IMPLEMENTATION_CANDIDATE_SHA256, "implementation candidate hash")
    need(not implementation.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), "implementation candidate executable")
    need(not (ROOT / IMPLEMENTATION_CANDIDATE.removesuffix(".txt")).exists(), "active implementation twin")
    assignments = candidate_assignments(implementation.read_text(encoding="utf-8"))
    for name in (
        "EXECUTION_ENABLED",
        "ARCHIVE_ACCESS_ENABLED",
        "ARCHIVE_LISTING_ENABLED",
        "DATABASE_CONNECTION_ENABLED",
        "RESTORE_EXECUTION_ENABLED",
    ):
        need(assignments.get(name) is False, "candidate gate " + name)

    targets = ci_targets(ci)
    commands = python_lines(ci)
    need(len(targets) == 147 and len(set(targets)) == 147, "CI target cardinality")
    need(PACKAGE_PATHS <= set(targets), "CI package targets")
    need(sequence_sha256(targets) == EXPECTED_CI_TARGETS_SHA256, "CI target contract")
    need(len(commands) == 30, "CI command cardinality")
    need(sequence_sha256(commands) == EXPECTED_CI_COMMANDS_SHA256, "CI command contract")
    need(
        commands[-5:-2]
        == [
            "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_review_v3.py || exit 1",
            "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_external_execution_authorization_v3.py || exit 1",
            "python3 " + VALIDATOR + " || exit 1",
        ],
        "CI command order",
    )
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, "CI file hash")
    need(not list((ROOT / "backend/migrations/versions").glob("0010*.py")), "active 0010 migration")

    print("PASS: PMAI-P0-04 Fresh Disposable Target Provisioning Execution Evidence V3")
    print("stage_id=PMAI-P0-04")
    print("substage=FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V3")
    print("package_status=FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_RECORD_ONLY")
    print("external_create_request_submitted=true")
    print("execution_attempts_consumed=1")
    print("execution_attempts_remaining=0")
    print("automatic_retry=false")
    print("manual_retry_authorized=false")
    print("target_created=true")
    print("target_status=AVAILABLE")
    print("target_contract_match=true")
    print("target_service_identifier_captured=false")
    print("credentials_collected=false")
    print("database_connection=false")
    print("active_restore_runner_created=false")
    print("restore_runner_activated=false")
    print("restore_runner_executed=false")
    print("restore_execution=false")
    print("migration_created=false")
    print("migration_executed=false")
    print("resource_deleted=false")
    print("backup_restoreability_verified=false")
    print("disposable_restore_rehearsal_complete=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("decision=" + EXPECTED_DECISION)
    print("next_subject=ACTIVE_RESTORE_RUNNER_V3_CREATION_AND_ACTIVATION_PREPARATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
