#!/usr/bin/env python3
"""Validate PMAI-P0-04 disposable-target retirement authorization review."""

from __future__ import annotations

import ast
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py'
ABORT_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md'
ABORT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
AUTH_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
AUTH_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py'
EVIDENCE_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py'
RESTORE_AUTH_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py'
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_CI_SHA256 = 'e09532f6b3069ab07e7f6d155457791ccad1844617999b95cee2cad7dea4d508'
EXPECTED_PRIOR_CI_SHA256 = 'ee5b75fe566218490ca1edef2405596309a6302879ec486249b435ae07832cde'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_ABORT_DOC_COMMITTED_SHA256 = 'c1d44d9652ff7fc14fafa2747572716d1d7aaf3b87052008eb2dda6cded658eb'
EXPECTED_ABORT_DOC_CURRENT_SHA256 = '94aab2c50f508f4e1714725cec38dc11b76a98217ccc2287866654c15e3c3b1f'
EXPECTED_APPROVAL_STATEMENT = '批准 PMAI-P0-04 仅对 pet-med-ai-db-p0-04-disposable-restore-ohio 执行一次控制面删除并完成退休留证；删除前必须重新核验目标身份、Available、Apps=0、无依赖且无外部 restore runner 进程，并须在 2026-08-11 00:08 +08:00 前完成；不授权 production、staging source、数据库连接、Restore/Recovery、pg_restore、psql、Alembic、0010 migration、locked runner 或任何应用部署。'
EXPECTED_APPROVAL_STATEMENT_SHA256 = '525efdddd4f15257e1211ef3e0b7c5215ef5bf54aa6560f07e1e26c6ed8ea6f8'
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
 '|| exit 1']
