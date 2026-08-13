#!/usr/bin/env python3
"""Validate PMAI-P0-04 V2 pre-execution-abort and retirement preparation."""

from __future__ import annotations

import ast
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1.md'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_external_disposable_restore_v2_pre_execution_abort_evidence_and_disposable_target_retirement_preparation_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
AUTH_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
AUTH_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py'
EVIDENCE_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py'
RESTORE_AUTH_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py'
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_CI_SHA256 = 'd6cae61ff10138ae48be1832291aeefc19442ac68b323d4153939d1fbf19ea2d'
EXPECTED_LOCKED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
EXPECTED_V2_RUNNER_SHA256 = 'e36c62f2a69c97c03c97cf9b76edb42759f4bdea5ae987acc34b9c6f4c356cf5'
EXPECTED_BACKUP_SHA256 = 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7'
EXPECTED_BACKUP_TOC_SHA256 = '6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c'
EXPECTED_EVIDENCE_SET_SHA256 = 'dc725fccd01d4a15f2faaa327cb3ebdfe9d833465a831be5171e6b589043fef1'
EXPECTED_EVIDENCE = (('P04-V2A-E01', '2521d0971ace653f644749fddee20e2a49ea5d768a5b5a358d86b6e6bdac3c40', 'fresh_pre_execution_status_version_region'),
 ('P04-V2A-E02', '2c6f0a725cdb9d91d1a069f77e79bb085d9d1ed732b14457585386768ddcc37d', 'fresh_pre_execution_storage_autoscaling_connection_pool'),
 ('P04-V2A-E03', '35ef0c19546c2759a5a3458e807e0ec8f1bb6ac55b436e5b2b2de02c53222ed2', 'fresh_pre_execution_instance_and_high_availability'),
 ('P04-V2A-E04', 'f61f0192db3d919a3bda0f6c31810e9582500cdd6fd20a2aed82cca85d3e48e9', 'fresh_pre_execution_application_isolation'),
 ('P04-V2A-E05', '1413b1eb0ba65457dcd483439a4dbd6a92695b81327ff4960d4e05b0304c05ba', 'third_final_call_pre_execution_abort_terminal'),
 ('P04-V2A-E06', '6294ce472ca7b3b32a7c292b40afd35ac3f51031ae6687abbaada2f44b8d3482', 'post_abort_target_available_status'),
 ('P04-V2A-E07', 'd80fce477cb7d19462ac4d7a6dc90a0448e6c20c24fbb932f77ceb9cd7c51e49', 'post_abort_storage_autoscaling_connection_pool_instance'))
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
 '|| exit 1']
HASH_EXTRA_PATHS = {'backend/models.py',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md',
 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt',
 'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md',
 'render.yaml'}
FALSE_MARKERS = (
    'fourth_external_runner_call_authorized',
    'fourth_external_runner_call_permitted',
    'v2_runner_execution_authorized',
    'v3_runner_preparation_authorized',
    'restore_execution_started',
    'restore_execution_completed',
    'technical_restore_attempt_reserved',
    'backup_restoreability_verified',
    'disposable_restore_rehearsal_complete',
    'disposable_target_retirement_authorized',
    'disposable_target_deletion_authorized',
    'disposable_target_deleted',
    'target_retirement_authorization_requested',
    'target_retirement_authorization_present',
    'target_retirement_execution_authorized',
    'render_delete_action_invoked',
    'network_access',
    'database_connection',
    'database_write',
    'restore_execution',
    'package_pg_restore_invoked',
    'package_psql_invoked',
    'package_alembic_invoked',
    'migration_created',
    'migration_executed',
    'restore_runner_created',
    'restore_runner_modified',
    'restore_runner_execution_enabled',
    'locked_runner_invoked',
    'application_deployment',
    'target_retirement_script_created',
    'corrected_migration_implementation_authorized',
    'active_0010_migration_file_created',
    'staging_0010_migration_executed',
    'p0_04_execution_authorized',
    'staging_0010_apply_authorized',
    'production_migration_authorized',
    'production_migration_executed',
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
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def read_text(rel: str) -> str:
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + rel)
    return path.read_text(encoding="utf-8")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def marker(value: str, key: str) -> str:
    found = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", value)
    need(len(found) == 1, "marker count " + key)
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
    need(len(values) == 1, "literal assignment " + name)
    return values[0]


