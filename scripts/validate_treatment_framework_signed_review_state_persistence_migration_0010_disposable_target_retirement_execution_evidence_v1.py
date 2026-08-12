#!/usr/bin/env python3
"""Validate PMAI-P0-04 disposable target retirement execution evidence V1."""

from __future__ import annotations

import ast
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_execution_evidence_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
AUTH_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
AUTH_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py'
EVIDENCE_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py'
RESTORE_AUTH_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py'
ABORT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py'
RETIREMENT_AUTH_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py'
RESTORE_AUTH_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md'
ABORT_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md'
RETIREMENT_AUTH_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md'
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_CI_SHA256 = '7cba5137d959d9f37a5e4f7a70798ff5090fc130ead6ce9d124c457c9a682811'
EXPECTED_PRIOR_CI_SHA256 = '779d896e877ade28ca67e4115d61de3309deff25cf79e137c8d9dab47720ec98'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_EVIDENCE_SET_SHA256 = '61d630c697bdf937e59e9f992105c9aa7a00726a03d1fcc3924524e64fc9ae77'
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
 '|| exit 1']
EXPECTED_EVIDENCE = (
    ('P04-DTR-E01', '35b0687c5a3b5873a1e33f5889b7a0272595c9dde3cdc3c9449af5b63b548126', 'pre_delete_identity_status_version_region'),
    ('P04-DTR-E02', '3ace6cb4a6e0bf151e72a70cba7247d015da23762e6eddad16a2fe841b4ff277', 'pre_delete_storage_autoscaling_pool'),
    ('P04-DTR-E03', 'f356bf7b8ddd9d42927834f5212714157d69b33708a1d7e99d2988e1bf7dd4f0', 'pre_delete_instance_high_availability'),
    ('P04-DTR-E04', 'ba6b6173aa918cfff395b840ea52d69dec46b965a55f1b1f8c1720c4b60546f5', 'pre_delete_apps_absent'),
    ('P04-DTR-E05', 'e918c4d5ac43e4093c4890e3ad603ebe892cce057f6f63c8d23fa35931bb1b3f', 'pre_delete_repository_process_gate'),
    ('P04-DTR-E06', '91cab1ec577e9e4c83a7ccc77160638a700128a8836ddf509eab28ae3abf73ed', 'pre_delete_identity_hash_and_process_gate'),
    ('P04-DTR-E07', 'd435032682d75814cbad4d1475b0011781ab44eaecb900a6d8276ff6945dfe8c', 'pre_delete_fresh_window_valid'),
    ('P04-DTR-E08', '2b63b70d3af6c21270e886598327f5b8ec07e4978962907c40199c596739dacc', 'post_delete_active_exact_search_absence'),
    ('P04-DTR-E09', '91c934395f313ed7b9d15a7252fe054e9387a9fa61ff2336fa7bdc9e1a19076f', 'post_delete_operator_action_summary'),
    ('P04-DTR-E10', 'bba14dd86fb85015387f49f148bc76702f90aa3e952bb930d48df53760cf4826', 'post_delete_all_services_context'),
    ('P04-DTR-E11', '96e94c9475ec9275538efd4612c359648dcd38e558e90dd1cd55cee23769c04a', 'post_delete_all_exact_search_absence'),
    ('P04-DTR-E12', '90df658e1b7e5e490d8a3b8d0fff44fcbbb89d34415ddd6b61f742ef281a2346', 'post_delete_suspended_scope_absence'),
)
HASH_EXTRA_PATHS = {
    'backend/models.py',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
    'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
    'render.yaml',
}
FALSE_MARKERS = (
    'backup_restoreability_verified',
    'disposable_restore_rehearsal_complete',
    'delete_retry_authorized',
    'delete_retry_performed',
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
    'application_deployment',
    'render_delete_action_invoked_by_package',
    'retirement_execution_performed_by_package',
    'external_target_mutated_by_package',
    'p0_04_execution_authorized',
    'staging_0010_apply_authorized',
    'production_migration_authorized',
    'production_migration_executed',
    'fourth_external_runner_call_authorized',
    'new_disposable_target_authorized',
    'fresh_restore_governance_approved',
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
    values = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            values.append(ast.literal_eval(node.value))
    need(len(values) == 1, 'literal assignment ' + name)
    return values[0]


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
    root_source = read_text(ROOT_VALIDATOR)
    ci = read_text(CI)
    read_text(LOCKED_RUNNER)
    previous_docs = [read_text(path) for path in (RESTORE_AUTH_DOC, ABORT_DOC, RETIREMENT_AUTH_DOC)]
    prep_source = read_text(AUTH_PREP_VALIDATOR)
    previous_sources = [
        read_text(path)
        for path in (
            AUTH_REVIEW_VALIDATOR,
            EVIDENCE_PREP_VALIDATOR,
            RESTORE_AUTH_VALIDATOR,
            ABORT_VALIDATOR,
            RETIREMENT_AUTH_VALIDATOR,
        )
    ]

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1',
        'evidence_status': 'COMPLETE_DISPOSABLE_TARGET_RETIREMENT',
        'evidence_record_id': 'PMAI-P0-04-DTREE-V1-20260809',
        'retirement_execution_performed': 'true',
        'render_delete_action_invoked': 'true',
        'render_delete_action_count': '1',
        'target_deleted': 'true',
        'disposable_target_retirement_complete': 'true',
        'cleanup_evidence_complete': 'true',
        'retirement_authorization_consumed': 'true',
        'target_absent_from_active': 'true',
        'target_absent_from_suspended': 'true',
        'target_absent_from_all_services': 'true',
        'target_absence_verified': 'true',
        'authorization_commit': 'aa045118ed52ddbf54e44a6f2924d1f6afe7498b',
        'github_ci_gate_number': '191',
        'github_ci_gate_status': 'PASS',
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_CI_SHA256,
        'locked_runner_sha256': EXPECTED_LOCKED_RUNNER_SHA256,
        'active_0010_migration_file_count': '0',
        'target_logical_name': 'pet-med-ai-db-p0-04-disposable-restore-ohio',
        'target_service_identifier_sha256': 'fcd569994776e091f001f7213cd02432339e172e51889b2acf0a3987e0be7b48',
        'retirement_action_recorded_at_local': '2026-08-09T23:05:25+08:00',
        'retirement_action_recorded_at_utc': '2026-08-09T15:05:25Z',
        'retirement_completed_before_hard_deadline': 'true',
        'fresh_pre_delete_gate_completed': 'true',
        'fresh_target_identity_match': 'true',
        'fresh_target_status_available': 'true',
        'fresh_target_apps_zero': 'true',
        'fresh_target_dependency_absence': 'true',
        'fresh_external_restore_runner_process_count': '0',
        'fresh_retirement_window_valid': 'true',
        'retirement_external_evidence_artifact_count': str(len(EXPECTED_EVIDENCE)),
        'retirement_evidence_set_sha256': EXPECTED_EVIDENCE_SET_SHA256,
        'post_delete_active_exact_search_result_count': '0',
        'post_delete_suspended_target_result_count': '0',
        'post_delete_all_exact_search_result_count': '0',
        'post_delete_active_absence_verified': 'true',
        'post_delete_suspended_absence_verified': 'true',
        'post_delete_all_services_absence_verified': 'true',
        'post_delete_target_absence_unambiguous': 'true',
        'decision': 'HOLD_PMAI_P0_04_RESTORE_REHEARSAL_INCOMPLETE_PENDING_FRESH_RESTORE_GOVERNANCE_DECISION',
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, 'document marker ' + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == 'false', 'required false marker ' + key)

    canonical = ''.join(
        evidence_id + '=' + digest + '\n'
        for evidence_id, digest, _purpose in EXPECTED_EVIDENCE
    )
    need(hashlib.sha256(canonical.encode('utf-8')).hexdigest() == EXPECTED_EVIDENCE_SET_SHA256, 'evidence set digest')
    for index, (evidence_id, digest, purpose) in enumerate(EXPECTED_EVIDENCE, 1):
        prefix = 'retirement_evidence_{:02d}_'.format(index)
        need(marker(doc, prefix + 'id') == evidence_id, 'evidence id')
        need(marker(doc, prefix + 'purpose') == purpose, 'evidence purpose')
        need(marker(doc, prefix + 'sha256') == digest, 'evidence hash')

    forbidden = (
        r'(?i)postgres(?:ql)?://\S+',
        r'(?im)^\s*(?:export\s+)?DATABASE_URL\s*=',
        r'(?im)^\s*(?:export\s+)?SECRET_KEY\s*=',
        r'(?im)^\s*(?:password|passwd|pwd)\s*[:=]',
        r'(?i)\bdpg-[a-z0-9-]+\b',
        r'(?im)^\s*(?:\$\s*)?(?:sudo\s+)?(?:pg_restore|psql|alembic)(?:\s|$)',
    )
    for pattern in forbidden:
        need(re.search(pattern, doc) is None, 'forbidden secret identifier or command')

    need(sha256_path(ROOT / CI) == EXPECTED_CI_SHA256, 'CI hash')
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, 'locked runner hash')
    need(not glob.glob(str(ROOT / 'backend/migrations/versions/0010*.py')), 'active 0010 migration')

    targets = literal(root_source, 'TARGETS')
    hashes = literal(root_source, 'HASHES')
    need(isinstance(targets, list) and len(targets) == len(set(targets)), 'root TARGETS')
    need(isinstance(hashes, dict), 'root HASHES')
    need(DOC in targets and VALIDATOR in targets, 'new package protection')
    need(set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS, 'protected hash scope')
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), 'missing protected ' + rel)
        need(sha256_path(path) == expected_hash, 'protected hash ' + rel)

    need(ci_targets(ci) == targets, 'CI/root target equality')
    need(python_lines(ci) == EXPECTED_COMMANDS, 'CI approved validators')
    marker_line = '# PMAI-P0-04 disposable target retirement execution evidence v1'
    command_line = 'python3 ' + VALIDATOR + ' || exit 1'
    need(ci.splitlines().count(marker_line) == 1, 'CI marker count')
    need(ci.splitlines().count(command_line) == 1, 'CI command count')

    need(literal(prep_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_CI_SHA256, 'auth-prep CI rollover')
    for previous in previous_sources:
        need(literal(previous, 'EXPECTED_CI_SHA256') == EXPECTED_CI_SHA256, 'prior CI rollover')
        need(literal(previous, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'prior command rollover')
    for previous_doc in previous_docs:
        need(marker(previous_doc, 'final_ci_sha256') == EXPECTED_CI_SHA256, 'prior document CI rollover')
    need(marker(previous_docs[2], 'retirement_execution_performed') == 'false', 'authorization record stays point-in-time')
    need(marker(previous_docs[2], 'target_deleted') == 'false', 'authorization record target state stays point-in-time')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw evidence target')
    for rel in (DOC, VALIDATOR):
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Disposable Target Retirement Execution Evidence V1')
    print('stage_id=PMAI-P0-04')
    print('evidence_status=COMPLETE_DISPOSABLE_TARGET_RETIREMENT')
    print('retirement_execution_performed=true')
    print('render_delete_action_invoked=true')
    print('render_delete_action_count=1')
    print('target_deleted=true')
    print('target_absent_from_active=true')
    print('target_absent_from_suspended=true')
    print('target_absent_from_all_services=true')
    print('cleanup_evidence_complete=true')
    print('delete_retry_authorized=false')
    print('database_connection=false')
    print('restore_execution=false')
    print('backup_restoreability_verified=false')
    print('disposable_restore_rehearsal_complete=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=HOLD_PMAI_P0_04_RESTORE_REHEARSAL_INCOMPLETE_PENDING_FRESH_RESTORE_GOVERNANCE_DECISION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
