#!/usr/bin/env python3
"""Validate PMAI-P0-04 Restore Runner Design Preparation V3."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_DESIGN_PREPARATION_V3.md"
CHECKLIST = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_DESIGN_PREPARATION_V3_CHECKLIST_V1.csv"
GO_NO_GO = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_DESIGN_PREPARATION_V3_GO_NO_GO_V1.csv"
TEST_MATRIX = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_DESIGN_PREPARATION_V3_TEST_MATRIX_V1.csv"
CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
V3_EVIDENCE_DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_V1.md"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_design_preparation_v3.py"
ROOT_VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"
CI = "scripts/ci_static_checks.sh"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"

EXPECTED_HEAD = "959b15b2ea15f31f19564d553207ce31a31561ce"
EXPECTED_PARENT = "8f7a4a25908e874f406b08e9ae2d1dc9de69db26"
EXPECTED_ISOLATED = "8d1dc8814ed8f80d8bc965b494c1c320fc08f228"
EXPECTED_PRIOR_CI_SHA256 = "74b9b164ef72436c3989e7b2920b5114c7abda52fec7f601bb322c58ec358f8a"
EXPECTED_FINAL_CI_SHA256 = "33d0cc12675211d7761ab1f1c7a909709c24df56854d31fad1d67638e555614f"
EXPECTED_LOCKED_RUNNER_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_CANDIDATE_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_INVESTIGATOR_V3_SHA256 = "6800bc57c018ad17deb84b2c821baad4752e23f9aa432b01d64f9518737d5e14"
EXPECTED_SANITIZED_V3_RESULT_SHA256 = "2d133850451ef0941443c4588f9f649aafa54f9a1d1e5670e54529f541429040"
EXPECTED_ARCHIVE_SHA256 = "ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7"
EXPECTED_MEMBER_SET_SHA256 = "3a509a2084dd279e644c95d83d77babe555f21de76950c1c092421952a75e229"
EXPECTED_ROOT_FINGERPRINT_SHA256 = "fcded0b983602688dfdd29b9742cdea17d429d8a19567c01feca91387c7c6d47"
PREPARATION_RECORD_ID = "PMAI-P0-04-RRDP-V3-20260813"
DECISION = "GO_TO_SEPARATE_RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1"
NEXT_ACTION = "SEPARATE_RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1_REQUIRED"

PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, CANDIDATE, VALIDATOR}
REQUIRED_TEST_IDS = {
    "PMAI-P0-04-RRDP-V3-T{:03d}".format(index) for index in range(1, 37)
}
EXPECTED_GATE_ORDER = (
    "SEPARATE_RUNNER_AUTHORIZATION_EFFECTIVE",
    "SEPARATE_FRESH_DISPOSABLE_TARGET_AUTHORIZATION_EFFECTIVE",
    "SEPARATE_ONE_TIME_RESTORE_EXECUTION_AUTHORIZATION_EFFECTIVE",
    "EXACT_RUNNER_SOURCE_SHA256_MATCH",
    "FRESH_TARGET_IDENTITY_AND_ISOLATION_RECHECK",
    "APPROVED_ARCHIVE_SHA256_MATCH",
    "SAFE_METADATA_CONTRACT_RECHECK",
    "SAFE_EXTRACTION_TO_NEW_0700_TEMP_DIRECTORY",
    "EXTRACTED_LOGICAL_ROOT_FINGERPRINT_MATCH",
    "READ_ONLY_EMPTY_TARGET_PREFLIGHT",
    "ONE_ATTEMPT_RESERVATION",
    "SINGLE_TRANSACTION_PG_RESTORE",
    "READ_ONLY_SANITIZED_POSTCHECK",
    "SANITIZED_EVIDENCE_WRITE",
    "TEMPORARY_SECRET_AND_EXTRACTION_CLEANUP",
)
EXPECTED_RESTORE_ARGV = (
    "pg_restore",
    "--dbname=service=pmai_p0_04_disposable_restore_v3",
    "--no-owner",
    "--no-privileges",
    "--no-tablespaces",
    "--no-publications",
    "--no-subscriptions",
    "--single-transaction",
    "--exit-on-error",
    "--verbose",
    "--no-password",
    "<SAFE_EXTRACTED_LOGICAL_ROOT>",
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marker(value: str, key: str) -> str:
    found = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", value)
    need(found and len(set(found)) == 1, "marker consistency " + key)
    return found[0]


def read_csv(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def assignments(source: str) -> tuple[ast.Module, dict[str, object]]:
    tree = ast.parse(source, filename=CANDIDATE)
    values: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        values[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            try:
                values[node.target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return tree, values


def ci_targets(value: str) -> list[str]:
    block = re.search(r"(?ms)^TARGETS=\(\n(.*?)^\)\s*$", value)
    need(block is not None, "CI TARGETS block")
    return re.findall(r'^\s*"([^"]+)"\s*$', block.group(1), flags=re.M)


def python_lines(value: str) -> list[str]:
    return [
        line.strip()
        for line in value.splitlines()
        if line.strip().startswith("python3 ")
        and not line.strip().startswith("python3 -m py_compile ")
    ]


def validate_candidate(source: str) -> None:
    tree, values = assignments(source)
    expected_false = {
        "EXECUTION_ENABLED",
        "ARCHIVE_ACCESS_ENABLED",
        "ARCHIVE_LISTING_ENABLED",
        "MEMBER_HEADER_READ_ENABLED",
        "MEMBER_PAYLOAD_READ_ENABLED",
        "ARCHIVE_EXTRACTION_IMPLEMENTED",
        "TARGET_PROVISIONING_ENABLED",
        "DATABASE_CONNECTION_ENABLED",
        "DATABASE_WRITE_ENABLED",
        "RESTORE_PROCESS_IMPLEMENTED",
        "RESTORE_EXECUTION_ENABLED",
        "PG_RESTORE_INVOCATION_ENABLED",
        "PSQL_INVOCATION_ENABLED",
        "AUTOMATIC_RETRY_ENABLED",
        "MANUAL_RETRY_ENABLED",
        "MIGRATION_0010_ENABLED",
        "DEPLOYMENT_ENABLED",
        "RESOURCE_DELETION_ENABLED",
    }
    for name in expected_false:
        need(values.get(name) is False, "candidate fail-closed literal " + name)

    expected_values = {
        "STAGE_ID": "PMAI-P0-04",
        "DESIGN_ID": PREPARATION_RECORD_ID,
        "DESIGN_VERSION": "RESTORE_RUNNER_DESIGN_V3",
        "EXPECTED_ARCHIVE_SHA256": EXPECTED_ARCHIVE_SHA256,
        "EXPECTED_MEMBER_NAME_SET_SHA256": EXPECTED_MEMBER_SET_SHA256,
        "EXPECTED_LOGICAL_ROOT_FINGERPRINT_SHA256": EXPECTED_ROOT_FINGERPRINT_SHA256,
        "EXPECTED_ROOT_LAYOUT_CLASSIFICATION": "PG_DIRECTORY_ROOT_DEEP_WRAPPED",
        "EXPECTED_WRAPPER_DEPTH": 2,
        "EXPECTED_ARCHIVE_MEMBER_COUNT": 29,
        "EXPECTED_TOC_DAT_CANDIDATE_COUNT": 1,
        "EXPECTED_TOC_DAT_NORMALIZED_DEPTH": 2,
        "EXPECTED_TOC_DAT_RELATION": "IMMEDIATE_CHILD_OF_IDENTIFIED_LOGICAL_ROOT",
        "FUTURE_GATE_ORDER": EXPECTED_GATE_ORDER,
        "RESTORE_ARGV_TEMPLATE": EXPECTED_RESTORE_ARGV,
    }
    for name, expected in expected_values.items():
        need(values.get(name) == expected, "candidate literal " + name)

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    need(imports.issubset({"__future__", "json", "sys"}), "candidate imports")

    forbidden_call_names = {"open", "input", "getpass", "run", "Popen", "call", "check_call", "check_output"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            need(node.func.id not in forbidden_call_names, "candidate forbidden call " + node.func.id)
        elif isinstance(node.func, ast.Attribute):
            need(node.func.attr not in forbidden_call_names, "candidate forbidden call " + node.func.attr)


def main() -> int:
    doc = read_text(DOC)
    evidence_doc = read_text(V3_EVIDENCE_DOC)
    candidate = read_text(CANDIDATE)
    ci = read_text(CI)

    expected_markers = {
        "stage_id": "PMAI-P0-04",
        "substage": "RESTORE_RUNNER_DESIGN_PREPARATION_V3",
        "package_status": "INERT_RESTORE_RUNNER_DESIGN_PREPARATION_ONLY",
        "preparation_record_id": PREPARATION_RECORD_ID,
        "current_substage": "ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_EXECUTION_EVIDENCE_V1",
        "selected_route": "ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3",
        "local_main": EXPECTED_HEAD,
        "origin_main": EXPECTED_HEAD,
        "main_parent": EXPECTED_PARENT,
        "github_ci_gate_number": "204",
        "github_ci_gate_status": "PASS",
        "github_ci_gate_commit": EXPECTED_HEAD,
        "prior_ci_sha256": EXPECTED_PRIOR_CI_SHA256,
        "final_ci_sha256": EXPECTED_FINAL_CI_SHA256,
        "local_isolated_branch": EXPECTED_ISOLATED,
        "remote_isolated_branch": EXPECTED_ISOLATED,
        "authorized_candidate_investigator_v3_sha256": EXPECTED_INVESTIGATOR_V3_SHA256,
        "sanitized_v3_investigation_result_sha256": EXPECTED_SANITIZED_V3_RESULT_SHA256,
        "approved_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "member_name_set_sha256": EXPECTED_MEMBER_SET_SHA256,
        "logical_root_fingerprint_sha256": EXPECTED_ROOT_FINGERPRINT_SHA256,
        "root_contract_resolved": "true",
        "root_layout_classification": "PG_DIRECTORY_ROOT_DEEP_WRAPPED",
        "wrapper_depth": "2",
        "inert_restore_runner_candidate_sha256": EXPECTED_CANDIDATE_SHA256,
        "active_restore_runner_created": "false",
        "restore_runner_execution_authorized": "false",
        "fresh_disposable_target_selected": "false",
        "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "decision": DECISION,
        "next_action": NEXT_ACTION,
    }
    for key, expected in expected_markers.items():
        need(marker(doc, key) == expected, "document marker " + key)

    evidence_markers = {
        "root_contract_resolved": "true",
        "root_layout_classification": "PG_DIRECTORY_ROOT_DEEP_WRAPPED",
        "wrapper_depth": "2",
        "sanitized_v3_investigation_result_sha256": EXPECTED_SANITIZED_V3_RESULT_SHA256,
        "decision": "GO_TO_SEPARATE_RESTORE_RUNNER_DESIGN_PREPARATION_V3",
    }
    for key, expected in evidence_markers.items():
        need(marker(evidence_doc, key) == expected, "V3 evidence marker " + key)

    need(CANDIDATE.endswith(".py.txt"), "candidate suffix")
    need(sha256_path(ROOT / CANDIDATE) == EXPECTED_CANDIDATE_SHA256, "candidate hash")
    validate_candidate(candidate)
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, "locked runner hash")
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, "CI hash")
    need(not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")), "active 0010 migration")

    checklist = read_csv(CHECKLIST)
    need(len(checklist) == 50, "checklist row count")
    need(len({row["control_id"] for row in checklist}) == 50, "checklist unique IDs")
    need(all(row["status"] == "PASS" for row in checklist), "checklist status")

    gates = read_csv(GO_NO_GO)
    need(len(gates) == 25, "Go/No-Go row count")
    need(len({row["gate_id"] for row in gates}) == 25, "Go/No-Go unique IDs")
    by_gate = {row["gate"]: row for row in gates}
    need(by_gate["root contract resolved"]["status"] == "PASS", "root contract gate")
    need(by_gate["runner authorization effective"]["status"] == "HOLD", "runner auth gate")
    need(by_gate["fresh target authorization effective"]["status"] == "HOLD", "target auth gate")
    need(by_gate["one-time restore authorization effective"]["status"] == "HOLD", "execution auth gate")
    need(by_gate["backup restoreability verified"]["status"] == "HOLD", "restoreability gate")

    tests = read_csv(TEST_MATRIX)
    need({row["test_id"] for row in tests} == REQUIRED_TEST_IDS, "test matrix IDs")
    need(all(row["status"] == "DESIGNED" for row in tests), "test matrix status")

    targets = ci_targets(ci)
    need(len(targets) == 112 and len(targets) == len(set(targets)), "CI TARGETS canonical")
    need(PACKAGE_PATHS.issubset(set(targets)), "runner design package targets")
    command = "python3 " + VALIDATOR + " || exit 1"
    authorization_review_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_authorization_review_v1.py || exit 1"
    implementation_preparation_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_preparation_v1.py || exit 1"
    need(
        ci.splitlines().count("# PMAI-P0-04 restore runner design preparation V3") == 1,
        "CI marker count",
    )
    need(ci.splitlines().count(command) == 1, "CI command count")
    need(
        len(python_lines(ci)) == 23
        and python_lines(ci)[-3:] == [command, authorization_review_command, implementation_preparation_command],
        "CI command order",
    )

    unsafe_suffixes = (".png", ".jpg", ".jpeg", ".json", ".tar", ".tar.gz", ".db", ".bak", ".save")
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), "raw or unsafe target")
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith("\n"), "final newline " + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), "trailing whitespace {}:{}".format(rel, line_no))

    print("PASS: PMAI-P0-04 Restore Runner Design Preparation V3")
    print("stage_id=PMAI-P0-04")
    print("substage=RESTORE_RUNNER_DESIGN_PREPARATION_V3")
    print("package_status=INERT_RESTORE_RUNNER_DESIGN_PREPARATION_ONLY")
    print("root_contract_resolved=true")
    print("root_layout_classification=PG_DIRECTORY_ROOT_DEEP_WRAPPED")
    print("wrapper_depth=2")
    print("inert_restore_runner_candidate_design_created=true")
    print("active_restore_runner_created=false")
    print("archive_file_opened=false")
    print("backup_archive_listing_invoked=false")
    print("database_connection=false")
    print("restore_execution=false")
    print("backup_restoreability_verified=false")
    print("disposable_restore_rehearsal_complete=false")
    print("p0_04_execution_authorized=false")
    print("staging_0010_apply_authorized=false")
    print("decision=" + DECISION)
    print("next_action=" + NEXT_ACTION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
