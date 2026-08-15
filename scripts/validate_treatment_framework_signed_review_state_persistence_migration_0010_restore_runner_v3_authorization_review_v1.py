#!/usr/bin/env python3
"""Validate PMAI-P0-04 Restore Runner V3 Authorization Review V1."""

from __future__ import annotations

import ast
import csv
import glob
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1.md"
CHECKLIST = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1_CHECKLIST_V1.csv"
GO_NO_GO = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1_GO_NO_GO_V1.csv"
TEST_MATRIX = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1_TEST_MATRIX_V1.csv"
DESIGN_DOC = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_RESTORE_RUNNER_DESIGN_PREPARATION_V3.md"
CANDIDATE = "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DISPOSABLE_RESTORE_RUNNER_V3.py.txt"
VALIDATOR = "scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_authorization_review_v1.py"
CI = "scripts/ci_static_checks.sh"
LOCKED_RUNNER = "scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py"

EXPECTED_HEAD = "190de64deac0eef19c9ffcaafc8ecbdcc12f7278"
EXPECTED_PARENT = "959b15b2ea15f31f19564d553207ce31a31561ce"
EXPECTED_ISOLATED = "8d1dc8814ed8f80d8bc965b494c1c320fc08f228"
EXPECTED_PRIOR_CI_SHA256 = "9d02f180ffac1f69ab4f93f0d160bf82cb18205003703d042720b5fda421c7c9"
EXPECTED_FINAL_CI_SHA256 = "8c23f683f89965f4b90bd2925a575d2ac5ee5340ece340cc12b02ec923dcce55"
EXPECTED_LOCKED_RUNNER_SHA256 = "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f"
EXPECTED_CANDIDATE_SHA256 = "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b"
EXPECTED_ARCHIVE_SHA256 = "ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7"
EXPECTED_MEMBER_SET_SHA256 = "3a509a2084dd279e644c95d83d77babe555f21de76950c1c092421952a75e229"
EXPECTED_ROOT_FINGERPRINT_SHA256 = "fcded0b983602688dfdd29b9742cdea17d429d8a19567c01feca91387c7c6d47"
AUTHORIZATION_RECORD_ID = "PMAI-P0-04-RR-V3-AUTH-V1-20260814"
DECISION = "GO_TO_SEPARATE_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1"
NEXT_ACTION = "SEPARATE_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_V1_REQUIRED"

