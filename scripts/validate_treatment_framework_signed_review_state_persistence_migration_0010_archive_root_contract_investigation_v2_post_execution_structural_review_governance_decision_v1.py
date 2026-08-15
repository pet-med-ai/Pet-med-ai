#!/usr/bin/env python3
"""Validate the PMAI-P0-04 V2 post-execution structural review decision."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1_TEST_MATRIX_V1.csv'
EVIDENCE_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1.md'
IMPLEMENTATION = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V2_AUTHORIZED_CANDIDATE.py.txt'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_post_execution_structural_review_governance_decision_v1.py'
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
V1_STRUCTURAL_DECISION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_structural_predicate_review_governance_decision_v1.py'
V2_PREPARATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_preparation_v1.py'
V2_AUTHORIZATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_authorization_review_v1.py'
V2_EVIDENCE_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_execution_evidence_v1.py'
ROLLING_VALIDATORS = (
    FRESH_DECISION_VALIDATOR,
    V1_PREPARATION_VALIDATOR,
    V1_AUTHORIZATION_VALIDATOR,
    V1_EVIDENCE_VALIDATOR,
    V1_STRUCTURAL_DECISION_VALIDATOR,
    V2_PREPARATION_VALIDATOR,
    V2_AUTHORIZATION_VALIDATOR,
    V2_EVIDENCE_VALIDATOR,
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
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_V1.md',
    EVIDENCE_DOC,
)
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = 'da837e6eb35819457b340d9fe9fd3a4336dc6673'
EXPECTED_PARENT = '9f00393543ec435353d5deadc6c74972aed4f6c2'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = '7cba5137d959d9f37a5e4f7a70798ff5090fc130ead6ce9d124c457c9a682811'
EXPECTED_FINAL_CI_SHA256 = 'e283cc5aa77f73d9fe79b1139411897b677daf8ebe71eb70212ae82edb07b31d'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_IMPLEMENTATION_SHA256 = 'ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6'
EXPECTED_V1_RESULT_SHA256 = 'c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893'
EXPECTED_V2_RESULT_SHA256 = '3eef22eeab17779b4e5499f53c22caf22fd5d0fd7c107cdaca6cbb8926ebf028'
DECISION_RECORD_ID = 'PMAI-P0-04-V2-POST-SPR-GOV-DEC-V1-20260812'
PRIOR_ROUTE = 'ROUTE_B_REBUILD_CORRECTED_METADATA_INVESTIGATION_CHAIN_V2'
SELECTED_ROUTE = 'ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3'
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
 '|| exit 1']
PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
REQUIRED_PROTECTED_PATHS = PACKAGE_PATHS | {EVIDENCE_DOC, IMPLEMENTATION}
HASH_EXTRA_PATHS = {
    'backend/models.py',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
    'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
    'render.yaml',
}
TRUE_MARKERS = (
    'repository_only',
    'investigation_execution_performed',
    'approved_archive_sha256_match',
    'toc_dat_presence_established',
    'v2_static_source_review_performed',
    'v2_normalization_coverage_gap_resolved',
    'v2_optional_leading_dot_prefix_policy_present',
    'v2_explicit_root_marker_policy_present',
    'v2_unwrapped_root_classification_present',
    'v2_single_wrapper_classification_present',
    'v2_structural_observability_gap_confirmed',
    'v3_require_exactly_one_optional_leading_dot_prefix_policy',
    'v3_require_explicit_root_marker_policy',
    'v3_require_internal_dot_component_rejection',
    'v3_require_parent_component_rejection',
    'v3_require_absolute_path_rejection',
    'v3_require_backslash_rejection',
    'v3_require_control_character_rejection',
    'v3_require_empty_component_rejection',
    'v3_require_drive_prefix_rejection',
    'v3_require_special_member_rejection',
    'v3_require_toc_dat_normalized_depth_metric',
    'v3_require_shared_prefix_depth_metric',
    'v3_require_top_level_component_count_metric',
    'v3_require_member_depth_min_max_metrics',
    'v3_require_unwrapped_root_classification',
    'v3_require_single_wrapper_classification',
    'v3_require_deep_wrapper_classification',
    'v3_require_mixed_top_level_classification',
    'v3_require_toc_dat_at_logical_root',
    'v3_require_bounded_numeric_outputs',
    'v3_require_sanitized_enum_outputs',
    'v3_require_raw_member_names_suppressed',
    'v3_require_raw_external_path_suppressed',
    'v3_require_member_payload_read_false',
    'v3_require_extraction_false',
    'v3_require_archive_write_false',
    'v3_require_automatic_retry_false',
    'v3_require_synthetic_depth_zero_fixture',
    'v3_require_synthetic_depth_one_fixture',
    'v3_require_synthetic_deep_wrapper_fixture',
    'v3_require_synthetic_mixed_top_level_fixture',
    'v3_require_separate_implementation_hash_review',
    'v3_require_separate_one_time_execution_authorization',
    'v3_require_explicit_single_attempt_budget',
    'v3_predicate_requirements_selected',
)
FALSE_MARKERS = (
    'root_contract_resolved',
    'v2_investigator_executed_during_review',
    'v2_deep_wrapper_classification_present',
    'v2_mixed_top_level_classification_present',
    'v2_toc_normalized_depth_emitted',
    'v2_shared_prefix_depth_emitted',
    'v2_top_level_component_count_emitted',
    'v2_member_depth_range_emitted',
    'aggregate_result_causal_attribution_possible',
    'toc_dat_at_logical_root_established',
    'actual_archive_layout_cause_resolved',
    'backup_corruption_established',
    'backup_safety_established',
    'backup_restoreability_established',
    'v2_structural_predicate_mismatch_cause_resolved',
    'v3_predicate_implementation_selected',
    'network_access',
    'external_execution',
    'archive_file_opened',
    'backup_archive_listing_invoked',
    'backup_archive_member_headers_read',
    'backup_archive_member_payload_read',
    'backup_archive_extracted',
    'backup_archive_copied',
    'backup_archive_uploaded',
    'backup_archive_modified',
    'backup_archive_repackaged',
    'investigation_retry',
    'automatic_retry',
    'manual_retry_authorized',
    'additional_archive_listing_attempt_authorized',
    'authorization_reuse_allowed',
    'new_investigator_created',
    'new_investigator_activated',
    'new_investigator_executed',
    'investigator_v3_creation_authorized',
    'investigator_v3_activation_authorized',
    'investigator_v3_execution_authorized',
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
    'PMAI-P0-04-V2-POST-SPR-GOV-T{:03d}'.format(number)
    for number in range(1, 56)
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


def function_source(source: str, name: str) -> str:
    nodes = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    need(len(nodes) == 1, 'function count ' + name)
    value = ast.get_source_segment(source, nodes[0])
    need(value is not None, 'function source ' + name)
    return value


def main() -> int:
    doc = read_text(DOC)
    evidence_doc = read_text(EVIDENCE_DOC)
    implementation = read_text(IMPLEMENTATION)
    package_text = '\n'.join(
        read_text(rel)
        for rel in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX)
    )
    ci = read_text(CI)
    root_source = read_text(ROOT_VALIDATOR)

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1',
        'package_status': 'GOVERNANCE_DECISION_ONLY',
        'decision_record_id': DECISION_RECORD_ID,
        'current_substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1',
        'proposed_substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1',
        'prior_route': PRIOR_ROUTE,
        'selected_route': SELECTED_ROUTE,
        'selected_route_status': 'APPROVED_GOVERNANCE_ONLY',
        'decision': 'GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION',
        'next_action': 'SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION_REQUIRED',
        'evidence_commit': EXPECTED_HEAD,
        'evidence_commit_parent': EXPECTED_PARENT,
        'local_main_at_decision_entry': EXPECTED_HEAD,
        'origin_main_at_decision_entry': EXPECTED_HEAD,
        'github_ci_gate_number': '200',
        'github_ci_gate_status': 'PASS',
        'github_ci_gate_commit': EXPECTED_HEAD,
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_FINAL_CI_SHA256,
        'local_isolated_branch': EXPECTED_ISOLATED,
        'remote_isolated_branch': EXPECTED_ISOLATED,
        'locked_runner_sha256': EXPECTED_LOCKED_RUNNER_SHA256,
        'authorized_investigator_v2_sha256': EXPECTED_IMPLEMENTATION_SHA256,
        'sanitized_v1_investigation_result_sha256': EXPECTED_V1_RESULT_SHA256,
        'sanitized_v2_investigation_result_sha256': EXPECTED_V2_RESULT_SHA256,
        'active_0010_migration_file_count': '0',
        'user_direction_source': 'EXPLICIT_USER_AUTHORIZATION_TO_CONTINUE_FOLLOWUP_GOVERNANCE_20260812',
        'investigation_exit_code': '0',
        'v1_archive_listing_attempts_consumed': '1',
        'v2_archive_listing_attempt_budget': '1',
        'v2_archive_listing_attempts_consumed': '1',
        'v2_archive_listing_attempts_remaining': '0',
        'cumulative_archive_listing_attempts_consumed': '2',
        'cumulative_archive_listing_attempts_remaining': '0',
        'archive_member_count': '29',
        'accepted_leading_dot_prefix_count': '28',
        'accepted_root_marker_count': '1',
        'normalized_path_violation_count': '0',
        'toc_dat_candidate_count': '1',
        'toc_dat_relation_category': 'NONE_OR_AMBIGUOUS',
        'root_layout_classification': 'NONE_OR_AMBIGUOUS',
        'wrapper_depth': '-1',
        'stop_code': 'V2_STRUCTURAL_PREDICATE_MISMATCH',
        'evidence_decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'deep_wrapper_layout_hypothesis_status': 'PLAUSIBLE_BUT_UNVERIFIED',
        'mixed_top_level_layout_hypothesis_status': 'PLAUSIBLE_BUT_UNVERIFIED',
        'route_a': 'ROUTE_A_DECLARE_BACKUP_INVALID_OR_REPLACE',
        'route_a_status': 'REJECTED_AT_THIS_GATE',
        'route_b': 'ROUTE_B_DIRECT_RUNNER_OR_RESTORE',
        'route_b_status': 'REJECTED',
        'route_c': SELECTED_ROUTE,
        'route_c_status': 'APPROVED_GOVERNANCE_ONLY',
        'route_d': 'ROUTE_D_REUSE_OR_RERUN_V2',
        'route_d_status': 'REJECTED',
        'database_revision': '0009_diag_data',
        'alembic_head': '0009_diag_data',
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, 'document marker ' + key)
    for key in TRUE_MARKERS:
        need(marker(doc, key) == 'true', 'required true marker ' + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == 'false', 'required false marker ' + key)

    need(sha256_path(ROOT / IMPLEMENTATION) == EXPECTED_IMPLEMENTATION_SHA256, 'V2 source hash changed')
    need(IMPLEMENTATION not in '\n'.join(python_lines(ci)), 'V2 source executed by CI')
    ast.parse(implementation)
    normalize_source = function_source(implementation, 'normalize_member')
    structural_source = function_source(implementation, 'structural_result')
    need('parts == ["."]' in normalize_source, 'V2 root marker policy')
    need('leading_dot_prefix = bool(parts and parts[0] == ".")' in normalize_source, 'V2 leading dot policy')
    need('parts = parts[1:]' in normalize_source, 'V2 leading dot removal')
    need('any(part == ".." for part in parts)' in normalize_source, 'V2 parent rejection')
    need('any(part == "." for part in parts)' in normalize_source, 'V2 internal dot rejection')
    need('parts[-1] == "toc.dat"' in structural_source, 'V2 toc candidate rule')
    need('toc_candidates[0] == ("toc.dat",)' in structural_source, 'V2 unwrapped rule')
    need('len(toc_candidates[0]) == 2' in structural_source, 'V2 single wrapper rule')
    need('PG_DIRECTORY_ROOT_UNWRAPPED' in structural_source, 'V2 unwrapped classification')
    need('PG_DIRECTORY_ROOT_WRAPPED' in structural_source, 'V2 wrapper classification')
    missing_v2_outputs = (
        'toc_dat_normalized_depth',
        'shared_prefix_depth',
        'top_level_component_count',
        'member_depth_min',
        'member_depth_max',
        'PG_DIRECTORY_ROOT_DEEP_WRAPPED',
        'MIXED_TOP_LEVEL',
    )
    for token in missing_v2_outputs:
        need(token not in structural_source, 'unexpected V2 depth-aware output ' + token)

    forbidden_patterns = (
        r'(?i)postgres(?:ql)?://\S+',
        r'(?im)^\s*(?:export\s+)?DATABASE_URL\s*=',
        r'(?im)^\s*(?:export\s+)?SECRET_KEY\s*=',
        r'(?im)^\s*(?:password|passwd|pwd)\s*[:=]',
        r'(?i)\bdpg-[a-z0-9-]+\b',
        r'(?i)(?:/Users/|~/Pet-med-ai-p0-04-)',
    )
    for pattern in forbidden_patterns:
        need(re.search(pattern, package_text) is None, 'forbidden secret path or identifier')

    checklist = read_csv(CHECKLIST)
    need(len(checklist) == 84, 'checklist row count')
    by_control = {row.get('control', ''): row for row in checklist}
    need(len(by_control) == len(checklist), 'checklist unique controls')
    checklist_expected = {
        'v2_archive_listing_attempts_consumed': '1',
        'v2_archive_listing_attempts_remaining': '0',
        'cumulative_archive_listing_attempts_consumed': '2',
        'root_contract_resolved': 'false',
        'v2_structural_observability_gap_confirmed': 'true',
        'toc_dat_at_logical_root_established': 'false',
        'backup_corruption_established': 'false',
        'route_c_status': 'APPROVED_GOVERNANCE_ONLY',
        'selected_route': SELECTED_ROUTE,
        'v3_predicate_implementation_selected': 'false',
        'new_investigator_created': 'false',
        'restore_execution': 'false',
        'next_action': 'SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION_REQUIRED',
    }
    for control, expected in checklist_expected.items():
        row = by_control.get(control)
        need(row is not None, 'checklist control ' + control)
        need(row.get('expected') == expected and row.get('current') == expected, 'checklist value ' + control)
        need(row.get('status') == 'PASS', 'checklist status ' + control)

    decisions = read_csv(GO_NO_GO)
    need(len(decisions) == 28, 'Go/No-Go row count')
    by_gate = {row.get('gate', ''): row for row in decisions}
    need(len(by_gate) == len(decisions), 'Go/No-Go unique gates')
    need(by_gate['Route C depth aware V3 chain']['current'] == 'APPROVED_GOVERNANCE_ONLY', 'Route C decision')
    need(by_gate['Route B direct runner restore']['current'] == 'REJECTED', 'Route B decision')
    need(by_gate['archive access authorization']['current'] == 'false', 'archive authority')
    need(
        by_gate['decision disposition']['current']
        == 'GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION',
        'decision disposition',
    )

    tests = read_csv(TEST_MATRIX)
    need({row.get('test_id', '') for row in tests} == REQUIRED_TEST_IDS, 'test matrix exact IDs')
    need(all(row.get('status') == 'DESIGNED' for row in tests), 'test matrix status')

    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, 'final CI hash')
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, 'locked runner hash')
    need(not glob.glob(str(ROOT / 'backend/migrations/versions/0010*.py')), 'active 0010 migration')

    targets = literal(root_source, 'TARGETS')
    hashes = literal(root_source, 'HASHES')
    need(isinstance(targets, list) and len(targets) == len(set(targets)), 'root TARGETS')
    need(isinstance(hashes, dict), 'root HASHES')
    need(REQUIRED_PROTECTED_PATHS.issubset(set(targets)), 'decision package protection')
    need(set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS, 'protected hash scope')
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), 'missing protected ' + rel)
        need(sha256_path(path) == expected_hash, 'protected hash ' + rel)

    need(ci_targets(ci) == targets, 'CI/root target equality')
    need(python_lines(ci) == EXPECTED_COMMANDS, 'CI approved validators')
    marker_line = '# PMAI-P0-04 V2 post-execution structural review governance decision v1'
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

    evidence_pointer = {
        'subsequent_v2_post_execution_structural_review_entry_commit': EXPECTED_HEAD,
        'subsequent_v2_post_execution_structural_review_ci_gate': '200',
        'subsequent_v2_post_execution_structural_review_ci_status': 'PASS',
        'subsequent_v2_post_execution_structural_review_selected_route': SELECTED_ROUTE,
        'subsequent_v3_investigation_authorized': 'false',
    }
    for key, expected in evidence_pointer.items():
        need(marker(evidence_doc, key) == expected, 'evidence pointer ' + key)
    need(marker(evidence_doc, 'v2_archive_listing_attempts_consumed') == '1', 'V2 attempt count changed')
    need(marker(evidence_doc, 'root_contract_resolved') == 'false', 'V2 result changed')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db', '.bak', '.save')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Archive Root Contract Investigation V2 Post-Execution Structural Review Governance Decision V1')
    print('stage_id=PMAI-P0-04')
    print('substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1')
    print('package_status=GOVERNANCE_DECISION_ONLY')
    print('v2_structural_observability_gap_confirmed=true')
    print('toc_dat_presence_established=true')
    print('actual_archive_layout_cause_resolved=false')
    print('backup_corruption_established=false')
    print('v2_archive_listing_attempts_consumed=1')
    print('cumulative_archive_listing_attempts_consumed=2')
    print('additional_archive_listing_attempts_remaining=0')
    print('root_contract_resolved=false')
    print('selected_route=' + SELECTED_ROUTE)
    print('new_investigator_created=false')
    print('new_investigation_authorized=false')
    print('restore_execution=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
