#!/usr/bin/env python3
"""Validate PMAI-P0-04 V4 provisioning and network-lockdown evidence."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "PMAI-P0-04"
WORK_BUNDLE = "PMAI-P0-04-DISP-TARGET-PROVISION-EVID-V4"
BASE_COMMIT = "8d48f29930d2849de9f03cfeeb050a917dd3f6d5"
BASE_TREE = "72dee05677050d0004d4a5b955f206c0de1accd2"
HEAD_BRANCH = "pmai-p0-04-v4-provisioning-execution-evidence"
EVIDENCE_RECORD = "PMAI-P0-04-FDTP-EXEC-EVID-V4-20260826"
AUTHORIZATION = (
    "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_"
    "V4_REPOSITORY_PATCH_CONTROLLED_EXECUTION_V1"
)
REVIEW_RECORD = "PMAI-P0-04-FDTP-AUTH-REVIEW-V4-20260823"
TARGET_NAME = "pet-med-ai-db-p0-04-fresh-disposable-restore-v4-ohio"
TARGET_CONTRACT_IDENTITY = (
    "e1cba6bc207fa4654d3155ef4abd8d818d8fd4323ce990446bc680fd15522529"
)
SERVICE_IDENTITY = (
    "3f0ed4e1cb1bbef10babb4d3ba7fa9ec03e048d7d30595389f30d0871bcdb4fe"
)
DECISION = "PASS_V4_PROVISIONING_AND_NETWORK_LOCKDOWN_EXECUTION_EVIDENCE_RECORDED"
NEXT_SUBJECT = (
    "ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_"
    "V4_PREPARATION"
)
PASS_MARKER = "fresh_disposable_target_provisioning_execution_evidence_v4=PASS"
PREVIOUS_POINTER = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_ACTIVE_"
    "POINTER_V1.json"
)
PREVIOUS_POINTER_SHA256 = (
    "b28619a0a3178a785782d898eb32192b164497fee5c23e96a5010cecc4bef798"
)
PREVIOUS_V4_VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_fresh_disposable_target_contract_rebind_v4.py"
)
PREVIOUS_V4_VALIDATOR_SHA256 = (
    "54566252e8097ec878c122ed95ce090c11cb623304f0b36fd7a91771b1c8ec74"
)
PREVIOUS_V4_PASS_MARKER = "fresh_disposable_target_contract_rebind_v4=PASS"
CURRENT_HOLD = (
    "HOLD_PMAI_P0_04_V4_TARGET_AVAILABLE_AND_NETWORK_LOCKED_PENDING_"
    "ACTIVE_RUNNER_AND_SRBE_CONTRACT_REBIND_V4"
)
CURRENT_COMPLETENESS = (
    "V4_TARGET_PROVISIONING_AND_NETWORK_LOCKDOWN_EVIDENCE_COMPLETE_PENDING_"
    "ACTIVE_RUNNER_SRBE_V4_REBIND_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION"
)
CURRENT_NEXT_STEP = (
    "PREPARE_ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4"
)

PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4"
)
DOC = PREFIX + ".md"
CHECKLIST = PREFIX + "_CHECKLIST_V1.csv"
GO_NO_GO = PREFIX + "_GO_NO_GO_V1.csv"
TEST_MATRIX = PREFIX + "_TEST_MATRIX_V1.csv"
BASELINE = PREFIX + "_LOCKED_BASELINE_V1.json"
POINTER = PREFIX + "_ACTIVE_POINTER_V1.json"
MANIFEST = PREFIX + "_PACKAGE_MANIFEST_V1.json"
VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_fresh_disposable_target_provisioning_execution_"
    "evidence_v4.py"
)
CENTRAL = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_staging_migration_apply.py"
)
CI = "scripts/ci_static_checks.sh"

MANIFEST_MEMBERS = tuple(sorted((
    DOC,
    CHECKLIST,
    GO_NO_GO,
    TEST_MATRIX,
    BASELINE,
    POINTER,
    VALIDATOR,
)))
PACKAGE_PATHS = tuple(sorted((*MANIFEST_MEMBERS, MANIFEST)))
AUTHORIZED_CHANGED_PATHS = set((*PACKAGE_PATHS, CENTRAL))

EXPECTED_CONTRACT_FIELDS = {
    "target_logical_name": TARGET_NAME,
    "target_provider": "Render",
    "target_region": "Ohio (US East)",
    "target_engine_family": "PostgreSQL",
    "target_server_major_version": 18,
    "target_instance_type": "Basic-256mb",
    "target_storage_gb": 1,
    "target_storage_autoscaling": False,
    "target_read_replica_count": 0,
    "target_high_availability": False,
    "target_connection_pooling": False,
    "target_application_attachment_count": 0,
    "target_network_scope": "UNATTACHED_NO_APPLICATION_TRAFFIC",
    "target_external_access_scope": "EXECUTION_TIME_SINGLE_OPERATOR_EGRESS_ALLOWLIST_ONLY",
    "target_cost_ceiling_usd": "1.00",
    "target_max_lifetime_hours": 72,
    "target_delete_within_hours_after_required_evidence": 24,
    "target_must_be_new": True,
    "target_must_be_empty": True,
    "target_provisioning_authorized": False,
}

EXPECTED_EVIDENCE_HASHES = {
    "configuration": "d2ee629ebbb8e515bd13a67bf1fe5b7cb4ab31912714fd7188769d7b9dc4e434",
    "availability": "20ba1c1d42e198da706d99774110e6d92816453fa9dc7fec4dd5163345f45f62",
    "network_lockdown": "882c28ea6cf259cd64bf2c61020685d2f36862dae62dde54f6b8384df77cc1e2",
    "lifecycle": "b27e47dded2440ac216f76e62d3efa2219cafd4789aaea833ba6a09507dfa083",
    "execution_history": "af8268416eeb00924893707c66154b7bbb57b31f50258f8f94df8e158006bc58",
}

EXPECTED_EXECUTION_HISTORY = {
    "prior_v1_authorization_id": (
        "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXTERNAL_EXECUTION_"
        "AUTHORIZATION_V4_CONTROLLED_EXECUTION_V1"
    ),
    "prior_v1_final_state": "STOPPED_NOT_EXECUTED_NETWORK_DEFAULT_CONTRACT_MISMATCH",
    "prior_v1_target_creation_count": 0,
    "provisioning_authorization_id": (
        "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_AND_NETWORK_LOCKDOWN_"
        "V4_CONTROLLED_EXECUTION_V2"
    ),
    "provisioning_authorization_final_state": (
        "STOPPED_PARTIAL_EXECUTION_NETWORK_LOCKDOWN_SAVE_NOT_PERSISTED"
    ),
    "target_created_under_v2": True,
    "target_creation_count": 1,
    "first_network_save_persisted": False,
    "network_lockdown_resave_authorization_source": (
        "EXPLICIT_USER_INSTRUCTION_AND_ACTION_TIME_CONFIRMATION_20260826"
    ),
    "network_lockdown_resave_persisted": True,
    "unapproved_retry_performed": False,
    "automatic_retry": False,
    "authorization_reuse_allowed": False,
}

EXPECTED_CURRENT_BOUNDARIES = {
    "future_single_operator_allowlist_authorized": False,
    "render_control_plane_write": False,
    "render_settings_change": False,
    "credential_or_connection_value_access": False,
    "database_connection": False,
    "database_read_write_export": False,
    "runner_import_or_execution": False,
    "backup_access": False,
    "restore_execution": False,
    "pg_restore_or_psql_execution": False,
    "migration_creation_or_execution": False,
    "deployment": False,
    "target_deletion": False,
    "production_staging_v3_resource_operations": False,
    "library_master_directory_update": False,
    "manual_retry": False,
    "automatic_retry": False,
}

EXPECTED_AUTHORIZATION = {
    "authorization_id": AUTHORIZATION,
    "risk_lane": "YELLOW_REPOSITORY_PLUS_RENDER_READONLY_EVIDENCE",
    "changed_path_scope": "EXACT_9_PATHS",
    "maximum_changed_path_count": 9,
    "maximum_commit_count": 1,
    "maximum_push_count": 1,
}

EXPECTED_PROVIDER_BINDING = {
    "target_service_identifier_sha256": SERVICE_IDENTITY,
    "external_resource_binding_state": "BOUND_SANITIZED_HASH_ONLY",
    "raw_target_service_identifier_recorded": False,
    "target_dashboard_url_recorded": False,
    "target_connection_url_recorded": False,
    "target_credential_material_recorded": False,
    "raw_provider_response_recorded": False,
    "render_readonly_metadata_revalidation": True,
    "render_readonly_scope": "EXACT_V4_TARGET_INFO_APPS_AND_NETWORK_ONLY",
    "render_service_identifier_hash_only_binding": True,
}

EXPECTED_OBSERVED_RESULT = {
    "target_created": True,
    "target_status": "AVAILABLE",
    "target_application_attachment_count": 0,
    "target_open_connection_count": 0,
    "target_open_connection_evidence_source": (
        "PRIOR_AND_POST_NETWORK_LOCKDOWN_RENDER_INFO_READBACK_20260826"
    ),
    "initial_service_inbound_ip_rule_set": ["0.0.0.0/0"],
    "required_final_service_inbound_ip_rule_set": [],
    "observed_final_service_inbound_ip_rule_set": [],
    "final_public_external_access_blocked": True,
    "network_lockdown_persisted_after_refresh": True,
    "post_refresh_network_lockdown_verification": "PASS",
    "workspace_network_rules_modified": False,
    "target_database_connectivity_verified": False,
    "target_database_empty_state_readback_verified": False,
    "backup_restoreability_verified": False,
}

PROTECTED_HISTORICAL_HASHES = {
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_"
        "REBIND_V4.md"
    ): "482679bf23019e25bd650f10be165c01c3894572fe803abb33ea0c17eca77c78",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_"
        "REBIND_V4_ACTIVE_POINTER_V1.json"
    ): "b28619a0a3178a785782d898eb32192b164497fee5c23e96a5010cecc4bef798",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_"
        "REBIND_V4_CHECKLIST_V1.csv"
    ): "259d388668b03f81eca0d766aeb459c783663ec0204700bff31b7306b75f1b52",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_"
        "REBIND_V4_GO_NO_GO_V1.csv"
    ): "a1bfbc35c61dda8a95e06ca2931d35cf50b57efbcff769f1b5f09be5ed6b5be6",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_"
        "REBIND_V4_TEST_MATRIX_V1.csv"
    ): "8f4650d61643c505c3148210059ee076d85e1864c5d5189084f4b295e229fd6b",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_"
        "REBIND_V4_LOCKED_BASELINE_V1.json"
    ): "082bfecba5593ec26faa36cb0a61a9ee4df5b1bc11537193a01917bb24d60c65",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_"
        "REBIND_V4_PACKAGE_MANIFEST_V1.json"
    ): "a6cb3a4a01bf7e18755338f950c03fc6c6cfbec69ae57d98f96a3003196ce025",
    (
        "scripts/validate_treatment_framework_signed_review_state_"
        "persistence_migration_0010_fresh_disposable_target_contract_rebind_v4.py"
    ): "54566252e8097ec878c122ed95ce090c11cb623304f0b36fd7a91771b1c8ec74",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_"
        "RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_PREPARATION_V1_"
        "LOCKED_BASELINE_V1.json"
    ): "152fb13e8feb5c019263a56d4a28fc6bcc6a6ad2b0c537385aea4f22c7b08fc8",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_"
        "RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_PREPARATION_V1_"
        "PACKAGE_MANIFEST_V1.json"
    ): "4439e3a4d86b9e8017ac29260631d7a0c16b9182bd7833a0cbc2e8c6e38d1855",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_CREATION_"
        "AND_ACTIVATION_EXECUTION_AUTHORIZATION_V1.md"
    ): "3f518dc9735060f4c74d9c0832f7228f0860cd244947573c80037e5962a384c1",
    CI: "a26f17997b73dffc542faa369c447431d97f36a84d4979fe26c3994dddcaee9b",
}


def need(condition: bool, message: str) -> None:
    if not condition:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def safe_path(relative: str) -> Path:
    path = ROOT / relative
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + relative)
    need(path.resolve().is_relative_to(ROOT.resolve()), "path escape " + relative)
    return path


def text(relative: str) -> str:
    return safe_path(relative).read_text(encoding="utf-8")


def digest(relative: str) -> str:
    return hashlib.sha256(safe_path(relative).read_bytes()).hexdigest()


def marker(source: str, key: str) -> str:
    matches = re.findall(r"(?m)^" + re.escape(key) + r"=(.*)$", source)
    need(len(matches) == 1, "marker cardinality " + key)
    return matches[0]


def rows(relative: str, expected_header: list[str]) -> list[dict[str, str]]:
    with safe_path(relative).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        need(reader.fieldnames == expected_header, "CSV header " + relative)
        data = list(reader)
        need(all(set(row) == set(expected_header) for row in data), "CSV row schema " + relative)
        return data


def literal_assignments(source: str) -> dict[str, object]:
    tree = ast.parse(source)
    assignments: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            assignments[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
    return assignments


def git_lines(*arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=False,
    )
    need(result.returncode == 0, "git inspection " + " ".join(arguments))
    return [line for line in result.stdout.splitlines() if line]


def validate_authorized_scope() -> None:
    need(len(PACKAGE_PATHS) == 8, "package path cardinality")
    need(len(AUTHORIZED_CHANGED_PATHS) == 9, "authorized path cardinality")
    need(git_lines("rev-parse", BASE_COMMIT + "^{tree}") == [BASE_TREE], "base tree drift")
    introductions = git_lines(
        "log", "--diff-filter=A", "--format=%H", "--", VALIDATOR
    )
    if introductions:
        need(len(introductions) == 1, "validator introduction commit count")
        introduction = introductions[0]
        need(git_lines("rev-parse", introduction + "^") == [BASE_COMMIT], "introduction parent")
        need(
            git_lines("rev-list", "--count", BASE_COMMIT + ".." + introduction) == ["1"],
            "one introduction commit",
        )
        need(git_lines("merge-base", introduction, "HEAD") == [introduction], "introduction ancestor")
        changed = git_lines(
            "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", introduction
        )
    else:
        need(git_lines("branch", "--show-current") == [HEAD_BRANCH], "head branch drift")
        need(git_lines("rev-parse", "HEAD") == [BASE_COMMIT], "uncommitted HEAD baseline")
        changed_set = set(git_lines("diff", "--name-only", BASE_COMMIT + "...HEAD"))
        changed_set.update(git_lines("diff", "--name-only"))
        changed_set.update(git_lines("diff", "--cached", "--name-only"))
        changed_set.update(git_lines("ls-files", "--others", "--exclude-standard"))
        changed = sorted(changed_set)
    need(set(changed) == AUTHORIZED_CHANGED_PATHS, "exact changed path scope")
    need(len(changed) == 9, "changed path count")


def validate_historical_anchors() -> None:
    for relative, expected in PROTECTED_HISTORICAL_HASHES.items():
        need(digest(relative) == expected, "protected historical hash " + relative)


def validate_previous_v4_rebind() -> None:
    need(digest(PREVIOUS_V4_VALIDATOR) == PREVIOUS_V4_VALIDATOR_SHA256, "previous V4 validator hash")
    result = subprocess.run(
        [sys.executable, "-B", str(safe_path(PREVIOUS_V4_VALIDATOR))],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    need(result.returncode == 0, "previous V4 validator exit")
    need(result.stderr == "", "previous V4 validator stderr")
    need(
        result.stdout.splitlines().count(PREVIOUS_V4_PASS_MARKER) == 1,
        "previous V4 validator PASS marker",
    )


def validate_document() -> None:
    source = text(DOC)
    required = {
        "stage_id": STAGE_ID,
        "substage": "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4",
        "work_bundle": WORK_BUNDLE,
        "evidence_record_id": EVIDENCE_RECORD,
        "authorization_record_id": AUTHORIZATION,
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "maximum_commit_count": "1",
        "maximum_push_count": "1",
        "review_record_id": REVIEW_RECORD,
        "target_contract_identity_sha256": TARGET_CONTRACT_IDENTITY,
        "target_contract_identity_is_opaque": "true",
        "target_contract_hash_recalculation_claim": "false",
        "target_logical_name": TARGET_NAME,
        "target_provider": "Render",
        "target_status": "AVAILABLE",
        "prior_v1_authorization_id": EXPECTED_EXECUTION_HISTORY["prior_v1_authorization_id"],
        "prior_v1_final_state": EXPECTED_EXECUTION_HISTORY["prior_v1_final_state"],
        "prior_v1_target_creation_count": "0",
        "provisioning_authorization_id": EXPECTED_EXECUTION_HISTORY["provisioning_authorization_id"],
        "provisioning_authorization_final_state": EXPECTED_EXECUTION_HISTORY["provisioning_authorization_final_state"],
        "target_created_under_v2": "true",
        "target_creation_count": "1",
        "first_network_save_persisted": "false",
        "network_lockdown_resave_authorization_source": EXPECTED_EXECUTION_HISTORY["network_lockdown_resave_authorization_source"],
        "network_lockdown_resave_persisted": "true",
        "unapproved_retry_performed": "false",
        "network_lockdown_automatic_retry": "false",
        "authorization_reuse_allowed": "false",
        "target_service_identifier_sha256": SERVICE_IDENTITY,
        "external_resource_binding_state": "BOUND_SANITIZED_HASH_ONLY",
        "render_readonly_scope": "EXACT_V4_TARGET_INFO_APPS_AND_NETWORK_ONLY",
        "render_service_identifier_hash_only_binding": "true",
        "target_open_connection_count": "0",
        "target_database_empty_state_readback_verified": "false",
        "backup_restoreability_verified": "false",
        "required_final_service_inbound_ip_rule_set": "[]",
        "observed_final_service_inbound_ip_rule_set": "[]",
        "final_public_external_access_blocked": "true",
        "network_lockdown_persisted_after_refresh": "true",
        "post_refresh_network_lockdown_verification": "PASS",
        "database_connection": "false",
        "future_single_operator_allowlist_authorized": "false",
        "manual_retry": "false",
        "automatic_retry": "false",
        "restore_execution": "false",
        "deployment": "false",
        "decision": DECISION,
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in required.items():
        need(marker(source, key) == expected, "document marker " + key)
    for key, expected in EXPECTED_EVIDENCE_HASHES.items():
        need(
            marker(source, "sanitized_" + key + "_evidence_sha256") == expected,
            "document evidence hash " + key,
        )
    for key, expected in EXPECTED_CONTRACT_FIELDS.items():
        rendered = str(expected).lower() if isinstance(expected, bool) else str(expected)
        need(marker(source, key) == rendered, "document contract field " + key)
    for key, expected in EXPECTED_CURRENT_BOUNDARIES.items():
        rendered = str(expected).lower() if isinstance(expected, bool) else str(expected)
        need(marker(source, key) == rendered, "document boundary " + key)
    need(SERVICE_IDENTITY != TARGET_CONTRACT_IDENTITY, "separate service and contract identities")


def validate_baseline() -> dict[str, object]:
    baseline = json.loads(text(BASELINE))
    expected_baseline = {
        "schema": "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_LOCKED_BASELINE_V1",
        "stage_id": STAGE_ID,
        "substage": "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4",
        "work_bundle": WORK_BUNDLE,
        "evidence_record_id": EVIDENCE_RECORD,
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "head_branch": HEAD_BRANCH,
        "authorization": EXPECTED_AUTHORIZATION,
        "reviewed_contract": {
            "review_record_id": REVIEW_RECORD,
            "target_contract_identity_sha256": TARGET_CONTRACT_IDENTITY,
            "identity_is_opaque": True,
            "hash_recalculation_claim": False,
            "contract_fields": EXPECTED_CONTRACT_FIELDS,
        },
        "execution_history": EXPECTED_EXECUTION_HISTORY,
        "sanitized_provider_binding": EXPECTED_PROVIDER_BINDING,
        "observed_result": EXPECTED_OBSERVED_RESULT,
        "sanitized_evidence_sha256": EXPECTED_EVIDENCE_HASHES,
        "current_boundaries": EXPECTED_CURRENT_BOUNDARIES,
        "decision": DECISION,
        "sole_next_subject": NEXT_SUBJECT,
    }
    need(
        baseline["schema"]
        == "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_LOCKED_BASELINE_V1",
        "baseline schema",
    )
    need(baseline["stage_id"] == STAGE_ID, "baseline stage")
    need(baseline["substage"] == "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4", "baseline substage")
    need(baseline["work_bundle"] == WORK_BUNDLE, "baseline work bundle")
    need(baseline["evidence_record_id"] == EVIDENCE_RECORD, "baseline evidence record")
    need(baseline["base_commit"] == BASE_COMMIT, "baseline commit")
    need(baseline["base_tree_sha"] == BASE_TREE, "baseline tree")
    need(baseline["authorization"]["authorization_id"] == AUTHORIZATION, "baseline authorization")
    reviewed = baseline["reviewed_contract"]
    need(reviewed["review_record_id"] == REVIEW_RECORD, "baseline review record")
    need(reviewed["target_contract_identity_sha256"] == TARGET_CONTRACT_IDENTITY, "baseline contract identity")
    need(reviewed["identity_is_opaque"] is True, "baseline opaque identity")
    need(reviewed["hash_recalculation_claim"] is False, "baseline no recalculation")
    need(reviewed["contract_fields"] == EXPECTED_CONTRACT_FIELDS, "baseline exact contract fields")
    history = baseline["execution_history"]
    need(history == EXPECTED_EXECUTION_HISTORY, "exact execution history")
    binding = baseline["sanitized_provider_binding"]
    need(binding["target_service_identifier_sha256"] == SERVICE_IDENTITY, "service identity hash")
    need(binding["external_resource_binding_state"] == "BOUND_SANITIZED_HASH_ONLY", "binding state")
    need(binding["target_service_identifier_sha256"] != TARGET_CONTRACT_IDENTITY, "distinct identity hashes")
    need(binding["render_readonly_metadata_revalidation"] is True, "readonly metadata revalidation")
    need(binding["render_readonly_scope"] == "EXACT_V4_TARGET_INFO_APPS_AND_NETWORK_ONLY", "readonly scope")
    need(binding["render_service_identifier_hash_only_binding"] is True, "hash-only identity binding")
    for key in (
        "raw_target_service_identifier_recorded",
        "target_dashboard_url_recorded",
        "target_connection_url_recorded",
        "target_credential_material_recorded",
        "raw_provider_response_recorded",
    ):
        need(binding[key] is False, "privacy boundary " + key)
    observed = baseline["observed_result"]
    need(observed["target_created"] is True, "target created")
    need(observed["target_status"] == "AVAILABLE", "target Available")
    need(observed["target_application_attachment_count"] == 0, "zero applications")
    need(observed["target_open_connection_count"] == 0, "zero connections")
    need(observed["required_final_service_inbound_ip_rule_set"] == [], "required empty rules")
    need(observed["observed_final_service_inbound_ip_rule_set"] == [], "observed empty rules")
    need(observed["final_public_external_access_blocked"] is True, "public access blocked")
    need(observed["network_lockdown_persisted_after_refresh"] is True, "lockdown persisted")
    need(observed["post_refresh_network_lockdown_verification"] == "PASS", "post-refresh verification")
    need(observed["workspace_network_rules_modified"] is False, "workspace unchanged")
    need(observed["target_database_connectivity_verified"] is False, "database connectivity unverified")
    need(observed["target_database_empty_state_readback_verified"] is False, "database emptiness unverified")
    need(observed["backup_restoreability_verified"] is False, "restoreability unverified")
    need(baseline["sanitized_evidence_sha256"] == EXPECTED_EVIDENCE_HASHES, "evidence hash set")
    boundaries = baseline["current_boundaries"]
    need(boundaries == EXPECTED_CURRENT_BOUNDARIES, "exact current boundaries")
    need(baseline["decision"] == DECISION, "baseline decision")
    need(baseline["sole_next_subject"] == NEXT_SUBJECT, "baseline next subject")
    need(baseline == expected_baseline, "exact locked baseline schema and values")
    return baseline


def validate_pointer() -> None:
    pointer = json.loads(text(POINTER))
    expected_pointer = {
        "schema": "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_ACTIVE_POINTER_V1",
        "stage_id": STAGE_ID,
        "substage": "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4",
        "work_bundle": WORK_BUNDLE,
        "evidence_record_id": EVIDENCE_RECORD,
        "pointer_version": 1,
        "pointer_scope": "SANITIZED_EXTERNAL_EXECUTION_EVIDENCE_ONLY",
        "supersedes_pointer_path": PREVIOUS_POINTER,
        "supersedes_pointer_sha256": PREVIOUS_POINTER_SHA256,
        "active_locked_baseline_path": BASELINE,
        "active_locked_baseline_sha256": digest(BASELINE),
        "active_contract_version": "V4",
        "active_review_record_id": REVIEW_RECORD,
        "active_target_logical_name": TARGET_NAME,
        "active_target_contract_identity_sha256": TARGET_CONTRACT_IDENTITY,
        "external_resource_binding_state": "BOUND_SANITIZED_HASH_ONLY",
        "target_service_identifier_sha256": SERVICE_IDENTITY,
        "target_selected": True,
        "target_created": True,
        "target_status": "AVAILABLE",
        "target_application_attachment_count": 0,
        "target_open_connection_count": 0,
        "final_service_inbound_ip_rule_set": [],
        "public_external_access_blocked": True,
        "network_lockdown_persisted_after_refresh": True,
        "post_refresh_network_lockdown_verification": "PASS",
        "workspace_network_rules_modified": False,
        "raw_provider_identifier_recorded": False,
        "provider_url_recorded": False,
        "credential_material_recorded": False,
        "database_connectivity_verified": False,
        "database_empty_state_readback_verified": False,
        "backup_restoreability_verified": False,
        "runtime_execution_authorized": False,
        "sole_next_subject": NEXT_SUBJECT,
    }
    need(
        pointer["schema"]
        == "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_ACTIVE_POINTER_V1",
        "pointer schema",
    )
    need(pointer["stage_id"] == STAGE_ID, "pointer stage")
    need(pointer["substage"] == "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4", "pointer substage")
    need(pointer["work_bundle"] == WORK_BUNDLE, "pointer work bundle")
    need(pointer["evidence_record_id"] == EVIDENCE_RECORD, "pointer evidence record")
    need(pointer["supersedes_pointer_path"] == PREVIOUS_POINTER, "pointer predecessor path")
    need(pointer["supersedes_pointer_sha256"] == PREVIOUS_POINTER_SHA256, "pointer predecessor hash")
    need(digest(PREVIOUS_POINTER) == PREVIOUS_POINTER_SHA256, "pointer predecessor bytes")
    need(pointer["active_locked_baseline_path"] == BASELINE, "pointer baseline path")
    need(pointer["active_locked_baseline_sha256"] == digest(BASELINE), "pointer baseline hash")
    need(pointer["active_contract_version"] == "V4", "pointer contract version")
    need(pointer["active_review_record_id"] == REVIEW_RECORD, "pointer review record")
    need(pointer["active_target_logical_name"] == TARGET_NAME, "pointer target")
    need(pointer["active_target_contract_identity_sha256"] == TARGET_CONTRACT_IDENTITY, "pointer contract identity")
    need(pointer["external_resource_binding_state"] == "BOUND_SANITIZED_HASH_ONLY", "pointer binding")
    need(pointer["target_service_identifier_sha256"] == SERVICE_IDENTITY, "pointer service hash")
    need(pointer["target_selected"] is True and pointer["target_created"] is True, "pointer created")
    need(pointer["target_status"] == "AVAILABLE", "pointer Available")
    need(pointer["target_application_attachment_count"] == 0, "pointer zero applications")
    need(pointer["target_open_connection_count"] == 0, "pointer zero connections")
    need(pointer["final_service_inbound_ip_rule_set"] == [], "pointer empty rules")
    need(pointer["public_external_access_blocked"] is True, "pointer access blocked")
    need(pointer["network_lockdown_persisted_after_refresh"] is True, "pointer lockdown persisted")
    need(pointer["post_refresh_network_lockdown_verification"] == "PASS", "pointer post-refresh verification")
    need(pointer["workspace_network_rules_modified"] is False, "pointer workspace rules unchanged")
    for key in (
        "raw_provider_identifier_recorded",
        "provider_url_recorded",
        "credential_material_recorded",
        "database_connectivity_verified",
        "database_empty_state_readback_verified",
        "backup_restoreability_verified",
        "runtime_execution_authorized",
    ):
        need(pointer[key] is False, "pointer boundary " + key)
    need(pointer["sole_next_subject"] == NEXT_SUBJECT, "pointer next subject")
    need(pointer == expected_pointer, "exact active pointer schema and values")


def validate_csvs() -> None:
    checklist = rows(CHECKLIST, ["control_id", "control", "expected", "current", "status", "evidence", "on_failure"])
    gates = rows(GO_NO_GO, ["gate_id", "scope", "expected", "current", "status", "on_failure"])
    tests = rows(TEST_MATRIX, ["test_id", "test", "method", "expected", "status", "on_failure"])
    need([row["control_id"] for row in checklist] == [f"FDTPV4-C{i:03d}" for i in range(1, 43)], "checklist IDs")
    need([row["gate_id"] for row in gates] == [f"FDTPV4-G{i:03d}" for i in range(1, 25)], "gate IDs")
    need([row["test_id"] for row in tests] == [f"FDTPV4-T{i:03d}" for i in range(1, 39)], "test IDs")
    need(all(row["status"] == "PASS" for row in checklist), "checklist status")
    expected_gate_statuses = ["PASS"] * 15 + ["HOLD_EXPECTED"] * 5 + ["PASS"] * 3 + ["HOLD_EXPECTED"]
    need([row["status"] for row in gates] == expected_gate_statuses, "gate status sequence")
    need(all(row["status"] == "DESIGNED" for row in tests), "test design status")
    need(all(row["on_failure"] == "STOP" for row in (*checklist, *gates, *tests)), "fail closed CSVs")


def validate_manifest() -> None:
    manifest = json.loads(text(MANIFEST))
    expected_keys = {
        "schema", "stage_id", "work_bundle", "repository", "base_branch",
        "base_commit", "base_tree_sha", "authorized_changed_path_count",
        "package_path_count", "manifest_member_count", "manifest_self_excluded",
        "central_integration_path", "ci_entrypoint_changed", "files",
    }
    need(set(manifest) == expected_keys, "manifest exact schema")
    need(
        manifest["schema"]
        == "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_PACKAGE_MANIFEST_V1",
        "manifest schema",
    )
    need(manifest["stage_id"] == STAGE_ID, "manifest stage")
    need(manifest["work_bundle"] == WORK_BUNDLE, "manifest work bundle")
    expected_metadata = {
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "base_tree_sha": BASE_TREE,
        "authorized_changed_path_count": 9,
        "package_path_count": 8,
        "manifest_member_count": 7,
        "manifest_self_excluded": True,
        "central_integration_path": CENTRAL,
        "ci_entrypoint_changed": False,
    }
    for key, expected in expected_metadata.items():
        need(type(manifest[key]) is type(expected) and manifest[key] == expected, "manifest metadata " + key)
    files = manifest["files"]
    need(type(files) is list and len(files) == 7, "manifest member count")
    need([item["path"] for item in files] == list(MANIFEST_MEMBERS), "manifest member sequence")
    for item in files:
        need(set(item) == {"path", "bytes", "sha256"}, "manifest member schema")
        relative = item["path"]
        path = safe_path(relative)
        need(item["bytes"] == path.stat().st_size, "manifest byte count " + relative)
        need(item["sha256"] == digest(relative), "manifest digest " + relative)
    need(MANIFEST not in {item["path"] for item in files}, "manifest self exclusion")


def validate_central_hook() -> None:
    source = text(CENTRAL)
    assignments = literal_assignments(source)
    expected = {
        "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_VALIDATOR": VALIDATOR,
        "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_VALIDATOR_SHA256": digest(VALIDATOR),
        "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_MANIFEST": MANIFEST,
        "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_MANIFEST_SHA256": digest(MANIFEST),
        "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_PASS_MARKER": PASS_MARKER,
        "CURRENT_HOLD": CURRENT_HOLD,
        "CURRENT_COMPLETENESS": CURRENT_COMPLETENESS,
        "CURRENT_NEXT_STEP": CURRENT_NEXT_STEP,
    }
    for key, value in expected.items():
        need(assignments.get(key) == value, "central hook constant " + key)
    need(source.count("v4_evidence_result = subprocess.run(") == 1, "central evidence subprocess count")
    need(
        source.count('[sys.executable, "-B", str(v4_evidence_validator_path)]') == 1,
        "central evidence subprocess command",
    )
    need(
        source.count("FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_PASS_MARKER") >= 3,
        "central evidence PASS checks",
    )
    need(source.index("v4_result = subprocess.run(") < source.index("v4_evidence_result = subprocess.run("), "central hook order")
    need(source.count('"decision=" + CURRENT_HOLD') == 1, "central current hold output")
    need(source.count('"next_step=" + CURRENT_NEXT_STEP') == 1, "central current next step output")


def validate_no_sensitive_material() -> None:
    combined = "\n".join(text(relative) for relative in (*PACKAGE_PATHS, CENTRAL))
    forbidden = {
        "provider or external URL": r"(?i)\bhttps?://",
        "database URI": r"(?i)\bpostgres(?:ql)?://",
        "raw provider resource identifier": r"(?i)\b(?:dpg|srv)-[a-z0-9]{6,}\b",
        "credential assignment": (
            r"(?i)\b(?:password|secret|database_url|access_token)\s*[:=]\s*"
            r"[^\s,}\]]+"
        ),
    }
    for label, pattern in forbidden.items():
        need(re.search(pattern, combined) is None, "forbidden " + label)
    cidrs = re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}(?![\d.])", combined)
    need(set(cidrs) <= {"0.0.0.0/0"}, "unexpected IP or CIDR material")


def main() -> int:
    for relative in PACKAGE_PATHS:
        safe_path(relative)
    validate_authorized_scope()
    validate_historical_anchors()
    validate_previous_v4_rebind()
    validate_document()
    validate_baseline()
    validate_pointer()
    validate_csvs()
    validate_manifest()
    validate_central_hook()
    validate_no_sensitive_material()
    for line in (
        PASS_MARKER,
        "stage_id=" + STAGE_ID,
        "work_bundle=" + WORK_BUNDLE,
        "base_commit=" + BASE_COMMIT,
        "base_tree_sha=" + BASE_TREE,
        "review_record_id=" + REVIEW_RECORD,
        "target_contract_identity_sha256=" + TARGET_CONTRACT_IDENTITY,
        "external_resource_binding_state=BOUND_SANITIZED_HASH_ONLY",
        "target_status=AVAILABLE",
        "target_creation_count=1",
        "final_service_inbound_ip_rule_set=[]",
        "final_public_external_access_blocked=true",
        "network_lockdown_persisted_after_refresh=true",
        "target_open_connection_count=0",
        "database_connection=false",
        "runner_import_or_execution=false",
        "restore_execution=false",
        "migration_creation_or_execution=false",
        "deployment=false",
        "target_deletion=false",
        "decision=" + DECISION,
        "sole_next_subject=" + NEXT_SUBJECT,
        "ALL PASS: PMAI-P0-04 V4 provisioning execution evidence repository package",
    ):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