PACKAGE_PATHS = {DOC, CHECKLIST, GO_NO_GO, TEST_MATRIX, VALIDATOR}
REQUIRED_TEST_IDS = {
    "PMAI-P0-04-RR-V3-AUTH-T{:03d}".format(index) for index in range(1, 41)
}


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
    false_names = {
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
    for name in false_names:
        need(values.get(name) is False, "candidate fail-closed literal " + name)

    expected_values = {
        "STAGE_ID": "PMAI-P0-04",
        "DESIGN_ID": "PMAI-P0-04-RRDP-V3-20260813",
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
    }
    for name, expected in expected_values.items():
        need(values.get(name) == expected, "candidate literal " + name)

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    need(imports.issubset({"__future__", "json", "sys"}), "candidate imports")

    forbidden = {
        "open", "input", "getpass", "run", "Popen", "call", "check_call",
        "check_output", "connect", "extract", "extractall",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            need(node.func.id not in forbidden, "candidate forbidden call " + node.func.id)
        elif isinstance(node.func, ast.Attribute):
            need(node.func.attr not in forbidden, "candidate forbidden call " + node.func.attr)


def main() -> int:
    doc = read_text(DOC)
    design_doc = read_text(DESIGN_DOC)
    candidate = read_text(CANDIDATE)
    ci = read_text(CI)

    expected_markers = {
        "stage_id": "PMAI-P0-04",
        "substage": "RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1",
        "package_status": "AUTHORIZATION_REVIEW_AND_BOUNDARY_RECORD_ONLY",
        "review_status": "PROPOSED_APPROVE_INERT_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION_ONLY",
        "authorization_record_id": AUTHORIZATION_RECORD_ID,
        "authorization_recorded_date": "2026-08-14",
        "authorization_scope": "ONE_EXACT_HASH_BOUND_INERT_RESTORE_RUNNER_V3_IMPLEMENTATION_PREPARATION",
        "authorization_scope_recorded": "true",
        "current_restore_runner_v3_implementation_preparation_authorized": "false",
        "post_effective_gate_restore_runner_v3_implementation_preparation_authorized": "true",
        "restore_runner_v3_implementation_authorized": "false",
        "restore_runner_v3_activation_authorized": "false",
        "restore_runner_v3_execution_authorized": "false",
        "local_main": EXPECTED_HEAD,
        "origin_main": EXPECTED_HEAD,
        "main_parent": EXPECTED_PARENT,
        "github_ci_gate_number": "205",
        "github_ci_gate_status": "PASS",
        "github_ci_gate_commit": EXPECTED_HEAD,
        "prior_ci_sha256": EXPECTED_PRIOR_CI_SHA256,
        "final_ci_sha256": EXPECTED_FINAL_CI_SHA256,
        "local_isolated_branch": EXPECTED_ISOLATED,
        "remote_isolated_branch": EXPECTED_ISOLATED,
        "completed_substage": "RESTORE_RUNNER_DESIGN_PREPARATION_V3",
        "completed_commit": EXPECTED_HEAD,
        "completed_ci_gate": "205",
        "selected_route": "ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3",
        "inert_restore_runner_design_candidate_sha256": EXPECTED_CANDIDATE_SHA256,
        "approved_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "member_name_set_sha256": EXPECTED_MEMBER_SET_SHA256,
        "logical_root_fingerprint_sha256": EXPECTED_ROOT_FINGERPRINT_SHA256,
        "root_contract_resolved": "true",
        "root_layout_classification": "PG_DIRECTORY_ROOT_DEEP_WRAPPED",
        "wrapper_depth": "2",
        "authorized_implementation_candidate_created": "false",
        "active_restore_runner_created": "false",
        "fresh_disposable_target_selected": "false",
        "target_provisioning_authorized": "false",
        "database_connection": "false",
        "restore_execution": "false",
        "backup_restoreability_verified": "false",
        "disposable_restore_rehearsal_complete": "false",
        "p0_04_execution_authorized": "false",
        "staging_0010_apply_authorized": "false",
        "files_staged": "false",
        "files_committed": "false",
        "files_pushed": "false",
        "decision": DECISION,
        "next_action": NEXT_ACTION,
    }
    for key, expected in expected_markers.items():
        need(marker(doc, key) == expected, "document marker " + key)

    design_markers = {
        "substage": "RESTORE_RUNNER_DESIGN_PREPARATION_V3",
        "restore_runner_design_preparation_complete": "true",
        "inert_restore_runner_candidate_sha256": EXPECTED_CANDIDATE_SHA256,
        "active_restore_runner_created": "false",
        "restore_runner_execution_authorized": "false",
        "decision": "GO_TO_SEPARATE_RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1",
    }
    for key, expected in design_markers.items():
        need(marker(design_doc, key) == expected, "design marker " + key)

    need(CANDIDATE.endswith(".py.txt"), "candidate suffix")
    need(sha256_path(ROOT / CANDIDATE) == EXPECTED_CANDIDATE_SHA256, "candidate hash")
    validate_candidate(candidate)
    need(sha256_path(ROOT / LOCKED_RUNNER) == EXPECTED_LOCKED_RUNNER_SHA256, "locked runner hash")
    need(sha256_path(ROOT / CI) == EXPECTED_FINAL_CI_SHA256, "CI hash")
    need(not (ROOT / CANDIDATE.removesuffix(".txt")).exists(), "no active runner candidate")
    need(not glob.glob(str(ROOT / "backend/migrations/versions/0010*.py")), "active 0010 migration absent")

    checklist = read_csv(CHECKLIST)
    need(len(checklist) == 52, "checklist row count")
    need(len({row["control_id"] for row in checklist}) == 52, "checklist unique IDs")
    need(all(row["status"] == "PASS" for row in checklist), "checklist status")

    gates = read_csv(GO_NO_GO)
    need(len(gates) == 28, "Go/No-Go row count")
    need(len({row["gate_id"] for row in gates}) == 28, "Go/No-Go unique IDs")
    by_gate = {row["gate"]: row for row in gates}
    need(by_gate["current implementation preparation authority"]["status"] == "PASS", "current authority gate")
    need(by_gate["proposed implementation preparation authority"]["status"] == "PASS", "proposed authority gate")
    need(by_gate["active runner created"]["status"] == "PASS", "active runner gate")
    need(by_gate["repository apply authority"]["status"] == "HOLD", "apply gate")
    need(by_gate["package publication authority"]["status"] == "HOLD", "publication gate")
    need(by_gate["one-time restore authorization"]["status"] == "HOLD", "restore authorization gate")
    need(by_gate["backup restoreability verified"]["status"] == "HOLD", "restoreability gate")

    tests = read_csv(TEST_MATRIX)
    need({row["test_id"] for row in tests} == REQUIRED_TEST_IDS, "test matrix IDs")
    need(all(row["status"] == "DESIGNED" for row in tests), "test matrix status")

    targets = ci_targets(ci)
    need(len(targets) == 122 and len(targets) == len(set(targets)), "CI TARGETS canonical")
    need(PACKAGE_PATHS.issubset(set(targets)), "authorization review package targets")
    command = "python3 " + VALIDATOR + " || exit 1"
    implementation_preparation_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_preparation_v1.py || exit 1"
    implementation_authorization_review_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_restore_runner_v3_implementation_authorization_review_v1.py || exit 1"
    fresh_target_preparation_command = "python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_fresh_disposable_target_provisioning_authorization_preparation_v3.py || exit 1"
    need(
        ci.splitlines().count("# PMAI-P0-04 restore runner V3 authorization review v1") == 1,
        "CI marker count",
    )
    need(ci.splitlines().count(command) == 1, "CI command count")
    need(len(python_lines(ci)) == 25 and python_lines(ci)[-4:] == [command, implementation_preparation_command, implementation_authorization_review_command, fresh_target_preparation_command], "CI command order")

    unsafe_suffixes = (".png", ".jpg", ".jpeg", ".json", ".tar", ".tar.gz", ".db", ".bak", ".save")
    need(not any(path.lower().endswith(unsafe_suffixes) for path in targets), "raw or unsafe target")
    for rel in PACKAGE_PATHS:
        value = read_text(rel)
        need(value.endswith("\n"), "final newline " + rel)
        for line_no, line in enumerate(value.splitlines(), 1):
            need(line == line.rstrip(), "trailing whitespace {}:{}".format(rel, line_no))

    print("PASS: PMAI-P0-04 Restore Runner V3 Authorization Review V1")
    print("stage_id=PMAI-P0-04")
    print("substage=RESTORE_RUNNER_V3_AUTHORIZATION_REVIEW_V1")
    print("package_status=AUTHORIZATION_REVIEW_AND_BOUNDARY_RECORD_ONLY")
    print("authorization_scope_recorded=true")
    print("current_restore_runner_v3_implementation_preparation_authorized=false")
    print("post_effective_gate_restore_runner_v3_implementation_preparation_authorized=true")
    print("restore_runner_v3_activation_authorized=false")
    print("restore_runner_v3_execution_authorized=false")
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
