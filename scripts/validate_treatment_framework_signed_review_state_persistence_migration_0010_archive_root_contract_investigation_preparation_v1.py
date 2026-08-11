#!/usr/bin/env python3
"""Validate PMAI-P0-04 Archive Root Contract Investigation Preparation V1."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1_TEST_MATRIX_V1.csv'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_preparation_v1.py'
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
PREVIOUS_VALIDATORS = (*LEGACY_VALIDATORS, FRESH_DECISION_VALIDATOR)
ROLLING_DOCS = (
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1.md',
)
FRESH_DECISION_DOC = ROLLING_DOCS[-1]
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = '65e51ab64845083f47a2e397abf0f0a739c51a72'
EXPECTED_PARENT = '0bc76d10af7a0168048fb007dff9e156341b9b4f'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = 'e09532f6b3069ab07e7f6d155457791ccad1844617999b95cee2cad7dea4d508'
EXPECTED_FINAL_CI_SHA256 = '80bd7f4e5186a33c3420fe4804a636c90e954d2d9349330803d0bb90bebc0870'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_BACKUP_SHA256 = 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7'
EXPECTED_TOC_SHA256 = '6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c'
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
 '|| exit 1']
PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
HASH_EXTRA_PATHS = {
    'backend/models.py',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
    'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
    'render.yaml',
}
FALSE_KEYS = (
    'archive_root_contract_investigation_authorized',
    'archive_root_contract_investigation_execution_authorized',
    'archive_listing_attempt_authorized',
    'fresh_chain_restore_attempt_authorized',
    'prior_root_contract_resolution_reusable',
    'root_contract_resolved',
    'archive_wrapper_depth_verified',
    'archive_common_root_verified',
    'toc_location_relative_to_root_verified',
    'directory_format_member_layout_verified',
    'restore_input_kind_verified',
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
    'fresh_restore_governance_route_b_approved',
    'archive_root_contract_investigation_preparation_complete',
    'ready_for_separate_archive_root_contract_investigation_authorization_review',
    'repository_clean_at_entry',
    'fresh_restore_governance_decision_complete',
    'prior_temporary_extraction_cleaned',
    'planned_sanitized_summary_only',
    'success_requires_approved_archive_sha256_match',
    'success_requires_single_common_root_present',
    'success_requires_all_members_contained_by_common_root',
    'repository_only',
)
QUESTION_KEYS = tuple('question_{:02d}'.format(number) for number in range(1, 16))
EVIDENCE_KEYS = tuple('evidence_field_{:02d}'.format(number) for number in range(1, 29))
REQUIRED_TEST_IDS = {
    'PMAI-P0-04-ARCIP-T{:03d}'.format(number)
    for number in range(1, 31)
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


def main() -> int:
    doc = read_text(DOC)
    package_text = '\n'.join(read_text(path) for path in (DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX))
    ci = read_text(CI)
    root_source = read_text(ROOT_VALIDATOR)
    fresh_decision_doc = read_text(FRESH_DECISION_DOC)

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1',
        'package_status': 'INVESTIGATION_PREPARATION_ONLY',
        'preparation_record_id': 'PMAI-P0-04-ARCIP-V1-20260810',
        'preparation_authority_source': 'EXPLICIT_USER_AUTHORIZATION_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_DESIGN_AND_DRY_RUN_20260810',
        'archive_listing_attempt_budget': '1',
        'decision': 'GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1',
        'next_action': 'SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1',
        'local_main': EXPECTED_HEAD,
        'origin_main': EXPECTED_HEAD,
        'main_parent': EXPECTED_PARENT,
        'github_ci_gate_number': '193',
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
        'completed_substage': 'FRESH_RESTORE_GOVERNANCE_DECISION_V1',
        'completed_commit': EXPECTED_HEAD,
        'completed_ci_gate': '193',
        'selected_route': 'ROUTE_B_REBUILD_FRESH_RESTORE_GOVERNANCE_CHAIN_FROM_ZERO',
        'legacy_third_call_stop_code': 'BACKUP_DIRECTORY_ROOT_MISMATCH',
        'approved_backup_file_size_bytes': '22299',
        'approved_backup_sha256': EXPECTED_BACKUP_SHA256,
        'approved_backup_toc_sha256': EXPECTED_TOC_SHA256,
        'approved_backup_toc_entry_count': '433',
        'prior_archive_member_count': '29',
        'prior_archive_uncompressed_size_bytes': '196874',
        'prior_benign_root_directory_entries': '1',
        'planned_future_operation': 'ARCHIVE_MEMBER_METADATA_LIST_ONLY_AFTER_SEPARATE_AUTHORIZATION',
        'planned_member_header_read_scope': 'METADATA_ONLY',
        'planned_member_payload_read_scope': 'FORBIDDEN',
        'planned_member_extraction_scope': 'FORBIDDEN',
        'planned_archive_write_scope': 'FORBIDDEN',
        'planned_network_scope': 'NONE',
        'common_root_repository_value': 'HASH_ONLY',
        'member_names_repository_value': 'COUNTS_AND_HASHES_ONLY',
        'raw_archive_listing_repository_value': 'FORBIDDEN',
        'permitted_success_classification': 'SINGLE_SAFE_GZIP_TAR_WRAPPED_PG_DIRECTORY_ROOT',
        'permitted_hold_classification': 'AMBIGUOUS_UNSAFE_OR_UNSUPPORTED',
        'success_requires_archive_member_count': '29',
        'success_requires_unsafe_or_special_member_count': '0',
        'success_requires_normalized_path_violation_count': '0',
        'success_requires_duplicate_normalized_member_count': '0',
        'success_requires_case_collision_count': '0',
        'success_requires_top_level_component_count': '1',
        'success_requires_toc_dat_candidate_count': '1',
        'success_requires_toc_dat_relation_category': 'IMMEDIATE_CHILD_OF_COMMON_ROOT',
        'future_success_next_gate': 'SEPARATE_CORRECTED_RESTORE_RUNNER_DESIGN_PREPARATION_V1',
        'future_non_success_decision': 'HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED',
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, 'document marker ' + key)
    for key in TRUE_KEYS:
        need(marker(doc, key) == 'true', 'required true marker ' + key)
    for key in FALSE_KEYS:
        need(marker(doc, key) == 'false', 'required false marker ' + key)

    need(len({marker(doc, key) for key in QUESTION_KEYS}) == len(QUESTION_KEYS), 'question set exact and unique')
    need(len({marker(doc, key) for key in EVIDENCE_KEYS}) == len(EVIDENCE_KEYS), 'evidence schema exact and unique')

    forbidden = (
        r'(?i)postgres(?:ql)?://\S+',
        r'(?im)^\s*(?:export\s+)?DATABASE_URL\s*=',
        r'(?im)^\s*(?:export\s+)?SECRET_KEY\s*=',
        r'(?im)^\s*(?:password|passwd|pwd)\s*[:=]',
        r'(?i)\bdpg-[a-z0-9-]+\b',
        r'(?im)^\s*(?:\$\s*)?(?:tar|gtar|bsdtar|gzip|gunzip|unzip|pg_restore|psql|alembic)(?:\s|$)',
        r'(?im)^\s*(?:\$\s*)?python(?:3)?\s+(?:-m\s+tarfile|[^\r\n]*tarfile)',
        r'(?i)(?:/Users/|~/Pet-med-ai-p0-04-)',
    )
    for pattern in forbidden:
        need(re.search(pattern, package_text) is None, 'forbidden secret path or executable command')

    checklist = read_csv(CHECKLIST)
    need(len(checklist) == 40, 'checklist row count')
    by_control = {row.get('control', ''): row for row in checklist}
    need(len(by_control) == len(checklist), 'checklist unique controls')
    for key in (
        'archive_root_contract_investigation_authorized',
        'archive_root_contract_investigation_execution_authorized',
        'archive_listing_attempt_authorized',
        'backup_archive_listing_invoked',
        'backup_archive_member_headers_read',
        'backup_archive_member_payload_read',
        'backup_archive_extracted',
        'backup_archive_copied',
        'backup_archive_uploaded',
        'backup_archive_modified',
        'backup_archive_repackaged',
        'prior_root_contract_resolution_reusable',
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
    ):
        row = by_control.get(key)
        need(row is not None and row.get('expected') == 'false' and row.get('current') == 'false', 'checklist false control ' + key)
    need(by_control['archive_root_contract_investigation_preparation_complete']['current'] == 'true', 'checklist preparation complete')
    need(by_control['ready_for_separate_archive_root_contract_investigation_authorization_review']['current'] == 'true', 'checklist review ready')
    need(by_control['approved_backup_sha256']['current'] == EXPECTED_BACKUP_SHA256, 'checklist backup hash')
    need(by_control['common_root_repository_value']['current'] == 'HASH_ONLY', 'checklist root privacy')
    need(by_control['next_action']['current'] == required['next_action'], 'checklist next action')

    decisions = read_csv(GO_NO_GO)
    need(len(decisions) == 1, 'Go/No-Go row count')
    decision = decisions[0]
    need(decision.get('preparation_complete') == 'true', 'Go/No-Go preparation')
    need(decision.get('investigation_authorized') == 'false', 'Go/No-Go investigation authority')
    need(decision.get('listing_invoked') == 'false', 'Go/No-Go listing')
    need(decision.get('external_execution_authorized') == 'false', 'Go/No-Go external authority')
    need(decision.get('decision') == required['decision'], 'Go/No-Go decision')
    need(decision.get('next_action') == required['next_action'], 'Go/No-Go next action')

    tests = read_csv(TEST_MATRIX)
    need({row.get('test_id', '') for row in tests} == REQUIRED_TEST_IDS, 'test matrix exact IDs')

    validator_source = read_text(VALIDATOR)
    imports = set()
    for node in ast.walk(ast.parse(validator_source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or '').split('.')[0])
    need(imports == {'__future__', 'ast', 'csv', 'glob', 'hashlib', 'pathlib', 're', 'sys'}, 'validator repository-only imports')
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
    marker_line = '# PMAI-P0-04 archive root contract investigation preparation v1'
    need(ci.splitlines().count(marker_line) == 1, 'CI marker count')
    need(ci.splitlines().count(CI_COMMAND) == 1, 'CI command count')

    prep_source = read_text(AUTH_PREP_VALIDATOR)
    need(literal(prep_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'auth-prep CI rollover')
    for rel in LEGACY_VALIDATORS:
        source = read_text(rel)
        need(literal(source, 'EXPECTED_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'legacy CI rollover ' + rel)
        need(literal(source, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'legacy command rollover ' + rel)
    fresh_source = read_text(FRESH_DECISION_VALIDATOR)
    need(literal(fresh_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'fresh decision CI rollover')
    need(VALIDATOR in fresh_source, 'fresh decision command rollover')
    for rel in ROLLING_DOCS:
        need(marker(read_text(rel), 'final_ci_sha256') == EXPECTED_FINAL_CI_SHA256, 'rolling document CI hash ' + rel)
    need(marker(fresh_decision_doc, 'fresh_restore_governance_route_b_approved') == 'true', 'fresh decision retained')
    need(marker(fresh_decision_doc, 'next_action') == 'SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1', 'fresh decision point-in-time next action')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db', '.bak', '.save')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Archive Root Contract Investigation Preparation V1')
    print('stage_id=PMAI-P0-04')
    print('substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1')
    print('archive_root_contract_investigation_preparation_complete=true')
    print('ready_for_separate_archive_root_contract_investigation_authorization_review=true')
    print('archive_root_contract_investigation_authorized=false')
    print('archive_root_contract_investigation_execution_authorized=false')
    print('backup_archive_listing_invoked=false')
    print('backup_archive_member_headers_read=false')
    print('backup_archive_member_payload_read=false')
    print('backup_archive_extracted=false')
    print('backup_archive_modified=false')
    print('backup_archive_repackaged=false')
    print('root_contract_resolved=false')
    print('new_restore_runner_design_authorized=false')
    print('new_disposable_target_authorized=false')
    print('new_restore_execution_authorized=false')
    print('backup_restoreability_verified=false')
    print('disposable_restore_rehearsal_complete=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1')
    print('next_action=SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_AUTHORIZATION_REVIEW_V1')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
