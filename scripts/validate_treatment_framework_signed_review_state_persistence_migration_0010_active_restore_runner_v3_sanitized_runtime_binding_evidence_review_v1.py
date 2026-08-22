#!/usr/bin/env python3
"""Offline fail-closed reviewer for PMAI-P0-04 hash-only runtime evidence.

Dry-run and self-test write nothing. Operational review, if separately
authorized later, reads only an exact hash/boolean collector record and writes
one downstream sanitized evidence JSON outside the canonical repository. It
does not access runtime observations, providers, credentials, targets,
databases, backups, runners, restore tooling, migrations, deployment, Git, or
the network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Mapping, NoReturn, Sequence


sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_TEMPLATE_PATH = REPOSITORY_ROOT / (
    "docs/clinical_data/"
    "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_"
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_"
    "COLLECTION_AND_REVIEW_PREPARATION_V1_SANITIZED_COLLECTOR_OUTPUT_TEMPLATE_V1.json"
)
CANONICAL_REPOSITORY = Path("/Users/zhaohaisheng/Documents/Pet-med-ai")
MAX_JSON_BYTES = 64 * 1024

ACTIVATION_AUTHORIZATION_RECORD_ID = (
    "PMAI-P0-04-ARR-V3-CA-EXEC-AUTH-V1-20260816"
)
ACTIVATION_AUTHORIZATION_RECORD_SHA256 = (
    "42aa5a864d73b1a3d8d1b8489be0d0cc36c761b8e9c030e0752a07c5f0264b4c"
)
COLLECTION_EXECUTION_AUTHORIZATION_RECORD_SHA256 = (
    "0fe8c6c39aeeb5304e97927c9e1872c2a7a1734ad3c590091d15ecee9d890f12"
)
EXPECTED_COLLECTOR_CONTRACT_SHA256 = (
    "fbfdf6e076c5acfcff4565ae1293d18e6cee2ab55f1eef0573c67f7d95f5e7c6"
)
TARGET_CONTRACT_IDENTITY_SHA256 = (
    "e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744"
)

HASH_KEYS = {
    "activation_authorization_record_sha256",
    "collection_execution_authorization_record_sha256",
    "collector_contract_sha256",
    "expected_schema_manifest_sha256",
    "expected_target_identity_sha256",
    "forbidden_production_identity_sha256",
    "forbidden_staging_identity_sha256",
    "source_observation_bundle_sha256",
    "target_available_recheck_evidence_sha256",
    "target_lifecycle_evidence_sha256",
}
BOOLEAN_KEYS = {
    "collection_execution_authorized",
    "evidence_complete",
    "fixture_only",
    "raw_connection_values_disclosed",
    "target_lifecycle_within_72h",
    "target_status_available",
}
COLLECTOR_KEYS = HASH_KEYS | BOOLEAN_KEYS
RUNTIME_HASH_KEYS = {
    "expected_schema_manifest_sha256",
    "expected_target_identity_sha256",
    "forbidden_production_identity_sha256",
    "forbidden_staging_identity_sha256",
}
DERIVED_EVIDENCE_HASH_KEYS = {
    "source_observation_bundle_sha256",
    "target_available_recheck_evidence_sha256",
    "target_lifecycle_evidence_sha256",
}
KNOWN_NON_RUNTIME_HASHES = {
    "91b9ba1da8cc290fd94a17b4c57c673be0a805ae25f1ddb0ace69922ff9e2081",
    "98d6cd0a1f01c551d6f43bae484842ff75163f5a3ea1fb0c600ef85167c0c31b",
    "c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f",
    TARGET_CONTRACT_IDENTITY_SHA256,
}
DOWNSTREAM_KEYS = {
    "activation_authorization_record_id",
    "expected_schema_manifest_sha256",
    "expected_target_identity_sha256",
    "forbidden_production_identity_sha256",
    "forbidden_staging_identity_sha256",
    "raw_connection_values_disclosed",
    "reviewed_sanitized_evidence_bundle_sha256",
    "schema",
    "target_available_recheck_evidence_sha256",
    "target_lifecycle_evidence_sha256",
    "target_lifecycle_within_72h",
    "target_status_available",
}


class Hold(RuntimeError):
    """Fixed stop code whose digest can be emitted without leaking input."""


class HashBooleanArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise Hold("ARGUMENT_CONTRACT_MISMATCH")


def need(condition: bool, code: str) -> None:
    if not condition:
        raise Hold(code)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def read_json_object(path: Path, label: str) -> dict[str, object]:
    need(path.is_file() and not path.is_symlink(), label + "_MISSING_OR_UNSAFE")
    need(path.stat().st_size <= MAX_JSON_BYTES, label + "_TOO_LARGE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Hold(label + "_INVALID_JSON") from exc
    need(isinstance(value, dict), label + "_NOT_OBJECT")
    return value


def validate_template(value: Mapping[str, object]) -> None:
    need(set(value) == COLLECTOR_KEYS, "TEMPLATE_KEY_SET_MISMATCH")
    for key in HASH_KEYS:
        need(value[key] == "UNBOUND", "TEMPLATE_HASH_NOT_UNBOUND")
    for key in BOOLEAN_KEYS:
        need(value[key] is False, "TEMPLATE_BOOLEAN_NOT_FALSE")


def validate_collector_record(value: Mapping[str, object], release: bool) -> None:
    need(set(value) == COLLECTOR_KEYS, "COLLECTOR_KEY_SET_MISMATCH")
    for key in HASH_KEYS:
        need(is_sha256(value[key]), "COLLECTOR_SHA256_REQUIRED")
        need(value[key] not in {"0" * 64, "f" * 64}, "SENTINEL_SHA256_FORBIDDEN")
    for key in BOOLEAN_KEYS:
        need(type(value[key]) is bool, "COLLECTOR_BOOLEAN_REQUIRED")
    need(
        value["activation_authorization_record_sha256"]
        == ACTIVATION_AUTHORIZATION_RECORD_SHA256,
        "ACTIVATION_AUTHORIZATION_BINDING_MISMATCH",
    )
    need(
        value["collection_execution_authorization_record_sha256"]
        == COLLECTION_EXECUTION_AUTHORIZATION_RECORD_SHA256,
        "COLLECTION_AUTHORIZATION_BINDING_MISMATCH",
    )
    need(
        value["collector_contract_sha256"] == EXPECTED_COLLECTOR_CONTRACT_SHA256,
        "COLLECTOR_CONTRACT_MISMATCH",
    )
    runtime_values = [str(value[key]) for key in sorted(RUNTIME_HASH_KEYS)]
    need(len(runtime_values) == len(set(runtime_values)), "RUNTIME_HASHES_NOT_DISTINCT")
    all_evidence_values = [
        str(value[key])
        for key in sorted(RUNTIME_HASH_KEYS | DERIVED_EVIDENCE_HASH_KEYS)
    ]
    need(
        len(all_evidence_values) == len(set(all_evidence_values)),
        "EVIDENCE_HASHES_NOT_DISTINCT",
    )
    need(
        all(item not in KNOWN_NON_RUNTIME_HASHES for item in all_evidence_values),
        "KNOWN_ARTIFACT_HASH_SUBSTITUTION_FORBIDDEN",
    )
    need(
        value["expected_target_identity_sha256"] != TARGET_CONTRACT_IDENTITY_SHA256,
        "TARGET_CONTRACT_IS_NOT_RUNTIME_IDENTITY",
    )
    need(
        value["raw_connection_values_disclosed"] is False,
        "RAW_CONNECTION_DISCLOSURE_FORBIDDEN",
    )
    if release:
        need(
            value["collection_execution_authorized"] is True,
            "SEPARATE_COLLECTION_EXECUTION_AUTHORIZATION_REQUIRED",
        )
        need(value["evidence_complete"] is True, "EVIDENCE_INCOMPLETE")
        need(value["fixture_only"] is False, "FIXTURE_EVIDENCE_FORBIDDEN")
        need(
            value["target_status_available"] is True,
            "TARGET_AVAILABLE_RECHECK_REQUIRED",
        )
        need(
            value["target_lifecycle_within_72h"] is True,
            "TARGET_LIFECYCLE_REVIEW_REQUIRED",
        )


def build_downstream_evidence(value: Mapping[str, object]) -> dict[str, object]:
    validate_collector_record(value, release=True)
    reviewed_bundle_sha256 = sha256_bytes(canonical_json_bytes(value))
    evidence_hashes = {
        str(value[key])
        for key in RUNTIME_HASH_KEYS | DERIVED_EVIDENCE_HASH_KEYS
    }
    need(
        reviewed_bundle_sha256 not in evidence_hashes,
        "REVIEWED_BUNDLE_HASH_COLLISION",
    )
    result: dict[str, object] = {
        "activation_authorization_record_id": ACTIVATION_AUTHORIZATION_RECORD_ID,
        "expected_schema_manifest_sha256": value[
            "expected_schema_manifest_sha256"
        ],
        "expected_target_identity_sha256": value[
            "expected_target_identity_sha256"
        ],
        "forbidden_production_identity_sha256": value[
            "forbidden_production_identity_sha256"
        ],
        "forbidden_staging_identity_sha256": value[
            "forbidden_staging_identity_sha256"
        ],
        "raw_connection_values_disclosed": False,
        "reviewed_sanitized_evidence_bundle_sha256": reviewed_bundle_sha256,
        "schema": "PMAI_P0_04_ARR_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_V1",
        "target_available_recheck_evidence_sha256": value[
            "target_available_recheck_evidence_sha256"
        ],
        "target_lifecycle_evidence_sha256": value[
            "target_lifecycle_evidence_sha256"
        ],
        "target_lifecycle_within_72h": True,
        "target_status_available": True,
    }
    need(set(result) == DOWNSTREAM_KEYS, "DOWNSTREAM_KEY_SET_MISMATCH")
    return result


def write_new_json(path: Path, value: Mapping[str, object]) -> None:
    expanded = path.expanduser()
    need(expanded.is_absolute(), "OUTPUT_PATH_MUST_BE_ABSOLUTE")
    parent = expanded.parent.resolve(strict=True)
    need(parent.is_dir() and not parent.is_symlink(), "OUTPUT_PARENT_UNSAFE")
    candidate = parent / expanded.name
    need(not candidate.exists(), "OUTPUT_PATH_ALREADY_EXISTS")
    for repository in (REPOSITORY_ROOT, CANONICAL_REPOSITORY):
        try:
            candidate.relative_to(repository)
        except ValueError:
            continue
        raise Hold("OUTPUT_INSIDE_REPOSITORY_FORBIDDEN")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(candidate, flags, 0o600)
    try:
        payload = (
            json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2).encode(
                "ascii"
            )
            + b"\n"
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def boundary_status() -> dict[str, bool]:
    return {
        "archive_accessed": False,
        "backup_accessed": False,
        "credential_accessed": False,
        "database_connected": False,
        "deployment_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_stage_performed": False,
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
        "target_accessed": False,
    }


def emit_hash_boolean(value: Mapping[str, object]) -> None:
    for item in value.values():
        need(type(item) is bool or is_sha256(item), "CONSOLE_VALUE_TYPE_FORBIDDEN")
    print(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    )


def synthetic_record() -> dict[str, object]:
    def digest(label: str) -> str:
        return sha256_bytes(("reviewer-self-test:" + label).encode("ascii"))

    return {
        "activation_authorization_record_sha256": (
            ACTIVATION_AUTHORIZATION_RECORD_SHA256
        ),
        "collection_execution_authorization_record_sha256": (
            COLLECTION_EXECUTION_AUTHORIZATION_RECORD_SHA256
        ),
        "collection_execution_authorized": False,
        "collector_contract_sha256": EXPECTED_COLLECTOR_CONTRACT_SHA256,
        "evidence_complete": True,
        "expected_schema_manifest_sha256": digest("schema"),
        "expected_target_identity_sha256": digest("target"),
        "fixture_only": True,
        "forbidden_production_identity_sha256": digest("production"),
        "forbidden_staging_identity_sha256": digest("staging"),
        "raw_connection_values_disclosed": False,
        "source_observation_bundle_sha256": digest("observation"),
        "target_available_recheck_evidence_sha256": digest("available"),
        "target_lifecycle_evidence_sha256": digest("lifecycle"),
        "target_lifecycle_within_72h": True,
        "target_status_available": True,
    }


def dry_run() -> int:
    template = read_json_object(COLLECTOR_TEMPLATE_PATH, "COLLECTOR_TEMPLATE")
    validate_template(template)
    result: dict[str, object] = {
        "collector_contract_sha256": EXPECTED_COLLECTOR_CONTRACT_SHA256,
        "collector_template_sha256": sha256_path(COLLECTOR_TEMPLATE_PATH),
        "dry_run": True,
        "hold": True,
        "runtime_evidence_reviewed": False,
        "sanitized_evidence_written": False,
    }
    result.update(boundary_status())
    emit_hash_boolean(result)
    return 0


def self_test() -> int:
    ineligible = synthetic_record()
    validate_collector_record(ineligible, release=False)
    rejected = False
    try:
        validate_collector_record(ineligible, release=True)
    except Hold:
        rejected = True
    need(rejected, "FIXTURE_RELEASE_REJECTION_FAILED")

    eligible = dict(ineligible)
    eligible["collection_execution_authorized"] = True
    eligible["fixture_only"] = False
    downstream = build_downstream_evidence(eligible)
    result: dict[str, object] = {
        "downstream_contract_sha256": sha256_bytes(
            canonical_json_bytes(downstream)
        ),
        "fixture_release_rejected": True,
        "hold": True,
        "operational_output_written": False,
        "release_eligible": False,
        "self_test": True,
        "synthetic_positive_path_validated": True,
        "synthetic_values_persisted": False,
    }
    result.update(boundary_status())
    emit_hash_boolean(result)
    return 0


def review(input_path: Path, output_path: Path) -> int:
    record = read_json_object(input_path.expanduser().resolve(strict=True), "COLLECTOR_RECORD")
    downstream = build_downstream_evidence(record)
    write_new_json(output_path, downstream)
    result: dict[str, object] = {
        "collector_record_sha256": sha256_bytes(canonical_json_bytes(record)),
        "hold": True,
        "runtime_evidence_reviewed": True,
        "sanitized_evidence_file_sha256": sha256_path(output_path.expanduser().resolve(strict=True)),
        "sanitized_evidence_written": True,
        "separate_binding_confirmation_still_required": True,
    }
    result.update(boundary_status())
    emit_hash_boolean(result)
    return 0


def parser() -> HashBooleanArgumentParser:
    value = HashBooleanArgumentParser(add_help=False, description=__doc__)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--review", action="store_true")
    value.add_argument("--input", type=Path)
    value.add_argument("--output", type=Path)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.dry_run:
        need(args.input is None and args.output is None, "DRY_RUN_EXTRA_ARGUMENT_FORBIDDEN")
        return dry_run()
    if args.self_test:
        need(args.input is None and args.output is None, "SELF_TEST_EXTRA_ARGUMENT_FORBIDDEN")
        return self_test()
    need(args.input is not None and args.output is not None, "REVIEW_PATHS_REQUIRED")
    return review(args.input, args.output)


def entrypoint() -> int:
    try:
        return main()
    except Exception as exc:
        result: dict[str, object] = {
            "error_code_sha256": sha256_bytes(str(exc).encode("utf-8")),
            "hold": True,
            "runtime_evidence_reviewed": False,
            "sanitized_evidence_written": False,
        }
        result.update(boundary_status())
        try:
            emit_hash_boolean(result)
        except Exception:
            print('{"hold":true}')
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
