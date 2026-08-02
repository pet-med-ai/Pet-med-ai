#!/usr/bin/env python3
"""Fail-closed validator for PMAI-P0-04 deployment-isolation promotion."""
import argparse, ast, csv, glob, hashlib, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLD = 'HOLD_PMAI_P0_04_PENDING_FRESH_BACKUP_REHEARSAL_AND_EXTERNAL_EVIDENCE'
COMPLETENESS = 'PENDING_FRESH_BACKUP_REHEARSAL_AND_EXTERNAL_EXECUTION'
DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md'
CHECKLIST = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv'
REGISTER = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv'
MATRIX = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv'
GO_NO_GO = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv'
EVIDENCE_DOC = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md'
CONTRACT = 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md'
RUNNER = 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
VALIDATOR = 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py'
CI = 'scripts/ci_static_checks.sh'
SMOKE = 'scripts/smoke_petmed.sh'
TARGETS = ['docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md', 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py', 'scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py', 'scripts/ci_static_checks.sh', 'scripts/smoke_petmed.sh']
HASHES = {'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md': '66e8caf12033b4d6ebd43759c08ffb86799d483ec85bef53082f21090136c234', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt': 'bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1.md': '9ca66949f5c515805ade771be5d224eda5bc35827e552c30b2c81656bff7a132', 'backend/models.py': '91d1343c1ebe3df16f00bada05b2b0053f9747e6f714f726a81cd499357b448c', 'docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md': 'a1996e0c022f7a42a83d40f5f2e9bdd8bec2e77a106aa7b8aa0a231b87d83844', 'scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py': 'c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f', 'render.yaml': 'd3bd51ce5fa0dffa8639d0b647784e54bebb8d1040a94f5c2ecd18a789d11150', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1.md': 'a50a807907c15b4cbc0d67f8ee21853468201925694ea52d213ccb5925a8fa41', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_CHECKLIST_V1.csv': 'a0120f2422598833d05671a6d60a0964ae444d4b489a02258f1f852588410746', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_EVIDENCE_REGISTER_V1.csv': '7a0d7d7ffa2216e5ac7c4579da95e61d351e99adec762233e58c10bd4831570e', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_TEST_MATRIX_V1.csv': '493e0fb47eb570567cf2675db3dba05d270e1f08c8a385e5f1ed47d61a24673c', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_GO_NO_GO_V1.csv': 'c7069661193e154dd91212b3383fab961de3ac4a7c1017ccdf212d2ff90989f2', 'docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md': '99bbe0447b47d1aa0c9fd87cb6f55a4554e879a9b8151377b96cec3550cab4c6', 'scripts/ci_static_checks.sh': '2f77ff114b74c2c0ba09d69e7608078814f0c92215554668fece785d45479cc1', 'scripts/smoke_petmed.sh': 'f8b7fa8befa951797ef7ab77b2bc0c16d50c4e411b60ae6ef22c547240febdb0'}
EVIDENCE_SHA256 = '67fe12a4dc32e8edf91217693bf5ad85a7ab17fee107111aeafde66fabd4525b'

def need(ok, message):
    if not ok:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)

def text(rel):
    path = ROOT / rel
    need(path.is_file(), "missing " + rel)
    return path.read_text(encoding="utf-8")

def marker(value, key):
    found = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", value)
    need(len(found) == 1, "marker count " + key)
    return found[0]

def csv_map(rel, id_name):
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    need(reader.fieldnames and reader.fieldnames[0] == id_name, "CSV header " + rel)
    ids = [row[id_name] for row in rows]
    need(len(ids) == len(set(ids)), "duplicate CSV id " + rel)
    return {row[id_name]: row for row in rows}

