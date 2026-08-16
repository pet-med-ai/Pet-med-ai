#!/usr/bin/env python3
"""Validate PMAI-P0-04 Archive Root Contract Investigation V2 Execution Evidence V1."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1_TEST_MATRIX_V1.csv'
AUTHORIZATION_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_V1.md'
CANDIDATE = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V2_AUTHORIZED_CANDIDATE.py.txt'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_execution_evidence_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
AUTH_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
LEGACY_VALIDATORS = (
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_execution_evidence_v1.py',
)
FRESH_DECISION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_restore_governance_decision_v1.py'
V1_PREPARATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py'
V1_AUTHORIZATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_authorization_review_v1.py'
V1_EVIDENCE_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_execution_evidence_v1.py'
STRUCTURAL_DECISION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_structural_predicate_review_governance_decision_v1.py'
V2_PREPARATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_preparation_v1.py'
V2_AUTHORIZATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_authorization_review_v1.py'
ROLLING_VALIDATORS = (
    FRESH_DECISION_VALIDATOR,
    V1_PREPARATION_VALIDATOR,
    V1_AUTHORIZATION_VALIDATOR,
    V1_EVIDENCE_VALIDATOR,
    STRUCTURAL_DECISION_VALIDATOR,
    V2_PREPARATION_VALIDATOR,
    V2_AUTHORIZATION_VALIDATOR,
)
ROLLING_DOCS = (
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_V1.md',
    AUTHORIZATION_DOC,
)
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = '9f00393543ec435353d5deadc6c74972aed4f6c2'
EXPECTED_PARENT = 'abeec6d7f1f5a592fc1435b4a370bd6cffb3a4ce'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = '73d3665a7e7645f2fbd7acf043f76094cf1b05527a9500e1565a03b3ced1e0f2'
EXPECTED_FINAL_CI_SHA256 = '4b50f28b230853bd57a983a7034aff170e11531bd276964a8c4b93769803c80c'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_ARCHIVE_SHA256 = 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7'
EXPECTED_CANDIDATE_SHA256 = 'ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6'
EXPECTED_RESULT_SHA256 = '3eef22eeab17779b4e5499f53c22caf22fd5d0fd7c107cdaca6cbb8926ebf028'
EXPECTED_V1_RESULT_SHA256 = 'c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893'
AUTHORIZATION_RECORD_ID = 'PMAI-P0-04-ARCI-V2-AUTH-V1-20260812'
EVIDENCE_RECORD_ID = 'PMAI-P0-04-ARCI-V2-EXEC-EVID-V1-20260812'
CI_COMMAND = 'python3 ' + VALIDATOR + ' || exit 1'
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
PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
REQUIRED_PROTECTED_PATHS = PACKAGE_PATHS | {AUTHORIZATION_DOC, CANDIDATE}
HASH_EXTRA_PATHS = {
    'backend/models.py',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
    'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
    'render.yaml',
}
TRUE_MARKERS = (
    'investigation_execution_performed',
    'investigation_process_completed',
    'repository_clean_before_investigation',
    'repository_clean_after_investigation',
    'execution_authorization_was_present',
    'execution_authorization_consumed',
    'one_time_execution_confirmation_was_present',
    'approved_archive_sha256_match',
    'v1_leading_dot_predicate_coverage_gap_resolved_by_v2',
    'observed_archive_leading_dot_prefix_count_confirmed',
    'observed_archive_root_marker_count_confirmed',
    'observed_toc_dat_candidate_count_confirmed',
    'investigation_archive_file_opened',
    'investigation_backup_archive_listing_invoked',
    'investigation_backup_archive_member_headers_read',
    'repository_only',
    'schema_ok',
)
FALSE_MARKERS = (
    'automatic_retry',
    'manual_retry_authorized',
    'additional_archive_listing_attempt_authorized',
    'root_contract_resolved',
    'backup_restoreability_verified',
    'disposable_restore_rehearsal_complete',
    'current_v2_investigation_authorized',
    'current_v2_investigation_execution_authorized',
    'current_v2_archive_listing_attempt_authorized',
    'authorization_reuse_allowed',
    'v2_investigator_reexecution_allowed',
    'v3_investigator_creation_authorized',
    'v3_investigator_execution_authorized',
    'restore_runner_design_authorized',
    'logical_root_fingerprint_sha256_present',
    'all_members_contained_by_logical_root',
    'toc_dat_logical_depth_established',
    'mixed_top_level_layout_established',
    'deep_wrapper_layout_established',
    'backup_corruption_established',
    'backup_safety_established',
    'backup_restoreability_established',
    'v2_structural_predicate_mismatch_cause_resolved',
    'raw_member_name_followup_performed',
    'additional_metadata_scan_performed',
    'corrected_v3_predicate_selected',
    'new_governance_route_selected',
    'investigation_backup_archive_member_payload_read',
    'investigation_backup_archive_extracted',
    'investigation_backup_archive_copied',
    'investigation_backup_archive_uploaded',
    'investigation_backup_archive_modified',
    'investigation_backup_archive_repackaged',
    'investigation_raw_member_names_emitted',
    'investigation_raw_external_path_emitted',
    'investigation_network_access',
    'investigation_database_connection',
    'investigation_database_write',
    'investigation_restore_execution',
    'investigation_pg_restore_invoked',
    'investigation_psql_invoked',
    'investigation_alembic_invoked',
    'investigation_target_created',
    'investigation_runner_created',
    'investigation_runner_modified',
    'investigation_locked_runner_invoked',
    'investigation_migration_created',
    'investigation_migration_executed',
    'investigation_application_deployment',
    'investigation_resource_deleted',
    'network_access',
    'external_execution',
    'package_archive_file_opened',
    'package_backup_archive_listing_invoked',
    'package_backup_archive_member_headers_read',
    'package_backup_archive_member_payload_read',
    'package_backup_archive_extracted',
    'package_backup_archive_copied',
    'package_backup_archive_uploaded',
    'package_backup_archive_modified',
    'package_backup_archive_repackaged',
    'investigation_retry',
    'new_investigator_created',
    'new_investigator_activated',
    'new_investigator_executed',
    'database_connection',
    'database_write',
    'restore_execution',
    'pg_restore_invoked',
    'psql_invoked',
    'alembic_invoked',
    'migration_created',
    'migration_executed',
    'restore_runner_created',
    'restore_runner_modified',
    'locked_runner_invoked',
    'render_target_created',
    'render_target_deleted',
    'application_deployment',
    'resource_deleted',
    'repository_apply_authorized',
    'git_stage_authorized',
    'git_commit_authorized',
    'git_push_authorized',
    'p0_04_execution_authorized',
    'staging_0010_apply_authorized',
    'writes_database',
    'exposes_database_url',
    'production_auto_deploy_verified',
    'ENABLE_EMR_REAL_IMPORT',
    'ENABLE_EMR_IMPORT_CASE_UPDATE',
    'ENABLE_EMR_ATTACHMENT_DOWNLOAD',
    'ENABLE_PREVENTIVE_AUTO_DELIVERY',
    'ENABLE_PREVENTIVE_SMS_DELIVERY',
    'ENABLE_PREVENTIVE_WECHAT_DELIVERY',
    'ENABLE_PREVENTIVE_EMAIL_DELIVERY',
    'ENABLE_PRESCRIPTION_STRUCTURED_WRITE',
    'ENABLE_DEVICE_REAL_INGEST',
    'ENABLE_BILLING_REAL_WRITE',
)
REQUIRED_TEST_IDS = {
    'PMAI-P0-04-ARCI-V2-EXEC-EVID-T{:03d}'.format(number)
    for number in range(1, 41)
}


def need(ok: bool, message: str) -> None:
    if not ok:
        print('NO-GO: ' + message, file=sys.stderr)
        raise SystemExit(1)


def read_text(rel: str) -> str:
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), 'missing or unsafe ' + rel)
    return path.read_text(encoding='utf-8')


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def marker(value: str, key: str) -> str:
    found = re.findall(r'(?m)^' + re.escape(key) + r'=([^\r\n]+)$', value)
    need(len(found) == 1, 'marker count ' + key)
    return found[0]


def literal(source: str, name: str):
    found = []
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            found.append(ast.literal_eval(node.value))
    need(len(found) == 1, 'literal assignment ' + name)
    return found[0]


def read_csv(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def ci_targets(value: str) -> list[str]:
    block = re.search(r'(?ms)^TARGETS=\(\n(.*?)^\)\s*$', value)
    need(block is not None, 'CI TARGETS block')
    targets = re.findall(r'^\s*"([^"]+)"\s*$', block.group(1), flags=re.M)
    need(targets and len(targets) == len(set(targets)), 'CI TARGETS canonical')
    return targets


def python_lines(value: str) -> list[str]:
    return [
        line.strip()
        for line in value.splitlines()
        if line.strip().startswith('python3 ')
        and not line.strip().startswith('python3 -m py_compile ')
    ]


def main() -> int:
    doc = read_text(DOC)
    authorization_doc = read_text(AUTHORIZATION_DOC)
    ci = read_text(CI)
    root_source = read_text(ROOT_VALIDATOR)
    package_text = '\n'.join(read_text(rel) for rel in sorted(PACKAGE_PATHS))

    expected_markers = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1',
        'package_status': 'V2_EXECUTION_EVIDENCE_RECORD_ONLY',
        'evidence_status': 'COMPLETE_SINGLE_V2_METADATA_ATTEMPT_HOLD',
        'evidence_record_id': EVIDENCE_RECORD_ID,
        'investigation_exit_code': '0',
        'v1_archive_listing_attempts_consumed': '1',
        'v2_archive_listing_attempt_budget': '1',
        'v2_archive_listing_attempts_consumed': '1',
        'v2_archive_listing_attempts_remaining': '0',
        'cumulative_archive_listing_attempts_consumed': '2',
        'cumulative_archive_listing_attempts_remaining': '0',
        'decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'next_action': 'SEPARATE_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_REQUIRED_BEFORE_ANY_NEW_INVESTIGATION',
        'authorization_review_commit': EXPECTED_HEAD,
        'authorization_review_commit_parent': EXPECTED_PARENT,
        'local_main_at_evidence_entry': EXPECTED_HEAD,
        'origin_main_at_evidence_entry': EXPECTED_HEAD,
        'github_ci_gate_number': '199',
        'github_ci_gate_status': 'PASS',
        'github_ci_gate_commit': EXPECTED_HEAD,
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_FINAL_CI_SHA256,
        'local_isolated_branch': EXPECTED_ISOLATED,
        'remote_isolated_branch': EXPECTED_ISOLATED,
        'active_0010_migration_file_count': '0',
        'authorization_record_id': AUTHORIZATION_RECORD_ID,
        'authorization_scope': 'ONE_EXACT_ARCHIVE_ONE_V2_METADATA_ONLY_ATTEMPT',
        'v2_attempt_number': '1',
        'cumulative_archive_listing_attempt_number': '2',
        'approved_backup_sha256': EXPECTED_ARCHIVE_SHA256,
        'investigation_implementation_sha256': EXPECTED_CANDIDATE_SHA256,
        'listing_tool_identity': 'PYTHON_STDLIB_TARFILE_METADATA_SCAN',
        'listing_tool_version': '3.9.6',
        'outer_container_classification': 'GZIP_TAR',
        'sanitized_v2_investigation_result_sha256': EXPECTED_RESULT_SHA256,
        'sanitized_v2_result_field_count': '37',
        'prior_v1_sanitized_result_sha256': EXPECTED_V1_RESULT_SHA256,
        'archive_member_count': '29',
        'archive_uncompressed_size_bytes': '196874',
        'regular_file_count': '26',
        'directory_entry_count': '3',
        'unsafe_or_special_member_count': '0',
        'accepted_canonical_relative_count': '0',
        'accepted_leading_dot_prefix_count': '28',
        'accepted_root_marker_count': '1',
        'normalized_path_violation_count': '0',
        'duplicate_normalized_member_count': '0',
        'case_collision_count': '0',
        'leading_dot_prefix_member_count': '28',
        'root_marker_count': '1',
        'wrapper_depth': '-1',
        'toc_dat_candidate_count': '1',
        'toc_dat_relation_category': 'NONE_OR_AMBIGUOUS',
        'root_layout_classification': 'NONE_OR_AMBIGUOUS',
        'member_name_set_sha256': '3a509a2084dd279e644c95d83d77babe555f21de76950c1c092421952a75e229',
        'restore_input_kind_classification': 'AMBIGUOUS_OR_UNSUPPORTED',
        'stop_code': 'V2_STRUCTURAL_PREDICATE_MISMATCH',
    }
    for key, expected in expected_markers.items():
        need(marker(doc, key) == expected, 'document marker ' + key)
    for key in TRUE_MARKERS:
        need(marker(doc, key) == 'true', 'true marker ' + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == 'false', 'false marker ' + key)

    json_matches = re.findall(r'(?ms)^~~~json\n(\{.*?\})\n~~~$', doc)
    need(len(json_matches) == 1, 'sanitized JSON block count')
    json_line = json_matches[0]
    result = json.loads(json_line)
    canonical = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
    need(canonical == json_line, 'sanitized JSON canonical serialization')
    need(hashlib.sha256(json_line.encode('utf-8')).hexdigest() == EXPECTED_RESULT_SHA256, 'sanitized result hash')
    need(len(result) == 37, 'sanitized result field count')
    result_expected = {
        'all_members_contained_by_logical_root': False,
        'approved_archive_sha256_match': True,
        'archive_member_count': 29,
        'archive_modified': False,
        'archive_uncompressed_size_bytes': 196874,
        'authorization_record_id': AUTHORIZATION_RECORD_ID,
        'automatic_retry': False,
        'case_collision_count': 0,
        'cumulative_archive_listing_attempt_number': 2,
        'decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'directory_entry_count': 3,
        'duplicate_normalized_member_count': 0,
        'implementation_sha256': EXPECTED_CANDIDATE_SHA256,
        'leading_dot_prefix_member_count': 28,
        'listing_tool_identity': 'PYTHON_STDLIB_TARFILE_METADATA_SCAN',
        'listing_tool_version': '3.9.6',
        'logical_root_fingerprint_sha256': '',
        'member_extraction_performed': False,
        'member_name_set_sha256': '3a509a2084dd279e644c95d83d77babe555f21de76950c1c092421952a75e229',
        'member_payload_read': False,
        'normalized_path_violation_count': 0,
        'outer_container_classification': 'GZIP_TAR',
        'raw_external_path_emitted': False,
        'raw_member_names_emitted': False,
        'regular_file_count': 26,
        'restore_execution': False,
        'restore_input_kind_classification': 'AMBIGUOUS_OR_UNSUPPORTED',
        'root_contract_resolved': False,
        'root_layout_classification': 'NONE_OR_AMBIGUOUS',
        'root_marker_count': 1,
        'stop_code': 'V2_STRUCTURAL_PREDICATE_MISMATCH',
        'toc_dat_candidate_count': 1,
        'toc_dat_relation_category': 'NONE_OR_AMBIGUOUS',
        'unsafe_or_special_member_count': 0,
        'v2_attempt_number': 1,
        'wrapper_depth': -1,
    }
    for key, expected in result_expected.items():
        need(result.get(key) == expected, 'sanitized result field ' + key)
    reason_expected = {
        'ACCEPTED_CANONICAL_RELATIVE': 0,
        'ACCEPTED_LEADING_DOT_PREFIX': 28,
        'ACCEPTED_ROOT_MARKER': 1,
        'REJECT_ABSOLUTE_PATH': 0,
        'REJECT_BACKSLASH': 0,
        'REJECT_CONTROL_CHARACTER': 0,
        'REJECT_DRIVE_PREFIX': 0,
        'REJECT_EMPTY_COMPONENT': 0,
        'REJECT_EMPTY_PATH': 0,
        'REJECT_INTERNAL_DOT_COMPONENT': 0,
        'REJECT_PARENT_COMPONENT': 0,
        'REJECT_ROOT_MARKER_NON_DIRECTORY': 0,
    }
    need(result.get('normalization_reason_counts') == reason_expected, 'normalization reason counts')

    forbidden_patterns = (
        re.escape('/' + 'Users/'),
        'postgres' + r'(?:ql)?://',
        r'(?m)^' + 'DATABASE' + r'_URL=',
        r'(?m)^raw_' + r'member_name=',
        r'(?m)^archive_' + r'external_path=',
    )
    for pattern in forbidden_patterns:
        need(re.search(pattern, package_text) is None, 'forbidden secret path or identifier')

    checklist = read_csv(CHECKLIST)
    need(len(checklist) == 72, 'checklist row count')
    by_control = {row.get('control', ''): row for row in checklist}
    need(len(by_control) == len(checklist), 'checklist unique controls')
    checklist_expected = {
        'v2_archive_listing_attempts_consumed': '1',
        'cumulative_archive_listing_attempts_consumed': '2',
        'v2_archive_listing_attempts_remaining': '0',
        'approved_archive_sha256_match': 'true',
        'accepted_leading_dot_prefix_count': '28',
        'normalized_path_violation_count': '0',
        'toc_dat_candidate_count': '1',
        'toc_dat_relation_category': 'NONE_OR_AMBIGUOUS',
        'root_layout_classification': 'NONE_OR_AMBIGUOUS',
        'root_contract_resolved': 'false',
        'stop_code': 'V2_STRUCTURAL_PREDICATE_MISMATCH',
        'decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'investigation_member_payload_read': 'false',
        'package_archive_file_opened': 'false',
        'new_investigator_created': 'false',
        'database_connection': 'false',
        'restore_execution': 'false',
        'staging_0010_apply_authorized': 'false',
    }
    for control, expected in checklist_expected.items():
        row = by_control.get(control)
        need(row is not None and row.get('expected') == expected and row.get('current') == expected, 'checklist control ' + control)
        need(row.get('status') == 'PASS', 'checklist status ' + control)

    decisions = read_csv(GO_NO_GO)
    need(len(decisions) == 25, 'Go/No-Go row count')
    by_gate = {row.get('gate', ''): row for row in decisions}
    need(len(by_gate) == len(decisions), 'Go/No-Go unique gates')
    need(by_gate['normalized path violations required for success']['status'] == 'PASS', 'Go/No-Go normalization pass')
    need(by_gate['toc relation required for success']['status'] == 'HOLD', 'Go/No-Go toc relation hold')
    need(by_gate['root contract resolved required for runner design']['status'] == 'HOLD', 'Go/No-Go root hold')
    need(by_gate['execution evidence disposition']['current'] == 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED', 'Go/No-Go disposition')

    tests = read_csv(TEST_MATRIX)
    need({row.get('test_id', '') for row in tests} == REQUIRED_TEST_IDS, 'test matrix exact IDs')

    need(sha256_path(ROOT / CANDIDATE) == EXPECTED_CANDIDATE_SHA256, 'candidate hash changed')
    need(CANDIDATE not in '\n'.join(python_lines(ci)), 'candidate executed by CI')
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, 'final CI hash')
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, 'locked runner hash')
    need(not glob.glob(str(ROOT / 'backend/migrations/versions/0010*.py')), 'active 0010 migration')

    targets = literal(root_source, 'TARGETS')
    hashes = literal(root_source, 'HASHES')
    need(isinstance(targets, list) and len(targets) == 137 and len(targets) == len(set(targets)), 'root TARGETS')
    need(isinstance(hashes, dict), 'root HASHES')
    need(REQUIRED_PROTECTED_PATHS.issubset(set(targets)), 'evidence package protection')
    need(set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS, 'protected hash scope')
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), 'missing protected ' + rel)
        need(sha256_path(path) == expected_hash, 'protected hash ' + rel)

    need(ci_targets(ci) == targets, 'CI/root target equality')
    need(python_lines(ci) == EXPECTED_COMMANDS, 'CI approved validators')
    marker_line = '# PMAI-P0-04 archive root contract investigation V2 execution evidence v1'
    need(ci.splitlines().count(marker_line) == 1, 'CI marker count')
    need(ci.splitlines().count(CI_COMMAND) == 1, 'CI command count')

    prep_source = read_text(AUTH_PREP_VALIDATOR)
    need(literal(prep_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'auth-prep CI rollover')
    for rel in LEGACY_VALIDATORS:
        source = read_text(rel)
        need(literal(source, 'EXPECTED_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'legacy CI rollover ' + rel)
        need(literal(source, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'legacy command rollover ' + rel)
    for rel in ROLLING_VALIDATORS:
        source = read_text(rel)
        need(literal(source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'rolling CI rollover ' + rel)
        need(literal(source, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'rolling command rollover ' + rel)
    for rel in ROLLING_DOCS:
        need(marker(read_text(rel), 'final_ci_sha256') == EXPECTED_FINAL_CI_SHA256, 'rolling document CI hash ' + rel)

    auth_pointer = {
        'subsequent_v2_execution_evidence_entry_commit': EXPECTED_HEAD,
        'subsequent_v2_execution_evidence_ci_gate': '199',
        'subsequent_v2_execution_evidence_ci_status': 'PASS',
        'subsequent_v2_execution_implementation_sha256': EXPECTED_CANDIDATE_SHA256,
        'subsequent_v2_sanitized_result_sha256': EXPECTED_RESULT_SHA256,
        'subsequent_v2_archive_listing_attempts_consumed': '1',
        'subsequent_cumulative_archive_listing_attempts_consumed': '2',
        'subsequent_archive_listing_attempts_remaining': '0',
        'subsequent_v2_root_contract_resolved': 'false',
        'subsequent_v2_stop_code': 'V2_STRUCTURAL_PREDICATE_MISMATCH',
        'subsequent_v2_decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'subsequent_v2_retry_authorized': 'false',
    }
    for key, expected in auth_pointer.items():
        need(marker(authorization_doc, key) == expected, 'authorization pointer ' + key)
    need(marker(authorization_doc, 'v2_attempts_consumed') == '0', 'authorization point-in-time consumption changed')
    need(marker(authorization_doc, 'current_v2_investigation_authorized') == 'false', 'authorization point-in-time authority changed')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db', '.bak', '.save')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    need(CANDIDATE not in PACKAGE_PATHS, 'candidate included as package write')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Archive Root Contract Investigation V2 Execution Evidence V1')
    print('stage_id=PMAI-P0-04')
    print('substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1')
    print('evidence_status=COMPLETE_SINGLE_V2_METADATA_ATTEMPT_HOLD')
    print('investigation_execution_performed=true')
    print('investigation_exit_code=0')
    print('v2_archive_listing_attempts_consumed=1')
    print('v2_archive_listing_attempts_remaining=0')
    print('cumulative_archive_listing_attempts_consumed=2')
    print('automatic_retry=false')
    print('approved_archive_sha256_match=true')
    print('accepted_leading_dot_prefix_count=28')
    print('normalized_path_violation_count=0')
    print('toc_dat_candidate_count=1')
    print('toc_dat_relation_category=NONE_OR_AMBIGUOUS')
    print('root_layout_classification=NONE_OR_AMBIGUOUS')
    print('root_contract_resolved=false')
    print('member_payload_read=false')
    print('member_extraction_performed=false')
    print('backup_restoreability_verified=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED')
    print('next_action=SEPARATE_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_REQUIRED_BEFORE_ANY_NEW_INVESTIGATION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
