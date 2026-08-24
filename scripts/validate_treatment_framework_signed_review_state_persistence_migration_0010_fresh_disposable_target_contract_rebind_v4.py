#!/usr/bin/env python3
"""Fail-closed validator for the PMAI-P0-04 V4 repository contract rebind."""

import ast
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "b8d79ff3af32b1452672cdeb766e2e35b72c1213"
STAGE_ID = "PMAI-P0-04"
WORK_BUNDLE = "PMAI-P0-04-DISP-TARGET-REBIND-V4"
REVIEW_RECORD = "PMAI-P0-04-FDTP-AUTH-REVIEW-V4-20260823"
V3_NAME = "pet-med-ai-db-p0-04-fresh-disposable-restore-v3-ohio"
V3_IDENTITY = "e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744"
V4_NAME = "pet-med-ai-db-p0-04-fresh-disposable-restore-v4-ohio"
V4_IDENTITY = "e1cba6bc207fa4654d3155ef4abd8d818d8fd4323ce990446bc680fd15522529"
ABSENCE_RESULT = (
    "PASS_PMAI_P0_04_V3_TARGET_RETIREMENT_AND_ABSENCE_READ_ONLY_EVIDENCE_V1"
)
NEXT_SUBJECT = (
    "FRESH_DISPOSABLE_TARGET_PROVISIONING_EXTERNAL_EXECUTION_AUTHORIZATION_V4"
)
PASS_MARKER = "fresh_disposable_target_contract_rebind_v4=PASS"

PREFIX = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4"
)
DOC = PREFIX + ".md"
CHECKLIST = PREFIX + "_CHECKLIST_V1.csv"
GO_NO_GO = PREFIX + "_GO_NO_GO_V1.csv"
TEST_MATRIX = PREFIX + "_TEST_MATRIX_V1.csv"
BASELINE = PREFIX + "_LOCKED_BASELINE_V1.json"
POINTER = PREFIX + "_ACTIVE_POINTER_V1.json"
MANIFEST = PREFIX + "_PACKAGE_MANIFEST_V1.json"
VALIDATOR = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_fresh_disposable_target_contract_rebind_v4.py"
)
CENTRAL = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_staging_migration_apply.py"
)
CI = "scripts/ci_static_checks.sh"

MANIFEST_MEMBERS = tuple(sorted((
    DOC,
    CHECKLIST,
    GO_NO_GO,
    TEST_MATRIX,
    BASELINE,
    POINTER,
    VALIDATOR,
)))
PACKAGE_PATHS = tuple(sorted((*MANIFEST_MEMBERS, MANIFEST)))
AUTHORIZED_CHANGED_PATHS = set((*PACKAGE_PATHS, CENTRAL))

EXPECTED_CONTRACT_FIELDS = {
    "target_logical_name": V4_NAME,
    "target_provider": "Render",
    "target_region": "Ohio (US East)",
    "target_engine_family": "PostgreSQL",
    "target_server_major_version": 18,
    "target_instance_type": "Basic-256mb",
    "target_storage_gb": 1,
    "target_storage_autoscaling": False,
    "target_read_replica_count": 0,
    "target_high_availability": False,
    "target_connection_pooling": False,
    "target_application_attachment_count": 0,
    "target_network_scope": "UNATTACHED_NO_APPLICATION_TRAFFIC",
    "target_external_access_scope": (
        "EXECUTION_TIME_SINGLE_OPERATOR_EGRESS_ALLOWLIST_ONLY"
    ),
    "target_cost_ceiling_usd": "1.00",
    "target_max_lifetime_hours": 72,
    "target_delete_within_hours_after_required_evidence": 24,
    "target_must_be_new": True,
    "target_must_be_empty": True,
    "target_provisioning_authorized": False,
}

