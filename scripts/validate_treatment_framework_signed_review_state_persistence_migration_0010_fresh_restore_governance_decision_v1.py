#!/usr/bin/env python3
"""Validate PMAI-P0-04 Fresh Restore Governance Decision V1."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_RESTORE_GOVERNANCE_DECISION_V1_TEST_MATRIX_V1.csv'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_restore_governance_decision_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
AUTH_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
PREVIOUS_VALIDATORS = (
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_authorization_review_v1.py',
    'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_retirement_execution_evidence_v1.py',
)
ROLLING_DOCS = (
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_REVIEW_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1.md',
)
RETIREMENT_DOC = ROLLING_DOCS[-1]
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = '0bc76d10af7a0168048fb007dff9e156341b9b4f'
EXPECTED_PARENT = 'aa045118ed52ddbf54e44a6f2924d1f6afe7498b'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = 'ccbed9cc605d145450a7a01deb5294799e284d5cbc694741cc95ebd18a095d4d'
EXPECTED_FINAL_CI_SHA256 = 'e09532f6b3069ab07e7f6d155457791ccad1844617999b95cee2cad7dea4d508'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
CI_COMMAND = 'python3 ' + VALIDATOR + ' || exit 1'
EXPECTED_COMMANDS = [
    'python3 ' + ROOT_VALIDATOR,
    'python3 ' + AUTH_PREP_VALIDATOR + ' || exit 1',
    *['python3 ' + path + ' || exit 1' for path in PREVIOUS_VALIDATORS],
    CI_COMMAND,
]
PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
HASH_EXTRA_PATHS = {
    'backend/models.py',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
    'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
    'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
    'render.yaml',
}
FALSE_KEYS = (
    'retired_target_reuse_allowed',
    'retired_target_recreation_inferred',
    'retirement_delete_retry_authorized',
    'retirement_delete_retry_performed',
    'legacy_restore_execution_started',
    'legacy_backup_restoreability_verified',
    'legacy_target_reuse_allowed',
    'legacy_runner_v1_reuse_allowed',
    'legacy_runner_v2_reuse_allowed',
    'legacy_authorization_reuse_allowed',
    'legacy_attempt_state_reuse_allowed',
    'legacy_execution_evidence_reuse_allowed',
    'legacy_fourth_external_runner_call_authorized',
    'fresh_chain_restore_attempt_authorized',
    'archive_root_contract_investigation_authorized',
    'archive_root_contract_investigation_started',
    'backup_archive_listing_invoked',
    'backup_archive_extracted',
    'backup_archive_modified',
    'backup_archive_repackaged',
    'new_restore_runner_design_authorized',
    'new_restore_runner_authorized',
    'new_disposable_target_authorized',
    'new_restore_execution_authorized',
    'network_access',
    'repository_apply_authorized',
    'git_stage_authorized',
    'git_commit_authorized',
    'git_push_authorized',
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
    'render_target_created',
    'render_target_deleted',
    'external_target_mutated',
    'corrected_migration_implementation_authorized',
    'p0_04_execution_authorized',
    'staging_0010_apply_authorized',
    'production_migration_authorized',
    'production_migration_executed',
    'backup_restoreability_verified',
    'disposable_restore_rehearsal_complete',
)
TRUE_KEYS = (
    'route_a_evaluated',
    'route_b_evaluated',
    'fresh_restore_governance_decision_complete',
    'fresh_restore_governance_route_b_selected',
    'fresh_restore_governance_route_b_approved',
    'fresh_restore_governance_approved',
    'disposable_target_retirement_evidence_complete',
    'disposable_target_retirement_complete',
    'retired_target_absence_verified',
    'backup_original_bytes_preserved',
    'repository_only',
    'ready_for_separate_archive_root_contract_investigation_preparation',
)
REQUIRED_TEST_IDS = {
    'PMAI-P0-04-FRGD-T{:03d}'.format(number)
    for number in range(1, 25)
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
    retirement_doc = read_text(RETIREMENT_DOC)

    required = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'FRESH_RESTORE_GOVERNANCE_DECISION_V1',
        'package_status': 'GOVERNANCE_DECISION_ONLY',
        'decision_record_id': 'PMAI-P0-04-FRGD-V1-20260810',
        'decision_authority_source': 'EXPLICIT_USER_AUTHORIZATION_CONTINUE_DEVELOPMENT_20260810',
        'selected_route': 'ROUTE_B_REBUILD_FRESH_RESTORE_GOVERNANCE_CHAIN_FROM_ZERO',
        'decision': 'GO_TO_PMAI_P0_04_FRESH_RESTORE_GOVERNANCE_CHAIN_PREPARATION',
        'next_action': 'SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1',
        'local_main': EXPECTED_HEAD,
        'origin_main': EXPECTED_HEAD,
        'main_parent': EXPECTED_PARENT,
        'github_ci_gate_number': '192',
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
        'legacy_external_runner_call_count': '3',
        'legacy_third_call_stop_code': 'BACKUP_DIRECTORY_ROOT_MISMATCH',
        'fresh_chain_restore_attempt_budget': '1',
        'archive_root_contract_investigation_scope': 'LIST_ONLY_NO_EXTRACTION_NO_WRITE',
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, 'document marker ' + key)
    for key in TRUE_KEYS:
        need(marker(doc, key) == 'true', 'required true marker ' + key)
    for key in FALSE_KEYS:
        need(marker(doc, key) == 'false', 'required false marker ' + key)

    need('### Route A — NO-GO / pause PMAI-P0-04' in doc, 'Route A comparison')
    need('### Route B — rebuild a fresh restore governance chain from zero' in doc, 'Route B comparison')

    forbidden = (
        r'(?i)postgres(?:ql)?://\S+',
        r'(?im)^\s*(?:export\s+)?DATABASE_URL\s*=',
        r'(?im)^\s*(?:export\s+)?SECRET_KEY\s*=',
        r'(?im)^\s*(?:password|passwd|pwd)\s*[:=]',
        r'(?i)\bdpg-[a-z0-9-]+\b',
        r'(?im)^\s*(?:\$\s*)?(?:sudo\s+)?(?:pg_restore|psql|alembic)(?:\s|$)',
    )
    for pattern in forbidden:
        need(re.search(pattern, package_text) is None, 'forbidden secret identifier or command')

    checklist = read_csv(CHECKLIST)
    need(len(checklist) == 30, 'checklist row count')
    by_control = {row.get('control', ''): row for row in checklist}
    need(len(by_control) == len(checklist), 'checklist unique controls')
    for key in (
        'retired_target_reuse_allowed',
        'legacy_runner_v1_reuse_allowed',
        'legacy_runner_v2_reuse_allowed',
        'legacy_authorization_reuse_allowed',
        'legacy_fourth_external_runner_call_authorized',
        'archive_root_contract_investigation_authorized',
        'backup_archive_listing_invoked',
        'backup_archive_extracted',
        'backup_archive_modified',
        'backup_archive_repackaged',
        'new_restore_runner_authorized',
        'new_disposable_target_authorized',
        'new_restore_execution_authorized',
        'database_connection',
        'restore_execution',
        'migration_created',
        'staging_0010_apply_authorized',
        'application_deployment',
        'backup_restoreability_verified',
        'disposable_restore_rehearsal_complete',
    ):
        row = by_control.get(key)
        need(row is not None and row.get('expected') == 'false' and row.get('current') == 'false', 'checklist false control ' + key)
    need(by_control['selected_route']['current'] == required['selected_route'], 'checklist selected route')
    need(by_control['fresh_restore_governance_route_b_approved']['current'] == 'true', 'checklist route approval')

    decisions = read_csv(GO_NO_GO)
    need(len(decisions) == 1, 'Go/No-Go row count')
    decision = decisions[0]
    need(decision.get('selected_route') == required['selected_route'], 'Go/No-Go selected route')
    need(decision.get('governance_route_authorized') == 'true', 'Go/No-Go governance route')
    need(decision.get('external_execution_authorized') == 'false', 'Go/No-Go external execution')
    need(decision.get('decision') == required['decision'], 'Go/No-Go decision')

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
    marker_line = '# PMAI-P0-04 fresh restore governance decision v1'
    need(ci.splitlines().count(marker_line) == 1, 'CI marker count')
    need(ci.splitlines().count(CI_COMMAND) == 1, 'CI command count')

    prep_source = read_text(AUTH_PREP_VALIDATOR)
    need(literal(prep_source, 'EXPECTED_FINAL_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'auth-prep CI rollover')
    for rel in PREVIOUS_VALIDATORS:
        source = read_text(rel)
        need(literal(source, 'EXPECTED_CI_SHA256') == EXPECTED_FINAL_CI_SHA256, 'prior CI rollover ' + rel)
        need(literal(source, 'EXPECTED_COMMANDS') == EXPECTED_COMMANDS, 'prior command rollover ' + rel)
    for rel in ROLLING_DOCS:
        need(marker(read_text(rel), 'final_ci_sha256') == EXPECTED_FINAL_CI_SHA256, 'prior document CI rollover ' + rel)
    need(marker(retirement_doc, 'fresh_restore_governance_approved') == 'false', 'retirement evidence remains point-in-time')
    need(marker(retirement_doc, 'target_deleted') == 'true', 'retirement evidence target state')

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Fresh Restore Governance Decision V1')
    print('stage_id=PMAI-P0-04')
    print('substage=FRESH_RESTORE_GOVERNANCE_DECISION_V1')
    print('selected_route=ROUTE_B_REBUILD_FRESH_RESTORE_GOVERNANCE_CHAIN_FROM_ZERO')
    print('fresh_restore_governance_route_b_approved=true')
    print('external_execution_authorized=false')
    print('archive_root_contract_investigation_authorized=false')
    print('new_restore_runner_authorized=false')
    print('new_disposable_target_authorized=false')
    print('new_restore_execution_authorized=false')
    print('backup_restoreability_verified=false')
    print('disposable_restore_rehearsal_complete=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=GO_TO_PMAI_P0_04_FRESH_RESTORE_GOVERNANCE_CHAIN_PREPARATION')
    print('next_action=SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
