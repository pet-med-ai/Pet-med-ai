#!/usr/bin/env python3
"""Validate PMAI-P0-04 provisioning evidence and restore-auth prep."""

from __future__ import annotations

import ast
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1.md'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
AUTH_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
AUTH_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py'
AUTH_REVIEW_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1.md'
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_CI_SHA256 = 'b795f8865470f4bfd19b20959a8abc0c4b616892ffd42d8983c77cbd0b194025'
EVIDENCE_PREPARATION_RECORD_CI_SHA256 = '26944102de1c64805425675dc4eedc06f150feb6bc0e57d26319028ae6618311'
AUTHORIZATION_REVIEW_RECORD_CI_SHA256 = 'f224dd3ed069a198613ad3ddbace564245586528acddab54e1eb835921ffea2f'
EXPECTED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
FALSE_MARKERS = ('network_access', 'database_connection', 'database_write', 'restore_execution', 'pg_restore_invoked', 'psql_invoked', 'alembic_invoked', 'migration_created', 'migration_executed', 'restore_runner_created', 'restore_runner_execution_enabled', 'restore_runner_executed_by_ci', 'disposable_restore_database_write_authorized', 'disposable_restore_execution_authorized', 'restore_execution_authorization_requested', 'explicit_restore_execution_approval_present', 'restore_command_reviewed', 'target_empty_application_data_verified', 'target_content_readback_performed', 'backup_restoreability_verified', 'disposable_restore_rehearsal_complete', 'corrected_migration_implementation_authorized', 'active_0010_migration_file_created', 'staging_0010_migration_executed', 'p0_04_execution_authorized', 'staging_0010_apply_authorized', 'production_migration_authorized', 'production_migration_executed', 'production_auto_deploy_verified', 'connection_value_captured', 'raw_service_identifier_recorded', 'external_evidence_content_copied', 'external_evidence_artifact_committed', 'connect_action_invoked', 'recovery_action_invoked', 'pgadmin_deployed', 'pghero_deployed', 'target_deleted', 'cleanup_evidence_complete', 'ENABLE_EMR_REAL_IMPORT', 'ENABLE_EMR_IMPORT_CASE_UPDATE', 'ENABLE_EMR_ATTACHMENT_DOWNLOAD', 'ENABLE_PREVENTIVE_AUTO_DELIVERY', 'ENABLE_PREVENTIVE_SMS_DELIVERY', 'ENABLE_PREVENTIVE_WECHAT_DELIVERY', 'ENABLE_PREVENTIVE_EMAIL_DELIVERY', 'ENABLE_PRESCRIPTION_STRUCTURED_WRITE', 'ENABLE_DEVICE_REAL_INGEST', 'ENABLE_BILLING_REAL_WRITE')
HASH_EXTRA_PATHS = set(('docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md', 'backend/models.py', 'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md', 'render.yaml'))
EVIDENCE_HASHES = (('P04-DTP-E01', '9789a602189d30d73f16ae9066d1ccd190facd52710db28bcd1d1d4d5c53654b', 'status_version_region'), ('P04-DTP-E02', 'eb81514e212b3f4f1a633eec165aa9d42e9bc8ad1671767e1bd850be13351298', 'read_replica_autoscaling_datadog'), ('P04-DTP-E03', 'f5628589735be8f1356e7a7871ae89938029164a0e5c082fca8d2cbc55f456a9', 'instance_storage_high_availability'), ('P04-DTP-E04', '0afda6cc8243a817a89e79e9919ef235eabe66383ead5ef2e3bcd2d5ca887695', 'application_isolation'))
EVIDENCE_SET_SHA256 = 'f2bc5bb7337bcfcd7b50df207f036e4c91dc78d9cdfca7084e1ebf7b112c7eb3'
EXPECTED_COMMANDS = [
    'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py',
    'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py || exit 1',
    'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py || exit 1',
    'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py || exit 1',
    'python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py || exit 1',
]


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
    root_source = read_text(ROOT_VALIDATOR)
    prep_source = read_text(AUTH_PREP_VALIDATOR)
    review_source = read_text(AUTH_REVIEW_VALIDATOR)
    review_doc = read_text(AUTH_REVIEW_DOC)
    ci = read_text(CI)
    read_text(VALIDATOR)
    read_text(LOCKED_RUNNER)

    required = {
        "stage_id": "PMAI-P0-04",
        "substage": 'DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1',
        "package_status": "EVIDENCE_COMPLETE_PREPARATION_ONLY",
        "evidence_completeness": "COMPLETE_FOR_PROVISIONING_PENDING_RESTORE_EXECUTION_AUTHORIZATION",
        "disposable_restore_target_provisioning_authorized": "true",
        "disposable_restore_database_created": "true",
        "provisioning_execution_performed": "true",
        "provisioning_evidence_complete": "true",
        "restore_execution_authorization_preparation_complete": "true",
        "ready_for_restore_execution_authorization_review": "true",
        "disposable_restore_execution_authorized": "false",
        "decision": "HOLD_PMAI_P0_04_PENDING_SEPARATE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW",
        "target_logical_name": 'pet-med-ai-db-p0-04-disposable-restore-ohio',
        "target_status": "Available",
        "target_region": "Ohio (US East)",
        "target_postgresql_major_version": "18",
        "target_instance_type": "Basic-256mb",
        "target_storage_gb": "1",
        "target_storage_autoscaling": "false",
        "target_read_replica_count": "0",
        "target_high_availability": "false",
        "target_application_attachment_count": "0",
        "target_isolated_control_plane_verified": "true",
        "target_empty_application_data_verified": "false",
        "target_empty_state_basis": "NEW_SERVICE_CONTROL_PLANE_INFERENCE_NOT_DATABASE_CONTENT_READBACK",
        "provisioning_evidence_artifact_count": "4",
        "provisioning_evidence_set_sha256": EVIDENCE_SET_SHA256,
        "provisioning_evidence_sha256_set_verified": "true",
        "target_operational_delete_deadline_local": "2026-08-11T00:00_OPERATOR_SCREENSHOT_LOCAL_TIME",
        "target_hard_expiry_not_later_than_local": "2026-08-11T00:08_OPERATOR_SCREENSHOT_LOCAL_TIME",
        "target_cost_ceiling_usd": "1.00",
        "final_ci_sha256": EVIDENCE_PREPARATION_RECORD_CI_SHA256,
        "locked_runner_sha256": EXPECTED_RUNNER_SHA256,
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == "false", "required false marker " + key)

    canonical = "".join(
        f"{evidence_id}={digest}\n"
        for evidence_id, digest, _purpose in EVIDENCE_HASHES
    )
    need(
        hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        == EVIDENCE_SET_SHA256,
        "evidence set digest",
    )
    for index, (evidence_id, digest, purpose) in enumerate(EVIDENCE_HASHES, 1):
        prefix = f"provisioning_evidence_{index:02d}_"
        need(marker(doc, prefix + "id") == evidence_id, "evidence id")
        need(marker(doc, prefix + "purpose") == purpose, "evidence purpose")
        need(marker(doc, prefix + "sha256") == digest, "evidence hash")

    forbidden = (
        r"(?i)postgres(?:ql)?://\S+",
        r"(?im)^\s*(?:export\s+)?DATABASE_URL\s*=",
        r"(?im)^\s*(?:export\s+)?SECRET_KEY\s*=",
        r"(?im)^\s*(?:password|passwd|pwd)\s*[:=]",
        r"(?im)^\s*(?:\$\s*)?(?:sudo\s+)?(?:pg_restore|psql|alembic)(?:\s|$)",
        r"(?i)\bdpg-[a-z0-9-]+\b",
    )
    for pattern in forbidden:
        need(
            re.search(pattern, doc) is None,
            "forbidden secret identifier or command",
        )

    need(sha256_path(ROOT / CI) == EXPECTED_CI_SHA256, "CI hash")
    need(
        sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_RUNNER_SHA256,
        "locked runner hash",
    )
    need(
        not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")),
        "active 0010 migration",
    )

    targets = literal(root_source, "TARGETS")
    hashes = literal(root_source, "HASHES")
    need(
        isinstance(targets, list) and len(targets) == len(set(targets)),
        "root TARGETS",
    )
    need(isinstance(hashes, dict), "root HASHES")
    need(DOC in targets and VALIDATOR in targets, "new package protection")
    need(
        set(hashes) == (set(targets) - {ROOT_VALIDATOR}) | HASH_EXTRA_PATHS,
        "protected hash scope",
    )
    for rel, expected_hash in hashes.items():
        path = ROOT / rel
        need(
            path.is_file() and not path.is_symlink(),
            "missing protected " + rel,
        )
        need(sha256_path(path) == expected_hash, "protected hash " + rel)

    need(ci_targets(ci) == targets, "CI/root target equality")
    need(python_lines(ci) == EXPECTED_COMMANDS, "CI approved validators")
    need(ci.splitlines().count('# PMAI-P0-04 disposable target provisioning evidence and restore execution authorization preparation v1') == 1, "CI marker count")
    need(ci.splitlines().count('python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py || exit 1') == 1, "CI command count")
    need(
        literal(prep_source, "EXPECTED_FINAL_CI_SHA256")
        == EXPECTED_CI_SHA256,
        "auth-prep CI rollover",
    )
    need(
        literal(review_source, "EXPECTED_CI_SHA256") == EXPECTED_CI_SHA256,
        "auth-review CI rollover",
    )
    need(
        literal(review_source, "AUTHORIZATION_RECORD_CI_SHA256")
        == AUTHORIZATION_REVIEW_RECORD_CI_SHA256,
        "auth-review historical record CI",
    )
    need(
        marker(review_doc, "final_ci_sha256")
        == AUTHORIZATION_REVIEW_RECORD_CI_SHA256,
        "auth-review document historical CI",
    )
    need(
        literal(review_source, "EXPECTED_COMMANDS") == EXPECTED_COMMANDS,
        "auth-review command rollover",
    )

    unsafe_suffixes = (".png", ".jpg", ".jpeg", ".json", ".tar", ".tar.gz")
    need(
        not any(path.lower().endswith(unsafe_suffixes) for path in targets),
        "raw evidence artifact in protected targets",
    )
    for rel in (DOC, VALIDATOR):
        value = read_text(rel)
        need(value.endswith("\n"), "final newline " + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(
                line == line.rstrip(),
                f"trailing whitespace {rel}:{line_no}",
            )

    print("PASS: PMAI-P0-04 Disposable Target Provisioning Evidence & Restore Authorization Preparation V1")
    print("stage_id=PMAI-P0-04")
    print("provisioning_evidence_complete=true")
    print("disposable_restore_database_created=true")
    print("restore_execution_authorization_preparation_complete=true")
    print("ready_for_restore_execution_authorization_review=true")
    print("disposable_restore_execution_authorized=false")
    print("database_connection=false")
    print("database_write=false")
    print("restore_execution=false")
    print("backup_restoreability_verified=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("decision=HOLD_PMAI_P0_04_PENDING_SEPARATE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
