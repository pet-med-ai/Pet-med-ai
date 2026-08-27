#!/usr/bin/env python3
"""Offline synthetic-only reviewer for the PMAI-P0-04 V4 rebind contract.

The CLI exposes only ``--dry-run`` and ``--self-test``. It cannot accept an
input path, write an output, collect runtime evidence, access a provider,
credential, target, database, backup, runner, restore tool, migration,
deployment, Git remote, or network service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Mapping, NoReturn, Sequence


sys.dont_write_bytecode = True

MAX_JSON_BYTES = 64 * 1024
UNBOUND = "UNBOUND"
TARGET_CONTRACT_IDENTITY_SHA256 = (
    "e1cba6bc207fa4654d3155ef4abd8d818d8fd4323ce990446bc680fd15522529"
)
TARGET_SERVICE_IDENTIFIER_SHA256 = (
    "3f0ed4e1cb1bbef10babb4d3ba7fa9ec03e048d7d30595389f30d0871bcdb4fe"
)
IMPLEMENTATION_CANDIDATE_SHA256 = (
    "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081"
)
EXPECTED_COLLECTOR_CONTRACT_SHA256 = (
    "1d4ce179cbd4ead48b6af7e3165bf7dd4e94eeef306c64cdcd40fa7788150a54"
)
PRIOR_V3_TARGET_CONTRACT_IDENTITY_SHA256 = (
    "e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744"
)

HASH_KEYS = {
    "collection_execution_authorization_record_sha256",
    "collector_contract_sha256",
    "expected_active_source_sha256",
    "expected_schema_manifest_sha256",
    "expected_target_identity_sha256",
    "forbidden_production_identity_sha256",
    "forbidden_staging_identity_sha256",
    "source_observation_bundle_sha256",
    "successor_activation_authorization_record_sha256",
    "target_application_attachment_recheck_evidence_sha256",
    "target_available_recheck_evidence_sha256",
    "target_lifecycle_evidence_sha256",
    "target_network_lockdown_recheck_evidence_sha256",
    "target_open_connection_recheck_evidence_sha256",
}
BOOLEAN_KEYS = {
    "collection_execution_authorized",
    "evidence_complete",
    "final_service_inbound_ip_rule_set_empty",
    "fixture_only",
    "public_external_access_blocked",
    "raw_connection_values_disclosed",
    "target_application_attachment_count_zero",
    "target_lifecycle_within_72h",
    "target_open_connection_count_zero",
    "target_status_available",
}
COLLECTOR_KEYS = HASH_KEYS | BOOLEAN_KEYS
RUNTIME_BINDING_KEYS = {
    "expected_active_source_sha256",
    "expected_schema_manifest_sha256",
    "expected_target_identity_sha256",
    "forbidden_production_identity_sha256",
    "forbidden_staging_identity_sha256",
    "successor_activation_authorization_record_sha256",
}
CANDIDATE_FORBIDDEN_BINDING_KEYS = HASH_KEYS - {
    "expected_active_source_sha256"
}
PROVENANCE_HASHES = {
    TARGET_CONTRACT_IDENTITY_SHA256,
    TARGET_SERVICE_IDENTIFIER_SHA256,
    PRIOR_V3_TARGET_CONTRACT_IDENTITY_SHA256,
}


class Hold(RuntimeError):
    """Fixed stop code whose digest is safe for console output."""


class OfflineArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise Hold("ARGUMENT_CONTRACT_MISMATCH")


def need(condition: bool, code: str) -> None:
    if not condition:
        raise Hold(code)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise Hold("CANONICAL_JSON_INVALID") from exc
    need(len(encoded) <= MAX_JSON_BYTES, "CANONICAL_JSON_TOO_LARGE")
    return encoded


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def unbound_template() -> dict[str, object]:
    value: dict[str, object] = {key: UNBOUND for key in HASH_KEYS}
    value.update({key: False for key in BOOLEAN_KEYS})
    return value


def validate_template(value: Mapping[str, object]) -> None:
    need(set(value) == COLLECTOR_KEYS, "TEMPLATE_KEY_SET_MISMATCH")
    need(all(value[key] == UNBOUND for key in HASH_KEYS), "TEMPLATE_HASH_NOT_UNBOUND")
    need(all(value[key] is False for key in BOOLEAN_KEYS), "TEMPLATE_BOOLEAN_NOT_FALSE")
    need(TARGET_CONTRACT_IDENTITY_SHA256 not in value.values(), "CONTRACT_HASH_IN_TEMPLATE")
    need(TARGET_SERVICE_IDENTIFIER_SHA256 not in value.values(), "SERVICE_HASH_IN_TEMPLATE")


def validate_collector_record(value: Mapping[str, object], release: bool) -> None:
    need(set(value) == COLLECTOR_KEYS, "COLLECTOR_KEY_SET_MISMATCH")
    for key in HASH_KEYS:
        need(is_sha256(value[key]), "COLLECTOR_SHA256_REQUIRED")
        need(value[key] not in {"0" * 64, "f" * 64}, "SENTINEL_SHA256_FORBIDDEN")
    for key in BOOLEAN_KEYS:
        need(type(value[key]) is bool, "COLLECTOR_BOOLEAN_REQUIRED")
    hash_values = [str(value[key]) for key in sorted(HASH_KEYS)]
    need(len(hash_values) == len(set(hash_values)), "COLLECTOR_HASHES_NOT_DISTINCT")
    need(all(item not in PROVENANCE_HASHES for item in hash_values), "PROVENANCE_HASH_SUBSTITUTION")
    need(
        all(value[key] != IMPLEMENTATION_CANDIDATE_SHA256 for key in CANDIDATE_FORBIDDEN_BINDING_KEYS),
        "IMPLEMENTATION_CANDIDATE_BINDING_DOMAIN_MISMATCH",
    )
    need(
        value["expected_target_identity_sha256"]
        not in {TARGET_CONTRACT_IDENTITY_SHA256, TARGET_SERVICE_IDENTIFIER_SHA256},
        "TARGET_RUNTIME_IDENTITY_SUBSTITUTION",
    )
    need(value["raw_connection_values_disclosed"] is False, "RAW_CONNECTION_DISCLOSURE")
    need(value["collector_contract_sha256"] == EXPECTED_COLLECTOR_CONTRACT_SHA256, "COLLECTOR_CONTRACT_MISMATCH")
    need(value["fixture_only"] is True, "FIXTURE_ONLY_REQUIRED")
    need(value["collection_execution_authorized"] is False, "COLLECTION_AUTHORIZATION_FORBIDDEN")
    need(value["evidence_complete"] is False, "LIVE_EVIDENCE_COMPLETENESS_FORBIDDEN")
    need(value["target_status_available"] is False, "LIVE_TARGET_STATUS_FORBIDDEN")
    need(value["target_lifecycle_within_72h"] is False, "LIVE_TARGET_LIFECYCLE_FORBIDDEN")
    need(value["target_application_attachment_count_zero"] is False, "LIVE_ATTACHMENT_RECHECK_FORBIDDEN")
    need(value["target_open_connection_count_zero"] is False, "LIVE_CONNECTION_RECHECK_FORBIDDEN")
    need(value["final_service_inbound_ip_rule_set_empty"] is False, "LIVE_NETWORK_RULE_RECHECK_FORBIDDEN")
    need(value["public_external_access_blocked"] is False, "LIVE_PUBLIC_ACCESS_RECHECK_FORBIDDEN")
    if release:
        need(False, "OPERATIONAL_REVIEW_NOT_AUTHORIZED_BY_PREPARATION")


def synthetic_hash(label: str) -> str:
    return sha256_bytes(("v4-rebind-reviewer-synthetic:" + label).encode("ascii"))


def synthetic_record() -> dict[str, object]:
    return {
        "collection_execution_authorization_record_sha256": synthetic_hash("collection-authorization"),
        "collection_execution_authorized": False,
        "collector_contract_sha256": EXPECTED_COLLECTOR_CONTRACT_SHA256,
        "evidence_complete": False,
        "expected_active_source_sha256": synthetic_hash("active-source"),
        "expected_schema_manifest_sha256": synthetic_hash("schema"),
        "expected_target_identity_sha256": synthetic_hash("target"),
        "final_service_inbound_ip_rule_set_empty": False,
        "fixture_only": True,
        "forbidden_production_identity_sha256": synthetic_hash("production"),
        "forbidden_staging_identity_sha256": synthetic_hash("staging"),
        "public_external_access_blocked": False,
        "raw_connection_values_disclosed": False,
        "source_observation_bundle_sha256": synthetic_hash("observation"),
        "successor_activation_authorization_record_sha256": synthetic_hash("activation-authorization"),
        "target_application_attachment_count_zero": False,
        "target_application_attachment_recheck_evidence_sha256": synthetic_hash("attachments"),
        "target_available_recheck_evidence_sha256": synthetic_hash("available"),
        "target_lifecycle_evidence_sha256": synthetic_hash("lifecycle"),
        "target_lifecycle_within_72h": False,
        "target_network_lockdown_recheck_evidence_sha256": synthetic_hash("network-lockdown"),
        "target_open_connection_count_zero": False,
        "target_open_connection_recheck_evidence_sha256": synthetic_hash("open-connections"),
        "target_status_available": False,
    }


def boundary_status() -> dict[str, bool]:
    return {
        "archive_accessed": False,
        "backup_accessed": False,
        "credential_accessed": False,
        "database_connected": False,
        "deployment_performed": False,
        "external_input_read": False,
        "external_output_written": False,
        "git_write_performed": False,
        "migration_created": False,
        "migration_executed": False,
        "network_accessed": False,
        "provider_control_plane_accessed": False,
        "resource_deleted": False,
        "restore_executed": False,
        "runner_activated": False,
        "runner_created": False,
        "runner_executed": False,
        "runner_imported": False,
        "runtime_evidence_reviewed": False,
        "target_accessed": False,
    }


def emit_hash_boolean(value: Mapping[str, object]) -> None:
    need(all(type(item) is bool or is_sha256(item) for item in value.values()), "CONSOLE_VALUE_TYPE_FORBIDDEN")
    print(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def dry_run() -> int:
    template = unbound_template()
    validate_template(template)
    result: dict[str, object] = {
        "hold": True,
        "operational_review_cli_present": False,
        "runtime_binding_contract_complete": False,
        "synthetic_fixture_tests_only": True,
        "target_contract_provenance_sha256": TARGET_CONTRACT_IDENTITY_SHA256,
        "target_service_provenance_sha256": TARGET_SERVICE_IDENTIFIER_SHA256,
        "template_contract_sha256": sha256_bytes(canonical_json_bytes(template)),
    }
    result.update(boundary_status())
    emit_hash_boolean(result)
    return 0


def self_test() -> int:
    validate_template(unbound_template())
    record = synthetic_record()
    validate_collector_record(record, release=False)
    release_rejected = False
    try:
        validate_collector_record(record, release=True)
    except Hold:
        release_rejected = True
    need(release_rejected, "OPERATIONAL_RELEASE_REJECTION_FAILED")

    contract_substitution = dict(record)
    contract_substitution["expected_target_identity_sha256"] = TARGET_CONTRACT_IDENTITY_SHA256
    substitution_rejected = False
    try:
        validate_collector_record(contract_substitution, release=False)
    except Hold:
        substitution_rejected = True
    need(substitution_rejected, "CONTRACT_SUBSTITUTION_REJECTION_FAILED")

    candidate_target_substitution = dict(record)
    candidate_target_substitution["expected_target_identity_sha256"] = IMPLEMENTATION_CANDIDATE_SHA256
    candidate_target_rejected = False
    try:
        validate_collector_record(candidate_target_substitution, release=False)
    except Hold:
        candidate_target_rejected = True
    need(candidate_target_rejected, "CANDIDATE_TARGET_SUBSTITUTION_REJECTION_FAILED")

    for key in (
        "fixture_only",
        "collection_execution_authorized",
        "evidence_complete",
        "final_service_inbound_ip_rule_set_empty",
        "public_external_access_blocked",
        "target_application_attachment_count_zero",
        "target_status_available",
        "target_lifecycle_within_72h",
        "target_open_connection_count_zero",
    ):
        mutation = dict(record)
        mutation[key] = not bool(mutation[key])
        rejected = False
        try:
            validate_collector_record(mutation, release=False)
        except Hold:
            rejected = True
        need(rejected, "LIVE_LOOKING_FIXTURE_REJECTION_FAILED")

    result: dict[str, object] = {
        "contract_substitution_rejected": True,
        "candidate_target_substitution_rejected": True,
        "fixture_record_sha256": sha256_bytes(canonical_json_bytes(record)),
        "hold": True,
        "operational_release_rejected": True,
        "release_eligible": False,
        "self_test": True,
        "synthetic_values_persisted": False,
    }
    result.update(boundary_status())
    emit_hash_boolean(result)
    return 0


def parser() -> OfflineArgumentParser:
    value = OfflineArgumentParser(add_help=False, description=__doc__)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--self-test", action="store_true")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return dry_run() if args.dry_run else self_test()


def entrypoint() -> int:
    try:
        return main()
    except Exception:
        result: dict[str, object] = {
            "error_code_sha256": sha256_bytes(b"OFFLINE_REVIEWER_HOLD"),
            "hold": True,
            "runtime_evidence_reviewed": False,
        }
        result.update(boundary_status())
        try:
            emit_hash_boolean(result)
        except Exception:
            print('{"hold":true}')
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