V3_ANCHOR_HASHES = {
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_"
        "AUTHORIZATION_REVIEW_V3.md"
    ): "73733bcf9ef0f165ac62a5d01005fc85c99811b6324b786ff820f11be7f7ef30",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_"
        "AUTHORIZATION_PREPARATION_V3.md"
    ): "0e087029080376122ecc3a152f9cf7b2b8d3374921bdb08b3021278ae4d01075",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_FRESH_DISPOSABLE_TARGET_PROVISIONING_"
        "EXECUTION_EVIDENCE_V3.md"
    ): "078e88826d67cdeeafcddf63df0c1205ee94d774cce238d1ef358357da00998c",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_"
        "RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_PREPARATION_V1_"
        "LOCKED_BASELINE_V1.json"
    ): "152fb13e8feb5c019263a56d4a28fc6bcc6a6ad2b0c537385aea4f22c7b08fc8",
    (
        "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_"
        "RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_PREPARATION_V1_"
        "PACKAGE_MANIFEST_V1.json"
    ): "4439e3a4d86b9e8017ac29260631d7a0c16b9182bd7833a0cbc2e8c6e38d1855",
}
CI_SHA256 = "a26f17997b73dffc542faa369c447431d97f36a84d4979fe26c3994dddcaee9b"
EVIDENCE_SHA256 = {
    "all_services_exact_search": (
        "327488e6bef5409eadd1bd4458db63abeaa035e1ed4adf60bba982967ad2bc4c"
    ),
    "blueprint_absence": (
        "01539bd09fc37aff36c91199e163cd23ba4f6eaad3620615b469c181df04b978"
    ),
    "browser_history": (
        "8d9628567e9b2d6c4d1c728faf31707f6d8458fb6177e4c20d38ac43d8880825"
    ),
    "direct_target_page_not_found": (
        "3e920d9a57b22f00a3345c64dfbf3f948e618d586f7a2cae27202197f033e76b"
    ),
    "recovery_page_not_found": (
        "710c73538c03e533531c3ea3d7a036374c0d00358f60f06d926522b81c98ef6b"
    ),
}


def need(condition, message):
    if not condition:
        print("NO-GO: " + message, file=sys.stderr)
        raise SystemExit(1)


def safe_path(relative):
    path = ROOT / relative
    need(path.is_file() and not path.is_symlink(), "missing or unsafe " + relative)
    size = path.stat().st_size
    need(0 < size <= 300_000, "unsafe file size " + relative)
    return path


def digest(relative):
    return hashlib.sha256(safe_path(relative).read_bytes()).hexdigest()


def text(relative):
    return safe_path(relative).read_text(encoding="utf-8")


def load_json(relative):
    try:
        return json.loads(text(relative))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        need(False, "invalid JSON " + relative + ": " + str(exc))


def marker(value, key):
    matches = re.findall(r"(?m)^" + re.escape(key) + r"=([^\r\n]+)$", value)
    need(len(matches) == 1, "marker count " + key)
    return matches[0]


def csv_rows(relative, expected_header, id_name):
    with safe_path(relative).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    need(reader.fieldnames == expected_header, "CSV header " + relative)
    ids = [row[id_name] for row in rows]
    need(len(ids) == len(set(ids)), "duplicate CSV id " + relative)
    need(all(set(row) == set(expected_header) for row in rows), "CSV row shape " + relative)
    return rows


def typed_equal(actual, expected):
    return type(actual) is type(expected) and actual == expected


def git_lines(*arguments):
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=False,
    )
    need(result.returncode == 0, "git inspection " + " ".join(arguments))
    return [line for line in result.stdout.splitlines() if line]


def validate_authorized_commit_scope():
    introductions = git_lines(
        "log", "-1", "--diff-filter=A", "--format=%H", "--", VALIDATOR
    )
    if introductions:
        need(len(introductions) == 1, "V4 validator introduction commit count")
        changed = set(git_lines(
            "diff-tree", "--root", "--no-commit-id", "--name-only", "-r",
            introductions[0],
        ))
    else:
        changed = set(git_lines("diff", "--name-only", BASE_COMMIT + "...HEAD"))
        changed.update(git_lines("diff", "--name-only"))
        changed.update(git_lines("diff", "--cached", "--name-only"))
        changed.update(git_lines("ls-files", "--others", "--exclude-standard"))
    need(changed == AUTHORIZED_CHANGED_PATHS, "exact authorized nine-path scope")


