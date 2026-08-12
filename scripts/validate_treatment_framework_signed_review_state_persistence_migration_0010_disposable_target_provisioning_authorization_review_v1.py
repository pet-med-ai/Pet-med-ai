#!/usr/bin/env python3
"""Validate PMAI-P0-04 disposable target provisioning-only authorization."""

from __future__ import annotations

import ast
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1.md'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'

EXPECTED_CI_SHA256 = 'e0497f7ba925d753728cc8ae364efcec95e995b2212648c2eda4ed57a4f4fccb'
AUTHORIZATION_RECORD_CI_SHA256 = 'f224dd3ed069a198613ad3ddbace564245586528acddab54e1eb835921ffea2f'
HISTORICAL_CI_SHA256 = '8068312d6aa24e667f344b3eea9082f0a9b3688bc664dee0984d3e3dd251f25c'
EXPECTED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
APPROVAL_STATEMENT = '批准以上参数，仅授权 disposable target provisioning，不授权 restore execution。'
APPROVAL_STATEMENT_SHA256 = '2afe7b8c5a9701b972fd81c15c67759a16c84d9658f7613583e5a7162a06d92b'
FALSE_MARKERS = ('network_access', 'database_connection', 'database_write', 'restore_execution', 'pg_restore_invoked', 'psql_invoked', 'alembic_invoked', 'migration_created', 'migration_executed', 'restore_runner_created', 'restore_runner_execution_enabled', 'restore_runner_executed_by_ci', 'disposable_restore_database_created', 'disposable_restore_database_write_authorized', 'disposable_restore_execution_authorized', 'backup_restoreability_verified', 'disposable_restore_rehearsal_complete', 'corrected_migration_implementation_authorized', 'active_0010_migration_file_created', 'staging_0010_migration_executed', 'p0_04_execution_authorized', 'staging_0010_apply_authorized', 'production_migration_authorized', 'production_migration_executed', 'candidate_migration_deployed', 'production_auto_deploy_verified', 'provisioning_execution_performed', 'target_created_by_package', 'ENABLE_EMR_REAL_IMPORT', 'ENABLE_EMR_IMPORT_CASE_UPDATE', 'ENABLE_EMR_ATTACHMENT_DOWNLOAD', 'ENABLE_PREVENTIVE_AUTO_DELIVERY', 'ENABLE_PREVENTIVE_SMS_DELIVERY', 'ENABLE_PREVENTIVE_WECHAT_DELIVERY', 'ENABLE_PREVENTIVE_EMAIL_DELIVERY', 'ENABLE_PRESCRIPTION_STRUCTURED_WRITE', 'ENABLE_DEVICE_REAL_INGEST', 'ENABLE_BILLING_REAL_WRITE')
HASH_EXTRA_PATHS = set(('docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md', 'backend/models.py', 'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md', 'render.yaml'))
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
 '|| exit 1']


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


