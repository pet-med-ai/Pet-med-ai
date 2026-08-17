#!/usr/bin/env python3
"""Validate PMAI-P0-04 Archive Root Contract Investigation V3 Execution Evidence V1."""

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
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_V1_CHECKLIST_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_V1_GO_NO_GO_V1.csv'
TEST_MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_V1_TEST_MATRIX_V1.csv'
AUTH_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_V1.md'
CANDIDATE_SOURCE = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V3_AUTHORIZED_CANDIDATE.py.txt'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_archive_root_contract_investigation_v3_execution_evidence_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_HEAD = '8f7a4a25908e874f406b08e9ae2d1dc9de69db26'
EXPECTED_PARENT = '0e6dfdd876227d88003bebc9edd966f0821c0b41'
EXPECTED_ISOLATED = '8d1dc8814ed8f80d8bc965b494c1c320fc08f228'
EXPECTED_PRIOR_CI_SHA256 = '27171bf84096af25dc25ff3f0153516108b92b22fec878b1afc9184df5c2dece'
EXPECTED_FINAL_CI_SHA256 = 'a433a4790a1ea2a638640906dd43e8402bfccaa463967968eb0e1eda915ad6d4'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_CANDIDATE_SOURCE_SHA256 = '6800bc57c018ad17deb84b2c821baad4752e23f9aa432b01d64f9518737d5e14'
EXPECTED_V1_RESULT_SHA256 = 'c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893'
EXPECTED_V2_RESULT_SHA256 = '3eef22eeab17779b4e5499f53c22caf22fd5d0fd7c107cdaca6cbb8926ebf028'
EXPECTED_V3_RESULT_SHA256 = '2d133850451ef0941443c4588f9f649aafa54f9a1d1e5670e54529f541429040'
AUTHORIZATION_RECORD_ID = 'PMAI-P0-04-ARCI-V3-AUTH-V1-20260813'
EVIDENCE_RECORD_ID = 'PMAI-P0-04-ARCI-V3-EXEC-EVID-V1-20260813'
DECISION = 'GO_TO_SEPARATE_RESTORE_RUNNER_DESIGN_PREPARATION_V3'
NEXT_ACTION = 'SEPARATE_RESTORE_RUNNER_DESIGN_PREPARATION_V3_REQUIRED'

EXPECTED_JSON = {"all_members_contained_by_logical_root":True,"approved_archive_sha256_match":True,"archive_member_count":29,"archive_modified":False,"archive_uncompressed_size_bytes":196874,"authorization_record_id":AUTHORIZATION_RECORD_ID,"automatic_retry":False,"case_collision_count":0,"cumulative_archive_listing_attempt_number":3,"decision":DECISION,"directory_entry_count":3,"duplicate_normalized_member_count":0,"implementation_sha256":EXPECTED_CANDIDATE_SOURCE_SHA256,"leading_dot_prefix_member_count":28,"listing_tool_identity":"PYTHON_STDLIB_TARFILE_METADATA_SCAN","listing_tool_version":"3.9.6","logical_root_fingerprint_sha256":"fcded0b983602688dfdd29b9742cdea17d429d8a19567c01feca91387c7c6d47","member_depth_max":3,"member_depth_min":1,"member_extraction_performed":False,"member_name_set_sha256":"3a509a2084dd279e644c95d83d77babe555f21de76950c1c092421952a75e229","member_payload_read":False,"normalization_reason_counts":{"ACCEPTED_CANONICAL_RELATIVE":0,"ACCEPTED_LEADING_DOT_PREFIX":28,"ACCEPTED_ROOT_MARKER":1,"REJECT_ABSOLUTE_PATH":0,"REJECT_BACKSLASH":0,"REJECT_CONTROL_CHARACTER":0,"REJECT_DRIVE_PREFIX":0,"REJECT_EMPTY_COMPONENT":0,"REJECT_EMPTY_PATH":0,"REJECT_EXCESSIVE_COMPONENT_DEPTH":0,"REJECT_EXCESSIVE_NAME_BYTES":0,"REJECT_INTERNAL_DOT_COMPONENT":0,"REJECT_PARENT_COMPONENT":0,"REJECT_ROOT_MARKER_NON_DIRECTORY":0},"normalized_path_violation_count":0,"numeric_metric_saturation_detected":False,"outer_container_classification":"GZIP_TAR","raw_external_path_emitted":False,"raw_member_names_emitted":False,"regular_file_count":26,"restore_execution":False,"restore_input_kind_classification":"PG_DIRECTORY_ROOT_DEEP_WRAPPED","root_contract_resolved":True,"root_layout_classification":"PG_DIRECTORY_ROOT_DEEP_WRAPPED","root_marker_count":1,"shared_prefix_depth":2,"stop_code":"NONE","toc_dat_candidate_count":1,"toc_dat_normalized_depth":2,"toc_dat_relation_category":"IMMEDIATE_CHILD_OF_IDENTIFIED_LOGICAL_ROOT","top_level_component_count":1,"unsafe_or_special_member_count":0,"v3_attempt_number":1,"wrapper_depth":2}

PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
REQUIRED_TEST_IDS = {'PMAI-P0-04-ARCI-V3-EXEC-EVID-T{:03d}'.format(i) for i in range(1, 36)}


def need(ok: bool, message: str) -> None:
    if not ok:
        print('NO-GO: ' + message, file=sys.stderr)
        raise SystemExit(1)


def read_text(rel: str) -> str:
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), 'missing or unsafe ' + rel)
    return path.read_text(encoding='utf-8')


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marker(value: str, key: str) -> str:
    found = re.findall(r'(?m)^' + re.escape(key) + r'=([^\r\n]+)$', value)
    need(found and len(set(found)) == 1, 'marker consistency ' + key)
    return found[0]


def read_csv(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def literal(source: str, name: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    return None
    return None


def ci_targets(value: str) -> list[str]:
    block = re.search(r'(?ms)^TARGETS=\(\n(.*?)^\)\s*$', value)
    need(block is not None, 'CI TARGETS block')
    return re.findall(r'^\s*"([^"]+)"\s*$', block.group(1), flags=re.M)


def python_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip().startswith('python3 ') and not line.strip().startswith('python3 -m py_compile ')]


def main() -> int:
    doc = read_text(DOC)
    auth_doc = read_text(AUTH_DOC)
    ci = read_text(CI)

    expected_markers = {
        'stage_id': 'PMAI-P0-04',
        'substage': 'ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_V1',
        'package_status': 'V3_EXECUTION_EVIDENCE_RECORD_ONLY',
        'evidence_record_id': EVIDENCE_RECORD_ID,
        'authorization_review_commit': EXPECTED_HEAD,
        'authorization_review_commit_parent': EXPECTED_PARENT,
        'github_ci_gate_number': '203',
        'github_ci_gate_status': 'PASS',
        'prior_ci_sha256': EXPECTED_PRIOR_CI_SHA256,
        'final_ci_sha256': EXPECTED_FINAL_CI_SHA256,
        'local_isolated_branch': EXPECTED_ISOLATED,
        'remote_isolated_branch': EXPECTED_ISOLATED,
        'authorization_record_id': AUTHORIZATION_RECORD_ID,
        'v3_archive_listing_attempts_consumed': '1',
        'v3_archive_listing_attempts_remaining': '0',
        'cumulative_archive_listing_attempts_consumed': '3',
        'root_contract_resolved': 'true',
        'root_layout_classification': 'PG_DIRECTORY_ROOT_DEEP_WRAPPED',
        'wrapper_depth': '2',
        'sanitized_v3_investigation_result_sha256': EXPECTED_V3_RESULT_SHA256,
        'backup_restoreability_verified': 'false',
        'disposable_restore_rehearsal_complete': 'false',
        'decision': DECISION,
        'next_action': NEXT_ACTION,
    }
    for key, expected in expected_markers.items():
        need(marker(doc, key) == expected, 'document marker ' + key)

    json_blocks = re.findall(r'(?ms)^~~~json\n(.*?)\n~~~$', doc)
    need(len(json_blocks) == 1, 'sanitized JSON block')
    result = json.loads(json_blocks[0])
    need(result == EXPECTED_JSON, 'sanitized JSON exact result')
    canonical = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
    need(canonical == json_blocks[0], 'sanitized JSON canonical form')
    need(hashlib.sha256(canonical.encode()).hexdigest() == EXPECTED_V3_RESULT_SHA256, 'sanitized JSON SHA')
    need(len(result) == 43, 'sanitized JSON field count')

    reason_counts = result['normalization_reason_counts']
    need(sum(reason_counts.values()) == 29, 'normalization reason total')
    need(result['root_contract_resolved'] is True, 'root contract result')
    need(result['root_layout_classification'] == 'PG_DIRECTORY_ROOT_DEEP_WRAPPED', 'root layout')
    need(result['wrapper_depth'] == result['toc_dat_normalized_depth'] == 2, 'depth metrics')
    need(result['all_members_contained_by_logical_root'] is True, 'logical root containment')
    need(result['toc_dat_relation_category'] == 'IMMEDIATE_CHILD_OF_IDENTIFIED_LOGICAL_ROOT', 'toc relation')
    need(result['stop_code'] == 'NONE' and result['decision'] == DECISION, 'GO decision')
    for key in ('member_payload_read', 'member_extraction_performed', 'archive_modified', 'raw_member_names_emitted', 'raw_external_path_emitted', 'automatic_retry', 'restore_execution', 'numeric_metric_saturation_detected'):
        need(result[key] is False, 'result safety ' + key)

    checklist = read_csv(CHECKLIST)
    need(len(checklist) == 54 and len({row['control_id'] for row in checklist}) == 54, 'checklist rows')
    need(all(row['status'] == 'PASS' for row in checklist), 'checklist status')
    gates = read_csv(GO_NO_GO)
    need(len(gates) == 22 and len({row['gate_id'] for row in gates}) == 22, 'Go/No-Go rows')
    by_gate = {row['gate']: row for row in gates}
    need(by_gate['root contract resolved required']['status'] == 'PASS', 'root gate')
    need(by_gate['backup restoreability verified required for migration']['status'] == 'HOLD', 'restoreability gate')
    need(by_gate['restore rehearsal complete required for migration']['status'] == 'HOLD', 'rehearsal gate')
    tests = read_csv(TEST_MATRIX)
    need({row['test_id'] for row in tests} == REQUIRED_TEST_IDS, 'test matrix IDs')
    need(all(row['status'] == 'DESIGNED' for row in tests), 'test matrix status')

    need(sha256_path(ROOT / CANDIDATE_SOURCE) == EXPECTED_CANDIDATE_SOURCE_SHA256, 'candidate source hash')
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, 'locked runner hash')
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, 'CI hash')
    need(not glob.glob(str(ROOT / 'backend/migrations/versions/0010*.py')), 'active 0010 migration')
    source = read_text(CANDIDATE_SOURCE)
    need(literal(source, 'AUTHORIZATION_RECORD_ID') == AUTHORIZATION_RECORD_ID, 'candidate authorization id')
    need(literal(source, 'EXPECTED_V3_ATTEMPT_NUMBER') == 1, 'candidate V3 attempt')
    need(literal(source, 'EXPECTED_CUMULATIVE_ATTEMPT_NUMBER') == 3, 'candidate cumulative attempt')
    need(literal(source, 'MEMBER_PAYLOAD_READ_ALLOWED') is False, 'payload forbidden')
    need(literal(source, 'MEMBER_EXTRACTION_ALLOWED') is False, 'extraction forbidden')
    need(literal(source, 'AUTOMATIC_RETRY_ALLOWED') is False, 'retry forbidden')

    need(marker(auth_doc, 'authorization_record_id') == AUTHORIZATION_RECORD_ID, 'auth document id')
    need(marker(auth_doc, 'authorized_candidate_v3_source_sha256') == EXPECTED_CANDIDATE_SOURCE_SHA256, 'auth source hash')
    auth_pointer = {
        'subsequent_v3_execution_evidence_entry_commit': EXPECTED_HEAD,
        'subsequent_v3_execution_evidence_ci_gate': '203',
        'subsequent_v3_execution_evidence_ci_status': 'PASS',
        'subsequent_v3_execution_implementation_sha256': EXPECTED_CANDIDATE_SOURCE_SHA256,
        'subsequent_v3_sanitized_result_sha256': EXPECTED_V3_RESULT_SHA256,
        'subsequent_v3_archive_listing_attempts_consumed': '1',
        'subsequent_cumulative_archive_listing_attempts_consumed': '3',
        'subsequent_archive_listing_attempts_remaining': '0',
        'subsequent_v3_root_contract_resolved': 'true',
        'subsequent_v3_root_layout_classification': 'PG_DIRECTORY_ROOT_DEEP_WRAPPED',
        'subsequent_v3_wrapper_depth': '2',
        'subsequent_backup_restoreability_verified': 'false',
        'subsequent_v3_decision': DECISION,
        'subsequent_v3_retry_authorized': 'false',
    }
    for key, expected in auth_pointer.items():
        need(marker(auth_doc, key) == expected, 'authorization pointer ' + key)

    targets = ci_targets(ci)
    need(len(targets) == 152 and len(targets) == len(set(targets)), 'CI TARGETS canonical')
    need(PACKAGE_PATHS.issubset(set(targets)), 'evidence package targets')
    command = 'python3 ' + VALIDATOR + ' || exit 1'
    runner_design_command = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_design_preparation_v3.py || exit 1'
    runner_authorization_review_command = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_authorization_review_v1.py || exit 1'
    implementation_preparation_command = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_preparation_v1.py || exit 1'
    implementation_authorization_review_command = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_authorization_review_v1.py || exit 1'
    fresh_target_preparation_command = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_preparation_v3.py || exit 1'
    fresh_target_authorization_review_command = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_review_v3.py || exit 1'
    fresh_target_external_execution_authorization_command = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_external_execution_authorization_v3.py || exit 1'
    fresh_target_execution_evidence_command = 'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_execution_evidence_v3.py || exit 1'
    need(ci.splitlines().count('# PMAI-P0-04 archive root contract investigation V3 execution evidence v1') == 1, 'CI marker count')
    need(ci.splitlines().count(command) == 1, 'CI command count')
    need(
        len(python_lines(ci)) == 31
        and python_lines(ci)[-12:-3] == [command, runner_design_command, runner_authorization_review_command, implementation_preparation_command, implementation_authorization_review_command, fresh_target_preparation_command, fresh_target_authorization_review_command, fresh_target_external_execution_authorization_command, fresh_target_execution_evidence_command],
        'CI command order',
    )

    unsafe_suffixes = ('.png', '.jpg', '.jpeg', '.json', '.tar', '.tar.gz', '.db', '.bak', '.save')
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), 'raw or unsafe target')
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith('\n'), 'final newline ' + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), 'trailing whitespace {}:{}'.format(rel, line_no))

    print('PASS: PMAI-P0-04 Archive Root Contract Investigation V3 Execution Evidence V1')
    print('stage_id=PMAI-P0-04')
    print('substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_V1')
    print('evidence_status=COMPLETE_SINGLE_V3_METADATA_ATTEMPT_ROOT_CONTRACT_RESOLVED')
    print('v3_archive_listing_attempts_consumed=1')
    print('cumulative_archive_listing_attempts_consumed=3')
    print('root_contract_resolved=true')
    print('root_layout_classification=PG_DIRECTORY_ROOT_DEEP_WRAPPED')
    print('wrapper_depth=2')
    print('backup_restoreability_verified=false')
    print('disposable_restore_rehearsal_complete=false')
    print('restore_runner_created=false')
    print('restore_execution=false')
    print('p0_04_execution_authorized=false')
    print('staging_0010_apply_authorized=false')
    print('decision=' + DECISION)
    print('next_action=' + NEXT_ACTION)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