def validate_document():
    value = text(DOC)
    expected_markers = {
        "stage_id": STAGE_ID,
        "substage": "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4",
        "work_bundle": WORK_BUNDLE,
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "risk_lane": "YELLOW_REPOSITORY_ONLY",
        "repository_only": "true",
        "changed_path_scope": "EXACT_9_PATHS",
        "maximum_changed_path_count": "9",
        "prior_v3_target_logical_name": V3_NAME,
        "prior_v3_target_contract_identity_sha256": V3_IDENTITY,
        "prior_v3_target_state": "RETIRED_ABSENCE_VERIFIED_HISTORICAL",
        "prior_v3_absence_evidence_required": "true",
        "prior_v3_absence_evidence_result": ABSENCE_RESULT,
        "prior_v3_absence_evidence_source": (
            "EXTERNAL_OPERATOR_READ_ONLY_EVIDENCE_DECISION_TOKEN"
        ),
        "prior_v3_absence_evidence_reverified_by_repository_validator": "false",
        "prior_v3_absence_evidence_raw_artifacts_stored": "false",
        "preserve_v3_historical_files_byte_exact": "true",
        "review_record_id": REVIEW_RECORD,
        "reviewed_v4_target_logical_name": V4_NAME,
        "reviewed_v4_target_contract_identity_sha256": V4_IDENTITY,
        "reviewed_v4_contract_identity_source": "PRIOR_APPROVED_REVIEW_RECORD",
        "reviewed_v4_contract_identity_reused_from_prior_review": "true",
        "reviewed_v4_contract_identity_is_opaque": "true",
        "reviewed_v4_contract_hash_recalculation_claim": "false",
        "reviewed_v4_contract_exact_field_count": "20",
        "provider_account_scope": "PROJECT_OWNER_EXISTING_RENDER_ACCOUNT",
        "target_contract_rebind_recorded": "true",
        "active_repository_contract_version": "V4",
        "active_repository_contract_identity_sha256": V4_IDENTITY,
        "prior_v3_contract_remains_historical": "true",
        "target_selected": "false",
        "target_created": "false",
        "external_resource_identity_bound": "false",
        "raw_provider_resource_identifier_recorded": "false",
        "provider_url_recorded": "false",
        "credential_material_recorded": "false",
        "external_target_provisioning_authorized": "false",
        "render_control_plane_access_performed": "false",
        "render_settings_change": "false",
        "database_connection": "false",
        "data_read_write_export": "false",
        "runner_execution": "false",
        "restore_execution": "false",
        "migration_execution": "false",
        "deployment": "false",
        "target_deletion": "false",
        "production_staging_v3_resource_operations": "false",
        "other_resource_operations": "false",
        "manual_retry": "false",
        "automatic_retry": "false",
        "decision": "PASS_REPOSITORY_CONTRACT_REBIND_RECORD_NO_EXTERNAL_AUTHORITY",
        "sole_next_subject": NEXT_SUBJECT,
    }
    for key, expected in expected_markers.items():
        need(marker(value, key) == expected, "document marker " + key)
    for key, expected in EXPECTED_CONTRACT_FIELDS.items():
        if isinstance(expected, bool):
            rendered = "true" if expected else "false"
        else:
            rendered = str(expected)
        need(marker(value, key) == rendered, "contract marker " + key)