def literal_assignment(source: str, name: str):
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
    root_source = read_text(ROOT_VALIDATOR)
    prep_source = read_text(PREP_VALIDATOR)
    ci = read_text(CI)
    read_text(VALIDATOR)
    read_text(LOCKED_RUNNER)

    expected_markers = {
        "stage_id": "PMAI-P0-04",
        "substage": "DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1",
        "stage_status": "IN_PROGRESS",
        "package_status": "AUTHORIZATION_RECORD_ONLY",
        "review_status": "APPROVED_PROVISIONING_ONLY",
        "authorization_record_id": 'PMAI-P0-04-DTPA-AUTH-20260808-001',
        "approval_statement": APPROVAL_STATEMENT,
        "approval_statement_sha256": APPROVAL_STATEMENT_SHA256,
        "authorization_scope": "ONE_NEW_EMPTY_ISOLATED_POSTGRES_SERVICE_ONLY",
        "authorization_effective_gate": "PACKAGE_COMMITTED_PUSHED_AND_CI_GATE_PASS",
        "disposable_restore_target_provisioning_authorized": "true",
        "disposable_restore_execution_authorized": "false",
        "decision": "GO_TO_DISPOSABLE_TARGET_PROVISIONING_ONLY",
        "target_logical_name": 'pet-med-ai-db-p0-04-disposable-restore-ohio',
        "target_provider": 'Render',
        "target_region": 'Ohio (US East)',
        "target_postgresql_major_version": '18',
        "target_instance_type": 'Basic-256mb',
        "target_storage_gb": '1',
        "target_storage_autoscaling": "false",
        "target_read_replica_count": "0",
        "target_high_availability": "false",
        "target_connection_pooling": "false",
        "target_application_attachment_count": "0",
        "target_is_disposable": "true",
        "target_must_be_new": "true",
        "target_must_be_empty": "true",
        "production_target_excluded": "true",
        "staging_source_target_excluded": "true",
        "application_traffic_disabled": "true",
        "source_database_service": "pet-med-ai-db-staging-source-ohio",
        "source_region": "Ohio (US East)",
        "source_postgresql_major_version": "18",
        "source_instance_type": "Basic-256mb",
        "source_storage_gb": "1",
        "source_storage_used_percent": "10.33",
        "restore_client_version": "18.4",
        "version_compatibility_review": "PASS_POSTGRESQL_18_SOURCE_TARGET_AND_CLIENT",
        "target_max_lifetime_hours": '72',
        "target_delete_within_hours_after_evidence": '24',
        "target_estimated_max_cost_usd": '0.63',
        "target_cost_ceiling_usd": '1.00',
        "deletion_owner": "PROJECT_OWNER_OPERATOR",
        "cleanup_evidence_required": "true",
        "final_ci_sha256": AUTHORIZATION_RECORD_CI_SHA256,
        "locked_runner_sha256": EXPECTED_RUNNER_SHA256,
        "production_database_revision": "0009_diag_data",
        "staging_database_revision": "0009_diag_data",
    }
    for key, expected in expected_markers.items():
        need(marker(doc, key) == expected, "document marker " + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == "false", "required false marker " + key)

    actual_approval_hash = hashlib.sha256(APPROVAL_STATEMENT.encode("utf-8")).hexdigest()
    need(actual_approval_hash == APPROVAL_STATEMENT_SHA256, "approval statement hash")

    secret_patterns = (
        r"(?i)postgres(?:ql)?://[^\s`]+",
        r"(?im)^\s*(?:export\s+)?DATABASE_URL\s*=",
        r"(?im)^\s*(?:export\s+)?SECRET_KEY\s*=",
        r"(?im)^\s*(?:password|passwd|pwd)\s*[:=]",
    )
    for pattern in secret_patterns:
        need(re.search(pattern, doc) is None, "secret or connection pattern")
    need(
        re.search(
            r"(?im)^\s*(?:\$\s*)?(?:sudo\s+)?(?:pg_restore|psql|alembic)(?:\s|$)",
            doc,
        ) is None,
        "executable database command",
    )

    need(sha256_path(ROOT / CI) == EXPECTED_CI_SHA256, "final CI hash")
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_RUNNER_SHA256, "locked runner hash")
    need(
        not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")),
        "active backend 0010 migration",
    )

    targets = literal_assignment(root_source, "TARGETS")
    hashes = literal_assignment(root_source, "HASHES")
    need(isinstance(targets, list) and len(targets) == len(set(targets)), "root TARGETS")
    need(isinstance(hashes, dict), "root HASHES")
    need(DOC in targets and VALIDATOR in targets, "review package target protection")
    need(
        set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS,
        "root protected hash scope",
    )
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), "missing protected " + rel)
        need(sha256_path(path) == expected_hash, "protected hash " + rel)

    need(ci_targets(ci) == targets, "CI and root TARGETS equality")
    need(python_lines(ci) == EXPECTED_COMMANDS, "CI approved direct validators")
    need(ci.splitlines().count('# PMAI-P0-04 disposable target provisioning authorization review v1') == 1, "CI review marker count")
    need(ci.splitlines().count('python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py || exit 1') == 1, "CI review command count")

    need(
        literal_assignment(prep_source, "EXPECTED_FINAL_CI_SHA256")
        == EXPECTED_CI_SHA256,
        "preparation validator final CI rollover",
    )
    need(
        "post_rollover_ci_sha256=" + HISTORICAL_CI_SHA256 in prep_source,
        "historical preparation rollover marker preserved",
    )

    for rel in (DOC, VALIDATOR):
        value = read_text(rel)
        need(value.endswith("\n"), "final newline " + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), f"trailing whitespace {rel}:{line_no}")

    print("PASS: PMAI-P0-04 Disposable Target Provisioning Authorization Review V1")
    print("stage_id=PMAI-P0-04")
    print("review_status=APPROVED_PROVISIONING_ONLY")
    print("authorization_scope=ONE_NEW_EMPTY_ISOLATED_POSTGRES_SERVICE_ONLY")
    print("disposable_restore_target_provisioning_authorized=true")
    print("disposable_restore_execution_authorized=false")
    print("database_connection=false")
    print("database_write=false")
    print("restore_execution=false")
    print("migration_created=false")
    print("migration_executed=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("provisioning_execution_performed=false")
    print("decision=GO_TO_DISPOSABLE_TARGET_PROVISIONING_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
