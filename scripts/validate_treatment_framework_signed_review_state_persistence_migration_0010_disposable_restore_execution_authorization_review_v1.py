#!/usr/bin/env python3
"""Validate PMAI-P0-04 disposable restore authorization review V1."""

from __future__ import annotations

import ast
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1.md'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py'
ROOT_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
AUTH_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_preparation_v1.py'
AUTH_REVIEW_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_authorization_review_v1.py'
EVIDENCE_PREP_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_TARGET_PROVISIONING_EVIDENCE_AND_RESTORE_EXECUTION_AUTHORIZATION_PREPARATION_V1.md'
EVIDENCE_PREP_VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_target_provisioning_evidence_and_restore_execution_authorization_preparation_v1.py'
CI = 'scripts/ci_static_checks.sh'
LOCKED_RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
EXPECTED_CI_SHA256 = '7cba5137d959d9f37a5e4f7a70798ff5090fc130ead6ce9d124c457c9a682811'
EVIDENCE_PREPARATION_RECORD_CI_SHA256 = '26944102de1c64805425675dc4eedc06f150feb6bc0e57d26319028ae6618311'
EXPECTED_RUNNER_SHA256 = 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f'
APPROVAL_STATEMENT = '批准 PMAI-P0-04 仅对 pet-med-ai-db-p0-04-disposable-restore-ohio 执行一次受控备份恢复演练；不授权 production、staging source、Alembic、0010 migration、locked runner 或任何应用部署。'
APPROVAL_STATEMENT_SHA256 = '888079b954b8a5e601e7b16c31b328a2070dd77e7de839a1a11fef1f5fdad4c2'
TARGET_SERVICE_IDENTIFIER_SHA256 = 'fcd569994776e091f001f7213cd02432339e172e51889b2acf0a3987e0be7b48'
PROVISIONING_EVIDENCE_SET_SHA256 = 'f2bc5bb7337bcfcd7b50df207f036e4c91dc78d9cdfca7084e1ebf7b112c7eb3'
BACKUP_ARTIFACT_SHA256 = 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7'
BACKUP_EXTERNAL_EVIDENCE_SHA256 = 'a7af6ca2c0cba862bb7f6073f0866ef6dafcb20364ae64db6c9693fe622798e1'
BACKUP_TOC_SHA256 = '6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c'
RESTORE_ARGV = ('pg_restore', '--dbname=service=pmai_p0_04_disposable_restore', '--no-owner', '--no-privileges', '--no-tablespaces', '--no-publications', '--no-subscriptions', '--single-transaction', '--exit-on-error', '--verbose', '--no-password', '<APPROVED_BACKUP_PATH>')
RESTORE_ARGV_SHA256 = 'cf80e22e4fd0914d2b52ca253489b5123859900d1ce1d8e4adddf871ee534c51'
FALSE_MARKERS = ('network_access', 'database_connection', 'database_write', 'restore_execution', 'pg_restore_invoked', 'psql_invoked', 'alembic_invoked', 'migration_created', 'migration_executed', 'restore_runner_created', 'restore_runner_execution_enabled', 'restore_runner_executed_by_ci', 'backup_restoreability_verified', 'disposable_restore_rehearsal_complete', 'corrected_migration_implementation_authorized', 'active_0010_migration_file_created', 'staging_0010_migration_executed', 'p0_04_execution_authorized', 'staging_0010_apply_authorized', 'production_migration_authorized', 'production_migration_executed', 'production_auto_deploy_verified', 'connection_value_captured', 'raw_service_identifier_recorded', 'external_evidence_content_copied', 'external_evidence_artifact_committed', 'restore_runner_hash_review_complete', 'one_time_execution_confirmation_present', 'restore_attempt_started', 'restore_attempt_completed', 'target_deleted', 'cleanup_evidence_complete', 'ENABLE_EMR_REAL_IMPORT', 'ENABLE_EMR_IMPORT_CASE_UPDATE', 'ENABLE_EMR_ATTACHMENT_DOWNLOAD', 'ENABLE_PREVENTIVE_AUTO_DELIVERY', 'ENABLE_PREVENTIVE_SMS_DELIVERY', 'ENABLE_PREVENTIVE_WECHAT_DELIVERY', 'ENABLE_PREVENTIVE_EMAIL_DELIVERY', 'ENABLE_PRESCRIPTION_STRUCTURED_WRITE', 'ENABLE_DEVICE_REAL_INGEST', 'ENABLE_BILLING_REAL_WRITE')
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
    evidence_doc = read_text(EVIDENCE_PREP_DOC)
    evidence_source = read_text(EVIDENCE_PREP_VALIDATOR)
    ci = read_text(CI)
    read_text(VALIDATOR)
    read_text(LOCKED_RUNNER)

    required = {
        "stage_id": "PMAI-P0-04",
        "substage": 'DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1',
        "package_status": "AUTHORIZATION_RECORD_ONLY",
        "review_status": "APPROVED_DISPOSABLE_RESTORE_ONLY",
        "authorization_record_id": 'PMAI-P0-04-DRER-V1-20260808',
        "approval_statement": APPROVAL_STATEMENT,
        "approval_statement_sha256": APPROVAL_STATEMENT_SHA256,
        "authorization_scope": "ONE_DISPOSABLE_TARGET_ONE_BACKUP_ONE_ATTEMPT_ONLY",
        "disposable_restore_execution_authorized": "true",
        "disposable_restore_database_connection_authorized": "true",
        "disposable_restore_database_write_authorized": "true",
        "restore_execution_authorization_requested": "true",
        "explicit_restore_execution_approval_present": "true",
        "restore_command_reviewed": "true",
        "p0_04_execution_authorized": "false",
        "staging_0010_apply_authorized": "false",
        "decision": "GO_TO_EXTERNAL_RESTORE_RUNNER_PREPARATION_AND_HASH_REVIEW_ONLY",
        "provisioning_evidence_complete": "true",
        "disposable_restore_database_created": "true",
        "provisioning_evidence_set_sha256": PROVISIONING_EVIDENCE_SET_SHA256,
        "target_logical_name": 'pet-med-ai-db-p0-04-disposable-restore-ohio',
        "target_service_identifier_sha256": TARGET_SERVICE_IDENTIFIER_SHA256,
        "target_empty_application_data_verified": "false",
        "backup_artifact_sha256": BACKUP_ARTIFACT_SHA256,
        "backup_external_sanitized_evidence_sha256": BACKUP_EXTERNAL_EVIDENCE_SHA256,
        "backup_toc_sha256": BACKUP_TOC_SHA256,
        "backup_toc_entry_count": '433',
        "restore_argv_sha256": RESTORE_ARGV_SHA256,
        "restore_single_transaction": "true",
        "restore_exit_on_error": "true",
        "restore_automatic_retry": "false",
        "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "final_ci_sha256": EXPECTED_CI_SHA256,
        "locked_runner_sha256": EXPECTED_RUNNER_SHA256,
    }
    for key, expected in required.items():
        need(marker(doc, key) == expected, "document marker " + key)
    for key in FALSE_MARKERS:
        need(marker(doc, key) == "false", "required false marker " + key)

    need(
        hashlib.sha256(APPROVAL_STATEMENT.encode("utf-8")).hexdigest()
        == APPROVAL_STATEMENT_SHA256,
        "approval statement digest",
    )
    canonical_argv = "".join(item + "\n" for item in RESTORE_ARGV)
    need(
        hashlib.sha256(canonical_argv.encode("utf-8")).hexdigest()
        == RESTORE_ARGV_SHA256,
        "restore argv digest",
    )
    for index, item in enumerate(RESTORE_ARGV, 1):
        need(
            marker(doc, f"restore_argv_{index:02d}") == item,
            "restore argv item",
        )

    forbidden = (
        r"(?i)postgres(?:ql)?://\S+",
        r"(?im)^\s*(?:export\s+)?DATABASE_URL\s*=",
        r"(?im)^\s*(?:export\s+)?SECRET_KEY\s*=",
        r"(?im)^\s*(?:password|passwd|pwd)\s*[:=]",
        r"(?i)\bdpg-[a-z0-9-]+\b",
    )
    for pattern in forbidden:
        need(re.search(pattern, doc) is None, "forbidden secret or raw identifier")

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
        need(path.is_file() and not path.is_symlink(), "missing protected " + rel)
        need(sha256_path(path) == expected_hash, "protected hash " + rel)

    need(ci_targets(ci) == targets, "CI/root target equality")
    need(python_lines(ci) == EXPECTED_COMMANDS, "CI approved validators")
    need(ci.splitlines().count('# PMAI-P0-04 disposable restore execution authorization review v1') == 1, "CI marker count")
    need(ci.splitlines().count('python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_disposable_restore_execution_authorization_review_v1.py || exit 1') == 1, "CI command count")
    need(
        literal(prep_source, "EXPECTED_FINAL_CI_SHA256") == EXPECTED_CI_SHA256,
        "auth-prep CI rollover",
    )
    need(
        literal(review_source, "EXPECTED_CI_SHA256") == EXPECTED_CI_SHA256,
        "target auth-review CI rollover",
    )
    need(
        literal(review_source, "EXPECTED_COMMANDS") == EXPECTED_COMMANDS,
        "target auth-review command rollover",
    )
    need(
        literal(evidence_source, "EXPECTED_CI_SHA256") == EXPECTED_CI_SHA256,
        "evidence-prep CI rollover",
    )
    need(
        literal(evidence_source, "EVIDENCE_PREPARATION_RECORD_CI_SHA256")
        == EVIDENCE_PREPARATION_RECORD_CI_SHA256,
        "evidence-prep historical CI constant",
    )
    need(
        literal(evidence_source, "EXPECTED_COMMANDS") == EXPECTED_COMMANDS,
        "evidence-prep command rollover",
    )
    need(
        marker(evidence_doc, "final_ci_sha256")
        == EVIDENCE_PREPARATION_RECORD_CI_SHA256,
        "evidence-prep historical document CI",
    )
    need(
        marker(evidence_doc, "provisioning_evidence_set_sha256")
        == PROVISIONING_EVIDENCE_SET_SHA256,
        "evidence set continuity",
    )

    unsafe_suffixes = (".png", ".jpg", ".jpeg", ".json", ".tar", ".tar.gz")
    need(
        not any(path.lower().endswith(unsafe_suffixes) for path in targets),
        "raw backup or evidence artifact in protected targets",
    )
    for rel in (DOC, VALIDATOR):
        value = read_text(rel)
        need(value.endswith("\n"), "final newline " + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), f"trailing whitespace {rel}:{line_no}")

    print("PASS: PMAI-P0-04 Disposable Restore Execution Authorization Review V1")
    print("stage_id=PMAI-P0-04")
    print("review_status=APPROVED_DISPOSABLE_RESTORE_ONLY")
    print("authorization_scope=ONE_DISPOSABLE_TARGET_ONE_BACKUP_ONE_ATTEMPT_ONLY")
    print("disposable_restore_execution_authorized=true")
    print("package_database_connection=false")
    print("package_database_write=false")
    print("restore_execution=false")
    print("restore_runner_created=false")
    print("backup_restoreability_verified=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("decision=GO_TO_EXTERNAL_RESTORE_RUNNER_PREPARATION_AND_HASH_REVIEW_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