def validate_baseline():
    baseline = load_json(BASELINE)
    expected_top = {
        "schema", "stage_id", "work_bundle", "repository", "base_branch",
        "base_commit", "authorized_changed_path_count", "authorization_record",
        "prior_v3_contract", "prior_v3_absence_evidence", "reviewed_v4_contract",
        "repository_rebind", "execution_boundaries", "sole_next_subject",
    }
    need(set(baseline) == expected_top, "locked baseline top-level schema")
    need(
        baseline["schema"]
        == "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_LOCKED_BASELINE_V1",
        "locked baseline schema",
    )
    for key, expected in {
        "stage_id": STAGE_ID,
        "work_bundle": WORK_BUNDLE,
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "authorized_changed_path_count": 9,
        "sole_next_subject": NEXT_SUBJECT,
    }.items():
        need(typed_equal(baseline[key], expected), "locked baseline " + key)

    authorization = baseline["authorization_record"]
    expected_authorization = {
        "authorization_id": (
            "PMAI_P0_04_DISP_TARGET_REBIND_V4_REPOSITORY_PATCH_"
            "CONTROLLED_EXECUTION_V1"
        ),
        "review_record_id": REVIEW_RECORD,
        "risk_lane": "YELLOW_REPOSITORY_ONLY",
        "provider_account_scope": "PROJECT_OWNER_EXISTING_RENDER_ACCOUNT",
        "changed_path_scope": "EXACT_9_PATHS",
        "maximum_changed_path_count": 9,
        "contract_identity_source": "PRIOR_APPROVED_REVIEW_RECORD",
        "contract_identity_reused_from_prior_review": True,
        "contract_identity_is_opaque": True,
        "contract_hash_recalculation_claim": False,
    }
    need(authorization == expected_authorization, "authorization record")

    expected_v3 = {
        "target_logical_name": V3_NAME,
        "target_contract_identity_sha256": V3_IDENTITY,
        "state": "RETIRED_ABSENCE_VERIFIED_HISTORICAL",
        "remains_historical": True,
        "historical_files_byte_exact": True,
    }
    need(baseline["prior_v3_contract"] == expected_v3, "prior V3 contract")

    absence = baseline["prior_v3_absence_evidence"]
    need(
        set(absence) == {
            "required", "result", "source", "repository_validator_reverified",
            "raw_artifacts_stored", "facts", "evidence_sha256",
        },
        "absence evidence schema",
    )
    need(absence["required"] is True, "absence evidence required")
    need(absence["result"] == ABSENCE_RESULT, "absence evidence result")
    need(
        absence["source"] == "EXTERNAL_OPERATOR_READ_ONLY_EVIDENCE_DECISION_TOKEN",
        "absence evidence source",
    )
    need(absence["repository_validator_reverified"] is False, "absence not reverified")
    need(absence["raw_artifacts_stored"] is False, "absence raw artifacts")
    expected_facts = {
        "target_deleted": True,
        "absent_from_active_services": True,
        "absent_from_suspended_services": True,
        "absent_from_all_services": True,
        "exact_name_search_no_match": True,
        "direct_target_lookup_page_not_found": True,
        "recovery_lookup_page_not_found": True,
        "blueprint_recreation_risk_observed": False,
        "retry_or_redelete_performed": False,
    }
    need(absence["facts"] == expected_facts, "absence evidence facts")
    need(absence["evidence_sha256"] == EVIDENCE_SHA256, "absence evidence digests")

    reviewed = baseline["reviewed_v4_contract"]
    need(
        set(reviewed) == {
            "review_record_id", "target_contract_identity_sha256",
            "identity_source", "identity_reused_from_prior_review",
            "identity_is_opaque", "hash_recalculation_claim", "exact_field_count",
            "contract_fields",
        },
        "reviewed V4 schema",
    )
    need(reviewed["review_record_id"] == REVIEW_RECORD, "V4 review record")
    need(reviewed["target_contract_identity_sha256"] == V4_IDENTITY, "V4 identity")
    need(reviewed["identity_source"] == "PRIOR_APPROVED_REVIEW_RECORD", "V4 source")
    need(reviewed["identity_reused_from_prior_review"] is True, "V4 identity reused")
    need(reviewed["identity_is_opaque"] is True, "V4 identity opaque")
    need(reviewed["hash_recalculation_claim"] is False, "V4 no hash recalculation")
    need(reviewed["exact_field_count"] == 20, "V4 field count")
    fields = reviewed["contract_fields"]
    need(set(fields) == set(EXPECTED_CONTRACT_FIELDS), "V4 contract exact keys")
    for key, expected in EXPECTED_CONTRACT_FIELDS.items():
        need(typed_equal(fields[key], expected), "V4 contract field " + key)
    need(V3_NAME != V4_NAME and V3_IDENTITY != V4_IDENTITY, "V3 V4 separation")

    expected_rebind = {
        "recorded": True,
        "active_contract_version": "V4",
        "active_contract_identity_sha256": V4_IDENTITY,
        "prior_v3_contract_remains_historical": True,
        "target_selected": False,
        "target_created": False,
        "external_resource_identity_bound": False,
        "external_resource_binding_state": "UNBOUND",
        "raw_provider_resource_identifier_recorded": False,
        "provider_url_recorded": False,
        "credential_material_recorded": False,
    }
    need(baseline["repository_rebind"] == expected_rebind, "repository rebind")
    boundaries = baseline["execution_boundaries"]
    need(len(boundaries) == 15, "execution boundary count")
    need(all(type(value) is bool and value is False for value in boundaries.values()),
         "execution boundary false")
    return baseline