def py_lines(value):
    return [line.strip() for line in value.splitlines() if line.strip().startswith("python3 ") and not line.strip().startswith("python3 -m py_compile ")]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    for rel, expected in HASHES.items():
        path = ROOT / rel
        need(path.is_file(), "missing protected file " + rel)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        need(actual == expected, "protected hash " + rel)
    need(not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")), "active 0010 migration exists")
    doc = text(DOC)
    exact = {
        "stage_id": "PMAI-P0-04", "STAGE_STATUS": "IN_PROGRESS",
        "EVIDENCE_COMPLETENESS": COMPLETENESS,
        "staging_only_branch_or_commit_pin_verified": "true",
        "production_deployment_freeze_verified": "false",
        "production_target_excluded": "true", "deployment_isolation_verified": "true",
        "manual_deploy_observed": "true", "manual_deploy_deviation_recorded": "true",
        "manual_deploy_deviation_safely_verified": "true",
        "candidate_migration_deployed": "false",
        "postdeploy_readonly_verification_passed": "true",
        "fresh_post_p0_03_staging_backup_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "corrected_migration_implementation_authorized": "false",
        "P0_04_EXECUTION_AUTHORIZED": "false", "STAGING_0010_APPLY_AUTHORIZED": "false",
        "ACTIVE_0010_MIGRATION_FILE_CREATED": "false", "migration_created": "false",
        "migration_executed": "false", "production_database_write": "false",
        "decision": HOLD,
    }
    for key, expected in exact.items():
        need(marker(doc, key) == expected, "document marker " + key)
    evidence = text(EVIDENCE_DOC)
    for key, expected in {
        "evidence_type": "DEPLOYMENT_ISOLATION_AND_SAFE_MANUAL_DEPLOY_READBACK",
        "evidence_artifact_sha256": EVIDENCE_SHA256,
        "render_configuration_observation_confirmed": "true",
        "baseline_commit_sha": '8d1dc8814ed8f80d8bc965b494c1c320fc08f228',
        "isolated_branch": 'pmai-p0-04-staging-0010',
        "staging_branch": 'pmai-p0-04-staging-0010', "staging_auto_deploy": "false",
        "production_branch": "main", "production_auto_deploy_trigger": "commit",
        "production_target_excluded": "true",
        "production_deployment_freeze_verified": "false",
        "deployment_isolation_verified_as_point_in_time": "true",
        "manual_deploy_observed": "true", "manual_deploy_deviation_recorded": "true",
        "manual_deploy_deviation_safely_verified": "true",
        "candidate_migration_deployed": "false",
        "postdeploy_readonly_verification_passed": "true",
        "staging_database_revision": "0009_diag_data",
        "production_database_revision": "0009_diag_data",
        "active_0010_migration_file_present": "false",
        "direct_database_connection": "false", "database_write": "false",
        "migration_created": "false", "migration_executed": "false",
        "runner_execution_enabled": "false", "runner_executed_by_ci": "false",
        "staging_0010_migration_executed": "false",
        "production_migration_authorized": "false",
        "production_migration_executed": "false",
        "decision": HOLD,
    }.items():
        need(marker(evidence, key) == expected, "evidence marker " + key)
    checklist = csv_map(CHECKLIST, "item_id")
    register = csv_map(REGISTER, "evidence_id")
    matrix = csv_map(MATRIX, "test_id")
    gates = csv_map(GO_NO_GO, "gate_id")
    need(checklist["P04-C010"]["status"] == "VERIFIED_EXTERNAL_EVIDENCE", "checklist isolation")
    need(checklist["P04-C025"]["status"] == "VERIFIED_EXTERNAL_EVIDENCE", "checklist deviation")
    need(register["P04-E009"]["status"] == "VERIFIED_EXTERNAL_EVIDENCE", "register isolation")
    need(register["P04-E021"]["status"] == "VERIFIED_EXTERNAL_EVIDENCE", "register deviation")
    need(matrix["P04-T012"]["status"] == "PASS" and matrix["P04-T021"]["status"] == "PASS", "matrix evidence")
    need(gates["P04-G004"]["current_state"] == "PASS", "isolation gate")
    need(gates["P04-G010"]["decision"] == HOLD, "final hold")
    need(gates["P04-G011"]["current_state"] == "PASS", "manual-deploy deviation gate")
    runner = text(RUNNER)
    tree = ast.parse(runner)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
    need(imports == {"__future__", "argparse", "sys"}, "locked runner imports")
    need("EXECUTION_ENABLED = False" in runner and "DATABASE_URL" not in runner, "locked runner source")
    ci = text(CI)
    match = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)", ci)
    need(match is not None, "CI targets")
    ci_targets = re.findall(r'^\s*"([^"]+)"\s*$', match.group(1), flags=re.M)
    need(ci_targets == TARGETS, "CI target scope")
    need(py_lines(ci) == ["python3 " + VALIDATOR], "CI executes only validator")
    smoke = text(SMOKE)
    gate = re.search(r"(?ms)^# >>> treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate$.*?^# <<< treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply_v1_smoke_petmed_runtime_gate$", smoke)
    need(gate is not None, "P0-04 smoke gate")
    need(py_lines(gate.group(0)) == ['python3 "${PETMED_P0_04_ROOT}/' + VALIDATOR + '"'], "smoke executes only P0-04 validator in current gate")
    need(RUNNER not in "\n".join(py_lines(smoke)), "smoke executes runner")
    for rel in (CI, SMOKE):
        result = subprocess.run(["bash", "-n", str(ROOT / rel)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        need(result.returncode == 0, "shell syntax " + rel)
    if args.require_complete:
        print("NO-GO: PMAI-P0-04 remains IN_PROGRESS; fresh backup and disposable rehearsal are incomplete", file=sys.stderr)
        return 1
    for line in (
        "stage_id=PMAI-P0-04", "stage_status=IN_PROGRESS",
        "evidence_completeness=" + COMPLETENESS,
        "deployment_isolation_verified=true", "staging_only_branch_or_commit_pin_verified=true",
        "deployment_isolation_verified_as_point_in_time=true",
        "production_target_excluded=true", "production_deployment_freeze_verified=false",
        "manual_deploy_observed=true", "manual_deploy_deviation_recorded=true",
        "manual_deploy_deviation_safely_verified=true", "candidate_migration_deployed=false",
        "postdeploy_readonly_verification_passed=true",
        "fresh_post_p0_03_staging_backup_verified=false",
        "disposable_restore_rehearsal_complete=false",
        "corrected_migration_implementation_authorized=false",
        "runner_execution_enabled=false", "runner_executed_by_ci=false",
        "p0_04_execution_authorized=false", "staging_0010_apply_authorized=false",
        "active_0010_migration_file_created=false", "direct_database_connection=false",
        "staging_0010_migration_executed=false",
        "production_migration_authorized=false", "production_migration_executed=false",
        "database_read_only_check_via_service=true", "database_write=false",
        "migration_executed=false", "production_database_write=false",
        "decision=" + HOLD,
        "ALL PASS: PMAI-P0-04 deployment isolation evidence governance",
    ):
        print(line)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
