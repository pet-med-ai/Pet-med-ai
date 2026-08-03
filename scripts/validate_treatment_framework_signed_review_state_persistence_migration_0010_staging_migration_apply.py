#!/usr/bin/env python3
"""Fail-closed validator for PMAI-P0-04 fresh-backup evidence promotion."""
import argparse, ast, csv, glob, hashlib, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLD = 'HOLD_PMAI_P0_04_PENDING_DISPOSABLE_RESTORE_REHEARSAL_AND_EXTERNAL_EVIDENCE'
COMPLETENESS = 'PENDING_DISPOSABLE_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION'
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv'
REGISTER = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv'
MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv'
BACKUP_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md'
RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
CI = 'scripts/ci_static_checks.sh'
SMOKE = 'scripts/smoke_petmed.sh'
TARGETS = ['docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md', 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py', 'scripts/ci_static_checks.sh', 'scripts/smoke_petmed.sh']
HASHES = {'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md': '66e8caf12033b4d6ebd43759c08ffb86799d483ec85bef53082f21090136c234', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt': 'bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md': '9ca66949f5c515805ade771be5d224eda5bc35827e552c30b2c81656bff7a132', 'backend/models.py': '91d1343c1ebe3df16f00bada05b2b0053f9747e6f714f726a81cd499357b448c', 'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md': 'a1996e0c022f7a42a83d40f5f2e9bdd8bec2e77a106aa7b8aa0a231b87d83844', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md': '99bbe0447b47d1aa0c9fd87cb6f55a4554e879a9b8151377b96cec3550cab4c6', 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py': 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f', 'render.yaml': 'd3bd51ce5fa0dffa8639d0b647784e54bebb8d1040a94f5c2ecd18a789d11150', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md': 'df6c4a7ff9d45f14e525825557758512b0691af77ec6c7bb9f79c1f423051fcb', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv': 'd812c5efaa7a8a31fab1934dae012b322bd0c3b513c58ab9e47704707f842f9b', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv': '7c3e39b298a1a2fd9ba85d3f7a21ee674150fa20edf2479b62b800aed4b096ac', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv': '9e539f9a2c5e97ed20347eb362167528319cfdfda82fc0c8b6cbf15aef413cc4', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv': '442addef358fab6bae8881d5e5c6ea837c7fda3c214e397ac7d7e2beb2e35fdf', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md': '0f36f2c4bcb673666aed6728f6dff407a8d45c4bfe9ba2a1b2f1fe0e3bbdf6b9', 'scripts/ci_static_checks.sh': '08127ce181a5aaa450338d3e68b3b7ed1c8cc4150fd9d2c47336197282277843', 'scripts/smoke_petmed.sh': '5135d630f7912bbf38790f106dd535d33a724a27be4f21dfd05e3ed877f6d11a'}

def need(ok, message):
    if not ok:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)

def text(rel):
    path = ROOT / rel
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + rel)
    return path.read_text(encoding="utf-8")

def marker(value, key):
    found = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", value)
    need(len(found) == 1, "marker count " + key)
    return found[0]

def csv_map(rel, id_name):
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle); rows = list(reader)
    need(reader.fieldnames and reader.fieldnames[0] == id_name, "CSV header " + rel)
    ids = [row[id_name] for row in rows]
    need(len(ids) == len(set(ids)), "duplicate CSV id " + rel)
    return {row[id_name]: row for row in rows}