def validate_pointer(baseline):
    pointer = load_json(POINTER)
    expected_keys = {
        "schema", "stage_id", "work_bundle", "pointer_version", "pointer_scope",
        "active_contract_version", "active_review_record_id",
        "active_target_logical_name", "active_target_contract_identity_sha256",
        "active_locked_baseline_path", "active_locked_baseline_sha256",
        "previous_contract_version", "previous_target_logical_name",
        "previous_target_contract_identity_sha256", "previous_contract_state",
        "prior_v3_absence_evidence_result", "external_resource_binding_state",
        "target_selected", "target_created", "external_execution_authorized",
        "sole_next_subject",
    }
    need(set(pointer) == expected_keys, "active pointer schema")
    expected_values = {
        "schema": "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_ACTIVE_POINTER_V1",
        "stage_id": STAGE_ID,
        "work_bundle": WORK_BUNDLE,
        "pointer_version": 1,
        "pointer_scope": "REPOSITORY_GOVERNANCE_ONLY",
        "active_contract_version": "V4",
        "active_review_record_id": REVIEW_RECORD,
        "active_target_logical_name": V4_NAME,
        "active_target_contract_identity_sha256": V4_IDENTITY,
        "active_locked_baseline_path": BASELINE,
        "active_locked_baseline_sha256": digest(BASELINE),
        "previous_contract_version": "V3",
        "previous_target_logical_name": V3_NAME,
        "previous_target_contract_identity_sha256": V3_IDENTITY,
        "previous_contract_state": "RETIRED_ABSENCE_VERIFIED_HISTORICAL",
        "prior_v3_absence_evidence_result": ABSENCE_RESULT,
        "external_resource_binding_state": "UNBOUND",
        "target_selected": False,
        "target_created": False,
        "external_execution_authorized": False,
        "sole_next_subject": NEXT_SUBJECT,
    }
    need(pointer == expected_values, "active pointer values")
    need(
        pointer["active_target_contract_identity_sha256"]
        == baseline["reviewed_v4_contract"]["target_contract_identity_sha256"],
        "pointer baseline identity",
    )


def validate_csvs():
    checklist = csv_rows(
        CHECKLIST,
        ["control_id", "control", "expected", "current", "status", "evidence", "on_failure"],
        "control_id",
    )
    need(len(checklist) == 51, "checklist row count")
    need(
        [row["control_id"] for row in checklist]
        == [f"CRV4-C{number:03d}" for number in range(1, 52)],
        "checklist identifiers",
    )
    need(all(row["status"] == "PASS" for row in checklist), "checklist status")

    gates = csv_rows(
        GO_NO_GO,
        ["gate_id", "gate", "required", "current", "status", "on_failure"],
        "gate_id",
    )
    need(len(gates) == 28, "go-no-go row count")
    need(
        [row["gate_id"] for row in gates]
        == [f"CRV4-G{number:03d}" for number in range(1, 29)],
        "go-no-go identifiers",
    )
    need(all(row["status"] == "PASS" for row in gates[:18]), "static gates pass")
    need(
        all(row["status"] == "HOLD_EXPECTED" for row in gates[18:]),
        "external gates hold",
    )

    tests = csv_rows(
        TEST_MATRIX,
        ["test_id", "test", "method", "expected", "status", "on_failure"],
        "test_id",
    )
    need(len(tests) == 42, "test matrix row count")
    need(
        [row["test_id"] for row in tests]
        == [f"CRV4-T{number:03d}" for number in range(1, 43)],
        "test matrix identifiers",
    )
    need(all(row["status"] == "DESIGNED" for row in tests[:40]), "negative tests designed")
    need(all(row["status"] == "PASS" for row in tests[40:]), "positive tests pass")


def validate_manifest():
    manifest = load_json(MANIFEST)
    expected_keys = {
        "schema", "stage_id", "work_bundle", "repository", "base_branch",
        "base_commit", "authorized_changed_path_count", "package_path_count",
        "manifest_member_count", "manifest_self_excluded",
        "central_integration_path", "ci_entrypoint_changed", "files",
    }
    need(set(manifest) == expected_keys, "package manifest schema")
    expected_metadata = {
        "schema": "PMAI_P0_04_FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_PACKAGE_MANIFEST_V1",
        "stage_id": STAGE_ID,
        "work_bundle": WORK_BUNDLE,
        "repository": "pet-med-ai/Pet-med-ai",
        "base_branch": "main",
        "base_commit": BASE_COMMIT,
        "authorized_changed_path_count": 9,
        "package_path_count": 8,
        "manifest_member_count": 7,
        "manifest_self_excluded": True,
        "central_integration_path": CENTRAL,
        "ci_entrypoint_changed": False,
    }
    for key, expected in expected_metadata.items():
        need(typed_equal(manifest[key], expected), "manifest metadata " + key)
    files = manifest["files"]
    need(type(files) is list and len(files) == 7, "manifest file count")
    need(
        [item.get("path") for item in files] == list(MANIFEST_MEMBERS),
        "manifest paths and order",
    )
    for item in files:
        need(set(item) == {"path", "bytes", "sha256"}, "manifest member schema")
        relative = item["path"]
        path = safe_path(relative)
        need(type(item["bytes"]) is int, "manifest byte type " + relative)
        need(item["bytes"] == path.stat().st_size, "manifest bytes " + relative)
        need(item["sha256"] == digest(relative), "manifest digest " + relative)
    need(MANIFEST not in {item["path"] for item in files}, "manifest self exclusion")


