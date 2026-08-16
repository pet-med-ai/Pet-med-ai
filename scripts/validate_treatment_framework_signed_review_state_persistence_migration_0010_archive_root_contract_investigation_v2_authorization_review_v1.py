#!/usr/bin/env python3
"""Validate PMAI-P0-04 Archive Root Contract Investigation V2 Authorization Review V1."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_V1_TEST_MATRIX_V1.csv'
PREPARATION_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_V1.md'
PREPARED_SOURCE = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V2.py.txt'
CANDIDATE_SOURCE = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V2_AUTHORIZED_CANDIDATE.py.txt'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_authorization_review_v1.py'
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
ROLLING_VALIDATORS = (
    FRESH_DECISION_VALIDATOR,
    V1_PREPARATION_VALIDATOR,
    V1_AUTHORIZATION_VALIDATOR,
    V1_EVIDENCE_VALIDATOR,
    STRUCTURAL_DECISION_VALIDATOR,
    V2_PREPARATION_VALIDATOR,
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
    PREPARATION_DOC,
)
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = 'abeec6d7f1f5a592fc1435b4a370bd6cffb3a4ce'
EXPECTED_PARENT = 'b5eaeb7b1a36b5fcb54734bda5886d93d56576e3'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = '0ddbb7e54bfdeaad96fa11911b747a0a17dd146fb72d6ed11ff9fb70942e2800'
EXPECTED_FINAL_CI_SHA256 = '2aa57fb16b2513954b8ab8f9f86646a3d961174576ea6aa3539e683636620b6c'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_PREPARED_SOURCE_SHA256 = '0d6303b0a5fc63d8231669b8a5d396d67b645120f9ac5421977cb79f3f6e8837'
EXPECTED_CANDIDATE_SOURCE_SHA256 = 'ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6'
EXPECTED_RESULT_SHA256 = 'c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893'
AUTHORIZATION_RECORD_ID = 'PMAI-P0-04-ARCI-V2-AUTH-V1-20260812'
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
PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, CANDIDATE_SOURCE, VALIDATOR}
REQUIRED_PROTECTED_PATHS = PACKAGE_PATHS | {PREPARATION_DOC, PREPARED_SOURCE}
HASH_EXTRA_PATHS = {
    'backend/models.py',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
    'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
    'render.yaml',
}
TRUE_MARKERS = (
    'authorization_scope_recorded',
    'post_effective_gate_v2_investigation_authorized',
    'v2_preparation_complete',
    'prepared_v2_source_retained_unchanged',
    'archive_hash_recheck_required_before_metadata_scan',
    'authorized_candidate_execution_gate_literal',
    'authorized_candidate_execute_flag_required',
    'authorized_candidate_authorization_record_id_required',
    'authorized_candidate_expected_archive_sha256_confirmation_required',
    'v2_allows_one_optional_leading_dot_prefix',
    'v2_allows_directory_root_marker',
    'v2_rejects_internal_dot_component',
    'v2_rejects_parent_component',
    'v2_rejects_absolute_path',
    'v2_rejects_backslash',
    'v2_rejects_control_character',
    'v2_rejects_empty_component',
    'v2_rejects_drive_prefix',
    'v2_rejects_special_member_for_success',
    'sanitized_summary_only',
    'repository_only',
    'schema_ok',
)
FALSE_MARKERS = (
    'current_v2_investigation_authorized',
    'current_package_v2_investigation_authorized',
    'v2_investigation_execution_authorized',
    'current_package_v2_investigation_execution_authorized',
    'v2_archive_listing_attempt_authorized',
    'current_package_v2_archive_listing_attempt_authorized',
    'one_time_execution_confirmation_present',
    'current_package_one_time_execution_confirmation_present',
    'v1_root_contract_resolved',
    'observed_archive_leading_dot_prefix_confirmed',
    'observed_archive_unwrapped_pg_directory_root_confirmed',
    'toc_dat_absence_established',
    'backup_corruption_established',
    'structural_predicate_mismatch_cause_resolved',
    'legacy_v1_authorization_reuse_allowed',
    'prepared_v2_source_execution_enabled',
    'prepared_v2_source_executed_by_ci',
    'prepared_v2_source_executed_by_package',
    'authorized_candidate_v2_source_repository_executable',
    'authorized_candidate_v2_source_executed_by_ci',
    'authorized_candidate_v2_source_executed_by_package',
    'authorized_candidate_v2_source_activation_authorized',
    'automatic_retry_allowed',
    'manual_retry_allowed',
    'authorization_reuse_allowed',
    'current_authorization_reuse_allowed',
    'raw_member_list_output',
    'raw_logical_root_output',
    'raw_external_path_output',
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
    'active_v2_investigator_created',
    'authorized_candidate_v2_source_activated',
    'authorized_candidate_v2_source_executed',
    'root_contract_resolved',
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
    'backup_restoreability_verified',
    'disposable_restore_rehearsal_complete',
    'corrected_migration_implementation_authorized',
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
    'PMAI-P0-04-ARCI-V2-AUTH-T{:03d}'.format(number)
    for number in range(1, 54)
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


def reference_normalize(raw: str, is_directory: bool = False):
    if is_directory and raw.endswith('/'):
        raw = raw[:-1]
    if not raw:
        return None, 'REJECT_EMPTY_PATH'
    if raw.startswith('/'):
        return None, 'REJECT_ABSOLUTE_PATH'
    if '\\' in raw:
        return None, 'REJECT_BACKSLASH'
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        return None, 'REJECT_CONTROL_CHARACTER'
    parts = list(raw.split('/'))
    if parts == ['.']:
        return ((), 'ACCEPTED_ROOT_MARKER') if is_directory else (None, 'REJECT_ROOT_MARKER_NON_DIRECTORY')
    leading_dot = bool(parts and parts[0] == '.')
    if leading_dot:
        parts = parts[1:]
    if not parts or any(part == '' for part in parts):
        return None, 'REJECT_EMPTY_COMPONENT'
    if any(part == '..' for part in parts):
        return None, 'REJECT_PARENT_COMPONENT'
    if any(part == '.' for part in parts):
        return None, 'REJECT_INTERNAL_DOT_COMPONENT'
    if len(parts[0]) >= 2 and parts[0][1] == ':':
        return None, 'REJECT_DRIVE_PREFIX'
    return tuple(parts), ('ACCEPTED_LEADING_DOT_PREFIX' if leading_dot else 'ACCEPTED_CANONICAL_RELATIVE')


def reference_layout(entries: list[tuple[str, str]]) -> str:
    normalized: list[tuple[tuple[str, ...], str]] = []
    root_markers = rejected = special = 0
    for raw, kind in entries:
        parts, reason = reference_normalize(raw, kind == 'dir')
        if reason == 'ACCEPTED_ROOT_MARKER':
            root_markers += 1
        elif parts is None:
            rejected += 1
        elif parts:
            normalized.append((parts, kind))
        if kind not in {'file', 'dir'}:
            special += 1
    names = ['/'.join(parts) for parts, _kind in normalized]
    duplicates = len(names) - len(set(names))
    folded: dict[str, set[str]] = {}
    for name in names:
        folded.setdefault(name.casefold(), set()).add(name)
    collisions = sum(len(values) - 1 for values in folded.values())
    toc = [parts for parts, kind in normalized if kind == 'file' and parts[-1] == 'toc.dat']
    base_ok = rejected == special == duplicates == collisions == 0 and root_markers <= 1
    if base_ok and len(toc) == 1 and toc[0] == ('toc.dat',):
        return 'PG_DIRECTORY_ROOT_UNWRAPPED'
    if base_ok and len(toc) == 1 and len(toc[0]) == 2:
        wrapper = toc[0][0]
        if normalized and all(parts[0] == wrapper for parts, _kind in normalized):
            return 'PG_DIRECTORY_ROOT_WRAPPED'
    return 'HOLD'


def main() -> int:
    doc = read_text(DOC)
    preparation_doc = read_text(PREPARATION_DOC)
    prepared_source = read_text(PREPARED_SOURCE)
    candidate_source = read_text(CANDIDATE_SOURCE)
    package_text = '\n'.join(read_text(path) for path in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX))
    ci = read_text(CI)
    root_source = read_text(ROOT_VALIDATOR)

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_V1',
        'package_status': 'AUTHORIZATION_REVIEW_RECORD_ONLY',
        'review_status': 'PROPOSED_APPROVE_BOUNDED_METADATA_ONLY_V2_INVESTIGATION',
        'authorization_record_id': AUTHORIZATION_RECORD_ID,
        'authorization_scope': 'ONE_EXACT_ARCHIVE_ONE_V2_METADATA_ONLY_ATTEMPT',
        'decision': 'GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY',
        'next_action': 'REQUEST_SEPARATE_REPOSITORY_APPLY_AUTHORIZATION_FOR_EXACT_BUNDLE',
        'local_main': EXPECTED_HEAD,
        'origin_main': EXPECTED_HEAD,
        'main_parent': EXPECTED_PARENT,
        'github_ci_gate_number': '198',
        'github_ci_gate_status': 'PASS',
        'github_ci_gate_commit': EXPECTED_HEAD,
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_FINAL_CI_SHA256,
        'local_isolated_branch': EXPECTED_ISOLATED,
        'remote_isolated_branch': EXPECTED_ISOLATED,
        'locked_runner_sha256': EXPECTED_LOCKED_RUNNER_SHA256,
        'prepared_v2_source_sha256': EXPECTED_PREPARED_SOURCE_SHA256,
        'authorized_candidate_v2_source_sha256': EXPECTED_CANDIDATE_SOURCE_SHA256,
        'sanitized_v1_result_sha256': EXPECTED_RESULT_SHA256,
        'active_0010_migration_file_count': '0',
        'completed_substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_V1',
        'completed_commit': EXPECTED_HEAD,
        'completed_ci_gate': '198',
        'selected_route': SELECTED_ROUTE,
        'v1_archive_listing_attempts_consumed': '1',
        'v1_archive_listing_attempts_remaining': '0',
        'v1_normalized_path_violation_count': '29',
        'v1_stop_code': 'STRUCTURAL_PREDICATE_MISMATCH',
        'v1_decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'approved_backup_sha256': 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7',
        'prepared_v2_source_path': PREPARED_SOURCE,
        'authorized_candidate_v2_source_path': CANDIDATE_SOURCE,
        'authorized_candidate_v2_source_storage_suffix': '.py.txt',
        'authorized_candidate_default_mode': 'CONTRACT_ONLY_NO_ARCHIVE_OPEN',
        'authorized_candidate_v2_attempt_number_required': '1',
        'authorized_candidate_cumulative_attempt_number': '2',
        'v1_attempts_consumed': '1',
        'v1_attempts_remaining': '0',
        'v2_attempt_budget': '1',
        'v2_attempts_consumed': '0',
        'v2_attempts_remaining_pre_effective_gate': '0',
        'v2_attempts_remaining_post_effective_gate': '1',
        'v2_attempt_number': '1',
        'cumulative_archive_listing_attempt_number_if_executed': '2',
        'database_revision': '0009_diag_data',
        'alembic_head': '0009_diag_data',
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, 'document marker ' + key)
    for key in TRUE_MARKERS:
        need(marker(doc, key) == 'true', 'required true marker ' + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == 'false', 'required false marker ' + key)

    need(PREPARED_SOURCE.endswith('.py.txt') and CANDIDATE_SOURCE.endswith('.py.txt'), 'source suffixes')
    need(sha256_path(ROOT / PREPARED_SOURCE) == EXPECTED_PREPARED_SOURCE_SHA256, 'prepared source hash changed')
    need(sha256_path(ROOT / CANDIDATE_SOURCE) == EXPECTED_CANDIDATE_SOURCE_SHA256, 'candidate source hash changed')
    ast.parse(prepared_source)
    ast.parse(candidate_source)
    prepared_literals = {
        'AUTHORIZATION_RECORD_ID': 'PENDING_SEPARATE_V2_AUTHORIZATION_REVIEW',
        'EXPECTED_ARCHIVE_MEMBER_COUNT': 29,
        'EXECUTION_ENABLED': False,
        'MEMBER_PAYLOAD_READ_ALLOWED': False,
        'MEMBER_EXTRACTION_ALLOWED': False,
        'ARCHIVE_WRITE_ALLOWED': False,
        'AUTOMATIC_RETRY_ALLOWED': False,
    }
    candidate_literals = {
        'AUTHORIZATION_RECORD_ID': AUTHORIZATION_RECORD_ID,
        'EXPECTED_ARCHIVE_SHA256': 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7',
        'EXPECTED_ARCHIVE_MEMBER_COUNT': 29,
        'V2_ATTEMPT_NUMBER': 1,
        'CUMULATIVE_ARCHIVE_LISTING_ATTEMPT_NUMBER': 2,
        'EXECUTION_ENABLED': True,
        'EXECUTION_REQUIRES_EXPLICIT_FLAG': True,
        'MEMBER_PAYLOAD_READ_ALLOWED': False,
        'MEMBER_EXTRACTION_ALLOWED': False,
        'ARCHIVE_WRITE_ALLOWED': False,
        'AUTOMATIC_RETRY_ALLOWED': False,
    }
    for name, expected in prepared_literals.items():
        need(literal(prepared_source, name) == expected, 'prepared literal ' + name)
    for name, expected in candidate_literals.items():
        need(literal(candidate_source, name) == expected, 'candidate literal ' + name)

    normalize_source = function_source(candidate_source, 'normalize_member')
    structural_source = function_source(candidate_source, 'structural_result')
    main_source = function_source(candidate_source, 'main')
    need("parts = list(raw.split(\"/\"))" in normalize_source, 'candidate explicit split')
    need("parts[0] == \".\"" in normalize_source, 'candidate optional leading dot')
    need("any(part == \".\" for part in parts)" in normalize_source, 'candidate internal dot rejection')
    need("any(part == \"..\" for part in parts)" in normalize_source, 'candidate parent rejection')
    need('normpath' not in normalize_source and 'resolve(' not in normalize_source, 'candidate general normalization forbidden')
    need('PG_DIRECTORY_ROOT_UNWRAPPED' in structural_source, 'candidate unwrapped classification')
    need('PG_DIRECTORY_ROOT_WRAPPED' in structural_source, 'candidate wrapped classification')
    need('normalization_reason_counts' in structural_source, 'candidate reason counters')
    default_at = main_source.index('if not args.execute')
    gate_at = main_source.index('if not EXECUTION_ENABLED')
    record_at = main_source.index('args.authorization_record_id')
    hash_at = main_source.index('args.confirm_archive_sha256')
    attempt_at = main_source.index('args.attempt_number')
    prompt_at = main_source.index('getpass.getpass')
    archive_open_at = main_source.index('archive_path.open')
    tar_at = main_source.index('tarfile.open')
    need(default_at < gate_at < record_at < hash_at < attempt_at < prompt_at < archive_open_at < tar_at, 'candidate fail-closed order')
    approved_python = '\n'.join(python_lines(ci))
    need(PREPARED_SOURCE not in approved_python and CANDIDATE_SOURCE not in approved_python, 'candidate source executed by CI')

    validator_tree = ast.parse(read_text(VALIDATOR))
    imported_modules = {
        node.names[0].name.split('.')[0]
        for node in validator_tree.body
        if isinstance(node, ast.Import)
    } | {
        (node.module or '').split('.')[0]
        for node in validator_tree.body
        if isinstance(node, ast.ImportFrom)
    }
    need(imported_modules <= {'__future__', 'ast', 'csv', 'glob', 'hashlib', 'pathlib', 're', 'sys'}, 'validator import allowlist')

    normalize_cases = {
        ('root/toc.dat', False): (('root', 'toc.dat'), 'ACCEPTED_CANONICAL_RELATIVE'),
        ('./root/toc.dat', False): (('root', 'toc.dat'), 'ACCEPTED_LEADING_DOT_PREFIX'),
        ('./', True): ((), 'ACCEPTED_ROOT_MARKER'),
        ('.', False): (None, 'REJECT_ROOT_MARKER_NON_DIRECTORY'),
        ('root/./toc.dat', False): (None, 'REJECT_INTERNAL_DOT_COMPONENT'),
        ('././toc.dat', False): (None, 'REJECT_INTERNAL_DOT_COMPONENT'),
        ('../toc.dat', False): (None, 'REJECT_PARENT_COMPONENT'),
        ('/toc.dat', False): (None, 'REJECT_ABSOLUTE_PATH'),
        ('root\\toc.dat', False): (None, 'REJECT_BACKSLASH'),
        ('root//toc.dat', False): (None, 'REJECT_EMPTY_COMPONENT'),
        ('C:/toc.dat', False): (None, 'REJECT_DRIVE_PREFIX'),
        ('root/\x01toc.dat', False): (None, 'REJECT_CONTROL_CHARACTER'),
    }
    for case, expected in normalize_cases.items():
        need(reference_normalize(*case) == expected, 'synthetic normalize ' + repr(case))
    need(reference_layout([('root/toc.dat', 'file'), ('root/data/1.dat', 'file')]) == 'PG_DIRECTORY_ROOT_WRAPPED', 'synthetic wrapped canonical')
    need(reference_layout([('./root/toc.dat', 'file'), ('./root/data/1.dat', 'file')]) == 'PG_DIRECTORY_ROOT_WRAPPED', 'synthetic wrapped leading dot')
    need(reference_layout([('toc.dat', 'file'), ('data/1.dat', 'file')]) == 'PG_DIRECTORY_ROOT_UNWRAPPED', 'synthetic unwrapped canonical')
    need(reference_layout([('./toc.dat', 'file'), ('./data/1.dat', 'file')]) == 'PG_DIRECTORY_ROOT_UNWRAPPED', 'synthetic unwrapped leading dot')
    need(reference_layout([('data/1.dat', 'file')]) == 'HOLD', 'synthetic missing toc')
    need(reference_layout([('toc.dat', 'file'), ('x/toc.dat', 'file')]) == 'HOLD', 'synthetic multiple toc')
    need(reference_layout([('root/toc.dat', 'file'), ('outside/1.dat', 'file')]) == 'HOLD', 'synthetic wrapper escape')
    need(reference_layout([('toc.dat', 'file'), ('toc.dat', 'file')]) == 'HOLD', 'synthetic duplicate')
    need(reference_layout([('toc.dat', 'file'), ('device', 'special')]) == 'HOLD', 'synthetic special member')

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
    need(len(checklist) == 82, 'checklist row count')
    by_control = {row.get('control', ''): row for row in checklist}
    need(len(by_control) == len(checklist), 'checklist unique controls')
    checklist_expected = {
        'github_ci_gate_number': '198',
        'selected_route': SELECTED_ROUTE,
        'prepared_v2_source_hash': EXPECTED_PREPARED_SOURCE_SHA256,
        'candidate_v2_source_hash': EXPECTED_CANDIDATE_SOURCE_SHA256,
        'candidate_source_suffix': '.py.txt',
        'authorization_record_id': AUTHORIZATION_RECORD_ID,
        'current_v2_investigation_authorized': 'false',
        'post_effective_gate_v2_investigation_authorized': 'true',
        'v1_attempts_consumed': '1',
        'v2_attempt_budget': '1',
        'v2_attempts_remaining_current': '0',
        'archive_file_opened': 'false',
        'candidate_executed': 'false',
        'restore_execution': 'false',
        'staging_0010_apply_authorized': 'false',
        'next_action': 'REQUEST_SEPARATE_REPOSITORY_APPLY_AUTHORIZATION_FOR_EXACT_BUNDLE',
    }
    for control, expected in checklist_expected.items():
        row = by_control.get(control)
        need(row is not None, 'checklist control ' + control)
        need(row.get('expected') == expected and row.get('current') == expected, 'checklist value ' + control)
        need(row.get('status') == 'PASS', 'checklist status ' + control)

    decisions = read_csv(GO_NO_GO)
    need(len(decisions) == 29, 'Go/No-Go row count')
    by_gate = {row.get('gate', ''): row for row in decisions}
    need(len(by_gate) == len(decisions), 'Go/No-Go unique gates')
    need(by_gate['candidate source inert suffix']['current'] == '.py.txt', 'candidate inert source decision')
    need(by_gate['current V2 investigation authorization']['current'] == 'false', 'current V2 authority')
    need(by_gate['post effective gate V2 authorization']['current'] == 'true', 'proposed V2 authority')
    need(by_gate['review disposition']['current'] == 'GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY', 'review disposition')

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
    need(REQUIRED_PROTECTED_PATHS.issubset(set(targets)), 'V2 authorization package protection')
    need(set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS, 'protected hash scope')
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), 'missing protected ' + rel)
        need(sha256_path(path) == expected_hash, 'protected hash ' + rel)

    need(ci_targets(ci) == targets, 'CI/root target equality')
    need(python_lines(ci) == EXPECTED_COMMANDS, 'CI approved validators')
    marker_line = '# PMAI-P0-04 archive root contract investigation V2 authorization review v1'
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

    preparation_pointer = {
        'subsequent_v2_authorization_review_entry_commit': EXPECTED_HEAD,
        'subsequent_v2_authorization_review_ci_gate': '198',
        'subsequent_v2_authorization_review_ci_status': 'PASS',
        'subsequent_v2_authorized_candidate_sha256': EXPECTED_CANDIDATE_SOURCE_SHA256,
        'subsequent_current_v2_investigation_authorized': 'false',
    }
    for key, expected in preparation_pointer.items():
        need(marker(preparation_doc, key) == expected, 'preparation pointer ' + key)
    need(marker(preparation_doc, 'v2_source_execution_enabled') == 'false', 'prepared source state changed')
    need(marker(preparation_doc, 'v1_root_contract_resolved') == 'false', 'root result changed')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db', '.bak', '.save')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Archive Root Contract Investigation V2 Authorization Review V1')
    print('stage_id=PMAI-P0-04')
    print('substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_V1')
    print('package_status=AUTHORIZATION_REVIEW_RECORD_ONLY')
    print('authorization_scope_recorded=true')
    print('current_v2_investigation_authorized=false')
    print('post_effective_gate_v2_investigation_authorized=true')
    print('v2_investigation_execution_authorized=false')
    print('v2_archive_listing_attempt_authorized=false')
    print('one_time_execution_confirmation_present=false')
    print('authorized_candidate_v2_source_sha256=' + EXPECTED_CANDIDATE_SOURCE_SHA256)
    print('authorized_candidate_v2_source_activated=false')
    print('authorized_candidate_v2_source_executed=false')
    print('v1_attempts_consumed=1')
    print('v2_attempts_consumed=0')
    print('v2_attempts_remaining_current=0')
    print('root_contract_resolved=false')
    print('restore_execution=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
