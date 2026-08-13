#!/usr/bin/env python3
"""Validate PMAI-P0-04 Archive Root Contract Investigation Authorization Review V1."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1_TEST_MATRIX_V1.csv'
IMPLEMENTATION = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V1.py.txt'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_authorization_review_v1.py'
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
ROLLING_DOCS = (
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1.md',
)
PREPARATION_DOC = ROLLING_DOCS[-1]
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = 'f521520f96ab28f1a6e696b60fc8f06e4a2eda69'
EXPECTED_PARENT = '65e51ab64845083f47a2e397abf0f0a739c51a72'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = 'a1684935365edfbe4db7ac08aa9b08e264d9dde533ca15685cd8bbb122b5f248'
EXPECTED_FINAL_CI_SHA256 = '27171bf84096af25dc25ff3f0153516108b92b22fec878b1afc9184df5c2dece'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_BACKUP_SHA256 = 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7'
EXPECTED_TOC_SHA256 = '6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c'
EXPECTED_IMPLEMENTATION_SHA256 = '2b99a7446fbd5509e22c9fa5f6cb18eca920711208aa37fb4af568fd21f6faab'
AUTHORIZATION_RECORD_ID = 'PMAI-P0-04-ARCI-AUTH-V1-20260811'
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
 '|| exit 1']
PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, IMPLEMENTATION, VALIDATOR}
HASH_EXTRA_PATHS = {
    'backend/models.py',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
    'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
    'render.yaml',
}
FALSE_KEYS = (
    'current_archive_root_contract_investigation_authorized',
    'archive_root_contract_investigation_execution_authorized',
    'archive_listing_attempt_authorized',
    'one_time_execution_confirmation_present',
    'fresh_chain_restore_attempt_authorized',
    'legacy_runner_v1_reuse_allowed',
    'legacy_runner_v2_reuse_allowed',
    'legacy_authorization_reuse_allowed',
    'legacy_fourth_external_runner_call_authorized',
    'investigation_implementation_executable_in_repository',
    'investigation_implementation_executed_by_ci',
    'investigation_implementation_executed_by_package',
    'investigation_shell_interpolation',
    'investigation_automatic_retry',
    'raw_member_list_output',
    'raw_common_root_output',
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
    'raw_archive_listing_printed',
    'raw_external_path_printed',
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
    'new_restore_runner_design_authorized',
    'new_restore_runner_authorized',
    'new_disposable_target_authorized',
    'new_restore_execution_authorized',
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
)
TRUE_KEYS = (
    'authorization_scope_recorded',
    'post_effective_gate_archive_root_contract_investigation_authorized',
    'repository_clean_at_entry',
    'fresh_restore_governance_route_b_approved',
    'archive_root_contract_investigation_preparation_complete',
    'ready_for_separate_archive_root_contract_investigation_authorization_review',
    'archive_hash_recheck_required_before_metadata_scan',
    'investigation_execute_flag_required',
    'investigation_authorization_record_id_required',
    'investigation_expected_archive_sha256_confirmation_required',
    'sanitized_summary_only',
    'success_requires_approved_archive_sha256_match',
    'success_requires_single_common_root_present',
    'success_requires_all_members_contained_by_common_root',
    'repository_only',
)
EVIDENCE_KEYS = tuple('evidence_field_{:02d}'.format(number) for number in range(1, 29))
REQUIRED_TEST_IDS = {
    'PMAI-P0-04-ARCI-AUTH-T{:03d}'.format(number)
    for number in range(1, 37)
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
    tree = ast.parse(source)
    found = []
    for node in tree.body:
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


def validate_inert_implementation(source: str) -> None:
    tree = ast.parse(source, filename=IMPLEMENTATION)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or '').split('.')[0])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            need(node.func.attr not in {'extract', 'extractall', 'extractfile'}, 'forbidden extraction API')
            need(node.func.attr not in {'write', 'write_text', 'write_bytes', 'unlink', 'rename', 'replace'}, 'forbidden write API')
    need(
        imports == {'__future__', 'argparse', 'getpass', 'hashlib', 'json', 'pathlib', 'sys', 'tarfile'},
        'implementation imports',
    )
    need(literal(source, 'AUTHORIZATION_RECORD_ID') == AUTHORIZATION_RECORD_ID, 'implementation authorization record')
    need(literal(source, 'EXPECTED_ARCHIVE_SHA256') == EXPECTED_BACKUP_SHA256, 'implementation backup hash')
    need(literal(source, 'EXPECTED_ARCHIVE_MEMBER_COUNT') == 29, 'implementation member count')
    need(literal(source, 'EXECUTION_REQUIRES_EXPLICIT_FLAG') is True, 'implementation execute guard')
    need(literal(source, 'MEMBER_PAYLOAD_READ_ALLOWED') is False, 'implementation payload guard')
    need(literal(source, 'MEMBER_EXTRACTION_ALLOWED') is False, 'implementation extraction guard')
    need(literal(source, 'ARCHIVE_WRITE_ALLOWED') is False, 'implementation write guard')
    need(literal(source, 'AUTOMATIC_RETRY_ALLOWED') is False, 'implementation retry guard')
    for required in (
        'if not args.execute:',
        'getpass.getpass(',
        'mode="r:gz"',
        'archive.getmembers()',
        'raw_member_names_emitted',
        'raw_external_path_emitted',
        'member_payload_read',
        'member_extraction_performed',
        'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
        'GO_TO_SEPARATE_CORRECTED_RESTORE_RUNNER_DESIGN_PREPARATION_V1',
    ):
        need(source.count(required) >= 1, 'implementation required source marker ' + required)
    need(source.index('if not args.execute:') < source.index('archive_value ='), 'default no-open ordering')
    forbidden = ('subprocess', 'socket', 'requests', 'urllib', 'psycopg', 'sqlalchemy', 'pg_restore', 'psql', 'alembic')
    for value in forbidden:
        need(value not in source, 'implementation forbidden capability ' + value)


def main() -> int:
    doc = read_text(DOC)
    package_text = '\n'.join(read_text(path) for path in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX))
    implementation = read_text(IMPLEMENTATION)
    ci = read_text(CI)
    root_source = read_text(ROOT_VALIDATOR)
    preparation_doc = read_text(PREPARATION_DOC)

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1',
        'package_status': 'AUTHORIZATION_REVIEW_RECORD_ONLY',
        'review_status': 'PROPOSED_APPROVE_BOUNDED_METADATA_ONLY_INVESTIGATION',
        'authorization_record_id': AUTHORIZATION_RECORD_ID,
        'authorization_recorded_date': '2026-08-11',
        'design_dry_run_authority_source': 'EXPLICIT_USER_AUTHORIZATION_IN_CURRENT_CONVERSATION_20260811',
        'authorization_scope': 'ONE_EXACT_ARCHIVE_ONE_METADATA_ONLY_ATTEMPT',
        'authorization_record_effective_gate': 'EXACT_PACKAGE_APPLIED_COMMITTED_PUSHED_GITHUB_CI_PASS_AND_SEPARATE_ONE_TIME_EXECUTION_CONFIRMATION',
        'decision': 'GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY',
        'next_action': 'REQUEST_SEPARATE_REPOSITORY_APPLY_AUTHORIZATION_FOR_EXACT_BUNDLE',
        'local_main': EXPECTED_HEAD,
        'origin_main': EXPECTED_HEAD,
        'main_parent': EXPECTED_PARENT,
        'github_ci_gate_number': '194',
        'github_ci_gate_status': 'PASS',
        'github_ci_gate_commit': EXPECTED_HEAD,
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_FINAL_CI_SHA256,
        'local_isolated_branch': EXPECTED_ISOLATED,
        'remote_isolated_branch': EXPECTED_ISOLATED,
        'production_runtime_baseline': 'd659aefb',
        'staging_runtime_baseline': '8d1dc881',
        'production_database_revision_baseline': '0009_diag_data',
        'staging_database_revision_baseline': '0009_diag_data',
        'locked_runner_sha256': EXPECTED_LOCKED_RUNNER_SHA256,
        'active_0010_migration_file_count': '0',
        'completed_substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1',
        'completed_commit': EXPECTED_HEAD,
        'completed_ci_gate': '194',
        'selected_route': 'ROUTE_B_REBUILD_FRESH_RESTORE_GOVERNANCE_CHAIN_FROM_ZERO',
        'approved_backup_file_size_bytes': '22299',
        'approved_backup_sha256': EXPECTED_BACKUP_SHA256,
        'approved_backup_toc_sha256': EXPECTED_TOC_SHA256,
        'approved_backup_toc_entry_count': '433',
        'prior_archive_member_count': '29',
        'prior_archive_uncompressed_size_bytes': '196874',
        'investigation_implementation_path': IMPLEMENTATION,
        'investigation_implementation_format': 'INERT_PYTHON_SOURCE_TEXT',
        'investigation_implementation_sha256': EXPECTED_IMPLEMENTATION_SHA256,
        'investigation_default_mode': 'CONTRACT_ONLY_NO_ARCHIVE_OPEN',
        'investigation_attempt_number_required': '1',
        'investigation_path_input': 'HIDDEN_INTERACTIVE_PROMPT_NOT_COMMAND_LINE',
        'investigation_output_contract': 'SANITIZED_JSON_COUNTS_BOOLEANS_CLASSIFICATIONS_AND_HASHES_ONLY',
        'archive_listing_attempt_budget': '1',
        'archive_listing_attempts_consumed': '0',
        'post_effective_gate_operation': 'GZIP_TAR_MEMBER_METADATA_SCAN_ONLY',
        'member_header_read_scope': 'METADATA_ONLY',
        'member_payload_read_scope': 'FORBIDDEN',
        'member_extraction_scope': 'FORBIDDEN',
        'common_root_repository_value': 'HASH_ONLY',
        'raw_archive_listing_repository_value': 'FORBIDDEN',
        'permitted_success_classification': 'SINGLE_SAFE_GZIP_TAR_WRAPPED_PG_DIRECTORY_ROOT',
        'success_requires_archive_member_count': '29',
        'success_requires_unsafe_or_special_member_count': '0',
        'success_requires_normalized_path_violation_count': '0',
        'success_requires_duplicate_normalized_member_count': '0',
        'success_requires_case_collision_count': '0',
        'success_requires_top_level_component_count': '1',
        'success_requires_toc_dat_candidate_count': '1',
        'success_requires_toc_dat_relation_category': 'IMMEDIATE_CHILD_OF_COMMON_ROOT',
        'success_next_gate': 'SEPARATE_CORRECTED_RESTORE_RUNNER_DESIGN_PREPARATION_V1',
        'non_success_decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, 'document marker ' + key)
    for key in TRUE_KEYS:
        need(marker(doc, key) == 'true', 'required true marker ' + key)
    for key in FALSE_KEYS:
        need(marker(doc, key) == 'false', 'required false marker ' + key)
    need(len({marker(doc, key) for key in EVIDENCE_KEYS}) == 28, 'evidence schema exact and unique')

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

    need(sha256_path(ROOT / IMPLEMENTATION) == EXPECTED_IMPLEMENTATION_SHA256, 'implementation hash')
    validate_inert_implementation(implementation)
    need(IMPLEMENTATION not in '\n'.join(python_lines(ci)), 'implementation executed by CI')

    checklist = read_csv(CHECKLIST)
    need(len(checklist) == 48, 'checklist row count')
    by_control = {row.get('control', ''): row for row in checklist}
    need(len(by_control) == len(checklist), 'checklist unique controls')
    for key in (
        'current_archive_root_contract_investigation_authorized',
        'archive_root_contract_investigation_execution_authorized',
        'archive_listing_attempt_authorized',
        'one_time_execution_confirmation_present',
        'archive_file_opened',
        'backup_archive_member_headers_read',
        'backup_archive_member_payload_read',
        'backup_archive_extracted',
        'backup_archive_copied',
        'backup_archive_uploaded',
        'backup_archive_modified',
        'backup_archive_repackaged',
        'investigation_implementation_executable_in_repository',
        'raw_member_list_output',
        'root_contract_resolved',
        'legacy_runner_v1_reuse_allowed',
        'legacy_runner_v2_reuse_allowed',
        'new_restore_runner_design_authorized',
        'new_disposable_target_authorized',
        'database_connection',
        'restore_execution',
        'migration_created',
        'application_deployment',
        'resource_deleted',
        'backup_restoreability_verified',
        'disposable_restore_rehearsal_complete',
        'repository_apply_authorized',
    ):
        row = by_control.get(key)
        need(row is not None and row.get('expected') == 'false' and row.get('current') == 'false', 'checklist false control ' + key)
    need(by_control['authorization_scope_recorded']['current'] == 'true', 'checklist scope record')
    need(by_control['post_effective_gate_archive_root_contract_investigation_authorized']['current'] == 'true', 'checklist conditional authority')
    need(by_control['approved_backup_sha256']['current'] == EXPECTED_BACKUP_SHA256, 'checklist backup hash')
    need(by_control['investigation_implementation_sha256']['current'] == EXPECTED_IMPLEMENTATION_SHA256, 'checklist implementation hash')
    need(by_control['next_action']['current'] == required['next_action'], 'checklist next action')

    decisions = read_csv(GO_NO_GO)
    need(len(decisions) == 1, 'Go/No-Go row count')
    decision = decisions[0]
    need(decision.get('scope_record_proposed') == 'true', 'Go/No-Go scope record')
    need(decision.get('current_investigation_authorized') == 'false', 'Go/No-Go current authority')
    need(decision.get('execution_authorized') == 'false', 'Go/No-Go execution')
    need(decision.get('listing_authorized') == 'false', 'Go/No-Go listing')
    need(decision.get('decision') == required['decision'], 'Go/No-Go decision')
    need(decision.get('next_action') == required['next_action'], 'Go/No-Go next action')

    tests = read_csv(TEST_MATRIX)
    need({row.get('test_id', '') for row in tests} == REQUIRED_TEST_IDS, 'test matrix exact IDs')

    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, 'final CI hash')
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, 'locked runner hash')
    need(not glob.glob(str(ROOT / 'backend/migrations/versions/0010*.py')), 'active 0010 migration')

    targets = literal(root_source, 'TARGETS')
    hashes = literal(root_source, 'HASHES')
    need(isinstance(targets, list) and len(targets) == len(set(targets)), 'root TARGETS')
    need(isinstance(hashes, dict), 'root HASHES')
    need(PACKAGE_PATHS.issubset(set(targets)), 'full package protected')
    need(set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS, 'protected hash scope')
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), 'missing protected ' + rel)
        need(sha256_path(path) == expected_hash, 'protected hash ' + rel)

    need(ci_targets(ci) == targets, 'CI/root target equality')
    need(python_lines(ci) == EXPECTED_COMMANDS, 'CI approved validators')
    marker_line = '# PMAI-P0-04 archive root contract investigation authorization review v1'
    need(ci.splitlines().count(marker_line) == 1, 'CI marker count')
    need(ci.splitlines().count(CI_COMMAND) == 1, 'CI command count')

    prep_source = read_text(AUTH_PREP_VALIDATOR)
    need(literal(prep_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'auth-prep CI rollover')
    for rel in LEGACY_VALIDATORS:
        source = read_text(rel)
        need(literal(source, 'EXPECTED_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'legacy CI rollover ' + rel)
        need(literal(source, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'legacy command rollover ' + rel)
    fresh_source = read_text(FRESH_DECISION_VALIDATOR)
    need(literal(fresh_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'fresh CI rollover')
    need(literal(fresh_source, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'fresh command rollover')
    preparation_source = read_text(PREPARATION_VALIDATOR)
    need(literal(preparation_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'preparation CI rollover')
    need(literal(preparation_source, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'preparation command rollover')
    for rel in ROLLING_DOCS:
        need(marker(read_text(rel), 'final_ci_sha256') == EXPECTED_FINAL_CI_SHA256, 'rolling document CI hash ' + rel)
    need(marker(preparation_doc, 'next_action') == 'SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1', 'preparation point-in-time next action')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db', '.bak', '.save')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Archive Root Contract Investigation Authorization Review V1')
    print('stage_id=PMAI-P0-04')
    print('substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1')
    print('authorization_scope_recorded=true')
    print('current_archive_root_contract_investigation_authorized=false')
    print('post_effective_gate_archive_root_contract_investigation_authorized=true')
    print('archive_root_contract_investigation_execution_authorized=false')
    print('archive_listing_attempt_authorized=false')
    print('backup_archive_listing_invoked=false')
    print('backup_archive_member_headers_read=false')
    print('backup_archive_member_payload_read=false')
    print('backup_archive_extracted=false')
    print('backup_archive_modified=false')
    print('backup_archive_repackaged=false')
    print('root_contract_resolved=false')
    print('repository_apply_authorized=false')
    print('git_stage_authorized=false')
    print('git_commit_authorized=false')
    print('git_push_authorized=false')
    print('new_restore_runner_design_authorized=false')
    print('new_disposable_target_authorized=false')
    print('new_restore_execution_authorized=false')
    print('backup_restoreability_verified=false')
    print('disposable_restore_rehearsal_complete=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=GO_TO_SEPARATE_REPOSITORY_APPLY_REVIEW_ONLY')
    print('next_action=REQUEST_SEPARATE_REPOSITORY_APPLY_AUTHORIZATION_FOR_EXACT_BUNDLE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