def literal_assignments(source):
    tree = ast.parse(source)
    assignments = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            assignments[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
    return assignments


def validate_central_hook():
    source = text(CENTRAL)
    assignments = literal_assignments(source)
    expected = {
        "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_VALIDATOR": VALIDATOR,
        "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_VALIDATOR_SHA256": digest(VALIDATOR),
        "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_MANIFEST": MANIFEST,
        "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_MANIFEST_SHA256": digest(MANIFEST),
        "FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_PASS_MARKER": PASS_MARKER,
    }
    for key, value in expected.items():
        need(assignments.get(key) == value, "central hook constant " + key)
    need(source.count("v4_result = subprocess.run(") == 1, "central V4 subprocess count")
    need(
        source.count('[sys.executable, "-B", str(v4_validator_path)]') == 1,
        "central V4 subprocess command",
    )
    need(
        source.count("FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4_PASS_MARKER") >= 3,
        "central V4 PASS marker checks",
    )


def validate_protected_anchors():
    for relative, expected in V3_ANCHOR_HASHES.items():
        need(digest(relative) == expected, "protected V3 hash " + relative)
    review_path = next(path for path in V3_ANCHOR_HASHES if "AUTHORIZATION_REVIEW_V3.md" in path)
    review = text(review_path)
    need(V3_NAME in review, "V3 logical name anchor")
    need(V3_IDENTITY in review, "V3 identity anchor")
    need(digest(CI) == CI_SHA256, "CI entrypoint byte exact")
    need(
        not list((ROOT / "backend/migrations/versions").glob("0010*.py")),
        "active 0010 migration implementation",
    )


def validate_no_sensitive_material():
    combined = "\n".join(text(relative) for relative in (*PACKAGE_PATHS,))
    forbidden = {
        "provider or external URL": r"(?i)\bhttps?://",
        "database URI": r"(?i)\bpostgres(?:ql)?://",
        "raw provider resource identifier": r"(?i)\b(?:dpg|srv)-[a-z0-9]{6,}\b",
        "credential assignment": (
            r"(?i)\b(?:password|secret|database_url|access_token)\s*[:=]\s*"
            r"[^\s,}\]]+"
        ),
    }
    for label, pattern in forbidden.items():
        need(re.search(pattern, combined) is None, "forbidden " + label)


def main():
    need(len(AUTHORIZED_CHANGED_PATHS) == 9, "authorized path cardinality")
    need(len(PACKAGE_PATHS) == 8, "package path cardinality")
    for relative in PACKAGE_PATHS:
        safe_path(relative)
    validate_authorized_commit_scope()
    validate_protected_anchors()
    validate_document()
    baseline = validate_baseline()
    validate_pointer(baseline)
    validate_csvs()
    validate_manifest()
    validate_central_hook()
    validate_no_sensitive_material()
    for line in (
        PASS_MARKER,
        "stage_id=" + STAGE_ID,
        "work_bundle=" + WORK_BUNDLE,
        "repository_only=true",
        "prior_v3_target_state=RETIRED_ABSENCE_VERIFIED_HISTORICAL",
        "prior_v3_absence_evidence_result=" + ABSENCE_RESULT,
        "review_record_id=" + REVIEW_RECORD,
        "reviewed_v4_target_contract_identity_sha256=" + V4_IDENTITY,
        "reviewed_v4_contract_identity_reused_from_prior_review=true",
        "reviewed_v4_contract_identity_is_opaque=true",
        "reviewed_v4_contract_hash_recalculation_claim=false",
        "reviewed_v4_contract_exact_field_count=20",
        "active_repository_contract_version=V4",
        "target_selected=false",
        "target_created=false",
        "external_resource_identity_bound=false",
        "external_target_provisioning_authorized=false",
        "database_connection=false",
        "runner_execution=false",
        "restore_execution=false",
        "migration_execution=false",
        "deployment=false",
        "resource_operations=false",
        "decision=PASS_REPOSITORY_CONTRACT_REBIND_RECORD_NO_EXTERNAL_AUTHORITY",
        "next_subject=" + NEXT_SUBJECT,
        "ALL PASS: PMAI-P0-04 Fresh Disposable Target Contract Rebind V4 repository package",
    ):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
