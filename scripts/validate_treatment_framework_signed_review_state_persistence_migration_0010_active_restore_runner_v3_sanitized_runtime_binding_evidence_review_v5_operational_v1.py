#!/usr/bin/env python3
"""Fail-closed offline reviewer for the PMAI-P0-04 V5 SRBE result.

Live review accepts one canonical sanitized result and one independently
authenticated canonical sidecar.  The 32-byte HMAC key is accepted only from
an inherited anonymous pipe descriptor.  The adapter, network, database,
ledger, signer, and provider implementations are intentionally absent.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Callable, Mapping, NoReturn, Sequence


sys.dont_write_bytecode = True

MAX_INPUT_BYTES = 256 * 1024
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 4096
RESULT_SCHEMA = "PMAI_P0_04_SRBE_V5_SANITIZED_COLLECTION_RESULT_V1"
RUNTIME_SCHEMA = "PMAI_P0_04_SRBE_V5_SANITIZED_RUNTIME_OBSERVATION_V1"
RESULT_SCHEMA_URN = "urn:pmai:p0-04:srbe:v5:sanitized-result-schema:v1"
RUNTIME_SCHEMA_URN = "urn:pmai:p0-04:srbe:v5:runtime-observation-schema:v1"
ATTESTATION_SCHEMA = "PMAI_P0_04_SRBE_V5_INDEPENDENT_RUNTIME_ATTESTATION_V1"
ATTEMPT_BINDING_SCHEMA = "PMAI_P0_04_SRBE_V5_ATTEMPT_BINDING_V2"
ATTESTATION_KEY_FD_ENV = "PMAI_P0_04_V5_INDEPENDENT_ATTESTATION_HMAC_KEY_FD"
EXPECTED_EMPTY_MANIFEST_SHA256 = (
    "f87acbf36011fa8656e82f1cb6067614a59d019e32ea36781fe1dc2ceb4fc010"
)
UNBOUND = "UNBOUND"

REVIEWER_PATH = Path(os.path.abspath(__file__))
REPOSITORY_ROOT = REVIEWER_PATH.resolve().parents[1]
PACKAGE_STEM = (
    "TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_"
    "ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_"
    "AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1"
)
DOCS = REPOSITORY_ROOT / "docs" / "clinical_data"
PROCEDURE_PATH = DOCS / f"{PACKAGE_STEM}.md"
RUNTIME_SCHEMA_PATH = DOCS / f"{PACKAGE_STEM}_RUNTIME_OBSERVATION_SCHEMA_V1.json"
RESULT_SCHEMA_PATH = DOCS / f"{PACKAGE_STEM}_SANITIZED_RESULT_SCHEMA_V1.json"
PACKAGE_MANIFEST_PATH = DOCS / f"{PACKAGE_STEM}_PACKAGE_MANIFEST_V1.json"
ADAPTER_PATH = REPOSITORY_ROOT / "scripts" / (
    "collect_treatment_framework_signed_review_state_persistence_migration_"
    "0010_active_restore_runner_v3_sanitized_runtime_binding_evidence_collection_"
    "and_review_v5_operational_adapter_v1.py"
)

SQL_SET_SESSION_READ_ONLY = "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"
SQL_BEGIN_READ_ONLY = "BEGIN READ ONLY"
SQL_SET_SEARCH_PATH = "SET LOCAL search_path TO pg_catalog"
SQL_SET_STATEMENT_TIMEOUT = "SET LOCAL statement_timeout TO '5000ms'"
SQL_SET_LOCK_TIMEOUT = "SET LOCAL lock_timeout TO '1000ms'"
SQL_SET_IDLE_TIMEOUT = (
    "SET LOCAL idle_in_transaction_session_timeout TO '5000ms'"
)
SQL_VERIFY_READ_ONLY = (
    "SELECT pg_catalog.current_setting('transaction_read_only', true)::text "
    "AS transaction_read_only"
)
SQL_DATABASE_IDENTITY = (
    "SELECT pg_catalog.current_database()::text AS database_name, "
    "pg_catalog.inet_server_addr()::text AS server_address, "
    "pg_catalog.inet_server_port()::integer AS server_port"
)
SQL_STRUCTURAL_MANIFEST = (
    "SELECT n.nspname::text AS namespace_name, "
    "c.relname::text AS relation_name, c.relkind::text AS relation_kind, "
    "a.attname::text AS column_name, a.attnum::integer AS ordinal_position, "
    "a.atttypid::integer AS type_oid, a.attnotnull::boolean AS not_null "
    "FROM pg_catalog.pg_class AS c "
    "JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace "
    "LEFT JOIN pg_catalog.pg_attribute AS a "
    "ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped "
    "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
    "AND n.nspname NOT LIKE 'pg_toast%' "
    "AND c.relkind IN ('r','p','v','m','f','S') "
    "ORDER BY n.nspname, c.relname, c.relkind, a.attnum"
)
FIXED_SQL = (
    ("SET_SESSION_READ_ONLY", SQL_SET_SESSION_READ_ONLY),
    ("BEGIN_READ_ONLY", SQL_BEGIN_READ_ONLY),
    ("SET_SEARCH_PATH", SQL_SET_SEARCH_PATH),
    ("SET_STATEMENT_TIMEOUT", SQL_SET_STATEMENT_TIMEOUT),
    ("SET_LOCK_TIMEOUT", SQL_SET_LOCK_TIMEOUT),
    ("SET_IDLE_TIMEOUT", SQL_SET_IDLE_TIMEOUT),
    ("VERIFY_READ_ONLY", SQL_VERIFY_READ_ONLY),
    ("DATABASE_IDENTITY", SQL_DATABASE_IDENTITY),
    ("STRUCTURAL_MANIFEST", SQL_STRUCTURAL_MANIFEST),
)

ERROR_CODES = frozenset(
    {
        "ALLOWLIST_ADD_FAILED",
        "ALLOWLIST_RECHECK_FAILED",
        "ALLOWLIST_REMOVE_FAILED",
        "ANTI_ROLLBACK_WITNESS_UNAVAILABLE",
        "ARGUMENT_CONTRACT_MISMATCH",
        "ATTEMPT_ALREADY_CONSUMED",
        "ATTEMPT_LEDGER_UNAVAILABLE",
        "ATTEMPT_LEDGER_UNCERTAIN",
        "AUTHORIZATION_BINDING_MISMATCH",
        "AUTHORIZATION_INVALID",
        "CLEANUP_SUPERVISOR_UNAVAILABLE",
        "CLEANUP_SUPERVISOR_UNCERTAIN",
        "CLEANUP_UNCERTAIN",
        "CONNECTION_MATERIAL_INVALID",
        "CONTROLLED_EXECUTION_HOLD",
        "DATABASE_CLOSE_FAILED",
        "DATABASE_CONNECT_FAILED",
        "DATABASE_OBSERVATION_INVALID",
        "DATABASE_READONLY_CONTRACT_FAILED",
        "FINAL_ALLOWLIST_NOT_EMPTY",
        "FINAL_PUBLIC_ACCESS_NOT_BLOCKED",
        "FIXED_SQL_TRACE_INVALID",
        "IDENTITY_DOMAIN_MISMATCH",
        "IDENTITY_SEPARATION_FAILED",
        "INDEPENDENT_ATTESTATION_INVALID",
        "INITIAL_ALLOWLIST_NOT_EMPTY",
        "INSTRUMENTATION_INCOMPLETE",
        "INTERNAL_FAILURE",
        "LEDGER_AUTHENTICATION_FAILED",
        "LIVE_PORTS_NOT_INJECTED",
        "PORT_IMPLEMENTATION_UNBOUND",
        "PUBLIC_ACCESS_NOT_BLOCKED",
        "RUNTIME_COMPONENT_BINDING_MISMATCH",
        "RUNTIME_PROVENANCE_INVALID",
        "RUNTIME_PROVENANCE_UNAVAILABLE",
        "SCHEMA_MANIFEST_MISMATCH",
        "TARGET_ATTACHMENTS_NONZERO",
        "TARGET_CONNECTIONS_NONZERO",
        "TARGET_NOT_AVAILABLE",
        "TARGET_TOO_OLD",
        "TLS_EVIDENCE_INVALID",
        "TLS_NEGOTIATION_INVALID",
    }
)
STAGE_CODES = frozenset(
    {
        "ALLOWLIST_ADD",
        "ALLOWLIST_REMOVE",
        "ALLOWLIST_REVALIDATION",
        "ANTI_ROLLBACK_WITNESS",
        "ATTEMPT_FINALIZATION",
        "ATTEMPT_RESERVATION",
        "CLEANUP_SUPERVISOR",
        "CLEANUP_SUPERVISOR_ARM",
        "CLEANUP_SUPERVISOR_FINALIZE",
        "COMPLETE",
        "CONNECTION_MATERIAL",
        "DATABASE_CLOSE",
        "DATABASE_CONNECT",
        "DATABASE_IDENTITY",
        "DATABASE_READONLY_SETUP",
        "FINAL_NETWORK_REVALIDATION",
        "INDEPENDENT_ATTESTATION",
        "OUTPUT_VALIDATION",
        "PRECHECK",
        "PROVIDER_INITIAL_REVALIDATION",
        "RUNTIME_PROVENANCE",
        "SCHEMA_MANIFEST",
    }
)

SUCCESS_HASH_KEYS = frozenset(
    {
        "adapter_contract_sha256",
        "authorization_record_sha256",
        "attempt_binding_sha256",
        "attempt_ledger_receipt_sha256",
        "provider_observation_sha256",
        "target_provider_identity_sha256",
        "forbidden_production_provider_identity_sha256",
        "forbidden_staging_provider_identity_sha256",
        "database_observation_sha256",
        "target_database_observed_identity_sha256",
        "target_connection_binding_sha256",
        "pre_restore_schema_manifest_sha256",
        "expected_pre_restore_schema_manifest_sha256",
        "operational_collection_procedure_contract_sha256",
        "reviewer_sha256",
        "instrumentation_receipt_sha256",
        "cleanup_receipt_sha256",
        "cleanup_supervisor_armed_receipt_sha256",
        "cleanup_supervisor_final_receipt_sha256",
        "database_execution_evidence_sha256",
        "fixed_sql_trace_sha256",
        "runtime_provenance_observation_receipt_sha256",
        "tls_readonly_contract_sha256",
    }
)
SUCCESS_TRUE_KEYS = frozenset(
    {
        "target_status_available",
        "target_lifecycle_within_72h",
        "target_application_attachment_count_zero",
        "target_open_connection_count_zero",
        "initial_inbound_ip_rule_set_empty",
        "final_inbound_ip_rule_set_empty",
        "public_external_access_blocked",
        "collection_attempt_consumed",
        "pre_restore_readonly_collection_complete",
    }
)
SUCCESS_FALSE_KEYS = frozenset(
    {
        "post_restore_schema_evidence_collected",
        "runtime_binding_contract_complete",
        "srbe_collection_evidence_complete",
        "evidence_complete",
        "raw_connection_values_disclosed",
        "fixture_only",
    }
)
SUCCESS_KEYS = frozenset(
    {"schema", "outcome", "expected_post_restore_schema_manifest_sha256"}
    | SUCCESS_HASH_KEYS
    | SUCCESS_TRUE_KEYS
    | SUCCESS_FALSE_KEYS
)
RUNTIME_KEYS = frozenset(SUCCESS_KEYS - {"outcome"})
FAILURE_BOOLEAN_KEYS = frozenset(
    {
        "hold",
        "attempt_reserved",
        "collection_attempt_consumed",
        "cleanup_required",
        "cleanup_completed",
        "final_network_state_verified",
        "runtime_evidence_emitted",
        "raw_connection_values_disclosed",
    }
)
FAILURE_KEYS = frozenset(
    {
        "schema",
        "outcome",
        "error_code",
        "stage_code",
        "attempt_state",
        "state_provenance",
    }
    | FAILURE_BOOLEAN_KEYS
)
ATTEMPT_STATES = frozenset({"KNOWN_NOT_STARTED", "CONSUMED", "UNCERTAIN"})
STATE_PROVENANCE = frozenset(
    {"ADAPTER_STATE_MACHINE", "UNVERIFIED_REVIEW_INPUT"}
)

AUTH_FIELDS = frozenset(
    {
        "authorization_record_sha256",
        "adapter_sha256",
        "reviewer_sha256",
        "operational_collection_procedure_contract_sha256",
        "runtime_observation_schema_sha256",
        "sanitized_result_schema_sha256",
        "package_manifest_sha256",
        "repository_commit_oid",
        "repository_tree_oid",
        "invocation_sha256",
        "operator_run_id_sha256",
        "operator_ipv4_cidr_32_sha256",
        "target_service_identifier_sha256",
        "target_contract_identity_sha256",
        "expected_target_provider_identity_sha256",
        "expected_production_provider_identity_sha256",
        "expected_staging_provider_identity_sha256",
        "execution_harness_sha256",
        "render_port_implementation_sha256",
        "database_port_implementation_sha256",
        "attempt_ledger_implementation_sha256",
        "supervisor_implementation_sha256",
        "runtime_provenance_implementation_sha256",
        "dependency_set_sha256",
        "independent_attestation_signer_implementation_sha256",
        "ledger_hmac_key_id_sha256",
        "runtime_provenance_hmac_key_id_sha256",
        "independent_attestation_hmac_key_id_sha256",
        "live_execution_authorized",
        "collection_attempt_limit",
        "collection_attempts_consumed",
    }
)
ATTESTATION_EVIDENCE_FIELDS = frozenset(
    {
        "sanitized_result_line_sha256",
        "runtime_observation_line_sha256",
        "runtime_provenance_observation_receipt_sha256",
        "runtime_provenance_worktree_clean",
        "runtime_provenance_package_paths_regular_nonsymlink",
        "runtime_provenance_fixture_only",
        "fixed_sql_trace_sha256",
        "tls_readonly_contract_sha256",
        "observed_target_provider_identity_sha256",
        "observed_production_provider_identity_sha256",
        "observed_staging_provider_identity_sha256",
        "attempt_binding_sha256",
        "attempt_ledger_receipt_sha256",
        "attempt_ledger_final_state",
        "collection_attempt_consumed",
        "provider_initial_observation_receipt_sha256",
        "provider_allowlist_recheck_receipt_sha256",
        "provider_final_observation_receipt_sha256",
        "database_instrumentation_receipt_sha256",
        "database_execution_evidence_sha256",
        "instrumentation_receipt_sha256",
        "cleanup_receipt_sha256",
        "cleanup_supervisor_armed_receipt_sha256",
        "cleanup_supervisor_final_receipt_sha256",
        "target_database_observed_identity_sha256",
        "target_connection_binding_sha256",
        "expected_pre_restore_schema_manifest_sha256",
        "observed_pre_restore_schema_manifest_sha256",
        "target_status_available",
        "target_lifecycle_within_72h",
        "target_application_attachment_count_zero",
        "target_open_connection_count_zero",
        "initial_inbound_ip_rule_set_empty",
        "final_inbound_ip_rule_set_empty",
        "public_external_access_blocked",
        "cleanup_required",
        "cleanup_completed",
        "final_network_state_verified",
        "pre_restore_readonly_collection_complete",
    }
)
ATTESTATION_KEYS = frozenset(
    {"schema", "hmac_sha256"} | AUTH_FIELDS | ATTESTATION_EVIDENCE_FIELDS
)
ATTEMPT_BINDING_FIELDS = frozenset(
    (AUTH_FIELDS - {"live_execution_authorized"})
    | {
        "fixed_sql_trace_sha256",
        "tls_readonly_contract_sha256",
        "runtime_provenance_observation_receipt_sha256",
    }
)
SENTINEL_HASHES = frozenset(
    {
        "0" * 64,
        "f" * 64,
        hashlib.sha256(b"").hexdigest(),
        hashlib.sha256(b"{}").hexdigest(),
        hashlib.sha256(b"[]").hexdigest(),
    }
)


class ReviewHold(RuntimeError):
    def __init__(self, public_code: str = "AUTHORIZATION_BINDING_MISMATCH") -> None:
        super().__init__(public_code)
        self.public_code = (
            public_code if public_code in ERROR_CODES else "INTERNAL_FAILURE"
        )


class DuplicateKey(ValueError):
    pass


class StrictArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise ReviewHold("ARGUMENT_CONTRACT_MISMATCH")


def need(condition: bool, code: str = "AUTHORIZATION_BINDING_MISMATCH") -> None:
    if not condition:
        raise ReviewHold(code)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ReviewHold() from exc
    need(len(payload) <= MAX_INPUT_BYTES)
    return payload


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKey(key)
        result[key] = value
    return result


def reject_nonfinite(value: str) -> NoReturn:
    del value
    raise ValueError


def parse_canonical_json_line(raw: bytes) -> dict[str, object]:
    need(0 < len(raw) <= MAX_INPUT_BYTES and b"\x00" not in raw)
    try:
        value = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=unique_object,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, DuplicateKey, ValueError) as exc:
        raise ReviewHold() from exc
    need(isinstance(value, dict))
    need(raw == canonical_json_bytes(value) + b"\n")
    return value


def read_stable_regular_file(path: Path, maximum: int) -> bytes:
    lexical = Path(os.path.abspath(path))
    need(lexical.is_absolute())
    descriptor = -1
    try:
        before = os.lstat(lexical)
        need(stat.S_ISREG(before.st_mode) and not stat.S_ISLNK(before.st_mode))
        need(0 < before.st_size <= maximum)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(lexical, flags)
        opened = os.fstat(descriptor)
        need(
            stat.S_ISREG(opened.st_mode)
            and (before.st_dev, before.st_ino, before.st_size)
            == (opened.st_dev, opened.st_ino, opened.st_size)
        )
        chunks: list[bytes] = []
        total = 0
        while total <= maximum:
            block = os.read(descriptor, min(65536, maximum + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
        after = os.fstat(descriptor)
        need(
            total == opened.st_size
            and total <= maximum
            and (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        )
        return b"".join(chunks)
    except (OSError, ValueError) as exc:
        raise ReviewHold() from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def sha256_path(path: Path) -> str:
    return sha256_bytes(read_stable_regular_file(path, MAX_ARTIFACT_BYTES))


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
        and value not in SENTINEL_HASHES
    )


def is_git_oid(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{40}", value) is not None
        and value not in {"0" * 40, "f" * 40}
    )


def fixed_sql_trace_sha256() -> str:
    record = {
        "schema": "PMAI_P0_04_SRBE_V5_FIXED_SQL_TRACE_V1",
        "statements": [
            {"statement_id": statement_id, "sql_sha256": sha256_bytes(sql.encode("ascii"))}
            for statement_id, sql in FIXED_SQL
        ],
    }
    return sha256_bytes(canonical_json_bytes(record))


def tls_readonly_contract_sha256() -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "begin_read_only": True,
                "connect_timeout_seconds": 10,
                "idle_transaction_timeout_ms": 5000,
                "lock_timeout_ms": 1000,
                "schema": "PMAI_P0_04_SRBE_V5_TLS_READONLY_CONTRACT_V2",
                "search_path": "pg_catalog",
                "session_default_read_only": True,
                "sslmode": "verify-full",
                "statement_timeout_ms": 5000,
                "verify_certificate": True,
                "verify_hostname": True,
            }
        )
    )


def normalized_procedure_contract_sha256() -> str:
    try:
        text = read_stable_regular_file(PROCEDURE_PATH, MAX_ARTIFACT_BYTES).decode(
            "utf-8"
        )
    except UnicodeError as exc:
        raise ReviewHold() from exc
    begin = "operational_collection_procedure_contract_begin\n\n~~~text\n"
    end = "\n~~~\n\noperational_collection_procedure_contract_end"
    need(text.count(begin) == 1 and text.count(end) == 1)
    body = text.split(begin, 1)[1].split(end, 1)[0]
    need(bool(body) and "\r" not in body)
    return sha256_bytes((body + "\n").encode("utf-8"))


def validate_failure(record: Mapping[str, object]) -> None:
    need(set(record) == FAILURE_KEYS)
    need(record["schema"] == RESULT_SCHEMA and record["outcome"] == "HOLD")
    need(record["error_code"] in ERROR_CODES and record["stage_code"] in STAGE_CODES)
    need(record["attempt_state"] in ATTEMPT_STATES)
    need(record["state_provenance"] in STATE_PROVENANCE)
    for key in FAILURE_BOOLEAN_KEYS:
        need(type(record[key]) is bool)
    need(
        record["hold"] is True
        and record["runtime_evidence_emitted"] is False
        and record["raw_connection_values_disclosed"] is False
    )
    need(record["attempt_reserved"] is record["collection_attempt_consumed"])
    need(not record["cleanup_completed"] or record["cleanup_required"] is True)
    need(
        not record["cleanup_completed"]
        or record["final_network_state_verified"] is True
    )
    need(
        not record["final_network_state_verified"]
        or record["cleanup_required"] is True
    )
    if record["attempt_state"] == "KNOWN_NOT_STARTED":
        need(
            record["attempt_reserved"] is False
            and record["cleanup_required"] is False
            and record["cleanup_completed"] is False
            and record["final_network_state_verified"] is False
        )
    elif record["attempt_state"] == "CONSUMED":
        need(record["attempt_reserved"] is True)
        need(
            (
                record["cleanup_required"],
                record["cleanup_completed"],
                record["final_network_state_verified"],
            )
            in {
                (False, False, False),
                (True, False, False),
                (True, True, True),
            }
        )
    else:
        need(
            record["attempt_reserved"] is True
            and record["cleanup_required"] is True
            and record["cleanup_completed"] is False
            and record["final_network_state_verified"] is False
        )
    if record["state_provenance"] == "UNVERIFIED_REVIEW_INPUT":
        need(
            record["attempt_state"] == "UNCERTAIN"
            and record["attempt_reserved"] is True
            and record["collection_attempt_consumed"] is True
            and record["cleanup_required"] is True
            and record["cleanup_completed"] is False
            and record["final_network_state_verified"] is False
        )


def conservative_failure(
    error_code: str = "CONTROLLED_EXECUTION_HOLD",
    stage_code: str = "OUTPUT_VALIDATION",
) -> dict[str, object]:
    if error_code not in ERROR_CODES:
        error_code = "INTERNAL_FAILURE"
    if stage_code not in STAGE_CODES:
        stage_code = "OUTPUT_VALIDATION"
    result: dict[str, object] = {
        "attempt_reserved": True,
        "attempt_state": "UNCERTAIN",
        "cleanup_completed": False,
        "cleanup_required": True,
        "collection_attempt_consumed": True,
        "error_code": error_code,
        "final_network_state_verified": False,
        "hold": True,
        "outcome": "HOLD",
        "raw_connection_values_disclosed": False,
        "runtime_evidence_emitted": False,
        "schema": RESULT_SCHEMA,
        "stage_code": stage_code,
        "state_provenance": "UNVERIFIED_REVIEW_INPUT",
    }
    validate_failure(result)
    return result


def validate_success_core(record: Mapping[str, object], *, runtime: bool) -> None:
    expected_keys = RUNTIME_KEYS if runtime else SUCCESS_KEYS
    need(set(record) == expected_keys)
    need(record["schema"] == (RUNTIME_SCHEMA if runtime else RESULT_SCHEMA))
    if not runtime:
        need(record["outcome"] == "SUCCESS")
    for key in SUCCESS_HASH_KEYS:
        need(is_sha256(record[key]))
    for key in SUCCESS_TRUE_KEYS:
        need(type(record[key]) is bool and record[key] is True)
    for key in SUCCESS_FALSE_KEYS:
        need(type(record[key]) is bool and record[key] is False)
    need(
        record["expected_post_restore_schema_manifest_sha256"] == UNBOUND
        and record["expected_pre_restore_schema_manifest_sha256"]
        == EXPECTED_EMPTY_MANIFEST_SHA256
        and record["pre_restore_schema_manifest_sha256"]
        == EXPECTED_EMPTY_MANIFEST_SHA256
    )
    provider = [
        record["target_provider_identity_sha256"],
        record["forbidden_production_provider_identity_sha256"],
        record["forbidden_staging_provider_identity_sha256"],
    ]
    need(len(set(provider)) == 3, "IDENTITY_SEPARATION_FAILED")
    need(
        record["target_database_observed_identity_sha256"] not in set(provider),
        "IDENTITY_DOMAIN_MISMATCH",
    )
    need(
        record["instrumentation_receipt_sha256"]
        != record["cleanup_receipt_sha256"]
    )


def runtime_observation_from_result(record: Mapping[str, object]) -> dict[str, object]:
    validate_success_core(record, runtime=False)
    runtime = dict(record)
    runtime.pop("outcome")
    runtime["schema"] = RUNTIME_SCHEMA
    validate_success_core(runtime, runtime=True)
    return runtime


def load_schema(path: Path) -> dict[str, object]:
    raw = read_stable_regular_file(path, MAX_INPUT_BYTES)
    return _parse_schema(raw)


def _parse_schema(raw: bytes) -> dict[str, object]:
    try:
        value = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=unique_object,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, DuplicateKey, ValueError) as exc:
        raise ReviewHold() from exc
    need(isinstance(value, dict))
    return value


def validate_schema_contracts() -> None:
    runtime = load_schema(RUNTIME_SCHEMA_PATH)
    result = load_schema(RESULT_SCHEMA_PATH)
    need(
        runtime.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        and runtime.get("$id") == RUNTIME_SCHEMA_URN
        and runtime.get("additionalProperties") is False
        and set(runtime.get("required", [])) == RUNTIME_KEYS
        and set(runtime.get("properties", {})) == RUNTIME_KEYS
    )
    need(
        result.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        and result.get("$id") == RESULT_SCHEMA_URN
        and result.get("oneOf")
        == [
            {"$ref": "#/$defs/successEnvelope"},
            {"$ref": "#/$defs/holdEnvelope"},
        ]
    )
    definitions = result.get("$defs")
    need(isinstance(definitions, dict))
    success = definitions.get("successEnvelope")
    hold = definitions.get("holdEnvelope")
    need(isinstance(success, dict) and isinstance(hold, dict))
    need(
        success.get("additionalProperties") is False
        and set(success.get("required", [])) == SUCCESS_KEYS
        and set(success.get("properties", {})) == SUCCESS_KEYS
        and hold.get("additionalProperties") is False
        and set(hold.get("required", [])) == FAILURE_KEYS
        and set(hold.get("properties", {})) == FAILURE_KEYS
    )
    hold_properties = hold["properties"]
    need(
        set(hold_properties["attempt_state"].get("enum", [])) == ATTEMPT_STATES
        and set(hold_properties["state_provenance"].get("enum", []))
        == STATE_PROVENANCE
        and set(hold_properties["error_code"].get("enum", [])) == ERROR_CODES
        and set(hold_properties["stage_code"].get("enum", [])) == STAGE_CODES
    )
    all_of = hold.get("allOf")
    need(isinstance(all_of, list) and len(all_of) >= 2)
    invariant_bytes = canonical_json_bytes(all_of)
    for token in (
        b'"if"',
        b'"then"',
        b'"ADAPTER_STATE_MACHINE"',
        b'"UNVERIFIED_REVIEW_INPUT"',
        b'"attempt_reserved"',
        b'"collection_attempt_consumed"',
        b'"cleanup_required"',
        b'"cleanup_completed"',
        b'"final_network_state_verified"',
    ):
        need(token in invariant_bytes)


def validate_artifact_bindings(
    result: Mapping[str, object], attestation: Mapping[str, object]
) -> None:
    for path in (
        ADAPTER_PATH,
        REVIEWER_PATH,
        PROCEDURE_PATH,
        RUNTIME_SCHEMA_PATH,
        RESULT_SCHEMA_PATH,
        PACKAGE_MANIFEST_PATH,
    ):
        need(path.is_file() and not path.is_symlink())
    need(
        stat.S_IMODE(os.lstat(ADAPTER_PATH).st_mode) == 0o755
        and stat.S_IMODE(os.lstat(REVIEWER_PATH).st_mode) == 0o755
    )
    for path in (
        PROCEDURE_PATH,
        RUNTIME_SCHEMA_PATH,
        RESULT_SCHEMA_PATH,
        PACKAGE_MANIFEST_PATH,
    ):
        need(stat.S_IMODE(os.lstat(path).st_mode) == 0o644)
    need(
        attestation["adapter_sha256"] == sha256_path(ADAPTER_PATH)
        and attestation["reviewer_sha256"] == sha256_path(REVIEWER_PATH)
        and attestation["operational_collection_procedure_contract_sha256"]
        == normalized_procedure_contract_sha256()
        and attestation["runtime_observation_schema_sha256"]
        == sha256_path(RUNTIME_SCHEMA_PATH)
        and attestation["sanitized_result_schema_sha256"]
        == sha256_path(RESULT_SCHEMA_PATH)
        and attestation["package_manifest_sha256"]
        == sha256_path(PACKAGE_MANIFEST_PATH)
    )
    need(
        result["adapter_contract_sha256"] == attestation["adapter_sha256"]
        and result["reviewer_sha256"] == attestation["reviewer_sha256"]
        and result["operational_collection_procedure_contract_sha256"]
        == attestation["operational_collection_procedure_contract_sha256"]
    )


def attempt_binding_sha256(attestation: Mapping[str, object]) -> str:
    record = {key: attestation[key] for key in ATTEMPT_BINDING_FIELDS}
    record["schema"] = ATTEMPT_BINDING_SCHEMA
    return sha256_bytes(canonical_json_bytes(record))


def instrumentation_binding_sha256(attestation: Mapping[str, object]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "adapter_sha256": attestation["adapter_sha256"],
                "attempt_binding_sha256": attestation["attempt_binding_sha256"],
                "database_execution_evidence_sha256": attestation[
                    "database_execution_evidence_sha256"
                ],
                "database_instrumentation_receipt_sha256": attestation[
                    "database_instrumentation_receipt_sha256"
                ],
                "fixed_sql_trace_sha256": attestation["fixed_sql_trace_sha256"],
                "provider_allowlist_recheck_receipt_sha256": attestation[
                    "provider_allowlist_recheck_receipt_sha256"
                ],
                "provider_observation_receipt_sha256": attestation[
                    "provider_initial_observation_receipt_sha256"
                ],
                "runtime_provenance_observation_receipt_sha256": attestation[
                    "runtime_provenance_observation_receipt_sha256"
                ],
                "schema": "PMAI_P0_04_SRBE_V5_INSTRUMENTATION_BINDING_V2",
                "tls_readonly_contract_sha256": attestation[
                    "tls_readonly_contract_sha256"
                ],
            }
        )
    )


def connection_binding_sha256(attestation: Mapping[str, object]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "attempt_binding_sha256": attestation["attempt_binding_sha256"],
                "authorization_record_sha256": attestation[
                    "authorization_record_sha256"
                ],
                "database_execution_evidence_sha256": attestation[
                    "database_execution_evidence_sha256"
                ],
                "database_observed_identity_sha256": attestation[
                    "target_database_observed_identity_sha256"
                ],
                "instrumentation_receipt_sha256": attestation[
                    "instrumentation_receipt_sha256"
                ],
                "provider_identity_sha256": attestation[
                    "observed_target_provider_identity_sha256"
                ],
                "runtime_provenance_observation_receipt_sha256": attestation[
                    "runtime_provenance_observation_receipt_sha256"
                ],
                "schema": "PMAI_P0_04_SRBE_V5_TARGET_CONNECTION_BINDING_V2",
                "tls_contract_sha256": attestation["tls_readonly_contract_sha256"],
            }
        )
    )


def attestation_mac(payload: Mapping[str, object], key: bytes | bytearray) -> str:
    message = (
        ATTESTATION_SCHEMA.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(payload)
        + b"\n"
    )
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def validate_attestation_shape(attestation: Mapping[str, object]) -> None:
    need(set(attestation) == ATTESTATION_KEYS)
    need(attestation["schema"] == ATTESTATION_SCHEMA)
    for name, value in attestation.items():
        if name.endswith("_sha256"):
            need(is_sha256(value))
    need(
        is_git_oid(attestation["repository_commit_oid"])
        and is_git_oid(attestation["repository_tree_oid"])
    )
    need(
        len(
            {
                attestation["ledger_hmac_key_id_sha256"],
                attestation["runtime_provenance_hmac_key_id_sha256"],
                attestation["independent_attestation_hmac_key_id_sha256"],
            }
        )
        == 3
    )
    for key in (
        "live_execution_authorized",
        "runtime_provenance_worktree_clean",
        "runtime_provenance_package_paths_regular_nonsymlink",
        "runtime_provenance_fixture_only",
        "collection_attempt_consumed",
        "target_status_available",
        "target_lifecycle_within_72h",
        "target_application_attachment_count_zero",
        "target_open_connection_count_zero",
        "initial_inbound_ip_rule_set_empty",
        "final_inbound_ip_rule_set_empty",
        "public_external_access_blocked",
        "cleanup_required",
        "cleanup_completed",
        "final_network_state_verified",
        "pre_restore_readonly_collection_complete",
    ):
        need(type(attestation[key]) is bool)
    need(
        attestation["live_execution_authorized"] is True
        and attestation["collection_attempt_limit"] == 1
        and type(attestation["collection_attempt_limit"]) is int
        and attestation["collection_attempts_consumed"] == 0
        and type(attestation["collection_attempts_consumed"]) is int
        and attestation["attempt_ledger_final_state"] == "COMPLETED"
    )
    for key in (
        "runtime_provenance_worktree_clean",
        "runtime_provenance_package_paths_regular_nonsymlink",
        "collection_attempt_consumed",
        "target_status_available",
        "target_lifecycle_within_72h",
        "target_application_attachment_count_zero",
        "target_open_connection_count_zero",
        "initial_inbound_ip_rule_set_empty",
        "final_inbound_ip_rule_set_empty",
        "public_external_access_blocked",
        "cleanup_required",
        "cleanup_completed",
        "final_network_state_verified",
        "pre_restore_readonly_collection_complete",
    ):
        need(attestation[key] is True)
    need(attestation["runtime_provenance_fixture_only"] is False)


def verify_attestation_hmac(
    attestation: Mapping[str, object], key: bytes | bytearray
) -> None:
    try:
        need(len(key) == 32 and any(key))
        validate_attestation_shape(attestation)
        need(
            hmac.compare_digest(
                sha256_bytes(bytes(key)),
                str(attestation["independent_attestation_hmac_key_id_sha256"]),
            )
        )
        payload = dict(attestation)
        supplied = str(payload.pop("hmac_sha256"))
        need(hmac.compare_digest(attestation_mac(payload, key), supplied))
    except ReviewHold as exc:
        raise ReviewHold("INDEPENDENT_ATTESTATION_INVALID") from exc


def validate_attested_success(
    result: Mapping[str, object],
    result_line: bytes,
    attestation: Mapping[str, object],
    key: bytes | bytearray,
) -> None:
    validate_success_core(result, runtime=False)
    runtime = runtime_observation_from_result(result)
    runtime_line = canonical_json_bytes(runtime) + b"\n"
    verify_attestation_hmac(attestation, key)
    need(
        attestation["sanitized_result_line_sha256"] == sha256_bytes(result_line)
        and attestation["runtime_observation_line_sha256"]
        == sha256_bytes(runtime_line)
        and attestation["fixed_sql_trace_sha256"] == fixed_sql_trace_sha256()
        and attestation["tls_readonly_contract_sha256"]
        == tls_readonly_contract_sha256()
        and attestation["attempt_binding_sha256"]
        == attempt_binding_sha256(attestation)
    )
    expected = (
        attestation["expected_target_provider_identity_sha256"],
        attestation["expected_production_provider_identity_sha256"],
        attestation["expected_staging_provider_identity_sha256"],
    )
    observed = (
        attestation["observed_target_provider_identity_sha256"],
        attestation["observed_production_provider_identity_sha256"],
        attestation["observed_staging_provider_identity_sha256"],
    )
    need(expected == observed and len(set(expected)) == 3)
    need(
        result["target_provider_identity_sha256"] == observed[0]
        and result["forbidden_production_provider_identity_sha256"] == observed[1]
        and result["forbidden_staging_provider_identity_sha256"] == observed[2]
        and result["attempt_binding_sha256"]
        == attestation["attempt_binding_sha256"]
        and result["attempt_ledger_receipt_sha256"]
        == attestation["attempt_ledger_receipt_sha256"]
        and result["provider_observation_sha256"]
        == attestation["provider_initial_observation_receipt_sha256"]
        and result["database_observation_sha256"]
        == attestation["database_instrumentation_receipt_sha256"]
        and result["database_execution_evidence_sha256"]
        == attestation["database_execution_evidence_sha256"]
        and result["target_database_observed_identity_sha256"]
        == attestation["target_database_observed_identity_sha256"]
        and result["cleanup_receipt_sha256"]
        == attestation["cleanup_receipt_sha256"]
        and result["cleanup_supervisor_armed_receipt_sha256"]
        == attestation["cleanup_supervisor_armed_receipt_sha256"]
        and result["cleanup_supervisor_final_receipt_sha256"]
        == attestation["cleanup_supervisor_final_receipt_sha256"]
        and result["fixed_sql_trace_sha256"]
        == attestation["fixed_sql_trace_sha256"]
        and result["runtime_provenance_observation_receipt_sha256"]
        == attestation["runtime_provenance_observation_receipt_sha256"]
        and result["tls_readonly_contract_sha256"]
        == attestation["tls_readonly_contract_sha256"]
    )
    need(
        attestation["instrumentation_receipt_sha256"]
        == instrumentation_binding_sha256(attestation)
        and result["instrumentation_receipt_sha256"]
        == attestation["instrumentation_receipt_sha256"]
        and attestation["target_connection_binding_sha256"]
        == connection_binding_sha256(attestation)
        and result["target_connection_binding_sha256"]
        == attestation["target_connection_binding_sha256"]
    )
    need(
        attestation["expected_pre_restore_schema_manifest_sha256"]
        == EXPECTED_EMPTY_MANIFEST_SHA256
        and attestation["observed_pre_restore_schema_manifest_sha256"]
        == EXPECTED_EMPTY_MANIFEST_SHA256
        and result["authorization_record_sha256"]
        == attestation["authorization_record_sha256"]
        and len(
            {
                attestation["ledger_hmac_key_id_sha256"],
                attestation["runtime_provenance_hmac_key_id_sha256"],
                attestation["independent_attestation_hmac_key_id_sha256"],
            }
        )
        == 3
    )
    receipts = {
        attestation["provider_initial_observation_receipt_sha256"],
        attestation["provider_allowlist_recheck_receipt_sha256"],
        attestation["provider_final_observation_receipt_sha256"],
        attestation["database_instrumentation_receipt_sha256"],
        attestation["database_execution_evidence_sha256"],
        attestation["instrumentation_receipt_sha256"],
        attestation["cleanup_receipt_sha256"],
        attestation["cleanup_supervisor_armed_receipt_sha256"],
        attestation["cleanup_supervisor_final_receipt_sha256"],
    }
    need(len(receipts) == 9)
    validate_artifact_bindings(result, attestation)


def read_anonymous_pipe_key() -> bytearray:
    value = os.environ.pop(ATTESTATION_KEY_FD_ENV, None)
    need(
        isinstance(value, str)
        and re.fullmatch(r"(?:[3-9]|[1-9][0-9]+)", value) is not None,
        "ARGUMENT_CONTRACT_MISMATCH",
    )
    descriptor = int(value)
    need(3 <= descriptor <= 1_048_575, "ARGUMENT_CONTRACT_MISMATCH")
    raw = bytearray()
    accepted = False
    try:
        metadata = os.fstat(descriptor)
        need(stat.S_ISFIFO(metadata.st_mode), "ARGUMENT_CONTRACT_MISMATCH")
        proc_root = Path("/proc/self/fd")
        need(proc_root.is_dir(), "ARGUMENT_CONTRACT_MISMATCH")
        proc_target = os.readlink(proc_root / str(descriptor))
        need(
            re.fullmatch(r"pipe:\[[0-9]+\]", proc_target) is not None,
            "ARGUMENT_CONTRACT_MISMATCH",
        )
        os.set_inheritable(descriptor, False)
        os.set_blocking(descriptor, False)
        while len(raw) <= 32:
            try:
                block = os.read(descriptor, 33 - len(raw))
            except BlockingIOError as exc:
                raise ReviewHold("ARGUMENT_CONTRACT_MISMATCH") from exc
            if not block:
                break
            raw.extend(block)
        need(len(raw) == 32 and any(raw), "ARGUMENT_CONTRACT_MISMATCH")
        accepted = True
        return raw
    except OSError as exc:
        raise ReviewHold("ARGUMENT_CONTRACT_MISMATCH") from exc
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        if not accepted:
            for index in range(len(raw)):
                raw[index] = 0


def review_files(result_path: Path, attestation_path: Path) -> dict[str, object]:
    need(result_path.is_absolute() and attestation_path.is_absolute())
    result_line = read_stable_regular_file(result_path, MAX_INPUT_BYTES)
    attestation_line = read_stable_regular_file(attestation_path, MAX_INPUT_BYTES)
    result = parse_canonical_json_line(result_line)
    try:
        attestation = parse_canonical_json_line(attestation_line)
    except ReviewHold as exc:
        raise ReviewHold("INDEPENDENT_ATTESTATION_INVALID") from exc
    need(result.get("outcome") == "SUCCESS")
    key = read_anonymous_pipe_key()
    try:
        validate_schema_contracts()
        validate_attested_success(result, result_line, attestation, key)
        return result
    finally:
        for index in range(len(key)):
            key[index] = 0


def _digest(label: str) -> str:
    return sha256_bytes(("pmai-p0-04-v5-reviewer-selftest:" + label).encode("ascii"))


def _oid(label: str) -> str:
    return _digest("oid:" + label)[:40]


def _synthetic_bundle(key: bytes) -> tuple[dict[str, object], dict[str, object]]:
    auth: dict[str, object] = {
        name: _digest(name) for name in AUTH_FIELDS if name.endswith("_sha256")
    }
    auth.update(
        {
            "adapter_sha256": sha256_path(ADAPTER_PATH),
            "reviewer_sha256": sha256_path(REVIEWER_PATH),
            "operational_collection_procedure_contract_sha256": (
                normalized_procedure_contract_sha256()
            ),
            "runtime_observation_schema_sha256": sha256_path(RUNTIME_SCHEMA_PATH),
            "sanitized_result_schema_sha256": sha256_path(RESULT_SCHEMA_PATH),
            "package_manifest_sha256": sha256_path(PACKAGE_MANIFEST_PATH),
            "repository_commit_oid": _oid("commit"),
            "repository_tree_oid": _oid("tree"),
            "independent_attestation_hmac_key_id_sha256": sha256_bytes(key),
            "live_execution_authorized": True,
            "collection_attempt_limit": 1,
            "collection_attempts_consumed": 0,
        }
    )
    attestation: dict[str, object] = dict(auth)
    for name in ATTESTATION_EVIDENCE_FIELDS:
        if name.endswith("_sha256"):
            attestation[name] = _digest(name)
    attestation.update(
        {
            "schema": ATTESTATION_SCHEMA,
            "runtime_provenance_worktree_clean": True,
            "runtime_provenance_package_paths_regular_nonsymlink": True,
            "runtime_provenance_fixture_only": False,
            "attempt_ledger_final_state": "COMPLETED",
            "collection_attempt_consumed": True,
            "target_status_available": True,
            "target_lifecycle_within_72h": True,
            "target_application_attachment_count_zero": True,
            "target_open_connection_count_zero": True,
            "initial_inbound_ip_rule_set_empty": True,
            "final_inbound_ip_rule_set_empty": True,
            "public_external_access_blocked": True,
            "cleanup_required": True,
            "cleanup_completed": True,
            "final_network_state_verified": True,
            "pre_restore_readonly_collection_complete": True,
            "fixed_sql_trace_sha256": fixed_sql_trace_sha256(),
            "tls_readonly_contract_sha256": tls_readonly_contract_sha256(),
            "expected_pre_restore_schema_manifest_sha256": (
                EXPECTED_EMPTY_MANIFEST_SHA256
            ),
            "observed_pre_restore_schema_manifest_sha256": (
                EXPECTED_EMPTY_MANIFEST_SHA256
            ),
        }
    )
    attestation["observed_target_provider_identity_sha256"] = attestation[
        "expected_target_provider_identity_sha256"
    ]
    attestation["observed_production_provider_identity_sha256"] = attestation[
        "expected_production_provider_identity_sha256"
    ]
    attestation["observed_staging_provider_identity_sha256"] = attestation[
        "expected_staging_provider_identity_sha256"
    ]
    attestation["attempt_binding_sha256"] = attempt_binding_sha256(attestation)
    attestation["instrumentation_receipt_sha256"] = (
        instrumentation_binding_sha256(attestation)
    )
    attestation["target_connection_binding_sha256"] = (
        connection_binding_sha256(attestation)
    )
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "outcome": "SUCCESS",
        "adapter_contract_sha256": attestation["adapter_sha256"],
        "authorization_record_sha256": attestation["authorization_record_sha256"],
        "attempt_binding_sha256": attestation["attempt_binding_sha256"],
        "attempt_ledger_receipt_sha256": attestation[
            "attempt_ledger_receipt_sha256"
        ],
        "provider_observation_sha256": attestation[
            "provider_initial_observation_receipt_sha256"
        ],
        "target_provider_identity_sha256": attestation[
            "observed_target_provider_identity_sha256"
        ],
        "forbidden_production_provider_identity_sha256": attestation[
            "observed_production_provider_identity_sha256"
        ],
        "forbidden_staging_provider_identity_sha256": attestation[
            "observed_staging_provider_identity_sha256"
        ],
        "database_observation_sha256": attestation[
            "database_instrumentation_receipt_sha256"
        ],
        "target_database_observed_identity_sha256": attestation[
            "target_database_observed_identity_sha256"
        ],
        "target_connection_binding_sha256": attestation[
            "target_connection_binding_sha256"
        ],
        "pre_restore_schema_manifest_sha256": EXPECTED_EMPTY_MANIFEST_SHA256,
        "expected_pre_restore_schema_manifest_sha256": EXPECTED_EMPTY_MANIFEST_SHA256,
        "operational_collection_procedure_contract_sha256": attestation[
            "operational_collection_procedure_contract_sha256"
        ],
        "reviewer_sha256": attestation["reviewer_sha256"],
        "instrumentation_receipt_sha256": attestation[
            "instrumentation_receipt_sha256"
        ],
        "cleanup_receipt_sha256": attestation["cleanup_receipt_sha256"],
        "cleanup_supervisor_armed_receipt_sha256": attestation[
            "cleanup_supervisor_armed_receipt_sha256"
        ],
        "cleanup_supervisor_final_receipt_sha256": attestation[
            "cleanup_supervisor_final_receipt_sha256"
        ],
        "database_execution_evidence_sha256": attestation[
            "database_execution_evidence_sha256"
        ],
        "fixed_sql_trace_sha256": attestation["fixed_sql_trace_sha256"],
        "runtime_provenance_observation_receipt_sha256": attestation[
            "runtime_provenance_observation_receipt_sha256"
        ],
        "tls_readonly_contract_sha256": attestation[
            "tls_readonly_contract_sha256"
        ],
        "target_status_available": True,
        "target_lifecycle_within_72h": True,
        "target_application_attachment_count_zero": True,
        "target_open_connection_count_zero": True,
        "initial_inbound_ip_rule_set_empty": True,
        "final_inbound_ip_rule_set_empty": True,
        "public_external_access_blocked": True,
        "collection_attempt_consumed": True,
        "pre_restore_readonly_collection_complete": True,
        "post_restore_schema_evidence_collected": False,
        "runtime_binding_contract_complete": False,
        "srbe_collection_evidence_complete": False,
        "evidence_complete": False,
        "raw_connection_values_disclosed": False,
        "fixture_only": False,
        "expected_post_restore_schema_manifest_sha256": UNBOUND,
    }
    result_line = canonical_json_bytes(result) + b"\n"
    runtime_line = canonical_json_bytes(runtime_observation_from_result(result)) + b"\n"
    attestation["sanitized_result_line_sha256"] = sha256_bytes(result_line)
    attestation["runtime_observation_line_sha256"] = sha256_bytes(runtime_line)
    payload = dict(attestation)
    attestation["hmac_sha256"] = attestation_mac(payload, key)
    return result, attestation


def _expect_hold(callback: Callable[[], object]) -> None:
    rejected = False
    try:
        callback()
    except ReviewHold:
        rejected = True
    need(rejected)


def _pipe_key(key: bytes) -> bytearray:
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, key)
    finally:
        os.close(write_fd)
    os.environ[ATTESTATION_KEY_FD_ENV] = str(read_fd)
    return read_anonymous_pipe_key()


def self_test() -> int:
    os.environ.pop(ATTESTATION_KEY_FD_ENV, None)
    try:
        validate_schema_contracts()
        key = hashlib.sha256(b"pmai-p0-04-v5-synthetic-attestation-key").digest()
        result, attestation = _synthetic_bundle(key)
        result_line = canonical_json_bytes(result) + b"\n"
        validate_attested_success(result, result_line, attestation, key)

        wrong_key = hashlib.sha256(b"wrong-key").digest()
        _expect_hold(
            lambda: validate_attested_success(
                result, result_line, attestation, wrong_key
            )
        )
        tampered = dict(attestation)
        tampered["cleanup_receipt_sha256"] = _digest("tampered-cleanup")
        _expect_hold(
            lambda: validate_attested_success(result, result_line, tampered, key)
        )
        extra = dict(attestation)
        extra["extra"] = False
        _expect_hold(
            lambda: validate_attested_success(result, result_line, extra, key)
        )
        missing = dict(attestation)
        missing.pop("runtime_observation_line_sha256")
        _expect_hold(
            lambda: validate_attested_success(result, result_line, missing, key)
        )
        key_collision = dict(attestation)
        key_collision["runtime_provenance_hmac_key_id_sha256"] = key_collision[
            "ledger_hmac_key_id_sha256"
        ]
        _expect_hold(lambda: validate_attestation_shape(key_collision))
        result_mismatch = dict(result)
        result_mismatch["cleanup_receipt_sha256"] = _digest(
            "result-line-mismatch"
        )
        _expect_hold(
            lambda: validate_attested_success(
                result_mismatch,
                canonical_json_bytes(result_mismatch) + b"\n",
                attestation,
                key,
            )
        )
        runtime_mismatch = dict(attestation)
        runtime_mismatch["runtime_observation_line_sha256"] = _digest(
            "wrong-runtime"
        )
        payload = dict(runtime_mismatch)
        payload.pop("hmac_sha256")
        runtime_mismatch["hmac_sha256"] = attestation_mac(payload, key)
        _expect_hold(
            lambda: validate_attested_success(
                result, result_line, runtime_mismatch, key
            )
        )
        _expect_hold(
            lambda: parse_canonical_json_line(
                json.dumps(attestation, indent=2, sort_keys=True).encode("ascii")
                + b"\n"
            )
        )
        _expect_hold(
            lambda: parse_canonical_json_line(
                b'{"schema":"x","schema":"y"}\n'
            )
        )

        adapter_hold = conservative_failure()
        adapter_hold["state_provenance"] = "ADAPTER_STATE_MACHINE"
        validate_failure(adapter_hold)
        invalid = dict(adapter_hold)
        invalid["attempt_reserved"] = False
        _expect_hold(lambda: validate_failure(invalid))
        invalid = conservative_failure()
        invalid["attempt_state"] = "KNOWN_NOT_STARTED"
        _expect_hold(lambda: validate_failure(invalid))

        pipe_value = _pipe_key(key)
        need(bytes(pipe_value) == key)
        for index in range(len(pipe_value)):
            pipe_value[index] = 0
        need(ATTESTATION_KEY_FD_ENV not in os.environ)
        _expect_hold(read_anonymous_pipe_key)
        os.environ[ATTESTATION_KEY_FD_ENV] = "not-a-fd"
        _expect_hold(read_anonymous_pipe_key)
        need(ATTESTATION_KEY_FD_ENV not in os.environ)
        os.environ[ATTESTATION_KEY_FD_ENV] = "2"
        _expect_hold(read_anonymous_pipe_key)
        need(ATTESTATION_KEY_FD_ENV not in os.environ)
        _expect_hold(lambda: _pipe_key(key[:31]))
        _expect_hold(lambda: _pipe_key(key + b"x"))
        with tempfile.TemporaryFile() as regular:
            regular_descriptor = os.dup(regular.fileno())
            os.environ[ATTESTATION_KEY_FD_ENV] = str(regular_descriptor)
            _expect_hold(read_anonymous_pipe_key)
        need(ATTESTATION_KEY_FD_ENV not in os.environ)
        with tempfile.TemporaryDirectory(prefix="pmai-v5-key-fifo-") as directory:
            named_fifo = Path(directory) / "named.fifo"
            os.mkfifo(named_fifo, 0o600)
            named_descriptor = os.open(
                named_fifo,
                os.O_RDWR | getattr(os, "O_NONBLOCK", 0),
            )
            os.environ[ATTESTATION_KEY_FD_ENV] = str(named_descriptor)
            _expect_hold(read_anonymous_pipe_key)
        need(ATTESTATION_KEY_FD_ENV not in os.environ)

        with tempfile.TemporaryDirectory(prefix="pmai-v5-reviewer-") as directory:
            root = Path(directory)
            result_path = root / "result.json"
            attestation_path = root / "attestation.json"
            result_path.write_bytes(result_line)
            attestation_path.write_bytes(canonical_json_bytes(attestation) + b"\n")
            read_fd, write_fd = os.pipe()
            try:
                os.write(write_fd, key)
            finally:
                os.close(write_fd)
            os.environ[ATTESTATION_KEY_FD_ENV] = str(read_fd)
            reviewed = review_files(result_path, attestation_path)
            need(reviewed == result)
        need(ATTESTATION_KEY_FD_ENV not in os.environ)
    finally:
        os.environ.pop(ATTESTATION_KEY_FD_ENV, None)
    emit(conservative_failure())
    return 0


def emit(record: Mapping[str, object]) -> None:
    payload = canonical_json_bytes(record) + b"\n"
    need(len(payload) <= MAX_OUTPUT_BYTES)
    written = os.write(sys.stdout.fileno(), payload)
    need(written == len(payload))


def parser() -> StrictArgumentParser:
    value = StrictArgumentParser(add_help=False, allow_abbrev=False)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--review-file", type=Path)
    value.add_argument("--independent-attestation-file", type=Path)
    return value


def validate_invocation_contract() -> None:
    need(sys.flags.isolated == 1, "ARGUMENT_CONTRACT_MISMATCH")
    need(sys.flags.ignore_environment == 1, "ARGUMENT_CONTRACT_MISMATCH")
    need(sys.flags.no_user_site == 1, "ARGUMENT_CONTRACT_MISMATCH")
    need(sys.flags.dont_write_bytecode == 1, "ARGUMENT_CONTRACT_MISMATCH")
    need(getattr(sys.flags, "safe_path", False) is True, "ARGUMENT_CONTRACT_MISMATCH")
    need(sys.flags.optimize == 0, "ARGUMENT_CONTRACT_MISMATCH")
    need("" not in sys.path, "ARGUMENT_CONTRACT_MISMATCH")
    need(str(REPOSITORY_ROOT) not in sys.path, "ARGUMENT_CONTRACT_MISMATCH")
    need(str(REPOSITORY_ROOT / "scripts") not in sys.path, "ARGUMENT_CONTRACT_MISMATCH")


def main(argv: Sequence[str] | None = None) -> int:
    validate_invocation_contract()
    args = parser().parse_args(argv)
    if args.self_test:
        need(
            args.review_file is None
            and args.independent_attestation_file is None,
            "ARGUMENT_CONTRACT_MISMATCH",
        )
        return self_test()
    need(
        args.review_file is not None
        and args.independent_attestation_file is not None,
        "ARGUMENT_CONTRACT_MISMATCH",
    )
    result = review_files(args.review_file, args.independent_attestation_file)
    emit(result)
    return 0


def entrypoint() -> int:
    try:
        return main()
    except BaseException as exc:
        public_code = (
            exc.public_code if isinstance(exc, ReviewHold) else "INTERNAL_FAILURE"
        )
        try:
            emit(conservative_failure(public_code))
        except BaseException:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