HASH_EXTRA_PATHS = {
    'backend/models.py',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
    'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
    'render.yaml',
}
FALSE_MARKERS = (
    'retirement_execution_performed',
    'render_delete_action_invoked',
    'target_deleted',
    'cleanup_evidence_complete',
    'fresh_pre_delete_gate_completed',
    'technical_restore_attempt_reserved',
    'database_connection',
    'database_write',
    'restore_execution',
    'backup_restoreability_verified',
    'disposable_restore_rehearsal_complete',
    'fourth_external_runner_call_authorized',
    'fourth_external_runner_call_permitted',
    'v2_runner_execution_authorized',
    'v3_runner_preparation_authorized',
    'retirement_connection_value_required',
    'retirement_database_connection_required',
    'retirement_database_write_required',
    'retirement_restore_action_required',
    'retirement_runner_created',
    'retirement_api_automation_authorized',
    'retirement_cli_automation_authorized',
    'package_pg_restore_invoked',
    'package_psql_invoked',
    'package_alembic_invoked',
    'migration_created',
    'migration_executed',
    'restore_runner_created',
    'restore_runner_modified',
    'locked_runner_invoked',
    'application_deployment',
    'target_retirement_script_created',
    'package_external_target_mutated',
    'package_render_delete_action_invoked',
    'package_retirement_execution_performed',
    'package_target_deleted',
    'corrected_migration_implementation_authorized',
    'active_0010_migration_file_created',
    'p0_04_execution_authorized',
    'staging_0010_apply_authorized',
    'production_migration_authorized',
    'production_migration_executed',
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
    source = read_text(VALIDATOR)
    abort_doc = read_text(ABORT_DOC)
    abort_source = read_text(ABORT_VALIDATOR)
    root_source = read_text(ROOT_VALIDATOR)
    prep_source = read_text(AUTH_PREP_VALIDATOR)
    auth_source = read_text(AUTH_REVIEW_VALIDATOR)
    evidence_source = read_text(EVIDENCE_PREP_VALIDATOR)
    restore_source = read_text(RESTORE_AUTH_VALIDATOR)
    ci = read_text(CI)
    read_text(LOCKED_RUNNER)

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1',
        'review_status': 'APPROVED_DISPOSABLE_TARGET_RETIREMENT_ONLY',
        'authorization_record_id': 'PMAI-P0-04-DTRAR-V1-20260809',
        'authorization_scope': 'ONE_EXACT_DISPOSABLE_RENDER_POSTGRES_SERVICE_CONTROL_PLANE_DELETE_ONLY',
        'approval_statement_sha256': EXPECTED_APPROVAL_STATEMENT_SHA256,
        'disposable_target_retirement_authorized': 'true',
        'disposable_target_deletion_authorized': 'true',
        'target_retirement_execution_authorized': 'true',
        'retirement_authorization_single_use': 'true',
        'retirement_authorization_expires_at_local': '2026-08-11T00:08+08:00',
        'repository_authorization_record_only': 'true',
        'local_main': '07446387f551aa5c544ddf8531d076c78c44a204',
        'origin_main': '07446387f551aa5c544ddf8531d076c78c44a204',
        'github_ci_gate_number': '190',
        'github_ci_gate_status': 'PASS',
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_CI_SHA256,
        'locked_runner_sha256': EXPECTED_LOCKED_RUNNER_SHA256,
        'abort_preparation_document_committed_sha256': EXPECTED_ABORT_DOC_COMMITTED_SHA256,
        'abort_preparation_document_current_sha256': EXPECTED_ABORT_DOC_CURRENT_SHA256,
        'third_and_final_external_runner_call_status': 'PRE_EXECUTION_ABORT',
        'third_and_final_external_runner_stop_code': 'BACKUP_DIRECTORY_ROOT_MISMATCH',
        'external_runner_execute_call_count': '3',
        'no_further_restore_retry': 'true',
        'target_logical_name': 'pet-med-ai-db-p0-04-disposable-restore-ohio',
        'target_service_identifier_sha256': 'fcd569994776e091f001f7213cd02432339e172e51889b2acf0a3987e0be7b48',
        'target_retirement_hard_deadline_local': '2026-08-11T00:08+08:00',
        'fresh_recheck_max_age_minutes': '5',
        'retirement_execution_channel': 'RENDER_DASHBOARD_MANUAL_CONTROL_PLANE_ONLY',
        'retirement_action': 'DELETE_EXACT_DISPOSABLE_POSTGRES_SERVICE',
        'retirement_action_count_limit': '1',
        'decision': 'GO_TO_EXTERNAL_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_ONLY',
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, 'document marker ' + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == 'false', 'required false marker ' + key)

    need(
        hashlib.sha256(EXPECTED_APPROVAL_STATEMENT.encode('utf-8')).hexdigest()
        == EXPECTED_APPROVAL_STATEMENT_SHA256,
        'approval statement digest',
    )
    need(sha256_path(ROOT / ABORT_DOC) == EXPECTED_ABORT_DOC_CURRENT_SHA256, 'abort preparation document current hash')
    need(marker(abort_doc, 'third_and_final_external_runner_call_status') == 'PRE_EXECUTION_ABORT', 'abort entry status')
    need(marker(abort_doc, 'fourth_external_runner_call_authorized') == 'false', 'no fourth call entry gate')
    need(marker(abort_doc, 'disposable_target_retirement_authorized') == 'false', 'separate prior authorization boundary')

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
    marker_line = '# PMAI-P0-04 disposable target retirement authorization review v1'
    command_line = 'python3 ' + VALIDATOR + ' || exit 1'
    need(ci.splitlines().count(marker_line) == 1, 'CI marker count')
    need(ci.splitlines().count(command_line) == 1, 'CI command count')

    need(literal(prep_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_CI_SHA256, 'auth-prep CI rollover')
    for previous in (auth_source, evidence_source, restore_source, abort_source):
        need(literal(previous, 'EXPECTED_CI_SHA256') == EXPECTED_CI_SHA256, 'prior CI rollover')
        need(literal(previous, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'prior command rollover')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw evidence target')
    for rel in (DOC, VALIDATOR):
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))
    need('target_retirement_script_created=false' in doc, 'no delete script')

    print('PASS: PMAI-P0-04 Disposable Target Retirement Authorization Review V1')
    print('stage_id=PMAI-P0-04')
    print('review_status=APPROVED_DISPOSABLE_TARGET_RETIREMENT_ONLY')
    print('authorization_scope=ONE_EXACT_DISPOSABLE_RENDER_POSTGRES_SERVICE_CONTROL_PLANE_DELETE_ONLY')
    print('disposable_target_retirement_authorized=true')
    print('disposable_target_deletion_authorized=true')
    print('target_retirement_execution_authorized=true')
    print('repository_only=true')
    print('network_access=false')
    print('database_connection=false')
    print('database_write=false')
    print('restore_execution=false')
    print('retirement_execution_performed=false')
    print('render_delete_action_invoked=false')
    print('target_deleted=false')
    print('fourth_external_runner_call_authorized=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=GO_TO_EXTERNAL_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_ONLY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