def ci_targets(value: str) -> list[str]:
    block = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)\s*$", value)
    need(block is not None, "CI TARGETS block")
    targets = re.findall(r'^\s*"([^"]+)"\s*$', block.group(1), flags=re.M)
    need(targets and len(targets) == len(set(targets)), "CI TARGETS canonical")
    return targets


def python_lines(value: str) -> list[str]:
    return [
        line.strip()
        for line in value.splitlines()
        if line.strip().startswith("python3 ")
        and not line.strip().startswith("python3 -m py_compile ")
    ]


def main() -> int:
    doc = read_text(DOC)
    source = read_text(VALIDATOR)
    root_source = read_text(ROOT_VALIDATOR)
    prep_source = read_text(AUTH_PREP_VALIDATOR)
    auth_source = read_text(AUTH_REVIEW_VALIDATOR)
    evidence_source = read_text(EVIDENCE_PREP_VALIDATOR)
    restore_source = read_text(RESTORE_AUTH_VALIDATOR)
    ci = read_text(CI)
    read_text(LOCKED_RUNNER)

    required = {
        "stage_id": "PMAI-P0-04",
        "substage": 'EXTERNAL_DISPOSABLE_RESTORE_V2_PRE_EXECUTION_ABORT_EVIDENCE_AND_DISPOSABLE_TARGET_RETIREMENT_PREPARATION_V1',
        "package_status": "PRE_EXECUTION_ABORT_EVIDENCE_COMPLETE_RETIREMENT_PREPARATION_ONLY",
        "evidence_completeness": "COMPLETE_FOR_V2_PRE_EXECUTION_ABORT_PENDING_SEPARATE_TARGET_RETIREMENT_AUTHORIZATION",
        "third_and_final_external_runner_call_status": "PRE_EXECUTION_ABORT",
        "third_and_final_external_runner_stop_code": "BACKUP_DIRECTORY_ROOT_MISMATCH",
        "third_and_final_external_runner_exit_code": "2",
        "external_runner_execute_call_count": "3",
        "third_call_runner_version": "V2",
        "external_v2_runner_sha256": EXPECTED_V2_RUNNER_SHA256,
        "approved_backup_sha256": EXPECTED_BACKUP_SHA256,
        "approved_backup_toc_sha256": EXPECTED_BACKUP_TOC_SHA256,
        "abort_evidence_artifact_count": "7",
        "abort_evidence_set_sha256": EXPECTED_EVIDENCE_SET_SHA256,
        "post_abort_target_status": "Available",
        "post_abort_target_available": "true",
        "post_abort_target_storage_used_percent": "9.9",
        "technical_restore_attempt_reserved": "false",
        "restore_execution_started": "false",
        "database_connection": "false",
        "database_write": "false",
        "pg_restore_list_invoked": "false",
        "pg_restore_restore_invoked": "false",
        "psql_database_invoked": "false",
        "no_further_restore_retry": "true",
        "disposable_target_retirement_preparation_complete": "true",
        "ready_for_separate_disposable_target_retirement_authorization_review": "true",
        "target_retirement_operational_deadline_local": "2026-08-11T00:00+08:00",
        "target_retirement_hard_deadline_local": "2026-08-11T00:08+08:00",
        "target_retirement_scope": "ONE_EXACT_DISPOSABLE_RENDER_POSTGRES_SERVICE_ONLY",
        "target_logical_name": 'pet-med-ai-db-p0-04-disposable-restore-ohio',
        "target_service_identifier_sha256": 'fcd569994776e091f001f7213cd02432339e172e51889b2acf0a3987e0be7b48',
        "final_ci_sha256": EXPECTED_CI_SHA256,
        "locked_runner_sha256": EXPECTED_LOCKED_RUNNER_SHA256,
        "decision": "HOLD_PMAI_P0_04_NO_FURTHER_RESTORE_CALLS_PENDING_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_AND_FRESH_RESTORE_GOVERNANCE_DECISION",
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == "false", "required false marker " + key)

    canonical = "".join(
        evidence_id + "=" + digest + "\n"
        for evidence_id, digest, _purpose in EXPECTED_EVIDENCE
    )
    need(
        hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        == EXPECTED_EVIDENCE_SET_SHA256,
        "evidence set digest",
    )
    for index, (evidence_id, digest, purpose) in enumerate(EXPECTED_EVIDENCE, 1):
        prefix = "abort_evidence_{:02d}_".format(index)
        need(marker(doc, prefix + "id") == evidence_id, "evidence id")
        need(marker(doc, prefix + "purpose") == purpose, "evidence purpose")
        need(marker(doc, prefix + "sha256") == digest, "evidence hash")

    forbidden = (
        r"(?i)postgres(?:ql)?://\S+",
        r"(?im)^\s*(?:export\s+)?DATABASE_URL\s*=",
        r"(?im)^\s*(?:export\s+)?SECRET_KEY\s*=",
        r"(?im)^\s*(?:password|passwd|pwd)\s*[:=]",
        r"(?i)\bdpg-[a-z0-9-]+\b",
        r"(?im)^\s*(?:\$\s*)?(?:sudo\s+)?(?:pg_restore|psql|alembic)(?:\s|$)",
    )
    for pattern in forbidden:
        need(re.search(pattern, doc) is None, "forbidden secret identifier or command")

    need(sha256_path(ROOT / CI) == EXPECTED_CI_SHA256, "CI hash")
    need(
        sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256,
        "locked runner hash",
    )
    need(
        not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")),
        "active 0010 migration",
    )

    targets = literal(root_source, "TARGETS")
    hashes = literal(root_source, "HASHES")
    need(isinstance(targets, list) and len(targets) == len(set(targets)), "root TARGETS")
    need(isinstance(hashes, dict), "root HASHES")
    need(DOC in targets and VALIDATOR in targets, "new package protection")
    need(
        set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS,
        "protected hash scope",
    )
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), "missing protected " + rel)
        need(sha256_path(path) == expected_hash, "protected hash " + rel)

    need(ci_targets(ci) == targets, "CI/root target equality")
    need(python_lines(ci) == EXPECTED_COMMANDS, "CI approved validators")
    marker_line = '# PMAI-P0-04 external disposable restore V2 pre-execution abort evidence and disposable target retirement preparation v1'
    command_line = 'python3 ' + VALIDATOR + ' || exit 1'
    need(ci.splitlines().count(marker_line) == 1, "CI marker count")
    need(ci.splitlines().count(command_line) == 1, "CI command count")

    need(literal(prep_source, "EXPECTED_FINAL_CI_SHA256") == EXPECTED_CI_SHA256, "auth-prep CI rollover")
    for previous in (auth_source, evidence_source, restore_source):
        need(literal(previous, "EXPECTED_CI_SHA256") == EXPECTED_CI_SHA256, "prior CI rollover")
        need(literal(previous, "EXPECTED_COMMANDS") == EXPECTED_COMMANDS, "prior command rollover")

    unsafe_suffixes = (".png", ".jpg", ".jpeg", ".json", ".tar", ".tar.gz")
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), "raw evidence target")
    for rel in (DOC, VALIDATOR):
        value = read_text(rel)
        need(value.endswith("\n"), "final newline " + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), "trailing whitespace {}:{}".format(rel, line_no))
    need(source.count("EXPECTED_V2_RUNNER_SHA256") >= 2, "V2 hash guard")

    print("PASS: PMAI-P0-04 External Disposable Restore V2 Pre-Execution Abort Evidence & Disposable Target Retirement Preparation V1")
    print("stage_id=PMAI-P0-04")
    print("third_and_final_external_runner_call_status=PRE_EXECUTION_ABORT")
    print("third_and_final_external_runner_stop_code=BACKUP_DIRECTORY_ROOT_MISMATCH")
    print("technical_restore_attempt_reserved=false")
    print("database_connection=false")
    print("database_write=false")
    print("restore_execution=false")
    print("backup_restoreability_verified=false")
    print("fourth_external_runner_call_authorized=false")
    print("disposable_target_retirement_preparation_complete=true")
    print("disposable_target_retirement_authorized=false")
    print("disposable_target_deleted=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("decision=HOLD_PMAI_P0_04_NO_FURTHER_RESTORE_CALLS_PENDING_DISPOSABLE_TARGET_RETIREMENT_AUTHORIZATION_AND_FRESH_RESTORE_GOVERNANCE_DECISION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
