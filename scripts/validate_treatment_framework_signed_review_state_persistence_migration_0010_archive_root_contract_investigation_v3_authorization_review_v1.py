#!/usr/bin/env python3
"""Validate PMAI-P0-04 Archive Root Contract Investigation V3 Authorization Review V1."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_V1_TEST_MATRIX_V1.csv'
PREPARATION_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION_V1.md'
PREPARED_SOURCE = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V3.py.txt'
CANDIDATE_SOURCE = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V3_AUTHORIZED_CANDIDATE.py.txt'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v3_authorization_review_v1.py'
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
V2_POST_DECISION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v2_post_execution_structural_review_governance_decision_v1.py'
V3_PREPARATION_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v3_preparation_v1.py'
ROLLING_VALIDATORS = (
    FRESH_DECISION_VALIDATOR,
    V1_PREPARATION_VALIDATOR,
    V1_AUTHORIZATION_VALIDATOR,
    V1_EVIDENCE_VALIDATOR,
    V1_STRUCTURAL_DECISION_VALIDATOR,
    V2_PREPARATION_VALIDATOR,
    V2_AUTHORIZATION_VALIDATOR,
    V2_EVIDENCE_VALIDATOR,
    V2_POST_DECISION_VALIDATOR,
    V3_PREPARATION_VALIDATOR,
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
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1.md',
    PREPARATION_DOC,
)
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = '0e6dfdd876227d88003bebc9edd966f0821c0b41'
EXPECTED_PARENT = '98fe4d902d4b24bf13837aaf0ea7e5f7bdc9d1f3'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = 'd6cae61ff10138ae48be1832291aeefc19442ac68b323d4153939d1fbf19ea2d'
EXPECTED_FINAL_CI_SHA256 = 'e283cc5aa77f73d9fe79b1139411897b677daf8ebe71eb70212ae82edb07b31d'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_PREPARED_SOURCE_SHA256 = '52fc4310065b0877152f592b4394c5f74d27e4812a6a30d71eb50cd94d0f4b55'
EXPECTED_CANDIDATE_SOURCE_SHA256 = '6800bc57c018ad17deb84b2c821baad4752e23f9aa432b01d64f9518737d5e14'
EXPECTED_V2_SOURCE_SHA256 = 'ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6'
EXPECTED_V1_RESULT_SHA256 = 'c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893'
EXPECTED_V2_RESULT_SHA256 = '3eef22eeab17779b4e5499f53c22caf22fd5d0fd7c107cdaca6cbb8926ebf028'
AUTHORIZATION_RECORD_ID = 'PMAI-P0-04-ARCI-V3-AUTH-V1-20260813'
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
    'post_effective_gate_v3_investigation_authorized',
    'v3_preparation_complete',
    'prepared_v3_source_retained_unchanged',
    'toc_dat_presence_established',
    'archive_hash_recheck_required_before_metadata_scan',
    'authorized_candidate_execution_gate_literal',
    'authorized_candidate_execute_flag_required',
    'authorized_candidate_authorization_record_id_required',
    'authorized_candidate_expected_archive_sha256_confirmation_required',
    'v3_allows_one_optional_leading_dot_prefix',
    'v3_allows_directory_root_marker',
    'v3_rejects_internal_dot_component',
    'v3_rejects_parent_component',
    'v3_rejects_absolute_path',
    'v3_rejects_backslash',
    'v3_rejects_control_character',
    'v3_rejects_empty_component',
    'v3_rejects_drive_prefix',
    'v3_rejects_special_member_for_success',
    'v3_rejects_excessive_component_depth',
    'v3_rejects_excessive_member_name_bytes',
    'v3_general_normpath_forbidden',
    'v3_toc_dat_normalized_depth_metric',
    'v3_shared_prefix_depth_metric',
    'v3_top_level_component_count_metric',
    'v3_member_depth_min_metric',
    'v3_member_depth_max_metric',
    'v3_wrapper_depth_metric',
    'v3_numeric_metrics_bounded',
    'v3_numeric_saturation_flag_required',
    'v3_logical_root_fingerprint_sha256_required',
    'v3_member_name_set_sha256_required',
    'v3_all_members_contained_by_identified_root_required',
    'v3_sanitized_reason_counters_required',
    'v3_sanitized_fixed_layout_enum_required',
    'sanitized_summary_only',
    'repository_only',
    'schema_ok',
)
FALSE_MARKERS = (
    'current_v3_investigation_authorized',
    'v3_investigation_execution_authorized',
    'v3_archive_listing_attempt_authorized',
    'one_time_execution_confirmation_present',
    'v1_root_contract_resolved',
    'v2_root_contract_resolved',
    'root_contract_resolved',
    'actual_archive_layout_cause_resolved',
    'backup_corruption_established',
    'legacy_v1_authorization_reuse_allowed',
    'legacy_v2_authorization_reuse_allowed',
    'prepared_v3_source_execution_enabled',
    'prepared_v3_source_executed_by_ci',
    'prepared_v3_source_executed_by_package',
    'authorized_candidate_v3_source_repository_executable',
    'authorized_candidate_v3_source_executed_by_ci',
    'authorized_candidate_v3_source_executed_by_package',
    'authorized_candidate_v3_source_activation_authorized',
    'automatic_retry_allowed',
    'manual_retry_allowed',
    'authorization_reuse_allowed',
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
    'current_authorization_reuse_allowed',
    'current_package_v3_investigation_authorized',
    'current_package_v3_investigation_execution_authorized',
    'current_package_v3_archive_listing_attempt_authorized',
    'current_package_one_time_execution_confirmation_present',
    'active_v3_investigator_created',
    'authorized_candidate_v3_source_activated',
    'authorized_candidate_v3_source_executed',
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
    'PMAI-P0-04-ARCI-V3-AUTH-T{:03d}'.format(number)
    for number in range(1, 89)
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


def reference_normalize(raw: str, kind: str):
    if kind == 'dir' and raw.endswith('/'):
        raw = raw[:-1]
    if not raw:
        return None, 'REJECT_EMPTY_PATH'
    if len(raw.encode('utf-8')) > 4096:
        return None, 'REJECT_EXCESSIVE_NAME_BYTES'
    if raw.startswith('/'):
        return None, 'REJECT_ABSOLUTE_PATH'
    if '\\' in raw:
        return None, 'REJECT_BACKSLASH'
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        return None, 'REJECT_CONTROL_CHARACTER'
    parts = list(raw.split('/'))
    if parts == ['.']:
        return ((), 'ACCEPTED_ROOT_MARKER') if kind == 'dir' else (None, 'REJECT_ROOT_MARKER_NON_DIRECTORY')
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
    if len(parts) > 64:
        return None, 'REJECT_EXCESSIVE_COMPONENT_DEPTH'
    return tuple(parts), ('ACCEPTED_LEADING_DOT_PREFIX' if leading_dot else 'ACCEPTED_CANONICAL_RELATIVE')


def reference_layout(entries: list[tuple[str, str]]) -> dict[str, object]:
    normalized: list[tuple[tuple[str, ...], str]] = []
    root_markers = rejected = special = 0
    for raw, kind in entries:
        parts, reason = reference_normalize(raw, kind)
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
    top_level_count = len({parts[0] for parts, _kind in normalized})
    classification = 'NONE_OR_AMBIGUOUS'
    toc_depth = -1
    contained = False
    if len(toc) == 1:
        root = toc[0][:-1]
        toc_depth = len(root)
        contained = bool(normalized) and all(
            True
            if not root
            else (
                parts[:len(root)] == root
                if len(parts) >= len(root)
                else kind == 'dir' and parts == root[:len(parts)]
            )
            for parts, kind in normalized
        )
        if contained:
            if toc_depth == 0:
                classification = 'PG_DIRECTORY_ROOT_UNWRAPPED'
            elif toc_depth == 1:
                classification = 'PG_DIRECTORY_ROOT_WRAPPED'
            else:
                classification = 'PG_DIRECTORY_ROOT_DEEP_WRAPPED'
        elif top_level_count > 1:
            classification = 'MIXED_TOP_LEVEL'
        else:
            classification = 'SHARED_TOP_LEVEL_DIVERGENT_SUBTREE'
    safe = rejected == special == duplicates == collisions == 0 and root_markers <= 1
    return {
        'classification': classification,
        'contained': contained,
        'safe': safe,
        'toc_depth': toc_depth,
        'top_level_count': top_level_count,
    }


def main() -> int:
    doc = read_text(DOC)
    preparation_doc = read_text(PREPARATION_DOC)
    prepared_source = read_text(PREPARED_SOURCE)
    candidate_source = read_text(CANDIDATE_SOURCE)
    package_text = '\n'.join(
        read_text(path)
        for path in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, CANDIDATE_SOURCE)
    )
    ci = read_text(CI)
    root_source = read_text(ROOT_VALIDATOR)

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_V1',
        'package_status': 'AUTHORIZATION_REVIEW_RECORD_ONLY',
        'review_status': 'PROPOSED_APPROVE_BOUNDED_DEPTH_AWARE_METADATA_ONLY_V3_INVESTIGATION',
        'authorization_record_id': AUTHORIZATION_RECORD_ID,
        'authorization_scope': 'ONE_EXACT_ARCHIVE_ONE_V3_DEPTH_AWARE_METADATA_ONLY_ATTEMPT',
        'decision': 'GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY',
        'next_action': 'REQUEST_SEPARATE_REPOSITORY_APPLY_AUTHORIZATION_FOR_EXACT_BUNDLE',
        'local_main': EXPECTED_HEAD,
        'origin_main': EXPECTED_HEAD,
        'main_parent': EXPECTED_PARENT,
        'github_ci_gate_number': '202',
        'github_ci_gate_status': 'PASS',
        'github_ci_gate_commit': EXPECTED_HEAD,
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_FINAL_CI_SHA256,
        'local_isolated_branch': EXPECTED_ISOLATED,
        'remote_isolated_branch': EXPECTED_ISOLATED,
        'locked_runner_sha256': EXPECTED_LOCKED_RUNNER_SHA256,
        'prepared_v3_source_sha256': EXPECTED_PREPARED_SOURCE_SHA256,
        'authorized_candidate_v3_source_sha256': EXPECTED_CANDIDATE_SOURCE_SHA256,
        'authorized_candidate_v2_source_sha256': EXPECTED_V2_SOURCE_SHA256,
        'sanitized_v1_result_sha256': EXPECTED_V1_RESULT_SHA256,
        'sanitized_v2_result_sha256': EXPECTED_V2_RESULT_SHA256,
        'active_0010_migration_file_count': '0',
        'completed_substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION_V1',
        'completed_commit': EXPECTED_HEAD,
        'completed_ci_gate': '202',
        'selected_route': SELECTED_ROUTE,
        'v1_archive_listing_attempts_consumed': '1',
        'v2_archive_listing_attempts_consumed': '1',
        'cumulative_archive_listing_attempts_consumed': '2',
        'cumulative_archive_listing_attempts_remaining': '0',
        'v2_toc_dat_candidate_count': '1',
        'v2_wrapper_depth': '-1',
        'v2_stop_code': 'V2_STRUCTURAL_PREDICATE_MISMATCH',
        'v2_decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'approved_backup_sha256': 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7',
        'prepared_v3_source_path': PREPARED_SOURCE,
        'authorized_candidate_v3_source_path': CANDIDATE_SOURCE,
        'authorized_candidate_v3_source_storage_suffix': '.py.txt',
        'authorized_candidate_default_mode': 'CONTRACT_ONLY_NO_ARCHIVE_OPEN',
        'authorized_candidate_v3_attempt_number_required': '1',
        'authorized_candidate_cumulative_attempt_number': '3',
        'v1_attempts_consumed': '1',
        'v2_attempts_consumed': '1',
        'v3_attempt_budget': '1',
        'v3_attempts_consumed': '0',
        'v3_attempts_remaining_pre_effective_gate': '0',
        'v3_attempts_remaining_post_effective_gate': '1',
        'v3_attempt_number': '1',
        'cumulative_archive_listing_attempt_number_if_executed': '3',
        'v3_max_normalized_component_depth': '64',
        'v3_max_member_name_utf8_bytes': '4096',
        'v3_max_sanitized_count': '30',
        'v3_max_sanitized_uncompressed_size_bytes': '1073741824',
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
        'AUTHORIZATION_RECORD_ID': 'PENDING_SEPARATE_V3_AUTHORIZATION_REVIEW',
        'EXPECTED_ARCHIVE_MEMBER_COUNT': 29,
        'EXPECTED_V3_ATTEMPT_NUMBER': 1,
        'EXPECTED_CUMULATIVE_ATTEMPT_NUMBER': 3,
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
        'EXPECTED_V3_ATTEMPT_NUMBER': 1,
        'EXPECTED_CUMULATIVE_ATTEMPT_NUMBER': 3,
        'EXECUTION_ENABLED': True,
        'EXECUTION_REQUIRES_EXPLICIT_FLAG': True,
        'MEMBER_PAYLOAD_READ_ALLOWED': False,
        'MEMBER_EXTRACTION_ALLOWED': False,
        'ARCHIVE_WRITE_ALLOWED': False,
        'AUTOMATIC_RETRY_ALLOWED': False,
        'MAX_NORMALIZED_COMPONENT_DEPTH': 64,
        'MAX_MEMBER_NAME_UTF8_BYTES': 4096,
        'MAX_SANITIZED_COUNT': 30,
        'MAX_SANITIZED_UNCOMPRESSED_SIZE_BYTES': 1073741824,
    }
    for name, expected in prepared_literals.items():
        need(literal(prepared_source, name) == expected, 'prepared literal ' + name)
    for name, expected in candidate_literals.items():
        need(literal(candidate_source, name) == expected, 'candidate literal ' + name)

    normalize_source = function_source(candidate_source, 'normalize_member')
    structural_source = function_source(candidate_source, 'structural_result')
    main_source = function_source(candidate_source, 'main')
    for token in (
        'REJECT_EXCESSIVE_NAME_BYTES',
        'REJECT_EXCESSIVE_COMPONENT_DEPTH',
        'REJECT_PARENT_COMPONENT',
        'REJECT_INTERNAL_DOT_COMPONENT',
        'ACCEPTED_LEADING_DOT_PREFIX',
        'ACCEPTED_ROOT_MARKER',
    ):
        need(token in normalize_source, 'candidate normalize token ' + token)
    need('normpath' not in normalize_source and 'resolve(' not in normalize_source, 'candidate general normalization forbidden')
    for token in (
        'toc_dat_normalized_depth',
        'shared_prefix_depth',
        'top_level_component_count',
        'member_depth_min',
        'member_depth_max',
        'numeric_metric_saturation_detected',
        'PG_DIRECTORY_ROOT_UNWRAPPED',
        'PG_DIRECTORY_ROOT_WRAPPED',
        'PG_DIRECTORY_ROOT_DEEP_WRAPPED',
        'MIXED_TOP_LEVEL',
        'SHARED_TOP_LEVEL_DIVERGENT_SUBTREE',
    ):
        need(token in structural_source, 'candidate structural token ' + token)
    default_at = main_source.index('if not args.execute')
    gate_at = main_source.index('if not EXECUTION_ENABLED')
    record_at = main_source.index('args.authorization_record_id')
    hash_at = main_source.index('args.confirm_archive_sha256')
    attempt_at = main_source.index('args.v3_attempt_number')
    cumulative_at = main_source.index('args.cumulative_attempt_number')
    prompt_at = main_source.index('getpass.getpass')
    file_check_at = main_source.index('archive_path.is_file')
    sha_at = main_source.index('sha256_path(archive_path)')
    archive_open_at = main_source.index('archive_path.open')
    tar_at = main_source.index('tarfile.open')
    need(
        default_at < gate_at < record_at < hash_at < attempt_at < cumulative_at < prompt_at < file_check_at < sha_at < archive_open_at < tar_at,
        'candidate fail-closed order',
    )
    for token in ('.extract(', '.extractall(', '.extractfile(', '.getfile(', 'subprocess', 'requests', 'psycopg', 'alembic'):
        need(token not in candidate_source, 'candidate forbidden operation ' + token)
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

    fixtures = {
        'unwrapped': ([('toc.dat', 'file'), ('1.dat', 'file')], 'PG_DIRECTORY_ROOT_UNWRAPPED', 0, True),
        'wrapped': ([('root/toc.dat', 'file'), ('root/1.dat', 'file')], 'PG_DIRECTORY_ROOT_WRAPPED', 1, True),
        'deep': ([('a/b/toc.dat', 'file'), ('a/b/1.dat', 'file')], 'PG_DIRECTORY_ROOT_DEEP_WRAPPED', 2, True),
        'deep_ancestors': ([('a/', 'dir'), ('a/b/', 'dir'), ('a/b/toc.dat', 'file'), ('a/b/1.dat', 'file')], 'PG_DIRECTORY_ROOT_DEEP_WRAPPED', 2, True),
        'mixed': ([('a/toc.dat', 'file'), ('other/1.dat', 'file')], 'MIXED_TOP_LEVEL', 1, False),
        'divergent': ([('a/b/toc.dat', 'file'), ('a/c/1.dat', 'file')], 'SHARED_TOP_LEVEL_DIVERGENT_SUBTREE', 2, False),
        'missing_toc': ([('a/1.dat', 'file')], 'NONE_OR_AMBIGUOUS', -1, False),
        'duplicate_toc': ([('a/toc.dat', 'file'), ('a/toc.dat', 'file')], 'NONE_OR_AMBIGUOUS', -1, False),
    }
    for name, (entries, expected_class, expected_depth, expected_contained) in fixtures.items():
        result = reference_layout(entries)
        need(result['classification'] == expected_class, 'synthetic classification ' + name)
        need(result['toc_depth'] == expected_depth, 'synthetic depth ' + name)
        need(result['contained'] == expected_contained, 'synthetic containment ' + name)
    rejection_fixtures = (
        ('a/./b', 'file'),
        ('././b', 'file'),
        ('a/../b', 'file'),
        ('/a/b', 'file'),
        ('a\\b', 'file'),
        ('a//b', 'file'),
        ('C:/b', 'file'),
        ('/'.join(['a'] * 65), 'file'),
        ('a\x00b', 'file'),
    )
    for raw, kind in rejection_fixtures:
        parts, _reason = reference_normalize(raw, kind)
        need(parts is None, 'synthetic rejection ' + repr(raw))
    need(reference_normalize('./', 'dir') == ((), 'ACCEPTED_ROOT_MARKER'), 'synthetic root marker')

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
    need(len(checklist) == 116, 'checklist row count')
    by_control = {row.get('control', ''): row for row in checklist}
    need(len(by_control) == len(checklist), 'checklist unique controls')
    checklist_expected = {
        'github_ci_gate_number': '202',
        'selected_route': SELECTED_ROUTE,
        'prepared_v3_source_hash': EXPECTED_PREPARED_SOURCE_SHA256,
        'candidate_v3_source_hash': EXPECTED_CANDIDATE_SOURCE_SHA256,
        'candidate_source_suffix': '.py.txt',
        'authorization_record_id': AUTHORIZATION_RECORD_ID,
        'current_v3_investigation_authorized': 'false',
        'post_effective_gate_v3_investigation_authorized': 'true',
        'cumulative_attempts_consumed': '2',
        'v3_attempt_budget': '1',
        'v3_attempts_remaining_current': '0',
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
    need(len(decisions) == 38, 'Go/No-Go row count')
    by_gate = {row.get('gate', ''): row for row in decisions}
    need(len(by_gate) == len(decisions), 'Go/No-Go unique gates')
    need(by_gate['candidate inert suffix']['current'] == '.py.txt', 'candidate inert source decision')
    need(by_gate['current V3 investigation authorization']['current'] == 'false', 'current V3 authority')
    need(by_gate['post effective gate V3 authorization']['current'] == 'true', 'proposed V3 authority')
    need(by_gate['review disposition']['current'] == 'GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY', 'review disposition')

    tests = read_csv(TEST_MATRIX)
    need({row.get('test_id', '') for row in tests} == REQUIRED_TEST_IDS, 'test matrix exact IDs')
    need(all(row.get('status') == 'DESIGNED' for row in tests), 'test matrix status')

    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, 'final CI hash')
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, 'locked runner hash')
    need(not glob.glob(str(ROOT / 'backend/migrations/versions/0010*.py')), 'active 0010 migration')

    targets = literal(root_source, 'TARGETS')
    hashes = literal(root_source, 'HASHES')
    need(isinstance(targets, list) and len(targets) == 127 and len(targets) == len(set(targets)), 'root TARGETS')
    need(isinstance(hashes, dict), 'root HASHES')
    need(REQUIRED_PROTECTED_PATHS.issubset(set(targets)), 'V3 authorization package protection')
    need(set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS, 'protected hash scope')
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), 'missing protected ' + rel)
        need(sha256_path(path) == expected_hash, 'protected hash ' + rel)
    need(ci_targets(ci) == targets, 'CI/root target equality')
    need(python_lines(ci) == EXPECTED_COMMANDS, 'CI approved validators')
    marker_line = '# PMAI-P0-04 archive root contract investigation V3 authorization review v1'
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
        'subsequent_v3_authorization_review_entry_commit': EXPECTED_HEAD,
        'subsequent_v3_authorization_review_ci_gate': '202',
        'subsequent_v3_authorization_review_ci_status': 'PASS',
        'subsequent_v3_authorized_candidate_sha256': EXPECTED_CANDIDATE_SOURCE_SHA256,
        'subsequent_current_v3_investigation_authorized': 'false',
    }
    for key, expected in preparation_pointer.items():
        need(marker(preparation_doc, key) == expected, 'preparation pointer ' + key)
    need(marker(preparation_doc, 'v3_source_execution_enabled') == 'false', 'prepared source state changed')
    need(marker(preparation_doc, 'v2_root_contract_resolved') == 'false', 'root result changed')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db', '.bak', '.save')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Archive Root Contract Investigation V3 Authorization Review V1')
    print('stage_id=PMAI-P0-04')
    print('substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_V1')
    print('package_status=AUTHORIZATION_REVIEW_RECORD_ONLY')
    print('authorization_scope_recorded=true')
    print('current_v3_investigation_authorized=false')
    print('post_effective_gate_v3_investigation_authorized=true')
    print('v3_investigation_execution_authorized=false')
    print('v3_archive_listing_attempt_authorized=false')
    print('one_time_execution_confirmation_present=false')
    print('authorized_candidate_v3_source_sha256=' + EXPECTED_CANDIDATE_SOURCE_SHA256)
    print('authorized_candidate_v3_source_activated=false')
    print('authorized_candidate_v3_source_executed=false')
    print('v1_attempts_consumed=1')
    print('v2_attempts_consumed=1')
    print('cumulative_attempts_consumed=2')
    print('v3_attempts_consumed=0')
    print('v3_attempts_remaining_current=0')
    print('root_contract_resolved=false')
    print('restore_execution=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