def py_lines(value):
    return [line.strip() for line in value.splitlines() if line.strip().startswith("python3 ") and not line.strip().startswith("python3 -m py_compile ")]

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--require-complete", action="store_true"); args = parser.parse_args()
    for rel, expected in HASHES.items():
        path = ROOT / rel
        need(path.is_file() and not path.is_symlink(), "missing protected file " + rel)
        need(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "protected hash " + rel)
    need(not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")), "active 0010 migration exists")
    doc = text(DOC)
    exact = {
        "stage_id": "PMAI-P0-04", "STAGE_STATUS": "IN_PROGRESS",
        "EVIDENCE_COMPLETENESS": COMPLETENESS,
        "fresh_backup_evidence_sha256": 'a7af6ca2c0cba862bb7f6073f0866ef6dafcb20364ae64db6c9693fe622798e1',
        "fresh_backup_artifact_sha256": 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7',
        "fresh_backup_pg_restore_toc_sha256": '6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c',
        "fresh_backup_integrity_verified": "true",
        "fresh_backup_independent_evidence_verification_complete": "true",
        "fresh_post_p0_03_staging_backup_verified": "true",
        "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "corrected_migration_implementation_authorized": "false",
        "P0_04_EXECUTION_AUTHORIZED": "false", "STAGING_0010_APPLY_AUTHORIZED": "false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED": "false", "migration_created": "false",
        "migration_executed": "false", "production_database_write": "false",
        "decision": HOLD,
    }
    for key, expected in exact.items(): need(marker(doc, key) == expected, "document marker " + key)
    evidence = text(BACKUP_DOC)
    for key, expected in {
        "staging_only_branch_or_commit_pin_verified": "true",
        "production_target_excluded": "true",
        "deployment_isolation_verified": "true",
        "deployment_isolation_verified_as_point_in_time": "true",
        "candidate_migration_deployed": "false",
        "production_deployment_freeze_verified": "false",
        "evidence_type": "fresh_post_p0_03_staging_backup_offline_integrity",
        "external_evidence_sha256": 'a7af6ca2c0cba862bb7f6073f0866ef6dafcb20364ae64db6c9693fe622798e1',
        "backup_file_sha256": 'ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7',
        "pg_restore_toc_sha256": '6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c',
        "pg_restore_mode": "list_only", "pg_restore_database_target_supplied": "false",
        "stored_evidence_independent_verification_complete": "false",
        "independent_evidence_verification_complete": "true",
        "fresh_post_p0_03_staging_backup_verified": "true",
        "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "p0_04_execution_authorized": "false", "staging_0010_apply_authorized": "false",
        "active_0010_migration_file_created": "false", "database_write": "false",
        "migration_created": "false", "migration_executed": "false",
        "production_database_write": "false", "decision": HOLD,
    }.items(): need(marker(evidence, key) == expected, "backup evidence marker " + key)
    checklist = csv_map(CHECKLIST, "item_id"); register = csv_map(REGISTER, "evidence_id")
    matrix = csv_map(MATRIX, "test_id"); gates = csv_map(GO_NO_GO, "gate_id")
    need(checklist["P04-C012"]["status"] == "VERIFIED_EXTERNAL_EVIDENCE", "checklist backup")
    need(checklist["P04-C026"]["status"] == "VERIFIED_EXTERNAL_EVIDENCE", "checklist independent verification")
    need(register["P04-E011"]["status"] == "VERIFIED_EXTERNAL_EVIDENCE", "register backup")
    need(register["P04-E022"]["status"] == "VERIFIED_EXTERNAL_EVIDENCE", "register independent verification")
    need(matrix["P04-T013"]["status"] == "PASS" and matrix["P04-T022"]["status"] == "PASS", "matrix backup")
    need(gates["P04-G005"]["current_state"] == "PASS", "fresh backup gate")
    need(gates["P04-G006"]["current_state"] == "BLOCKED", "restore rehearsal remains blocked")
    need(gates["P04-G010"]["decision"] == HOLD and gates["P04-G012"]["current_state"] == "PASS", "final hold")
    runner = text(RUNNER); tree = ast.parse(runner); imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.add((node.module or "").split(".")[0])
    need(imports == {"__future__", "argparse", "sys"}, "locked runner imports")
    need("EXECUTION_ENABLED = False" in runner and "DATABASE_URL" not in runner, "locked runner source")
    ci = text(CI); match = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)", ci); need(match is not None, "CI targets")
    need(re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M) == TARGETS, "CI target scope")
    need(py_lines(ci) == ["python3 " + VALIDATOR], "CI executes only validator")
    smoke = text(SMOKE)
    gate = re.search(r"(?ms)^# >>> treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate$.*?^# <<< treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate$", smoke)
    need(gate is not None, "P0-04 smoke gate")
    need(py_lines(gate.group(0)) == ['python3 "${PETMED_P0_04_ROOT}/' + VALIDATOR + '"'], "smoke executes only validator")
    need(RUNNER not in "\n".join(py_lines(smoke)), "smoke executes runner")
    for rel in (CI, SMOKE):
        result = subprocess.run(["bash", "-n", str(ROOT / rel)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        need(result.returncode == 0, "shell syntax " + rel)
    if args.require_complete:
        print("NO-GO: PMAI-P0-04 remains IN_PROGRESS; disposable restore rehearsal is incomplete", file=sys.stderr)
        return 1
    for line in (
        "stage_id=PMAI-P0-04", "stage_status=IN_PROGRESS", "evidence_completeness=" + COMPLETENESS,
        "deployment_isolation_verified=true", "fresh_backup_evidence_integrity=PASS",
        "fresh_backup_evidence_sha256=a7af6ca2c0cba862bb7f6073f0866ef6dafcb20364ae64db6c9693fe622798e1", "fresh_backup_artifact_sha256=ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7",
        "fresh_backup_pg_restore_toc_sha256=6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c",
        "fresh_post_p0_03_staging_backup_verified=true", "backup_restoreability_verified=false",
        "disposable_restore_rehearsal_complete=false", "corrected_migration_implementation_authorized=false",
        "runner_execution_enabled=false", "runner_executed_by_ci=false",
        "p0_04_execution_authorized=false", "staging_0010_apply_authorized=false",
        "active_0010_migration_file_created=false", "database_write=false", "migration_executed=false",
        "production_database_write=false", "decision=" + HOLD,
        "ALL PASS: PMAI-P0-04 fresh backup evidence governance",
    ): print(line)
    return 0

if __name__ == "__main__": raise SystemExit(main())
