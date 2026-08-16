#!/usr/bin/env python3
"""Validate PMAI-P0-04 Structural Predicate Review Governance Decision V1."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1_TEST_MATRIX_V1.csv'
EVIDENCE_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1.md'
IMPLEMENTATION = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V1.py.txt'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_structural_predicate_review_governance_decision_v1.py'
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
PREPARATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py'
AUTHORIZATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_authorization_review_v1.py'
EVIDENCE_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_execution_evidence_v1.py'
ROLLING_VALIDATORS = (
    FRESH_DECISION_VALIDATOR,
    PREPARATION_VALIDATOR,
    AUTHORIZATION_VALIDATOR,
    EVIDENCE_VALIDATOR,
)
ROLLING_DOCS = (
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1.md',
    EVIDENCE_DOC,
)
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = '992976b033f115f6872e53f9144c56387c4c4ecf'
EXPECTED_PARENT = '7e5e4008ed3613b566aebcf1fc0d12e527ac816c'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = '80bd7f4e5186a33c3420fe4804a636c90e954d2d9349330803d0bb90bebc0870'
EXPECTED_FINAL_CI_SHA256 = '2aa57fb16b2513954b8ab8f9f86646a3d961174576ea6aa3539e683636620b6c'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_IMPLEMENTATION_SHA256 = '2b99a7446fbd5509e22c9fa5f6cb18eca920711208aa37fb4af568fd21f6faab'
EXPECTED_RESULT_SHA256 = 'c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893'
DECISION_RECORD_ID = 'PMAI-P0-04-SPR-GOV-DEC-V1-20260812'
SELECTED_ROUTE = 'ROUTE_B_REBUILD_CORRECTED_METADATA_INVESTIGATION_CHAIN_V2'
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
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_creation_and_activation_preparation_v1.py '
 '|| exit 1',
 'python3 '
 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_creation_and_activation_authorization_review_v1.py '
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
    'v1_static_source_review_performed',
    'v1_predicate_coverage_gap_confirmed',
    'v1_rejects_any_dot_component',
    'v1_rejects_parent_component',
    'v1_requires_single_common_wrapper_root',
    'v1_requires_toc_dat_under_wrapper',
    'v2_require_exactly_one_optional_leading_dot_prefix_policy',
    'v2_require_explicit_root_marker_policy',
    'v2_require_internal_dot_component_rejection',
    'v2_require_parent_component_rejection',
    'v2_require_absolute_path_rejection',
    'v2_require_backslash_rejection',
    'v2_require_control_character_rejection',
    'v2_require_empty_component_rejection',
    'v2_require_drive_prefix_rejection',
    'v2_require_special_member_rejection',
    'v2_require_wrapped_root_classification',
    'v2_require_unwrapped_root_classification',
    'v2_require_toc_dat_at_logical_root',
    'v2_require_sanitized_reason_counters',
    'v2_require_raw_member_names_suppressed',
    'v2_require_raw_external_path_suppressed',
    'v2_require_member_payload_read_false',
    'v2_require_extraction_false',
    'v2_require_archive_write_false',
    'v2_require_automatic_retry_false',
    'v2_require_synthetic_fixture_validation',
    'v2_require_separate_implementation_hash_review',
    'v2_require_separate_one_time_execution_authorization',
    'corrected_predicate_requirements_selected',
)
FALSE_MARKERS = (
    'root_contract_resolved',
    'v1_investigator_executed_during_review',
    'v1_single_leading_dot_prefix_normalization_present',
    'v1_unwrapped_pg_directory_root_classification_present',
    'v1_sanitized_rejection_reason_counters_present',
    'aggregate_result_causal_attribution_possible',
    'observed_archive_leading_dot_prefix_confirmed',
    'observed_archive_unwrapped_pg_directory_root_confirmed',
    'toc_dat_absence_established',
    'backup_corruption_established',
    'backup_safety_established',
    'backup_restoreability_established',
    'structural_predicate_mismatch_cause_resolved',
    'corrected_predicate_implementation_selected',
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
    'new_investigator_executed',
    'investigator_v2_creation_authorized',
    'investigator_v2_execution_authorized',
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
    'PMAI-P0-04-SPR-GOV-T{:03d}'.format(number)
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


def function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    need(len(nodes) == 1, 'function count ' + name)
    value = ast.get_source_segment(source, nodes[0])
    need(value is not None, 'function source ' + name)
    return value


def v1_reference_normalized_parts(raw: str, is_directory: bool = False):
    if is_directory and raw.endswith('/'):
        raw = raw[:-1]
    if not raw or raw.startswith('/') or '\\' in raw:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        return None
    parts = tuple(raw.split('/'))
    if any(not part or part in {'.', '..'} for part in parts):
        return None
    if len(parts[0]) >= 2 and parts[0][1] == ':':
        return None
    return parts


def main() -> int:
    doc = read_text(DOC)
    evidence_doc = read_text(EVIDENCE_DOC)
    implementation = read_text(IMPLEMENTATION)
    package_text = '\n'.join(read_text(path) for path in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX))
    ci = read_text(CI)
    root_source = read_text(ROOT_VALIDATOR)

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1',
        'package_status': 'GOVERNANCE_DECISION_ONLY',
        'decision_record_id': DECISION_RECORD_ID,
        'current_substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1',
        'proposed_substage': 'STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1',
        'selected_route': SELECTED_ROUTE,
        'selected_route_status': 'APPROVED_GOVERNANCE_ONLY',
        'decision': 'GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION',
        'next_action': 'SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_REQUIRED',
        'evidence_commit': EXPECTED_HEAD,
        'evidence_commit_parent': EXPECTED_PARENT,
        'local_main_at_decision_entry': EXPECTED_HEAD,
        'origin_main_at_decision_entry': EXPECTED_HEAD,
        'github_ci_gate_number': '196',
        'github_ci_gate_status': 'PASS',
        'github_ci_gate_commit': EXPECTED_HEAD,
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_FINAL_CI_SHA256,
        'local_isolated_branch': EXPECTED_ISOLATED,
        'remote_isolated_branch': EXPECTED_ISOLATED,
        'locked_runner_sha256': EXPECTED_LOCKED_RUNNER_SHA256,
        'inert_investigator_v1_sha256': EXPECTED_IMPLEMENTATION_SHA256,
        'sanitized_investigation_result_sha256': EXPECTED_RESULT_SHA256,
        'active_0010_migration_file_count': '0',
        'user_direction_source': 'EXPLICIT_USER_AUTHORIZATION_IN_CURRENT_CONVERSATION_20260812',
        'investigation_exit_code': '0',
        'archive_listing_attempt_budget': '1',
        'archive_listing_attempts_consumed': '1',
        'archive_listing_attempts_remaining': '0',
        'archive_member_count': '29',
        'normalized_path_violation_count': '29',
        'top_level_component_count': '0',
        'toc_dat_candidate_count': '0',
        'stop_code': 'STRUCTURAL_PREDICATE_MISMATCH',
        'evidence_decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'leading_dot_prefix_hypothesis_status': 'PLAUSIBLE_BUT_UNVERIFIED',
        'unwrapped_pg_directory_root_hypothesis_status': 'PLAUSIBLE_BUT_UNVERIFIED',
        'route_a': 'ROUTE_A_STOP_AND_REPLACE_APPROVED_BACKUP',
        'route_a_status': 'REJECTED_AT_THIS_GATE',
        'route_b': SELECTED_ROUTE,
        'route_b_status': 'APPROVED_GOVERNANCE_ONLY',
        'route_c': 'ROUTE_C_DIRECT_RUNNER_OR_RESTORE',
        'route_c_status': 'REJECTED',
        'route_d': 'ROUTE_D_REUSE_V1_AUTHORIZATION_OR_RETRY',
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

    need(sha256_path(ROOT / IMPLEMENTATION) == EXPECTED_IMPLEMENTATION_SHA256, 'V1 investigator hash changed')
    need(IMPLEMENTATION not in '\n'.join(python_lines(ci)), 'V1 investigator executed by CI')
    normalized_source = function_source(implementation, 'normalized_parts')
    structural_source = function_source(implementation, 'structural_result')
    need('parts = tuple(raw.split("/"))' in normalized_source, 'V1 split rule')
    need('part in {".", ".."}' in normalized_source, 'V1 dot rejection rule')
    need('raw.startswith("/")' in normalized_source, 'V1 absolute path rejection')
    need('"\\\\" in raw' in normalized_source, 'V1 backslash rejection')
    need('lstrip' not in normalized_source and 'normpath' not in normalized_source, 'V1 unexpected canonicalization')
    need('len(top_level_components) == 1' in structural_source, 'V1 wrapper requirement')
    need('toc_candidates[0] == (common_root, "toc.dat")' in structural_source, 'V1 toc relation requirement')

    need(v1_reference_normalized_parts('root/toc.dat') == ('root', 'toc.dat'), 'synthetic wrapped path')
    need(v1_reference_normalized_parts('./toc.dat') is None, 'synthetic leading dot root path')
    need(v1_reference_normalized_parts('./root/toc.dat') is None, 'synthetic leading dot wrapped path')
    need(v1_reference_normalized_parts('root/./toc.dat') is None, 'synthetic internal dot path')
    need(v1_reference_normalized_parts('../toc.dat') is None, 'synthetic parent path')
    need(v1_reference_normalized_parts('/toc.dat') is None, 'synthetic absolute path')
    need(v1_reference_normalized_parts('root\\toc.dat') is None, 'synthetic backslash path')

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
    need(len(checklist) == 72, 'checklist row count')
    by_control = {row.get('control', ''): row for row in checklist}
    need(len(by_control) == len(checklist), 'checklist unique controls')
    checklist_expected = {
        'archive_listing_attempts_consumed': '1',
        'archive_listing_attempts_remaining': '0',
        'root_contract_resolved': 'false',
        'v1_predicate_coverage_gap_confirmed': 'true',
        'observed_archive_leading_dot_prefix_confirmed': 'false',
        'backup_corruption_established': 'false',
        'route_b_status': 'APPROVED_GOVERNANCE_ONLY',
        'selected_route': SELECTED_ROUTE,
        'new_investigator_created': 'false',
        'restore_execution': 'false',
        'staging_0010_apply_authorized': 'false',
        'next_action': 'SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_REQUIRED',
    }
    for control, expected in checklist_expected.items():
        row = by_control.get(control)
        need(row is not None, 'checklist control ' + control)
        need(row.get('expected') == expected and row.get('current') == expected, 'checklist value ' + control)
        need(row.get('status') == 'PASS', 'checklist status ' + control)

    decisions = read_csv(GO_NO_GO)
    need(len(decisions) == 25, 'Go/No-Go row count')
    by_gate = {row.get('gate', ''): row for row in decisions}
    need(len(by_gate) == len(decisions), 'Go/No-Go unique gates')
    need(by_gate['Route B corrected V2 chain']['current'] == 'APPROVED_GOVERNANCE_ONLY', 'Route B decision')
    need(by_gate['Route C direct runner restore']['current'] == 'REJECTED', 'Route C decision')
    need(by_gate['new investigation execution authorization']['current'] == 'false', 'execution authority')
    need(by_gate['decision disposition']['current'] == 'GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION', 'decision disposition')

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
    marker_line = '# PMAI-P0-04 structural predicate review governance decision v1'
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
        'subsequent_structural_predicate_review_entry_commit': EXPECTED_HEAD,
        'subsequent_structural_predicate_review_ci_gate': '196',
        'subsequent_structural_predicate_review_ci_status': 'PASS',
        'subsequent_structural_predicate_review_selected_route': SELECTED_ROUTE,
        'subsequent_new_investigation_authorized': 'false',
    }
    for key, expected in evidence_pointer.items():
        need(marker(evidence_doc, key) == expected, 'evidence pointer ' + key)
    need(marker(evidence_doc, 'archive_listing_attempts_consumed') == '1', 'evidence attempt count changed')
    need(marker(evidence_doc, 'root_contract_resolved') == 'false', 'evidence point-in-time result changed')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db', '.bak', '.save')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Structural Predicate Review Governance Decision V1')
    print('stage_id=PMAI-P0-04')
    print('substage=STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1')
    print('package_status=GOVERNANCE_DECISION_ONLY')
    print('v1_predicate_coverage_gap_confirmed=true')
    print('observed_archive_leading_dot_prefix_confirmed=false')
    print('backup_corruption_established=false')
    print('archive_listing_attempts_consumed=1')
    print('archive_listing_attempts_remaining=0')
    print('root_contract_resolved=false')
    print('selected_route=' + SELECTED_ROUTE)
    print('new_investigator_created=false')
    print('new_investigation_authorized=false')
    print('restore_execution=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
