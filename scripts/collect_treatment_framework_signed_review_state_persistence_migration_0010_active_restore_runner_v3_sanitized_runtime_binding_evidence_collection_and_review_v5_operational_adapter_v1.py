#!/usr/bin/env python3
"""Fail-closed V5 SRBE operational collection adapter preparation.

The module has no live provider, database, ledger, cleanup-supervisor, or
runtime-provenance implementation and imports no network or database client.
``--dry-run`` and ``--self-test`` are wholly offline.
``--collect-once`` is deliberately unavailable from the command line: a future
single-use authorization must import :func:`collect_once` and inject reviewed
``RenderPort``, ``DatabasePort``, ``AttemptLedgerPort``,
``CleanupSupervisorPort``, and ``RuntimeProvenancePort`` implementations whose
exact source and dependency hashes are bound by that future authorization.

Only fixed public error codes are emitted.  Raw provider identifiers, database
identifiers, connection material, credentials, SQL results, exception text,
and tracebacks are never written to stdout or stderr.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Callable, Mapping, NoReturn, Protocol, Sequence
import unicodedata


sys.dont_write_bytecode = True

RESULT_SCHEMA = "PMAI_P0_04_SRBE_V5_SANITIZED_COLLECTION_RESULT_V1"
RUNTIME_OBSERVATION_SCHEMA = (
    "PMAI_P0_04_SRBE_V5_SANITIZED_RUNTIME_OBSERVATION_V1"
)
MANIFEST_SCHEMA = "PMAI_P0_04_SRBE_STRUCTURAL_SCHEMA_MANIFEST_V5_V1"
LEDGER_SCHEMA = "PMAI_P0_04_SRBE_V5_DURABLE_ATTEMPT_LEDGER_V1"
EXPECTED_EMPTY_MANIFEST_LINE = (
    b'{"relations":[],"schema":"PMAI_P0_04_SRBE_STRUCTURAL_SCHEMA_MANIFEST_V5_V1"}\n'
)
EXPECTED_EMPTY_MANIFEST_SHA256 = (
    "f87acbf36011fa8656e82f1cb6067614a59d019e32ea36781fe1dc2ceb4fc010"
)
UNBOUND = "UNBOUND"
MAX_JSON_BYTES = 256 * 1024
MAX_TEXT_BYTES = 1024
MAX_RELATIONS = 10000
MAX_COLUMNS_PER_RELATION = 4096
MAX_RECHECK_SKEW_SECONDS = 300
MAX_TARGET_AGE_SECONDS = 72 * 60 * 60
CONNECT_TIMEOUT_SECONDS = 10
RUNTIME_PROVENANCE_HMAC_KEY_BYTES = 32
RUNTIME_PROVENANCE_HMAC_DOMAIN = (
    b"PMAI_P0_04_SRBE_V5_RUNTIME_PROVENANCE_HMAC_V1\x00"
)

ADAPTER_RELATIVE = (
    "scripts/collect_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_collection_and_review_v5_operational_adapter_v1.py"
)
REVIEWER_RELATIVE = (
    "scripts/validate_treatment_framework_signed_review_state_persistence_"
    "migration_0010_active_restore_runner_v3_sanitized_runtime_binding_"
    "evidence_review_v5_operational_v1.py"
)
RUNTIME_SCHEMA_RELATIVE = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_"
    "ADAPTER_PREPARATION_V1_RUNTIME_OBSERVATION_SCHEMA_V1.json"
)
RESULT_SCHEMA_RELATIVE = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_"
    "ADAPTER_PREPARATION_V1_SANITIZED_RESULT_SCHEMA_V1.json"
)
PACKAGE_MANIFEST_RELATIVE = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_"
    "ADAPTER_PREPARATION_V1_PACKAGE_MANIFEST_V1.json"
)
CONTRACT_DOCUMENT_RELATIVE = (
    "docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_"
    "MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_"
    "EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_"
    "ADAPTER_PREPARATION_V1.md"
)
PROCEDURE_BEGIN = b"operational_collection_procedure_contract_begin\n"
PROCEDURE_END = b"operational_collection_procedure_contract_end\n"

SQL_SET_SESSION_READ_ONLY = (
    "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"
)
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

FIXED_SQL = {
    "BEGIN_READ_ONLY": SQL_BEGIN_READ_ONLY,
    "DATABASE_IDENTITY": SQL_DATABASE_IDENTITY,
    "SET_IDLE_TIMEOUT": SQL_SET_IDLE_TIMEOUT,
    "SET_LOCK_TIMEOUT": SQL_SET_LOCK_TIMEOUT,
    "SET_SEARCH_PATH": SQL_SET_SEARCH_PATH,
    "SET_SESSION_READ_ONLY": SQL_SET_SESSION_READ_ONLY,
    "SET_STATEMENT_TIMEOUT": SQL_SET_STATEMENT_TIMEOUT,
    "STRUCTURAL_MANIFEST": SQL_STRUCTURAL_MANIFEST,
    "VERIFY_READ_ONLY": SQL_VERIFY_READ_ONLY,
}

FIXED_SQL_ORDER = (
    "SET_SESSION_READ_ONLY",
    "BEGIN_READ_ONLY",
    "SET_SEARCH_PATH",
    "SET_STATEMENT_TIMEOUT",
    "SET_LOCK_TIMEOUT",
    "SET_IDLE_TIMEOUT",
    "VERIFY_READ_ONLY",
    "DATABASE_IDENTITY",
    "STRUCTURAL_MANIFEST",
)

SUCCESS_KEYS = {
    "adapter_contract_sha256",
    "attempt_binding_sha256",
    "attempt_ledger_receipt_sha256",
    "authorization_record_sha256",
    "cleanup_receipt_sha256",
    "cleanup_supervisor_armed_receipt_sha256",
    "cleanup_supervisor_final_receipt_sha256",
    "collection_attempt_consumed",
    "database_execution_evidence_sha256",
    "database_observation_sha256",
    "evidence_complete",
    "expected_post_restore_schema_manifest_sha256",
    "expected_pre_restore_schema_manifest_sha256",
    "final_inbound_ip_rule_set_empty",
    "fixture_only",
    "fixed_sql_trace_sha256",
    "forbidden_production_provider_identity_sha256",
    "forbidden_staging_provider_identity_sha256",
    "initial_inbound_ip_rule_set_empty",
    "instrumentation_receipt_sha256",
    "operational_collection_procedure_contract_sha256",
    "outcome",
    "post_restore_schema_evidence_collected",
    "pre_restore_readonly_collection_complete",
    "pre_restore_schema_manifest_sha256",
    "provider_observation_sha256",
    "public_external_access_blocked",
    "raw_connection_values_disclosed",
    "reviewer_sha256",
    "runtime_binding_contract_complete",
    "runtime_provenance_observation_receipt_sha256",
    "schema",
    "srbe_collection_evidence_complete",
    "target_application_attachment_count_zero",
    "target_connection_binding_sha256",
    "target_database_observed_identity_sha256",
    "target_lifecycle_within_72h",
    "target_open_connection_count_zero",
    "target_provider_identity_sha256",
    "target_status_available",
    "tls_readonly_contract_sha256",
}

RUNTIME_OBSERVATION_KEYS = SUCCESS_KEYS - {"outcome"}

FAILURE_KEYS = {
    "attempt_state",
    "attempt_reserved",
    "cleanup_completed",
    "cleanup_required",
    "collection_attempt_consumed",
    "error_code",
    "final_network_state_verified",
    "hold",
    "outcome",
    "raw_connection_values_disclosed",
    "runtime_evidence_emitted",
    "schema",
    "stage_code",
    "state_provenance",
}

ATTEMPT_STATES = {"KNOWN_NOT_STARTED", "CONSUMED", "UNCERTAIN"}
STATE_PROVENANCE_VALUES = {
    "ADAPTER_STATE_MACHINE",
    "UNVERIFIED_REVIEW_INPUT",
}

ERROR_CODES = {
    "ALLOWLIST_ADD_FAILED",
    "ALLOWLIST_REMOVE_FAILED",
    "ALLOWLIST_RECHECK_FAILED",
    "ARGUMENT_CONTRACT_MISMATCH",
    "ANTI_ROLLBACK_WITNESS_UNAVAILABLE",
    "ATTEMPT_ALREADY_CONSUMED",
    "ATTEMPT_LEDGER_UNAVAILABLE",
    "ATTEMPT_LEDGER_UNCERTAIN",
    "AUTHORIZATION_BINDING_MISMATCH",
    "AUTHORIZATION_INVALID",
    "CLEANUP_UNCERTAIN",
    "CONNECTION_MATERIAL_INVALID",
    "CONTROLLED_EXECUTION_HOLD",
    "CLEANUP_SUPERVISOR_UNAVAILABLE",
    "CLEANUP_SUPERVISOR_UNCERTAIN",
    "DATABASE_CLOSE_FAILED",
    "DATABASE_CONNECT_FAILED",
    "DATABASE_OBSERVATION_INVALID",
    "DATABASE_READONLY_CONTRACT_FAILED",
    "FINAL_ALLOWLIST_NOT_EMPTY",
    "FINAL_PUBLIC_ACCESS_NOT_BLOCKED",
    "FIXED_SQL_TRACE_INVALID",
    "IDENTITY_DOMAIN_MISMATCH",
    "IDENTITY_SEPARATION_FAILED",
    "INITIAL_ALLOWLIST_NOT_EMPTY",
    "INSTRUMENTATION_INCOMPLETE",
    "INDEPENDENT_ATTESTATION_INVALID",
    "INTERNAL_FAILURE",
    "LEDGER_AUTHENTICATION_FAILED",
    "LIVE_PORTS_NOT_INJECTED",
    "PORT_IMPLEMENTATION_UNBOUND",
    "PUBLIC_ACCESS_NOT_BLOCKED",
    "RUNTIME_PROVENANCE_INVALID",
    "RUNTIME_PROVENANCE_UNAVAILABLE",
    "RUNTIME_COMPONENT_BINDING_MISMATCH",
    "SCHEMA_MANIFEST_MISMATCH",
    "TARGET_ATTACHMENTS_NONZERO",
    "TARGET_CONNECTIONS_NONZERO",
    "TARGET_NOT_AVAILABLE",
    "TARGET_TOO_OLD",
    "TLS_NEGOTIATION_INVALID",
    "TLS_EVIDENCE_INVALID",
}

STAGE_CODES = {
    "ALLOWLIST_ADD",
    "ALLOWLIST_REVALIDATION",
    "ATTEMPT_FINALIZATION",
    "ATTEMPT_RESERVATION",
    "ANTI_ROLLBACK_WITNESS",
    "COMPLETE",
    "CLEANUP_SUPERVISOR_ARM",
    "CLEANUP_SUPERVISOR_FINALIZE",
    "CLEANUP_SUPERVISOR",
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
    "ALLOWLIST_REMOVE",
}

LEDGER_STATES = (
    "RESERVED",
    "PROVIDER_OBSERVE_INTENT",
    "PROVIDER_VERIFIED",
    "SUPERVISOR_ARM_INTENT",
    "SUPERVISOR_ARMED",
    "ALLOWLIST_ADD_INTENT",
    "ALLOWLIST_ADDED",
    "ALLOWLIST_REVALIDATE_INTENT",
    "ALLOWLIST_REVALIDATED",
    "CONNECTION_MATERIAL_INTENT",
    "CONNECTION_MATERIAL_ACQUIRED",
    "DATABASE_CONNECT_INTENT",
    "DATABASE_CONNECTED",
    "DATABASE_OBSERVED",
    "DATABASE_CLOSE_INTENT",
    "DATABASE_CLOSED",
    "ALLOWLIST_REMOVE_INTENT",
    "ALLOWLIST_REMOVED",
    "FINAL_RECHECK_INTENT",
    "FINAL_NETWORK_VERIFIED",
    "SUPERVISOR_CONFIRM_INTENT",
    "SUPERVISOR_CONFIRMED",
    "COMPLETED",
    "FAILED_CLEANED",
    "FAILED_UNCERTAIN",
)

LEDGER_ALLOWED_TRANSITIONS = {
    "RESERVED": {"PROVIDER_OBSERVE_INTENT", "FAILED_CLEANED", "FAILED_UNCERTAIN"},
    "PROVIDER_OBSERVE_INTENT": {"PROVIDER_VERIFIED", "FAILED_CLEANED", "FAILED_UNCERTAIN"},
    "PROVIDER_VERIFIED": {"SUPERVISOR_ARM_INTENT", "FAILED_CLEANED", "FAILED_UNCERTAIN"},
    "SUPERVISOR_ARM_INTENT": {"SUPERVISOR_ARMED", "FAILED_CLEANED", "FAILED_UNCERTAIN"},
    "SUPERVISOR_ARMED": {"ALLOWLIST_ADD_INTENT", "FAILED_CLEANED", "FAILED_UNCERTAIN"},
    "ALLOWLIST_ADD_INTENT": {"ALLOWLIST_ADDED", "FAILED_UNCERTAIN"},
    "ALLOWLIST_ADDED": {"ALLOWLIST_REVALIDATE_INTENT", "ALLOWLIST_REMOVE_INTENT", "FAILED_UNCERTAIN"},
    "ALLOWLIST_REVALIDATE_INTENT": {"ALLOWLIST_REVALIDATED", "ALLOWLIST_REMOVE_INTENT", "FAILED_UNCERTAIN"},
    "ALLOWLIST_REVALIDATED": {"CONNECTION_MATERIAL_INTENT", "ALLOWLIST_REMOVE_INTENT", "FAILED_UNCERTAIN"},
    "CONNECTION_MATERIAL_INTENT": {"CONNECTION_MATERIAL_ACQUIRED", "ALLOWLIST_REMOVE_INTENT", "FAILED_UNCERTAIN"},
    "CONNECTION_MATERIAL_ACQUIRED": {"DATABASE_CONNECT_INTENT", "ALLOWLIST_REMOVE_INTENT", "FAILED_UNCERTAIN"},
    "DATABASE_CONNECT_INTENT": {"DATABASE_CONNECTED", "DATABASE_CLOSE_INTENT", "FAILED_UNCERTAIN"},
    "DATABASE_CONNECTED": {"DATABASE_OBSERVED", "DATABASE_CLOSE_INTENT", "FAILED_UNCERTAIN"},
    "DATABASE_OBSERVED": {"DATABASE_CLOSE_INTENT", "FAILED_UNCERTAIN"},
    "DATABASE_CLOSE_INTENT": {"DATABASE_CLOSED", "FAILED_UNCERTAIN"},
    "DATABASE_CLOSED": {"ALLOWLIST_REMOVE_INTENT", "FAILED_UNCERTAIN"},
    "ALLOWLIST_REMOVE_INTENT": {"ALLOWLIST_REMOVED", "FAILED_UNCERTAIN"},
    "ALLOWLIST_REMOVED": {"FINAL_RECHECK_INTENT", "FAILED_UNCERTAIN"},
    "FINAL_RECHECK_INTENT": {"FINAL_NETWORK_VERIFIED", "FAILED_UNCERTAIN"},
    "FINAL_NETWORK_VERIFIED": {"SUPERVISOR_CONFIRM_INTENT", "FAILED_CLEANED", "FAILED_UNCERTAIN"},
    "SUPERVISOR_CONFIRM_INTENT": {"SUPERVISOR_CONFIRMED", "FAILED_UNCERTAIN"},
    "SUPERVISOR_CONFIRMED": {"COMPLETED", "FAILED_CLEANED", "FAILED_UNCERTAIN"},
    "COMPLETED": set(),
    "FAILED_CLEANED": set(),
    "FAILED_UNCERTAIN": set(),
}

FORBIDDEN_KEY = re.compile(
    r"(?:password|passwd|secret|token|credential|api[_-]?key|private[_-]?key|"
    r"connection[_-]?(?:string|url)|dsn|uri|url)$",
    re.IGNORECASE,
)


class Hold(RuntimeError):
    """A fixed-code failure; its cause and text are never emitted."""

    def __init__(self, error_code: str, stage_code: str) -> None:
        if error_code not in ERROR_CODES or stage_code not in STAGE_CODES:
            error_code = "INTERNAL_FAILURE"
            stage_code = "PRECHECK"
        super().__init__(error_code)
        self.error_code = error_code
        self.stage_code = stage_code


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise Hold("ARGUMENT_CONTRACT_MISMATCH", "PRECHECK")


def need(condition: bool, error_code: str, stage_code: str) -> None:
    if not condition:
        raise Hold(error_code, stage_code)


def validate_isolated_invocation() -> None:
    """Require the exact isolated, no-bytecode Python execution boundary."""

    repository_root = Path(__file__).resolve().parents[1]
    need(sys.flags.isolated == 1, "ARGUMENT_CONTRACT_MISMATCH", "PRECHECK")
    need(
        sys.flags.ignore_environment == 1,
        "ARGUMENT_CONTRACT_MISMATCH",
        "PRECHECK",
    )
    need(sys.flags.no_user_site == 1, "ARGUMENT_CONTRACT_MISMATCH", "PRECHECK")
    need(
        sys.flags.dont_write_bytecode == 1,
        "ARGUMENT_CONTRACT_MISMATCH",
        "PRECHECK",
    )
    need(
        getattr(sys.flags, "safe_path", False) is True,
        "ARGUMENT_CONTRACT_MISMATCH",
        "PRECHECK",
    )
    need(sys.flags.optimize == 0, "ARGUMENT_CONTRACT_MISMATCH", "PRECHECK")
    need("" not in sys.path, "ARGUMENT_CONTRACT_MISMATCH", "PRECHECK")
    need(
        str(repository_root) not in sys.path,
        "ARGUMENT_CONTRACT_MISMATCH",
        "PRECHECK",
    )
    need(
        str(repository_root / "scripts") not in sys.path,
        "ARGUMENT_CONTRACT_MISMATCH",
        "PRECHECK",
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def is_git_oid(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def safe_sha256(value: object, stage: str = "PRECHECK") -> str:
    need(is_sha256(value), "AUTHORIZATION_INVALID", stage)
    need(value not in {"0" * 64, "f" * 64}, "AUTHORIZATION_INVALID", stage)
    return str(value)


def canonical_json_bytes(value: object) -> bytes:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise Hold("INTERNAL_FAILURE", "OUTPUT_VALIDATION") from exc
    need(len(payload) <= MAX_JSON_BYTES, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    return payload


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise Hold("AUTHORIZATION_BINDING_MISMATCH", "PRECHECK") from exc
    return digest.hexdigest()


def repository_root() -> Path:
    source = Path(__file__)
    try:
        source_stat = source.lstat()
        resolved = source.resolve(strict=True)
    except OSError as exc:
        raise Hold("RUNTIME_PROVENANCE_INVALID", "RUNTIME_PROVENANCE") from exc
    need(
        stat.S_ISREG(source_stat.st_mode) and not source.is_symlink(),
        "RUNTIME_PROVENANCE_INVALID",
        "RUNTIME_PROVENANCE",
    )
    return resolved.parents[1]


def stable_regular_file_bytes(path: Path) -> bytes:
    """Read one bounded regular file without following its final symlink."""

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise Hold("RUNTIME_PROVENANCE_INVALID", "RUNTIME_PROVENANCE") from exc
    try:
        before = os.fstat(descriptor)
        need(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and 0 < before.st_size <= MAX_JSON_BYTES * 8,
            "RUNTIME_PROVENANCE_INVALID",
            "RUNTIME_PROVENANCE",
        )
        chunks: list[bytes] = []
        total = 0
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            total += len(block)
            need(
                total <= MAX_JSON_BYTES * 8,
                "RUNTIME_PROVENANCE_INVALID",
                "RUNTIME_PROVENANCE",
            )
            chunks.append(block)
        after = os.fstat(descriptor)
        need(
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and total == before.st_size,
            "RUNTIME_PROVENANCE_INVALID",
            "RUNTIME_PROVENANCE",
        )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def stable_relative_sha256(relative: str) -> str:
    need(
        relative and not relative.startswith("/") and ".." not in Path(relative).parts,
        "RUNTIME_PROVENANCE_INVALID",
        "RUNTIME_PROVENANCE",
    )
    candidate = repository_root() / relative
    need(
        not candidate.is_symlink(),
        "RUNTIME_PROVENANCE_INVALID",
        "RUNTIME_PROVENANCE",
    )
    return sha256_bytes(stable_regular_file_bytes(candidate))


def procedure_contract_sha256() -> str:
    raw = stable_regular_file_bytes(repository_root() / CONTRACT_DOCUMENT_RELATIVE)
    need(
        raw.count(PROCEDURE_BEGIN) == 1 and raw.count(PROCEDURE_END) == 1,
        "RUNTIME_PROVENANCE_INVALID",
        "RUNTIME_PROVENANCE",
    )
    section = raw.split(PROCEDURE_BEGIN, 1)[1].split(PROCEDURE_END, 1)[0]
    prefix = b"\n~~~text\n"
    suffix = b"~~~\n\n"
    need(
        section.startswith(prefix) and section.endswith(suffix),
        "RUNTIME_PROVENANCE_INVALID",
        "RUNTIME_PROVENANCE",
    )
    body = section[len(prefix) : -len(suffix)]
    need(
        body.endswith(b"\n") and b"\r" not in body,
        "RUNTIME_PROVENANCE_INVALID",
        "RUNTIME_PROVENANCE",
    )
    return sha256_bytes(body)


def clean_text(value: object, error: str, stage: str) -> str:
    need(isinstance(value, str) and bool(value), error, stage)
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise Hold(error, stage) from exc
    need(len(encoded) <= MAX_TEXT_BYTES, error, stage)
    need(unicodedata.normalize("NFC", value) == value, error, stage)
    need(not any(ord(char) < 32 or ord(char) == 127 for char in value), error, stage)
    return value


def parse_utc(value: object, stage: str) -> datetime:
    need(
        isinstance(value, str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is not None,
        "AUTHORIZATION_BINDING_MISMATCH",
        stage,
    )
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise Hold("AUTHORIZATION_BINDING_MISMATCH", stage) from exc


def validate_no_forbidden_keys(value: object, stage: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            need(isinstance(key, str), "INTERNAL_FAILURE", stage)
            need(FORBIDDEN_KEY.search(key) is None, "INTERNAL_FAILURE", stage)
            validate_no_forbidden_keys(child, stage)
    elif isinstance(value, (list, tuple)):
        for child in value:
            validate_no_forbidden_keys(child, stage)


@dataclass(frozen=True)
class ProviderConnectionTuple:
    database: str
    hostname: str
    port: int


@dataclass(frozen=True)
class DatabaseObservedIdentity:
    database: str
    server_address: str
    port: int


@dataclass(frozen=True)
class ProviderSnapshot:
    service_identifier_sha256: str
    target_contract_identity_sha256: str
    target_identity: ProviderConnectionTuple
    production_identity: ProviderConnectionTuple
    staging_identity: ProviderConnectionTuple
    target_resolved_server_addresses: tuple[str, ...]
    status: str
    created_at_utc: str
    observed_at_utc: str
    application_attachment_count: int
    open_connection_count: int
    inbound_ip_rules: tuple[str, ...]
    public_external_access_blocked: bool
    observation_receipt_sha256: str
    cleanup_receipt_sha256: str | None = None
    fixture_only: bool = False


@dataclass(frozen=True)
class EphemeralConnectionMaterial:
    provider_identity: ProviderConnectionTuple
    opaque_material: object = field(repr=False, compare=False)
    fixture_only: bool = False


@dataclass(frozen=True)
class TlsReadOnlyContract:
    sslmode: str = "verify-full"
    verify_hostname: bool = True
    verify_certificate: bool = True
    connect_timeout_seconds: int = CONNECT_TIMEOUT_SECONDS
    session_default_read_only: bool = True
    begin_read_only: bool = True
    search_path: str = "pg_catalog"
    statement_timeout_ms: int = 5000
    lock_timeout_ms: int = 1000
    idle_transaction_timeout_ms: int = 5000


@dataclass(frozen=True)
class ExecutionAuthorization:
    authorization_record_sha256: str
    adapter_sha256: str
    reviewer_sha256: str
    operational_collection_procedure_contract_sha256: str
    runtime_observation_schema_sha256: str
    sanitized_result_schema_sha256: str
    package_manifest_sha256: str
    repository_commit_oid: str
    repository_tree_oid: str
    invocation_sha256: str
    operator_run_id_sha256: str
    operator_ipv4_cidr_32_sha256: str
    target_service_identifier_sha256: str
    target_contract_identity_sha256: str
    expected_target_provider_identity_sha256: str
    expected_production_provider_identity_sha256: str
    expected_staging_provider_identity_sha256: str
    execution_harness_sha256: str
    render_port_implementation_sha256: str
    database_port_implementation_sha256: str
    attempt_ledger_implementation_sha256: str
    supervisor_implementation_sha256: str
    runtime_provenance_implementation_sha256: str
    runtime_provenance_hmac_key_id_sha256: str
    dependency_set_sha256: str
    independent_attestation_signer_implementation_sha256: str
    ledger_hmac_key_id_sha256: str
    independent_attestation_hmac_key_id_sha256: str
    live_execution_authorized: bool
    collection_attempt_limit: int
    collection_attempts_consumed: int


@dataclass(frozen=True)
class AttemptReceipt:
    binding_sha256: str
    receipt_sha256: str
    state: str
    sequence: int
    atomic: bool
    durable: bool
    authenticated: bool
    prior_attempt_count: int
    fixture_only: bool


@dataclass(frozen=True)
class CleanupSupervisorReceipt:
    binding_sha256: str
    receipt_sha256: str
    state: str
    authenticated: bool
    durable: bool
    fixture_only: bool


@dataclass(frozen=True)
class DatabaseExecutionEvidence:
    target_provider_identity_sha256: str
    observed_server_address: str
    provider_resolved_server_addresses: tuple[str, ...]
    sslmode: str
    hostname_verified: bool
    certificate_verified: bool
    connect_timeout_seconds: int
    session_default_read_only: bool
    begin_read_only: bool
    transaction_read_only_verified: bool
    search_path: str
    statement_timeout_ms: int
    lock_timeout_ms: int
    idle_transaction_timeout_ms: int
    fixed_sql_statement_ids: tuple[str, ...]
    fixed_sql_trace_sha256: str
    receipt_sha256: str
    fixture_only: bool


@dataclass(frozen=True)
class RuntimeProvenance:
    authorization_record_sha256: str
    adapter_sha256: str
    reviewer_sha256: str
    operational_collection_procedure_contract_sha256: str
    runtime_observation_schema_sha256: str
    sanitized_result_schema_sha256: str
    package_manifest_sha256: str
    repository_commit_oid: str
    repository_tree_oid: str
    invocation_sha256: str
    execution_harness_sha256: str
    render_port_implementation_sha256: str
    database_port_implementation_sha256: str
    attempt_ledger_implementation_sha256: str
    supervisor_implementation_sha256: str
    runtime_provenance_implementation_sha256: str
    runtime_provenance_hmac_key_id_sha256: str
    dependency_set_sha256: str
    independent_attestation_signer_implementation_sha256: str
    ledger_hmac_key_id_sha256: str
    independent_attestation_hmac_key_id_sha256: str
    fixed_sql_trace_sha256: str
    tls_readonly_contract_sha256: str
    worktree_clean: bool
    package_paths_regular_nonsymlink: bool
    fixture_only: bool
    observation_receipt_sha256: str
    hmac_sha256: str


class RenderPort(Protocol):
    """Injected, separately reviewed provider control-plane boundary."""

    implementation_sha256: str
    fixture_only: bool

    def observe_target(self) -> ProviderSnapshot: ...

    def add_operator_ipv4_cidr_32(self, cidr: str) -> None: ...

    def get_ephemeral_connection_material(self) -> EphemeralConnectionMaterial: ...

    def remove_operator_ipv4_cidr_32(self, cidr: str) -> None: ...


class DatabasePort(Protocol):
    """Injected DB boundary; implementations must execute only exact FIXED_SQL."""

    implementation_sha256: str
    fixture_only: bool

    def open_readonly(
        self,
        material: EphemeralConnectionMaterial,
        contract: TlsReadOnlyContract,
    ) -> None: ...

    def execute_fixed(
        self,
        statement_id: str,
        sql: str,
    ) -> Sequence[Mapping[str, object]]: ...

    def instrumentation_receipt_sha256(self) -> str: ...

    def execution_evidence(self) -> DatabaseExecutionEvidence: ...

    def rollback_and_close(self) -> None: ...


class AttemptLedgerPort(Protocol):
    """Atomic durable reservation boundary, required before external access."""

    implementation_sha256: str
    fixture_only: bool

    def reserve_once(self, binding_sha256: str) -> AttemptReceipt: ...

    def transition(
        self,
        current: AttemptReceipt,
        new_state: str,
    ) -> AttemptReceipt: ...


class CleanupSupervisorPort(Protocol):
    """Independently authenticated durable cleanup watchdog boundary."""

    implementation_sha256: str
    fixture_only: bool

    def arm_cleanup(
        self,
        binding_sha256: str,
        operator_ipv4_cidr_32: str,
        target_service_identifier_sha256: str,
        target_contract_identity_sha256: str,
    ) -> CleanupSupervisorReceipt: ...

    def confirm_cleanup(
        self,
        armed: CleanupSupervisorReceipt,
        final_observation_receipt_sha256: str,
    ) -> CleanupSupervisorReceipt: ...


class RuntimeProvenancePort(Protocol):
    """Local-only independently authenticated runtime observation boundary."""

    implementation_sha256: str
    fixture_only: bool

    def observe_local_runtime(self) -> RuntimeProvenance: ...


def canonical_provider_identity(value: ProviderConnectionTuple) -> dict[str, object]:
    stage = "PROVIDER_INITIAL_REVALIDATION"
    database = clean_text(value.database, "IDENTITY_DOMAIN_MISMATCH", stage)
    hostname = clean_text(value.hostname, "IDENTITY_DOMAIN_MISMATCH", stage)
    need(hostname == hostname.lower(), "IDENTITY_DOMAIN_MISMATCH", stage)
    need(not hostname.endswith("."), "IDENTITY_DOMAIN_MISMATCH", stage)
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise Hold("IDENTITY_DOMAIN_MISMATCH", stage) from exc
    need(ascii_hostname == hostname, "IDENTITY_DOMAIN_MISMATCH", stage)
    need(len(hostname) <= 253 and "." in hostname, "IDENTITY_DOMAIN_MISMATCH", stage)
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise Hold("IDENTITY_DOMAIN_MISMATCH", stage)
    for label in hostname.split("."):
        need(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            is not None,
            "IDENTITY_DOMAIN_MISMATCH",
            stage,
        )
    need(type(value.port) is int and 1 <= value.port <= 65535, "IDENTITY_DOMAIN_MISMATCH", stage)
    return {
        "database": database,
        "domain": "PROVIDER_CONNECTION_TUPLE_V5",
        "hostname": hostname,
        "port": value.port,
    }


def provider_identity_sha256(value: ProviderConnectionTuple) -> str:
    return sha256_bytes(canonical_json_bytes(canonical_provider_identity(value)))


def canonical_database_identity(value: DatabaseObservedIdentity) -> dict[str, object]:
    stage = "DATABASE_IDENTITY"
    database = clean_text(value.database, "DATABASE_OBSERVATION_INVALID", stage)
    address = clean_text(value.server_address, "DATABASE_OBSERVATION_INVALID", stage)
    try:
        canonical_address = ipaddress.ip_address(address).compressed
    except ValueError as exc:
        raise Hold("DATABASE_OBSERVATION_INVALID", stage) from exc
    need(address == canonical_address, "DATABASE_OBSERVATION_INVALID", stage)
    need(type(value.port) is int and 1 <= value.port <= 65535, "DATABASE_OBSERVATION_INVALID", stage)
    return {
        "database": database,
        "domain": "DATABASE_OBSERVED_IDENTITY_V5",
        "port": value.port,
        "server_address": address,
    }


def database_identity_sha256(value: DatabaseObservedIdentity) -> str:
    return sha256_bytes(canonical_json_bytes(canonical_database_identity(value)))


def normalize_structural_manifest(relations: object) -> bytes:
    stage = "SCHEMA_MANIFEST"
    need(isinstance(relations, list), "DATABASE_OBSERVATION_INVALID", stage)
    need(len(relations) <= MAX_RELATIONS, "DATABASE_OBSERVATION_INVALID", stage)
    normalized: list[dict[str, object]] = []
    exact_seen: set[tuple[str, str, str]] = set()
    folded_seen: set[tuple[str, str, str]] = set()
    for relation in relations:
        need(isinstance(relation, Mapping), "DATABASE_OBSERVATION_INVALID", stage)
        need(
            set(relation) == {"namespace", "name", "kind", "columns"},
            "DATABASE_OBSERVATION_INVALID",
            stage,
        )
        namespace = clean_text(relation["namespace"], "DATABASE_OBSERVATION_INVALID", stage)
        name = clean_text(relation["name"], "DATABASE_OBSERVATION_INVALID", stage)
        kind = clean_text(relation["kind"], "DATABASE_OBSERVATION_INVALID", stage)
        need(kind in {"r", "p", "v", "m", "f", "S"}, "DATABASE_OBSERVATION_INVALID", stage)
        exact_key = (namespace, name, kind)
        folded_key = (namespace.casefold(), name.casefold(), kind)
        need(exact_key not in exact_seen, "DATABASE_OBSERVATION_INVALID", stage)
        need(folded_key not in folded_seen, "DATABASE_OBSERVATION_INVALID", stage)
        exact_seen.add(exact_key)
        folded_seen.add(folded_key)
        columns = relation["columns"]
        need(isinstance(columns, list), "DATABASE_OBSERVATION_INVALID", stage)
        need(len(columns) <= MAX_COLUMNS_PER_RELATION, "DATABASE_OBSERVATION_INVALID", stage)
        normalized_columns: list[dict[str, object]] = []
        ordinal_seen: set[int] = set()
        column_folded_seen: set[str] = set()
        for column in columns:
            need(isinstance(column, Mapping), "DATABASE_OBSERVATION_INVALID", stage)
            need(
                set(column) == {"name", "not_null", "ordinal", "type_oid"},
                "DATABASE_OBSERVATION_INVALID",
                stage,
            )
            column_name = clean_text(column["name"], "DATABASE_OBSERVATION_INVALID", stage)
            ordinal = column["ordinal"]
            type_oid = column["type_oid"]
            not_null = column["not_null"]
            need(type(ordinal) is int and ordinal > 0, "DATABASE_OBSERVATION_INVALID", stage)
            need(type(type_oid) is int and type_oid > 0, "DATABASE_OBSERVATION_INVALID", stage)
            need(type(not_null) is bool, "DATABASE_OBSERVATION_INVALID", stage)
            need(ordinal not in ordinal_seen, "DATABASE_OBSERVATION_INVALID", stage)
            need(column_name.casefold() not in column_folded_seen, "DATABASE_OBSERVATION_INVALID", stage)
            ordinal_seen.add(ordinal)
            column_folded_seen.add(column_name.casefold())
            normalized_columns.append(
                {
                    "name": column_name,
                    "not_null": not_null,
                    "ordinal": ordinal,
                    "type_oid": type_oid,
                }
            )
        normalized_columns.sort(key=lambda item: (int(item["ordinal"]), str(item["name"])))
        need(
            [item["ordinal"] for item in normalized_columns]
            == list(range(1, len(normalized_columns) + 1)),
            "DATABASE_OBSERVATION_INVALID",
            stage,
        )
        normalized.append(
            {
                "columns": normalized_columns,
                "kind": kind,
                "name": name,
                "namespace": namespace,
            }
        )
    normalized.sort(key=lambda item: (str(item["namespace"]), str(item["name"]), str(item["kind"])))
    return canonical_json_bytes({"relations": normalized, "schema": MANIFEST_SCHEMA}) + b"\n"


def manifest_from_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    stage = "SCHEMA_MANIFEST"
    groups: dict[tuple[str, str, str], dict[str, object]] = {}
    expected = {
        "column_name",
        "namespace_name",
        "not_null",
        "ordinal_position",
        "relation_kind",
        "relation_name",
        "type_oid",
    }
    for row in rows:
        need(isinstance(row, Mapping) and set(row) == expected, "DATABASE_OBSERVATION_INVALID", stage)
        namespace = clean_text(row["namespace_name"], "DATABASE_OBSERVATION_INVALID", stage)
        name = clean_text(row["relation_name"], "DATABASE_OBSERVATION_INVALID", stage)
        kind = clean_text(row["relation_kind"], "DATABASE_OBSERVATION_INVALID", stage)
        key = (namespace, name, kind)
        relation = groups.setdefault(
            key,
            {"namespace": namespace, "name": name, "kind": kind, "columns": []},
        )
        if row["column_name"] is None:
            need(
                row["ordinal_position"] is None
                and row["type_oid"] is None
                and row["not_null"] is None,
                "DATABASE_OBSERVATION_INVALID",
                stage,
            )
            continue
        relation_columns = relation["columns"]
        need(isinstance(relation_columns, list), "INTERNAL_FAILURE", stage)
        relation_columns.append(
            {
                "name": row["column_name"],
                "not_null": row["not_null"],
                "ordinal": row["ordinal_position"],
                "type_oid": row["type_oid"],
            }
        )
    return list(groups.values())


def adapter_descriptor() -> dict[str, object]:
    return {
        "database_identity_domain": "DATABASE_OBSERVED_IDENTITY_V5",
        "expected_empty_manifest_sha256": EXPECTED_EMPTY_MANIFEST_SHA256,
        "failure_keys": sorted(FAILURE_KEYS),
        "fixed_sql_trace_sha256": fixed_sql_trace_sha256(),
        "ledger_schema": LEDGER_SCHEMA,
        "provider_identity_domain": "PROVIDER_CONNECTION_TUPLE_V5",
        "result_schema": RESULT_SCHEMA,
        "runtime_observation_keys": sorted(RUNTIME_OBSERVATION_KEYS),
        "schema": "PMAI_P0_04_SRBE_V5_OPERATIONAL_ADAPTER_CONTRACT_V2",
        "success_keys": sorted(SUCCESS_KEYS),
        "tls_mode": "verify-full",
    }


def adapter_contract_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(adapter_descriptor()))


def fixed_sql_trace_sha256() -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "schema": "PMAI_P0_04_SRBE_V5_FIXED_SQL_TRACE_V1",
                "statements": [
                    {
                        "sql_sha256": sha256_bytes(FIXED_SQL[item].encode("ascii")),
                        "statement_id": item,
                    }
                    for item in FIXED_SQL_ORDER
                ],
            }
        )
    )


def tls_readonly_contract_sha256() -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "begin_read_only": True,
                "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
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


def validate_authorization(value: ExecutionAuthorization) -> None:
    stage = "PRECHECK"
    for item in (
        value.authorization_record_sha256,
        value.adapter_sha256,
        value.reviewer_sha256,
        value.operational_collection_procedure_contract_sha256,
        value.runtime_observation_schema_sha256,
        value.sanitized_result_schema_sha256,
        value.package_manifest_sha256,
        value.invocation_sha256,
        value.operator_run_id_sha256,
        value.operator_ipv4_cidr_32_sha256,
        value.target_service_identifier_sha256,
        value.target_contract_identity_sha256,
        value.expected_target_provider_identity_sha256,
        value.expected_production_provider_identity_sha256,
        value.expected_staging_provider_identity_sha256,
        value.execution_harness_sha256,
        value.render_port_implementation_sha256,
        value.database_port_implementation_sha256,
        value.attempt_ledger_implementation_sha256,
        value.supervisor_implementation_sha256,
        value.runtime_provenance_implementation_sha256,
        value.runtime_provenance_hmac_key_id_sha256,
        value.dependency_set_sha256,
        value.independent_attestation_signer_implementation_sha256,
        value.ledger_hmac_key_id_sha256,
        value.independent_attestation_hmac_key_id_sha256,
    ):
        safe_sha256(item, stage)
    hmac_key_ids = (
        value.ledger_hmac_key_id_sha256,
        value.runtime_provenance_hmac_key_id_sha256,
        value.independent_attestation_hmac_key_id_sha256,
    )
    need(
        len(set(hmac_key_ids)) == len(hmac_key_ids),
        "AUTHORIZATION_INVALID",
        stage,
    )
    need(
        is_git_oid(value.repository_commit_oid)
        and is_git_oid(value.repository_tree_oid),
        "AUTHORIZATION_INVALID",
        stage,
    )
    need(type(value.live_execution_authorized) is bool, "AUTHORIZATION_INVALID", stage)
    need(value.live_execution_authorized is True, "AUTHORIZATION_INVALID", stage)
    need(value.collection_attempt_limit == 1, "AUTHORIZATION_INVALID", stage)
    need(value.collection_attempts_consumed == 0, "AUTHORIZATION_INVALID", stage)
    need(
        stable_relative_sha256(ADAPTER_RELATIVE) == value.adapter_sha256,
        "AUTHORIZATION_BINDING_MISMATCH",
        stage,
    )
    local_bindings = {
        "reviewer_sha256": stable_relative_sha256(REVIEWER_RELATIVE),
        "runtime_observation_schema_sha256": stable_relative_sha256(
            RUNTIME_SCHEMA_RELATIVE
        ),
        "sanitized_result_schema_sha256": stable_relative_sha256(
            RESULT_SCHEMA_RELATIVE
        ),
        "package_manifest_sha256": stable_relative_sha256(
            PACKAGE_MANIFEST_RELATIVE
        ),
        "operational_collection_procedure_contract_sha256": (
            procedure_contract_sha256()
        ),
    }
    for field_name, observed in local_bindings.items():
        need(
            observed == getattr(value, field_name),
            "AUTHORIZATION_BINDING_MISMATCH",
            "RUNTIME_PROVENANCE",
        )


def attempt_binding_sha256(
    value: ExecutionAuthorization,
    runtime_provenance_observation_receipt_sha256: str,
) -> str:
    safe_sha256(runtime_provenance_observation_receipt_sha256, "RUNTIME_PROVENANCE")
    return sha256_bytes(
        canonical_json_bytes(
            {
                "adapter_sha256": value.adapter_sha256,
                "attempt_ledger_implementation_sha256": value.attempt_ledger_implementation_sha256,
                "authorization_record_sha256": value.authorization_record_sha256,
                "collection_attempt_limit": value.collection_attempt_limit,
                "collection_attempts_consumed": value.collection_attempts_consumed,
                "database_port_implementation_sha256": value.database_port_implementation_sha256,
                "dependency_set_sha256": value.dependency_set_sha256,
                "execution_harness_sha256": value.execution_harness_sha256,
                "expected_production_provider_identity_sha256": value.expected_production_provider_identity_sha256,
                "expected_staging_provider_identity_sha256": value.expected_staging_provider_identity_sha256,
                "expected_target_provider_identity_sha256": value.expected_target_provider_identity_sha256,
                "fixed_sql_trace_sha256": fixed_sql_trace_sha256(),
                "independent_attestation_hmac_key_id_sha256": value.independent_attestation_hmac_key_id_sha256,
                "independent_attestation_signer_implementation_sha256": value.independent_attestation_signer_implementation_sha256,
                "invocation_sha256": value.invocation_sha256,
                "ledger_hmac_key_id_sha256": value.ledger_hmac_key_id_sha256,
                "operational_collection_procedure_contract_sha256": (
                    value.operational_collection_procedure_contract_sha256
                ),
                "operator_ipv4_cidr_32_sha256": value.operator_ipv4_cidr_32_sha256,
                "operator_run_id_sha256": value.operator_run_id_sha256,
                "package_manifest_sha256": value.package_manifest_sha256,
                "render_port_implementation_sha256": value.render_port_implementation_sha256,
                "repository_commit_oid": value.repository_commit_oid,
                "repository_tree_oid": value.repository_tree_oid,
                "reviewer_sha256": value.reviewer_sha256,
                "runtime_provenance_implementation_sha256": value.runtime_provenance_implementation_sha256,
                "runtime_provenance_hmac_key_id_sha256": value.runtime_provenance_hmac_key_id_sha256,
                "runtime_provenance_observation_receipt_sha256": runtime_provenance_observation_receipt_sha256,
                "runtime_observation_schema_sha256": value.runtime_observation_schema_sha256,
                "sanitized_result_schema_sha256": value.sanitized_result_schema_sha256,
                "schema": "PMAI_P0_04_SRBE_V5_ATTEMPT_BINDING_V2",
                "supervisor_implementation_sha256": value.supervisor_implementation_sha256,
                "target_contract_identity_sha256": value.target_contract_identity_sha256,
                "target_service_identifier_sha256": value.target_service_identifier_sha256,
                "tls_readonly_contract_sha256": tls_readonly_contract_sha256(),
            }
        )
    )


def runtime_provenance_payload(value: RuntimeProvenance) -> dict[str, object]:
    """Canonical authenticated payload; receipt and HMAC are derived fields."""

    return {
        "adapter_sha256": value.adapter_sha256,
        "attempt_ledger_implementation_sha256": value.attempt_ledger_implementation_sha256,
        "authorization_record_sha256": value.authorization_record_sha256,
        "database_port_implementation_sha256": value.database_port_implementation_sha256,
        "dependency_set_sha256": value.dependency_set_sha256,
        "execution_harness_sha256": value.execution_harness_sha256,
        "fixture_only": value.fixture_only,
        "fixed_sql_trace_sha256": value.fixed_sql_trace_sha256,
        "independent_attestation_hmac_key_id_sha256": value.independent_attestation_hmac_key_id_sha256,
        "independent_attestation_signer_implementation_sha256": value.independent_attestation_signer_implementation_sha256,
        "invocation_sha256": value.invocation_sha256,
        "ledger_hmac_key_id_sha256": value.ledger_hmac_key_id_sha256,
        "operational_collection_procedure_contract_sha256": value.operational_collection_procedure_contract_sha256,
        "package_manifest_sha256": value.package_manifest_sha256,
        "package_paths_regular_nonsymlink": value.package_paths_regular_nonsymlink,
        "render_port_implementation_sha256": value.render_port_implementation_sha256,
        "repository_commit_oid": value.repository_commit_oid,
        "repository_tree_oid": value.repository_tree_oid,
        "reviewer_sha256": value.reviewer_sha256,
        "runtime_observation_schema_sha256": value.runtime_observation_schema_sha256,
        "runtime_provenance_hmac_key_id_sha256": value.runtime_provenance_hmac_key_id_sha256,
        "runtime_provenance_implementation_sha256": value.runtime_provenance_implementation_sha256,
        "sanitized_result_schema_sha256": value.sanitized_result_schema_sha256,
        "schema": "PMAI_P0_04_SRBE_V5_RUNTIME_PROVENANCE_PAYLOAD_V1",
        "supervisor_implementation_sha256": value.supervisor_implementation_sha256,
        "tls_readonly_contract_sha256": value.tls_readonly_contract_sha256,
        "worktree_clean": value.worktree_clean,
    }


def clear_bytearray(value: object) -> None:
    if type(value) is bytearray:
        try:
            for index in range(len(value)):
                value[index] = 0
        except BaseException:
            pass


def validate_runtime_provenance_hmac(
    value: RuntimeProvenance,
    authorization: ExecutionAuthorization,
    provenance_hmac_key: bytearray,
) -> None:
    stage = "RUNTIME_PROVENANCE"
    try:
        need(
            isinstance(value, RuntimeProvenance),
            "RUNTIME_PROVENANCE_INVALID",
            stage,
        )
        need(
            type(provenance_hmac_key) is bytearray
            and len(provenance_hmac_key) == RUNTIME_PROVENANCE_HMAC_KEY_BYTES
            and any(provenance_hmac_key),
            "RUNTIME_PROVENANCE_INVALID",
            stage,
        )
        observed_key_id = hashlib.sha256(provenance_hmac_key).hexdigest()
        safe_sha256(
            value.runtime_provenance_hmac_key_id_sha256,
            stage,
        )
        need(
            hmac.compare_digest(
                observed_key_id,
                authorization.runtime_provenance_hmac_key_id_sha256,
            )
            and hmac.compare_digest(
                value.runtime_provenance_hmac_key_id_sha256,
                authorization.runtime_provenance_hmac_key_id_sha256,
            ),
            "RUNTIME_PROVENANCE_INVALID",
            stage,
        )
        payload = canonical_json_bytes(runtime_provenance_payload(value))
        expected_receipt = sha256_bytes(payload)
        safe_sha256(value.observation_receipt_sha256, stage)
        need(
            hmac.compare_digest(
                value.observation_receipt_sha256,
                expected_receipt,
            ),
            "RUNTIME_PROVENANCE_INVALID",
            stage,
        )
        safe_sha256(value.hmac_sha256, stage)
        expected_hmac = hmac.new(
            provenance_hmac_key,
            RUNTIME_PROVENANCE_HMAC_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest()
        need(
            hmac.compare_digest(value.hmac_sha256, expected_hmac),
            "RUNTIME_PROVENANCE_INVALID",
            stage,
        )
    finally:
        clear_bytearray(provenance_hmac_key)


def validate_runtime_provenance(
    value: RuntimeProvenance,
    authorization: ExecutionAuthorization,
    *,
    fixture_only: bool,
) -> None:
    stage = "RUNTIME_PROVENANCE"
    need(isinstance(value, RuntimeProvenance), "RUNTIME_PROVENANCE_INVALID", stage)
    expected = {
        "authorization_record_sha256": authorization.authorization_record_sha256,
        "adapter_sha256": authorization.adapter_sha256,
        "reviewer_sha256": authorization.reviewer_sha256,
        "operational_collection_procedure_contract_sha256": authorization.operational_collection_procedure_contract_sha256,
        "runtime_observation_schema_sha256": authorization.runtime_observation_schema_sha256,
        "sanitized_result_schema_sha256": authorization.sanitized_result_schema_sha256,
        "package_manifest_sha256": authorization.package_manifest_sha256,
        "repository_commit_oid": authorization.repository_commit_oid,
        "repository_tree_oid": authorization.repository_tree_oid,
        "invocation_sha256": authorization.invocation_sha256,
        "execution_harness_sha256": authorization.execution_harness_sha256,
        "render_port_implementation_sha256": authorization.render_port_implementation_sha256,
        "database_port_implementation_sha256": authorization.database_port_implementation_sha256,
        "attempt_ledger_implementation_sha256": authorization.attempt_ledger_implementation_sha256,
        "supervisor_implementation_sha256": authorization.supervisor_implementation_sha256,
        "runtime_provenance_implementation_sha256": authorization.runtime_provenance_implementation_sha256,
        "runtime_provenance_hmac_key_id_sha256": authorization.runtime_provenance_hmac_key_id_sha256,
        "dependency_set_sha256": authorization.dependency_set_sha256,
        "independent_attestation_signer_implementation_sha256": authorization.independent_attestation_signer_implementation_sha256,
        "ledger_hmac_key_id_sha256": authorization.ledger_hmac_key_id_sha256,
        "independent_attestation_hmac_key_id_sha256": authorization.independent_attestation_hmac_key_id_sha256,
        "fixed_sql_trace_sha256": fixed_sql_trace_sha256(),
        "tls_readonly_contract_sha256": tls_readonly_contract_sha256(),
    }
    for field_name, expected_value in expected.items():
        need(
            getattr(value, field_name) == expected_value,
            "RUNTIME_PROVENANCE_INVALID",
            stage,
        )
    need(
        value.worktree_clean is True
        and value.package_paths_regular_nonsymlink is True,
        "RUNTIME_PROVENANCE_INVALID",
        stage,
    )
    need(
        type(value.fixture_only) is bool and value.fixture_only is fixture_only,
        "RUNTIME_PROVENANCE_INVALID",
        stage,
    )
    safe_sha256(value.observation_receipt_sha256, stage)
    safe_sha256(value.hmac_sha256, stage)


def validate_operator_cidr(
    value: object,
    authorization: ExecutionAuthorization,
) -> str:
    need(isinstance(value, str), "AUTHORIZATION_INVALID", "PRECHECK")
    try:
        network = ipaddress.ip_network(value, strict=True)
    except ValueError as exc:
        raise Hold("AUTHORIZATION_INVALID", "PRECHECK") from exc
    need(
        isinstance(network, ipaddress.IPv4Network) and network.prefixlen == 32,
        "AUTHORIZATION_INVALID",
        "PRECHECK",
    )
    need(str(network) == value, "AUTHORIZATION_INVALID", "PRECHECK")
    need(
        sha256_bytes(value.encode("ascii"))
        == authorization.operator_ipv4_cidr_32_sha256,
        "AUTHORIZATION_BINDING_MISMATCH",
        "PRECHECK",
    )
    return value


def validate_attempt_receipt(
    receipt: AttemptReceipt,
    binding: str,
    expected_state: str,
) -> None:
    stage = "ATTEMPT_RESERVATION" if expected_state == "RESERVED" else "ATTEMPT_FINALIZATION"
    need(receipt.binding_sha256 == binding, "ATTEMPT_LEDGER_UNCERTAIN", stage)
    need(is_sha256(receipt.receipt_sha256), "ATTEMPT_LEDGER_UNCERTAIN", stage)
    need(receipt.state == expected_state, "ATTEMPT_LEDGER_UNCERTAIN", stage)
    need(type(receipt.sequence) is int and receipt.sequence >= 0, "ATTEMPT_LEDGER_UNCERTAIN", stage)
    need(
        receipt.atomic is True
        and receipt.durable is True
        and receipt.authenticated is True,
        "ATTEMPT_LEDGER_UNCERTAIN",
        stage,
    )
    need(type(receipt.fixture_only) is bool, "ATTEMPT_LEDGER_UNCERTAIN", stage)
    need(receipt.prior_attempt_count == 0, "ATTEMPT_ALREADY_CONSUMED", stage)


class SyntheticReferenceFileAttemptLedger:
    """Synthetic-only crash model; never a future live ledger implementation.

    A leftover ``.next`` file is treated as uncertainty and is never repaired or
    retried automatically.  It is deliberately unauthenticated on disk and is
    rejected by the public live path through ``fixture_only=True``.
    """

    implementation_sha256 = sha256_bytes(
        b"PMAI_P0_04_SRBE_V5_SYNTHETIC_REFERENCE_LEDGER_V1"
    )
    fixture_only = True

    def __init__(self, path: Path) -> None:
        self.path = path
        self.next_path = path.with_name(path.name + ".next")

    def _validate_location(self) -> Path:
        need(self.path.is_absolute(), "ATTEMPT_LEDGER_UNAVAILABLE", "ATTEMPT_RESERVATION")
        try:
            parent = self.path.parent.resolve(strict=True)
        except OSError as exc:
            raise Hold("ATTEMPT_LEDGER_UNAVAILABLE", "ATTEMPT_RESERVATION") from exc
        need(parent.is_dir() and not parent.is_symlink(), "ATTEMPT_LEDGER_UNAVAILABLE", "ATTEMPT_RESERVATION")
        need(self.path == parent / self.path.name, "ATTEMPT_LEDGER_UNAVAILABLE", "ATTEMPT_RESERVATION")
        repository_root = Path(__file__).resolve().parents[1]
        try:
            self.path.relative_to(repository_root)
        except ValueError:
            pass
        else:
            raise Hold("ATTEMPT_LEDGER_UNAVAILABLE", "ATTEMPT_RESERVATION")
        return parent

    @staticmethod
    def _record(binding: str, state: str, sequence: int) -> dict[str, object]:
        return {
            "binding_sha256": binding,
            "schema": LEDGER_SCHEMA,
            "sequence": sequence,
            "state": state,
        }

    @staticmethod
    def _receipt(record: Mapping[str, object]) -> AttemptReceipt:
        return AttemptReceipt(
            binding_sha256=str(record["binding_sha256"]),
            receipt_sha256=sha256_bytes(canonical_json_bytes(record)),
            state=str(record["state"]),
            sequence=int(record["sequence"]),
            atomic=True,
            durable=True,
            authenticated=True,
            prior_attempt_count=0,
            fixture_only=True,
        )

    @staticmethod
    def _write_exclusive(path: Path, record: Mapping[str, object]) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        payload = canonical_json_bytes(record) + b"\n"
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError as exc:
            raise Hold("ATTEMPT_ALREADY_CONSUMED", "ATTEMPT_RESERVATION") from exc
        except OSError as exc:
            raise Hold("ATTEMPT_LEDGER_UNAVAILABLE", "ATTEMPT_RESERVATION") from exc
        try:
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

    @staticmethod
    def _sync_directory(parent: Path) -> None:
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        descriptor = os.open(parent, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _read(self) -> dict[str, object]:
        need(self.path.is_file() and not self.path.is_symlink(), "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        try:
            ledger_stat = self.path.stat()
        except OSError as exc:
            raise Hold("ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION") from exc
        need(stat.S_ISREG(ledger_stat.st_mode), "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(stat.S_IMODE(ledger_stat.st_mode) == 0o600, "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(not self.next_path.exists(), "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        try:
            raw = self.path.read_bytes()
            need(len(raw) <= 4096 and raw.endswith(b"\n"), "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
            value = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise Hold("ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION") from exc
        need(isinstance(value, dict), "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(set(value) == {"binding_sha256", "schema", "sequence", "state"}, "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(value["schema"] == LEDGER_SCHEMA, "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(value["state"] in LEDGER_STATES, "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(is_sha256(value["binding_sha256"]), "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(type(value["sequence"]) is int and value["sequence"] >= 0, "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        return value

    def reserve_once(self, binding_sha256: str) -> AttemptReceipt:
        parent = self._validate_location()
        need(not self.next_path.exists(), "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_RESERVATION")
        record = self._record(binding_sha256, "RESERVED", 0)
        self._write_exclusive(self.path, record)
        self._sync_directory(parent)
        return self._receipt(record)

    def transition(self, current: AttemptReceipt, new_state: str) -> AttemptReceipt:
        parent = self._validate_location()
        need(new_state in LEDGER_STATES and new_state != "RESERVED", "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        record = self._read()
        observed = self._receipt(record)
        need(observed == current, "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(
            new_state in LEDGER_ALLOWED_TRANSITIONS[current.state],
            "ATTEMPT_LEDGER_UNCERTAIN",
            "ATTEMPT_FINALIZATION",
        )
        updated = self._record(current.binding_sha256, new_state, current.sequence + 1)
        try:
            self._write_exclusive(self.next_path, updated)
            os.replace(self.next_path, self.path)
            self._sync_directory(parent)
        except Hold as exc:
            if exc.error_code == "ATTEMPT_ALREADY_CONSUMED":
                raise Hold("ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION") from exc
            raise
        except OSError as exc:
            raise Hold("ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION") from exc
        return self._receipt(updated)


def failure_envelope(
    error_code: str,
    stage_code: str,
    *,
    attempt_reserved: bool = False,
    cleanup_required: bool = False,
    cleanup_completed: bool = False,
    final_network_state_verified: bool = False,
    attempt_state: str = "KNOWN_NOT_STARTED",
) -> dict[str, object]:
    if error_code not in ERROR_CODES:
        error_code = "INTERNAL_FAILURE"
    if stage_code not in STAGE_CODES:
        stage_code = "PRECHECK"
    if attempt_reserved and attempt_state == "KNOWN_NOT_STARTED":
        attempt_state = "CONSUMED"
    if attempt_state not in ATTEMPT_STATES:
        attempt_state = "UNCERTAIN"
    if attempt_state == "UNCERTAIN":
        attempt_reserved = True
        cleanup_required = True
        cleanup_completed = False
        final_network_state_verified = False
    result: dict[str, object] = {
        "attempt_state": attempt_state,
        "attempt_reserved": bool(attempt_reserved),
        "cleanup_completed": bool(cleanup_completed),
        "cleanup_required": bool(cleanup_required),
        "collection_attempt_consumed": attempt_state != "KNOWN_NOT_STARTED",
        "error_code": error_code,
        "final_network_state_verified": bool(final_network_state_verified),
        "hold": True,
        "outcome": "HOLD",
        "raw_connection_values_disclosed": False,
        "runtime_evidence_emitted": False,
        "schema": RESULT_SCHEMA,
        "stage_code": stage_code,
        "state_provenance": "ADAPTER_STATE_MACHINE",
    }
    validate_failure_envelope(result)
    return result


def validate_failure_envelope(value: Mapping[str, object]) -> None:
    need(set(value) == FAILURE_KEYS, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(value["schema"] == RESULT_SCHEMA and value["outcome"] == "HOLD", "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(value["error_code"] in ERROR_CODES, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(value["stage_code"] in STAGE_CODES, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(value["attempt_state"] in ATTEMPT_STATES, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(
        value["state_provenance"] in STATE_PROVENANCE_VALUES,
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    for key in (
        "attempt_reserved",
        "cleanup_completed",
        "cleanup_required",
        "collection_attempt_consumed",
        "final_network_state_verified",
        "hold",
        "raw_connection_values_disclosed",
        "runtime_evidence_emitted",
    ):
        need(type(value[key]) is bool, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(value["hold"] is True, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    if value["state_provenance"] == "ADAPTER_STATE_MACHINE":
        if value["attempt_state"] == "KNOWN_NOT_STARTED":
            need(
                value["attempt_reserved"] is False
                and value["collection_attempt_consumed"] is False,
                "INTERNAL_FAILURE",
                "OUTPUT_VALIDATION",
            )
            need(
                value["cleanup_required"] is False
                and value["cleanup_completed"] is False
                and value["final_network_state_verified"] is False,
                "INTERNAL_FAILURE",
                "OUTPUT_VALIDATION",
            )
        elif value["attempt_state"] == "CONSUMED":
            need(
                value["attempt_reserved"] is True
                and value["collection_attempt_consumed"] is True,
                "INTERNAL_FAILURE",
                "OUTPUT_VALIDATION",
            )
            need(
                (
                    value["cleanup_required"] is False
                    and value["cleanup_completed"] is False
                    and value["final_network_state_verified"] is False
                )
                or (
                    value["cleanup_required"] is True
                    and value["cleanup_completed"] is False
                    and value["final_network_state_verified"] is False
                )
                or (
                    value["cleanup_required"] is True
                    and value["cleanup_completed"] is True
                    and value["final_network_state_verified"] is True
                ),
                "INTERNAL_FAILURE",
                "OUTPUT_VALIDATION",
            )
        else:
            need(
                value["attempt_reserved"] is True
                and value["collection_attempt_consumed"] is True
                and value["cleanup_required"] is True
                and value["cleanup_completed"] is False
                and value["final_network_state_verified"] is False,
                "INTERNAL_FAILURE",
                "OUTPUT_VALIDATION",
            )
    need(value["runtime_evidence_emitted"] is False, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(value["raw_connection_values_disclosed"] is False, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(not value["cleanup_completed"] or value["cleanup_required"], "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(not value["final_network_state_verified"] or value["cleanup_required"], "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(not value["cleanup_completed"] or value["final_network_state_verified"], "INTERNAL_FAILURE", "OUTPUT_VALIDATION")


def validate_runtime_observation(value: Mapping[str, object]) -> None:
    need(set(value) == RUNTIME_OBSERVATION_KEYS, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(
        value["schema"] == RUNTIME_OBSERVATION_SCHEMA,
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    hash_keys = {
        key for key in RUNTIME_OBSERVATION_KEYS if key.endswith("_sha256")
    } - {"expected_post_restore_schema_manifest_sha256"}
    for key in hash_keys:
        need(is_sha256(value[key]), "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
        need(value[key] not in {"0" * 64, "f" * 64}, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    independently_distinct_hash_keys = hash_keys - {
        "expected_pre_restore_schema_manifest_sha256",
        "pre_restore_schema_manifest_sha256",
    }
    independently_distinct_hashes = [
        value[key] for key in sorted(independently_distinct_hash_keys)
    ]
    need(
        len(independently_distinct_hashes)
        == len(set(independently_distinct_hashes)),
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    need(value["expected_post_restore_schema_manifest_sha256"] == UNBOUND, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    true_keys = {
        "collection_attempt_consumed",
        "final_inbound_ip_rule_set_empty",
        "initial_inbound_ip_rule_set_empty",
        "pre_restore_readonly_collection_complete",
        "public_external_access_blocked",
        "target_application_attachment_count_zero",
        "target_lifecycle_within_72h",
        "target_open_connection_count_zero",
        "target_status_available",
    }
    false_keys = {
        "evidence_complete",
        "post_restore_schema_evidence_collected",
        "raw_connection_values_disclosed",
        "runtime_binding_contract_complete",
        "srbe_collection_evidence_complete",
    }
    for key in true_keys:
        need(value[key] is True, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    for key in false_keys:
        need(value[key] is False, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(type(value["fixture_only"]) is bool, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(
        value["pre_restore_schema_manifest_sha256"] == EXPECTED_EMPTY_MANIFEST_SHA256,
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    need(
        value["expected_pre_restore_schema_manifest_sha256"]
        == EXPECTED_EMPTY_MANIFEST_SHA256,
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    validate_no_forbidden_keys(value, "OUTPUT_VALIDATION")


def validate_success_envelope(value: Mapping[str, object]) -> None:
    need(set(value) == SUCCESS_KEYS, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(
        value["schema"] == RESULT_SCHEMA and value["outcome"] == "SUCCESS",
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    observation = dict(value)
    del observation["outcome"]
    observation["schema"] = RUNTIME_OBSERVATION_SCHEMA
    validate_runtime_observation(observation)


def validate_provider_snapshot(
    snapshot: ProviderSnapshot,
    authorization: ExecutionAuthorization,
    now_utc: datetime,
    expected_rules: tuple[str, ...],
    *,
    final: bool = False,
    fixture_only: bool = False,
) -> tuple[str, str, str]:
    stage = "FINAL_NETWORK_REVALIDATION" if final else "PROVIDER_INITIAL_REVALIDATION"
    need(snapshot.service_identifier_sha256 == authorization.target_service_identifier_sha256, "AUTHORIZATION_BINDING_MISMATCH", stage)
    need(snapshot.target_contract_identity_sha256 == authorization.target_contract_identity_sha256, "AUTHORIZATION_BINDING_MISMATCH", stage)
    target_hash = provider_identity_sha256(snapshot.target_identity)
    production_hash = provider_identity_sha256(snapshot.production_identity)
    staging_hash = provider_identity_sha256(snapshot.staging_identity)
    need(len({target_hash, production_hash, staging_hash}) == 3, "IDENTITY_SEPARATION_FAILED", "PROVIDER_INITIAL_REVALIDATION")
    need(
        target_hash == authorization.expected_target_provider_identity_sha256
        and production_hash
        == authorization.expected_production_provider_identity_sha256
        and staging_hash == authorization.expected_staging_provider_identity_sha256,
        "AUTHORIZATION_BINDING_MISMATCH",
        stage,
    )
    need(
        type(snapshot.fixture_only) is bool
        and snapshot.fixture_only is fixture_only,
        "AUTHORIZATION_BINDING_MISMATCH",
        stage,
    )
    addresses: list[str] = []
    need(snapshot.target_resolved_server_addresses, "IDENTITY_DOMAIN_MISMATCH", stage)
    for address in snapshot.target_resolved_server_addresses:
        clean = clean_text(address, "IDENTITY_DOMAIN_MISMATCH", stage)
        try:
            canonical = ipaddress.ip_address(clean).compressed
        except ValueError as exc:
            raise Hold("IDENTITY_DOMAIN_MISMATCH", stage) from exc
        need(clean == canonical, "IDENTITY_DOMAIN_MISMATCH", stage)
        addresses.append(canonical)
    need(
        tuple(addresses) == tuple(sorted(set(addresses))),
        "IDENTITY_DOMAIN_MISMATCH",
        stage,
    )
    need(snapshot.status == "AVAILABLE", "TARGET_NOT_AVAILABLE", stage)
    need(type(snapshot.application_attachment_count) is int and snapshot.application_attachment_count == 0, "TARGET_ATTACHMENTS_NONZERO", stage)
    need(type(snapshot.open_connection_count) is int and snapshot.open_connection_count == 0, "TARGET_CONNECTIONS_NONZERO", stage)
    need(type(snapshot.public_external_access_blocked) is bool and snapshot.public_external_access_blocked, "FINAL_PUBLIC_ACCESS_NOT_BLOCKED" if final else "PUBLIC_ACCESS_NOT_BLOCKED", stage)
    need(snapshot.inbound_ip_rules == expected_rules, "FINAL_ALLOWLIST_NOT_EMPTY" if final else "INITIAL_ALLOWLIST_NOT_EMPTY", stage)
    safe_sha256(snapshot.observation_receipt_sha256, stage)
    created = parse_utc(snapshot.created_at_utc, stage)
    observed = parse_utc(snapshot.observed_at_utc, stage)
    need(now_utc.tzinfo is not None, "AUTHORIZATION_BINDING_MISMATCH", stage)
    skew = (now_utc.astimezone(timezone.utc) - observed).total_seconds()
    age = (observed - created).total_seconds()
    need(0 <= skew <= MAX_RECHECK_SKEW_SECONDS, "AUTHORIZATION_BINDING_MISMATCH", stage)
    need(0 <= age <= MAX_TARGET_AGE_SECONDS, "TARGET_TOO_OLD", stage)
    if final:
        safe_sha256(snapshot.cleanup_receipt_sha256, stage)
    return target_hash, production_hash, staging_hash


def validate_cleanup_supervisor_receipt(
    value: CleanupSupervisorReceipt,
    binding: str,
    expected_state: str,
    *,
    fixture_only: bool,
) -> None:
    stage = (
        "CLEANUP_SUPERVISOR_ARM"
        if expected_state == "ARMED"
        else "CLEANUP_SUPERVISOR_FINALIZE"
    )
    need(
        isinstance(value, CleanupSupervisorReceipt)
        and value.binding_sha256 == binding
        and value.state == expected_state
        and value.authenticated is True
        and value.durable is True
        and value.fixture_only is fixture_only,
        "CLEANUP_SUPERVISOR_UNCERTAIN",
        stage,
    )
    safe_sha256(value.receipt_sha256, stage)


def validate_database_execution_evidence(
    value: DatabaseExecutionEvidence,
    target_hash: str,
    resolved_addresses: tuple[str, ...],
    *,
    fixture_only: bool,
) -> str:
    stage = "DATABASE_READONLY_SETUP"
    need(
        isinstance(value, DatabaseExecutionEvidence),
        "TLS_NEGOTIATION_INVALID",
        stage,
    )
    need(
        value.target_provider_identity_sha256 == target_hash
        and value.provider_resolved_server_addresses == resolved_addresses,
        "TLS_NEGOTIATION_INVALID",
        stage,
    )
    try:
        observed = ipaddress.ip_address(value.observed_server_address).compressed
    except ValueError as exc:
        raise Hold("TLS_NEGOTIATION_INVALID", stage) from exc
    need(
        observed == value.observed_server_address
        and observed in resolved_addresses,
        "TLS_NEGOTIATION_INVALID",
        stage,
    )
    need(
        value.sslmode == "verify-full"
        and value.hostname_verified is True
        and value.certificate_verified is True
        and value.connect_timeout_seconds == CONNECT_TIMEOUT_SECONDS
        and value.session_default_read_only is True
        and value.begin_read_only is True
        and value.transaction_read_only_verified is True
        and value.search_path == "pg_catalog"
        and value.statement_timeout_ms == 5000
        and value.lock_timeout_ms == 1000
        and value.idle_transaction_timeout_ms == 5000
        and value.fixed_sql_statement_ids == FIXED_SQL_ORDER
        and value.fixed_sql_trace_sha256 == fixed_sql_trace_sha256()
        and value.fixture_only is fixture_only,
        "TLS_NEGOTIATION_INVALID",
        stage,
    )
    safe_sha256(value.receipt_sha256, stage)
    descriptor = {
        "begin_read_only": True,
        "certificate_verified": True,
        "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "fixed_sql_statement_ids": list(FIXED_SQL_ORDER),
        "fixed_sql_trace_sha256": fixed_sql_trace_sha256(),
        "hostname_verified": True,
        "idle_transaction_timeout_ms": 5000,
        "lock_timeout_ms": 1000,
        "observed_server_address": observed,
        "provider_resolved_server_addresses": list(resolved_addresses),
        "receipt_sha256": value.receipt_sha256,
        "fixture_only": fixture_only,
        "schema": "PMAI_P0_04_SRBE_V5_DATABASE_EXECUTION_EVIDENCE_V2",
        "search_path": "pg_catalog",
        "session_default_read_only": True,
        "sslmode": "verify-full",
        "statement_timeout_ms": 5000,
        "target_provider_identity_sha256": target_hash,
        "transaction_read_only_verified": True,
    }
    return sha256_bytes(canonical_json_bytes(descriptor))


def fixed_execute(
    database: DatabasePort,
    statement_id: str,
) -> Sequence[Mapping[str, object]]:
    need(statement_id in FIXED_SQL, "INTERNAL_FAILURE", "DATABASE_READONLY_SETUP")
    try:
        rows = database.execute_fixed(statement_id, FIXED_SQL[statement_id])
    except BaseException as exc:
        raise Hold("DATABASE_READONLY_CONTRACT_FAILED", "DATABASE_READONLY_SETUP") from exc
    need(isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)), "DATABASE_OBSERVATION_INVALID", "DATABASE_READONLY_SETUP")
    return rows


def _collect_once_core(
    authorization: ExecutionAuthorization,
    operator_ipv4_cidr_32: str,
    ledger: AttemptLedgerPort,
    render: RenderPort,
    database: DatabasePort,
    supervisor: CleanupSupervisorPort,
    provenance: RuntimeProvenancePort,
    provenance_hmac_key: bytearray,
    *,
    clock: Callable[[], datetime],
    fixture_only: bool,
) -> dict[str, object]:
    """Private core shared by public-live and synthetic-only entry points."""

    attempt_reserved = False
    attempt_state = "KNOWN_NOT_STARTED"
    cleanup_required = False
    cleanup_completed = False
    final_network_verified = False
    supervisor_confirmed = False
    database_may_be_open = False
    allowlist_may_exist = False
    stage = "PRECHECK"
    error: Hold | None = None
    receipt: AttemptReceipt | None = None
    binding = ""
    success_values: dict[str, object] = {}
    cidr = ""
    baseline_hashes: tuple[str, str, str] | None = None
    initial: ProviderSnapshot | None = None
    after_add: ProviderSnapshot | None = None
    armed_supervisor: CleanupSupervisorReceipt | None = None
    runtime_provenance: RuntimeProvenance | None = None

    try:
        validate_isolated_invocation()
        need(
            ledger is not None
            and render is not None
            and database is not None
            and supervisor is not None
            and provenance is not None,
            "LIVE_PORTS_NOT_INJECTED",
            stage,
        )
        validate_authorization(authorization)
        expected_ports = (
            (ledger, authorization.attempt_ledger_implementation_sha256),
            (render, authorization.render_port_implementation_sha256),
            (database, authorization.database_port_implementation_sha256),
            (supervisor, authorization.supervisor_implementation_sha256),
            (provenance, authorization.runtime_provenance_implementation_sha256),
        )
        for port, expected_implementation in expected_ports:
            need(
                getattr(port, "implementation_sha256", None)
                == expected_implementation
                and getattr(port, "fixture_only", None) is fixture_only,
                "PORT_IMPLEMENTATION_UNBOUND",
                "PRECHECK",
            )
        stage = "RUNTIME_PROVENANCE"
        try:
            runtime_provenance = provenance.observe_local_runtime()
        except BaseException as exc:
            raise Hold("RUNTIME_PROVENANCE_UNAVAILABLE", stage) from exc
        validate_runtime_provenance_hmac(
            runtime_provenance,
            authorization,
            provenance_hmac_key,
        )
        validate_runtime_provenance(
            runtime_provenance,
            authorization,
            fixture_only=fixture_only,
        )
        cidr = validate_operator_cidr(operator_ipv4_cidr_32, authorization)
        binding = attempt_binding_sha256(
            authorization,
            runtime_provenance.observation_receipt_sha256,
        )

        stage = "ATTEMPT_RESERVATION"
        try:
            receipt = ledger.reserve_once(binding)
        except BaseException as exc:
            attempt_state = "UNCERTAIN"
            raise Hold("ATTEMPT_LEDGER_UNCERTAIN", stage) from exc
        validate_attempt_receipt(receipt, binding, "RESERVED")
        need(
            receipt.fixture_only is fixture_only,
            "ATTEMPT_LEDGER_UNCERTAIN",
            stage,
        )
        attempt_reserved = True
        attempt_state = "CONSUMED"

        stage = "PROVIDER_INITIAL_REVALIDATION"
        receipt = ledger.transition(receipt, "PROVIDER_OBSERVE_INTENT")
        validate_attempt_receipt(receipt, binding, "PROVIDER_OBSERVE_INTENT")
        try:
            initial = render.observe_target()
        except BaseException as exc:
            raise Hold("AUTHORIZATION_BINDING_MISMATCH", stage) from exc
        now = clock()
        target_hash, production_hash, staging_hash = validate_provider_snapshot(
            initial,
            authorization,
            now,
            (),
            fixture_only=fixture_only,
        )
        baseline_hashes = (target_hash, production_hash, staging_hash)
        receipt = ledger.transition(receipt, "PROVIDER_VERIFIED")
        validate_attempt_receipt(receipt, binding, "PROVIDER_VERIFIED")

        stage = "CLEANUP_SUPERVISOR_ARM"
        receipt = ledger.transition(receipt, "SUPERVISOR_ARM_INTENT")
        validate_attempt_receipt(receipt, binding, "SUPERVISOR_ARM_INTENT")
        try:
            armed_supervisor = supervisor.arm_cleanup(
                binding,
                cidr,
                authorization.target_service_identifier_sha256,
                authorization.target_contract_identity_sha256,
            )
        except BaseException as exc:
            raise Hold("CLEANUP_SUPERVISOR_UNAVAILABLE", stage) from exc
        validate_cleanup_supervisor_receipt(
            armed_supervisor,
            binding,
            "ARMED",
            fixture_only=fixture_only,
        )
        receipt = ledger.transition(receipt, "SUPERVISOR_ARMED")
        validate_attempt_receipt(receipt, binding, "SUPERVISOR_ARMED")

        stage = "ALLOWLIST_ADD"
        cleanup_required = True
        allowlist_may_exist = True
        receipt = ledger.transition(receipt, "ALLOWLIST_ADD_INTENT")
        validate_attempt_receipt(receipt, binding, "ALLOWLIST_ADD_INTENT")
        try:
            render.add_operator_ipv4_cidr_32(cidr)
        except BaseException as exc:
            raise Hold("ALLOWLIST_ADD_FAILED", stage) from exc

        receipt = ledger.transition(receipt, "ALLOWLIST_ADDED")
        validate_attempt_receipt(receipt, binding, "ALLOWLIST_ADDED")

        stage = "ALLOWLIST_REVALIDATION"
        receipt = ledger.transition(receipt, "ALLOWLIST_REVALIDATE_INTENT")
        validate_attempt_receipt(receipt, binding, "ALLOWLIST_REVALIDATE_INTENT")
        try:
            after_add = render.observe_target()
        except BaseException as exc:
            raise Hold("ALLOWLIST_RECHECK_FAILED", stage) from exc
        after_add_now = clock()
        rechecked_hashes = validate_provider_snapshot(
            after_add,
            authorization,
            after_add_now,
            (cidr,),
            fixture_only=fixture_only,
        )
        need(rechecked_hashes == (target_hash, production_hash, staging_hash), "IDENTITY_DOMAIN_MISMATCH", stage)
        need(
            after_add.observation_receipt_sha256
            != initial.observation_receipt_sha256,
            "INSTRUMENTATION_INCOMPLETE",
            stage,
        )
        receipt = ledger.transition(receipt, "ALLOWLIST_REVALIDATED")
        validate_attempt_receipt(receipt, binding, "ALLOWLIST_REVALIDATED")

        stage = "CONNECTION_MATERIAL"
        receipt = ledger.transition(receipt, "CONNECTION_MATERIAL_INTENT")
        validate_attempt_receipt(receipt, binding, "CONNECTION_MATERIAL_INTENT")
        try:
            material = render.get_ephemeral_connection_material()
        except BaseException as exc:
            raise Hold("CONNECTION_MATERIAL_INVALID", stage) from exc
        need(isinstance(material, EphemeralConnectionMaterial), "CONNECTION_MATERIAL_INVALID", stage)
        need(
            material.fixture_only is fixture_only
            and
            canonical_provider_identity(material.provider_identity)
            == canonical_provider_identity(initial.target_identity),
            "CONNECTION_MATERIAL_INVALID",
            stage,
        )
        receipt = ledger.transition(receipt, "CONNECTION_MATERIAL_ACQUIRED")
        validate_attempt_receipt(receipt, binding, "CONNECTION_MATERIAL_ACQUIRED")

        stage = "DATABASE_CONNECT"
        database_may_be_open = True
        receipt = ledger.transition(receipt, "DATABASE_CONNECT_INTENT")
        validate_attempt_receipt(receipt, binding, "DATABASE_CONNECT_INTENT")
        try:
            database.open_readonly(material, TlsReadOnlyContract())
        except BaseException as exc:
            raise Hold("DATABASE_CONNECT_FAILED", stage) from exc
        receipt = ledger.transition(receipt, "DATABASE_CONNECTED")
        validate_attempt_receipt(receipt, binding, "DATABASE_CONNECTED")

        stage = "DATABASE_READONLY_SETUP"
        for statement in (
            "SET_SESSION_READ_ONLY",
            "BEGIN_READ_ONLY",
            "SET_SEARCH_PATH",
            "SET_STATEMENT_TIMEOUT",
            "SET_LOCK_TIMEOUT",
            "SET_IDLE_TIMEOUT",
        ):
            need(len(fixed_execute(database, statement)) == 0, "DATABASE_READONLY_CONTRACT_FAILED", stage)
        readonly_rows = fixed_execute(database, "VERIFY_READ_ONLY")
        need(
            len(readonly_rows) == 1
            and set(readonly_rows[0]) == {"transaction_read_only"}
            and readonly_rows[0]["transaction_read_only"] == "on",
            "DATABASE_READONLY_CONTRACT_FAILED",
            stage,
        )

        stage = "DATABASE_IDENTITY"
        identity_rows = fixed_execute(database, "DATABASE_IDENTITY")
        need(len(identity_rows) == 1, "DATABASE_OBSERVATION_INVALID", stage)
        identity_row = identity_rows[0]
        need(set(identity_row) == {"database_name", "server_address", "server_port"}, "DATABASE_OBSERVATION_INVALID", stage)
        observed_identity = DatabaseObservedIdentity(
            database=identity_row["database_name"],  # type: ignore[arg-type]
            server_address=identity_row["server_address"],  # type: ignore[arg-type]
            port=identity_row["server_port"],  # type: ignore[arg-type]
        )
        database_identity_hash = database_identity_sha256(observed_identity)
        provider_canonical = canonical_provider_identity(initial.target_identity)
        database_canonical = canonical_database_identity(observed_identity)
        need(
            database_canonical["database"] == provider_canonical["database"]
            and database_canonical["port"] == provider_canonical["port"],
            "IDENTITY_DOMAIN_MISMATCH",
            stage,
        )

        stage = "SCHEMA_MANIFEST"
        schema_rows = fixed_execute(database, "STRUCTURAL_MANIFEST")
        manifest = normalize_structural_manifest(manifest_from_rows(schema_rows))
        manifest_hash = sha256_bytes(manifest)
        need(manifest == EXPECTED_EMPTY_MANIFEST_LINE, "SCHEMA_MANIFEST_MISMATCH", stage)
        need(manifest_hash == EXPECTED_EMPTY_MANIFEST_SHA256, "SCHEMA_MANIFEST_MISMATCH", stage)
        try:
            database_receipt = database.instrumentation_receipt_sha256()
        except BaseException as exc:
            raise Hold("INSTRUMENTATION_INCOMPLETE", stage) from exc
        safe_sha256(database_receipt, stage)
        need(database_receipt != initial.observation_receipt_sha256, "INSTRUMENTATION_INCOMPLETE", stage)
        try:
            database_execution = database.execution_evidence()
        except BaseException as exc:
            raise Hold("TLS_NEGOTIATION_INVALID", "DATABASE_READONLY_SETUP") from exc
        database_execution_hash = validate_database_execution_evidence(
            database_execution,
            target_hash,
            initial.target_resolved_server_addresses,
            fixture_only=fixture_only,
        )
        need(
            database_execution.observed_server_address
            == database_canonical["server_address"],
            "TLS_NEGOTIATION_INVALID",
            "DATABASE_IDENTITY",
        )
        instrumentation_receipt = sha256_bytes(
            canonical_json_bytes(
                {
                    "adapter_sha256": authorization.adapter_sha256,
                    "attempt_binding_sha256": binding,
                    "database_execution_evidence_sha256": database_execution_hash,
                    "database_instrumentation_receipt_sha256": database_receipt,
                    "fixed_sql_trace_sha256": fixed_sql_trace_sha256(),
                    "provider_allowlist_recheck_receipt_sha256": after_add.observation_receipt_sha256,
                    "provider_observation_receipt_sha256": initial.observation_receipt_sha256,
                    "runtime_provenance_observation_receipt_sha256": runtime_provenance.observation_receipt_sha256,
                    "schema": "PMAI_P0_04_SRBE_V5_INSTRUMENTATION_BINDING_V2",
                    "tls_readonly_contract_sha256": tls_readonly_contract_sha256(),
                }
            )
        )
        connection_binding = sha256_bytes(
            canonical_json_bytes(
                {
                    "attempt_binding_sha256": binding,
                    "authorization_record_sha256": authorization.authorization_record_sha256,
                    "database_execution_evidence_sha256": database_execution_hash,
                    "database_observed_identity_sha256": database_identity_hash,
                    "instrumentation_receipt_sha256": instrumentation_receipt,
                    "provider_identity_sha256": target_hash,
                    "runtime_provenance_observation_receipt_sha256": runtime_provenance.observation_receipt_sha256,
                    "schema": "PMAI_P0_04_SRBE_V5_TARGET_CONNECTION_BINDING_V2",
                    "tls_contract_sha256": tls_readonly_contract_sha256(),
                }
            )
        )
        receipt = ledger.transition(receipt, "DATABASE_OBSERVED")
        validate_attempt_receipt(receipt, binding, "DATABASE_OBSERVED")

        success_values = {
            "adapter_contract_sha256": authorization.adapter_sha256,
            "attempt_binding_sha256": binding,
            "authorization_record_sha256": authorization.authorization_record_sha256,
            "cleanup_supervisor_armed_receipt_sha256": armed_supervisor.receipt_sha256,
            "database_execution_evidence_sha256": database_execution_hash,
            "database_observation_sha256": database_receipt,
            "evidence_complete": False,
            "expected_post_restore_schema_manifest_sha256": UNBOUND,
            "expected_pre_restore_schema_manifest_sha256": EXPECTED_EMPTY_MANIFEST_SHA256,
            "fixture_only": fixture_only,
            "fixed_sql_trace_sha256": fixed_sql_trace_sha256(),
            "forbidden_production_provider_identity_sha256": production_hash,
            "forbidden_staging_provider_identity_sha256": staging_hash,
            "initial_inbound_ip_rule_set_empty": True,
            "instrumentation_receipt_sha256": instrumentation_receipt,
            "operational_collection_procedure_contract_sha256": authorization.operational_collection_procedure_contract_sha256,
            "post_restore_schema_evidence_collected": False,
            "pre_restore_readonly_collection_complete": True,
            "pre_restore_schema_manifest_sha256": manifest_hash,
            "provider_observation_sha256": initial.observation_receipt_sha256,
            "public_external_access_blocked": True,
            "raw_connection_values_disclosed": False,
            "reviewer_sha256": authorization.reviewer_sha256,
            "runtime_binding_contract_complete": False,
            "runtime_provenance_observation_receipt_sha256": runtime_provenance.observation_receipt_sha256,
            "schema": RUNTIME_OBSERVATION_SCHEMA,
            "srbe_collection_evidence_complete": False,
            "target_application_attachment_count_zero": True,
            "target_connection_binding_sha256": connection_binding,
            "target_database_observed_identity_sha256": database_identity_hash,
            "target_lifecycle_within_72h": True,
            "target_open_connection_count_zero": True,
            "target_provider_identity_sha256": target_hash,
            "target_status_available": True,
            "tls_readonly_contract_sha256": tls_readonly_contract_sha256(),
        }
    except Hold as exc:
        if exc.error_code in {
            "ATTEMPT_LEDGER_UNAVAILABLE",
            "ATTEMPT_LEDGER_UNCERTAIN",
        }:
            attempt_state = "UNCERTAIN"
        error = exc
    except BaseException:
        if attempt_reserved:
            attempt_state = "UNCERTAIN"
        error = Hold("INTERNAL_FAILURE", stage)
    finally:
        close_ok = not database_may_be_open
        remove_ok = not allowlist_may_exist

        if database_may_be_open:
            stage = "DATABASE_CLOSE"
            if receipt is not None:
                try:
                    receipt = ledger.transition(receipt, "DATABASE_CLOSE_INTENT")
                    validate_attempt_receipt(receipt, binding, "DATABASE_CLOSE_INTENT")
                except BaseException:
                    attempt_state = "UNCERTAIN"
                    error = Hold("ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
            try:
                database.rollback_and_close()
                close_ok = True
                if receipt is not None:
                    receipt = ledger.transition(receipt, "DATABASE_CLOSED")
                    validate_attempt_receipt(receipt, binding, "DATABASE_CLOSED")
            except BaseException:
                close_ok = False
                error = Hold("DATABASE_CLOSE_FAILED", stage)

        if allowlist_may_exist:
            stage = "ALLOWLIST_REMOVE"
            if receipt is not None:
                try:
                    receipt = ledger.transition(receipt, "ALLOWLIST_REMOVE_INTENT")
                    validate_attempt_receipt(receipt, binding, "ALLOWLIST_REMOVE_INTENT")
                except BaseException:
                    attempt_state = "UNCERTAIN"
                    error = Hold("ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
            try:
                render.remove_operator_ipv4_cidr_32(cidr)
                remove_ok = True
                if receipt is not None and close_ok:
                    receipt = ledger.transition(receipt, "ALLOWLIST_REMOVED")
                    validate_attempt_receipt(receipt, binding, "ALLOWLIST_REMOVED")
            except BaseException:
                remove_ok = False
                error = Hold("ALLOWLIST_REMOVE_FAILED", stage)

            stage = "FINAL_NETWORK_REVALIDATION"
            if receipt is not None and remove_ok:
                try:
                    receipt = ledger.transition(receipt, "FINAL_RECHECK_INTENT")
                    validate_attempt_receipt(receipt, binding, "FINAL_RECHECK_INTENT")
                except BaseException:
                    attempt_state = "UNCERTAIN"
                    error = Hold("ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
            try:
                final_snapshot = render.observe_target()
                final_now = clock()
                final_hashes = validate_provider_snapshot(
                    final_snapshot,
                    authorization,
                    final_now,
                    (),
                    final=True,
                    fixture_only=fixture_only,
                )
                need(
                    baseline_hashes is not None
                    and final_hashes == baseline_hashes,
                    "IDENTITY_DOMAIN_MISMATCH",
                    stage,
                )
                need(
                    initial is not None
                    and after_add is not None
                    and final_snapshot.observation_receipt_sha256
                    not in {
                        initial.observation_receipt_sha256,
                        after_add.observation_receipt_sha256,
                    },
                    "INSTRUMENTATION_INCOMPLETE",
                    stage,
                )
                final_network_verified = True
                success_values["cleanup_receipt_sha256"] = final_snapshot.cleanup_receipt_sha256
                success_values["final_inbound_ip_rule_set_empty"] = True
                if receipt is not None and remove_ok:
                    receipt = ledger.transition(receipt, "FINAL_NETWORK_VERIFIED")
                    validate_attempt_receipt(receipt, binding, "FINAL_NETWORK_VERIFIED")
            except BaseException:
                final_network_verified = False
                error = Hold("CLEANUP_UNCERTAIN", stage)

            if final_network_verified and armed_supervisor is not None:
                stage = "CLEANUP_SUPERVISOR_FINALIZE"
                try:
                    if receipt is not None:
                        receipt = ledger.transition(receipt, "SUPERVISOR_CONFIRM_INTENT")
                        validate_attempt_receipt(
                            receipt,
                            binding,
                            "SUPERVISOR_CONFIRM_INTENT",
                        )
                    final_supervisor = supervisor.confirm_cleanup(
                        armed_supervisor,
                        final_snapshot.observation_receipt_sha256,
                    )
                    validate_cleanup_supervisor_receipt(
                        final_supervisor,
                        binding,
                        "CLEANUP_CONFIRMED",
                        fixture_only=fixture_only,
                    )
                    success_values["cleanup_supervisor_final_receipt_sha256"] = (
                        final_supervisor.receipt_sha256
                    )
                    supervisor_confirmed = True
                    if receipt is not None:
                        receipt = ledger.transition(receipt, "SUPERVISOR_CONFIRMED")
                        validate_attempt_receipt(
                            receipt,
                            binding,
                            "SUPERVISOR_CONFIRMED",
                        )
                except BaseException:
                    supervisor_confirmed = False
                    final_network_verified = False
                    error = Hold("CLEANUP_SUPERVISOR_UNCERTAIN", stage)

        cleanup_completed = (
            cleanup_required
            and close_ok
            and remove_ok
            and final_network_verified
            and supervisor_confirmed
        )
        if cleanup_required and not cleanup_completed:
            error = Hold("CLEANUP_UNCERTAIN", "FINAL_NETWORK_REVALIDATION")

    if error is not None:
        if attempt_state != "UNCERTAIN" and attempt_reserved and receipt is not None:
            try:
                final_state = (
                    "FAILED_CLEANED"
                    if not cleanup_required or cleanup_completed
                    else "FAILED_UNCERTAIN"
                )
                receipt = ledger.transition(receipt, final_state)
                validate_attempt_receipt(receipt, binding, final_state)
            except BaseException:
                attempt_state = "UNCERTAIN"
                error = Hold("ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        return failure_envelope(
            error.error_code,
            error.stage_code,
            attempt_reserved=attempt_reserved,
            cleanup_required=cleanup_required,
            cleanup_completed=cleanup_completed,
            final_network_state_verified=final_network_verified,
            attempt_state=attempt_state,
        )

    need(
        receipt is not None
        and cleanup_completed
        and attempt_state == "CONSUMED",
        "CLEANUP_UNCERTAIN",
        "ATTEMPT_FINALIZATION",
    )
    try:
        receipt = ledger.transition(receipt, "COMPLETED")
        validate_attempt_receipt(receipt, binding, "COMPLETED")
    except BaseException:
        return failure_envelope(
            "ATTEMPT_LEDGER_UNCERTAIN",
            "ATTEMPT_FINALIZATION",
            attempt_reserved=True,
            cleanup_required=True,
            cleanup_completed=True,
            final_network_state_verified=True,
            attempt_state="UNCERTAIN",
        )
    success_values["attempt_ledger_receipt_sha256"] = receipt.receipt_sha256
    success_values["collection_attempt_consumed"] = True
    validate_runtime_observation(success_values)
    result = dict(success_values)
    result["outcome"] = "SUCCESS"
    result["schema"] = RESULT_SCHEMA
    validate_success_envelope(result)
    return result


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def collect_once(
    authorization: ExecutionAuthorization,
    operator_ipv4_cidr_32: str,
    ledger: AttemptLedgerPort,
    render: RenderPort,
    database: DatabasePort,
    supervisor: CleanupSupervisorPort,
    provenance: RuntimeProvenancePort,
    provenance_hmac_key: bytearray,
) -> dict[str, object]:
    """Future-live API; its clock is not injectable and fixtures are rejected."""

    try:
        return _collect_once_core(
            authorization,
            operator_ipv4_cidr_32,
            ledger,
            render,
            database,
            supervisor,
            provenance,
            provenance_hmac_key,
            clock=_utc_now,
            fixture_only=False,
        )
    finally:
        clear_bytearray(provenance_hmac_key)


def _collect_once_with_clock(
    authorization: ExecutionAuthorization,
    operator_ipv4_cidr_32: str,
    ledger: AttemptLedgerPort,
    render: RenderPort,
    database: DatabasePort,
    supervisor: CleanupSupervisorPort,
    provenance: RuntimeProvenancePort,
    provenance_hmac_key: bytearray,
    clock: Callable[[], datetime],
) -> dict[str, object]:
    """Synthetic-only API; every successful record is marked fixture-only."""

    try:
        return _collect_once_core(
            authorization,
            operator_ipv4_cidr_32,
            ledger,
            render,
            database,
            supervisor,
            provenance,
            provenance_hmac_key,
            clock=clock,
            fixture_only=True,
        )
    finally:
        clear_bytearray(provenance_hmac_key)


class _FakeLedger:
    implementation_sha256 = sha256_bytes(b"v5-self-test:ledger-implementation")
    fixture_only = True

    def __init__(
        self,
        fail_transition: str | None = None,
        *,
        reserve_uncertain: bool = False,
        events: list[str] | None = None,
    ) -> None:
        self.receipt: AttemptReceipt | None = None
        self.fail_transition = fail_transition
        self.reserve_uncertain = reserve_uncertain
        self.transitions: list[str] = []
        self.events = events if events is not None else []

    def reserve_once(self, binding_sha256: str) -> AttemptReceipt:
        self.events.append("ledger:reserve")
        if self.reserve_uncertain:
            raise RuntimeError("synthetic uncertain reservation")
        if self.receipt is not None:
            raise Hold("ATTEMPT_ALREADY_CONSUMED", "ATTEMPT_RESERVATION")
        self.receipt = AttemptReceipt(
            binding_sha256=binding_sha256,
            receipt_sha256=sha256_bytes((binding_sha256 + ":RESERVED:0").encode("ascii")),
            state="RESERVED",
            sequence=0,
            atomic=True,
            durable=True,
            authenticated=True,
            prior_attempt_count=0,
            fixture_only=True,
        )
        return self.receipt

    def transition(self, current: AttemptReceipt, new_state: str) -> AttemptReceipt:
        if self.fail_transition == new_state:
            raise RuntimeError("synthetic secret password=do-not-emit")
        need(self.receipt == current, "ATTEMPT_LEDGER_UNCERTAIN", "ATTEMPT_FINALIZATION")
        need(
            new_state in LEDGER_ALLOWED_TRANSITIONS[current.state],
            "ATTEMPT_LEDGER_UNCERTAIN",
            "ATTEMPT_FINALIZATION",
        )
        self.transitions.append(new_state)
        self.events.append("ledger:" + new_state)
        self.receipt = AttemptReceipt(
            binding_sha256=current.binding_sha256,
            receipt_sha256=sha256_bytes(
                (current.binding_sha256 + ":" + new_state + ":" + str(current.sequence + 1)).encode("ascii")
            ),
            state=new_state,
            sequence=current.sequence + 1,
            atomic=True,
            durable=True,
            authenticated=True,
            prior_attempt_count=0,
            fixture_only=True,
        )
        return self.receipt


def _digest(label: str) -> str:
    return sha256_bytes(("v5-self-test:" + label).encode("ascii"))


def _synthetic_snapshot(
    rules: tuple[str, ...],
    *,
    final: bool = False,
    status: str = "AVAILABLE",
) -> ProviderSnapshot:
    return ProviderSnapshot(
        service_identifier_sha256=_digest("service"),
        target_contract_identity_sha256=_digest("target-contract"),
        target_identity=ProviderConnectionTuple("fixture_target", "target.example.invalid", 5432),
        production_identity=ProviderConnectionTuple("fixture_production", "production.example.invalid", 5432),
        staging_identity=ProviderConnectionTuple("fixture_staging", "staging.example.invalid", 5432),
        target_resolved_server_addresses=("192.0.2.10",),
        status=status,
        created_at_utc="2026-08-27T00:00:00Z",
        observed_at_utc="2026-08-28T00:00:00Z",
        application_attachment_count=0,
        open_connection_count=0,
        inbound_ip_rules=rules,
        public_external_access_blocked=True,
        observation_receipt_sha256=_digest(
            "provider-final" if final else ("provider-after-add" if rules else "provider-initial")
        ),
        cleanup_receipt_sha256=_digest("cleanup") if final else None,
        fixture_only=True,
    )


class _FakeRender:
    implementation_sha256 = sha256_bytes(b"v5-self-test:render-implementation")
    fixture_only = True

    def __init__(
        self,
        fail_at: str | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.rules: tuple[str, ...] = ()
        self.fail_at = fail_at
        self.observe_count = 0
        self.remove_called = False
        self.add_count = 0
        self.remove_count = 0
        self.events = events if events is not None else []

    def observe_target(self) -> ProviderSnapshot:
        self.observe_count += 1
        self.events.append("render:observe:" + str(self.observe_count))
        label = {1: "observe-initial", 2: "observe-after-add", 3: "observe-final"}.get(
            self.observe_count, "observe-extra"
        )
        if self.fail_at == label:
            raise RuntimeError("synthetic credential=do-not-emit")
        snapshot = _synthetic_snapshot(self.rules, final=self.observe_count >= 3)
        if self.fail_at == "wrong-target":
            snapshot = ProviderSnapshot(
                **{
                    **snapshot.__dict__,
                    "target_identity": ProviderConnectionTuple(
                        "fixture_wrong",
                        "wrong.example.invalid",
                        5432,
                    ),
                }
            )
        elif self.fail_at == "swap-identities":
            snapshot = ProviderSnapshot(
                **{
                    **snapshot.__dict__,
                    "target_identity": snapshot.production_identity,
                    "production_identity": snapshot.target_identity,
                }
            )
        elif self.fail_at == "final-continuity" and self.observe_count >= 3:
            snapshot = ProviderSnapshot(
                **{
                    **snapshot.__dict__,
                    "target_identity": ProviderConnectionTuple(
                        "fixture_changed",
                        "changed.example.invalid",
                        5432,
                    ),
                }
            )
        elif self.fail_at == "stale-clock":
            snapshot = ProviderSnapshot(
                **{**snapshot.__dict__, "observed_at_utc": "2026-08-27T23:00:00Z"}
            )
        elif self.fail_at == "future-clock":
            snapshot = ProviderSnapshot(
                **{**snapshot.__dict__, "observed_at_utc": "2026-08-28T00:10:00Z"}
            )
        return snapshot

    def add_operator_ipv4_cidr_32(self, cidr: str) -> None:
        self.add_count += 1
        self.events.append("render:add")
        if self.fail_at == "add":
            self.rules = (cidr,)
            raise RuntimeError("synthetic secret=do-not-emit")
        self.rules = (cidr,)

    def get_ephemeral_connection_material(self) -> EphemeralConnectionMaterial:
        self.events.append("render:material")
        if self.fail_at == "material":
            raise RuntimeError("postgres://user:password@example.invalid/db")
        return EphemeralConnectionMaterial(
            ProviderConnectionTuple("fixture_target", "target.example.invalid", 5432),
            object(),
            fixture_only=True,
        )

    def remove_operator_ipv4_cidr_32(self, cidr: str) -> None:
        self.remove_called = True
        self.remove_count += 1
        self.events.append("render:remove")
        if self.fail_at == "remove":
            raise RuntimeError("synthetic token=do-not-emit")
        need(self.rules == (cidr,), "ALLOWLIST_REMOVE_FAILED", "ALLOWLIST_REMOVE")
        self.rules = ()


class _FakeDatabase:
    implementation_sha256 = sha256_bytes(b"v5-self-test:database-implementation")
    fixture_only = True

    def __init__(
        self,
        fail_at: str | None = None,
        nonempty: bool = False,
        events: list[str] | None = None,
    ) -> None:
        self.fail_at = fail_at
        self.nonempty = nonempty
        self.opened = False
        self.closed = False
        self.executed: list[str] = []
        self.events = events if events is not None else []

    def open_readonly(self, material: EphemeralConnectionMaterial, contract: TlsReadOnlyContract) -> None:
        del material
        need(contract == TlsReadOnlyContract(), "DATABASE_READONLY_CONTRACT_FAILED", "DATABASE_CONNECT")
        self.opened = True
        self.events.append("database:open")
        if self.fail_at == "open":
            raise RuntimeError("synthetic dsn=do-not-emit")

    def execute_fixed(self, statement_id: str, sql: str) -> Sequence[Mapping[str, object]]:
        need(self.opened and statement_id in FIXED_SQL, "DATABASE_READONLY_CONTRACT_FAILED", "DATABASE_READONLY_SETUP")
        need(sql == FIXED_SQL[statement_id], "DATABASE_READONLY_CONTRACT_FAILED", "DATABASE_READONLY_SETUP")
        self.executed.append(statement_id)
        self.events.append("database:" + statement_id)
        if self.fail_at == statement_id:
            raise RuntimeError("synthetic password=do-not-emit")
        if statement_id == "VERIFY_READ_ONLY":
            return ({"transaction_read_only": "on"},)
        if statement_id == "DATABASE_IDENTITY":
            return (
                {
                    "database_name": "fixture_target",
                    "server_address": "192.0.2.10",
                    "server_port": 5432,
                },
            )
        if statement_id == "STRUCTURAL_MANIFEST" and self.nonempty:
            return (
                {
                    "column_name": "id",
                    "namespace_name": "public",
                    "not_null": True,
                    "ordinal_position": 1,
                    "relation_kind": "r",
                    "relation_name": "unexpected",
                    "type_oid": 23,
                },
            )
        return ()

    def instrumentation_receipt_sha256(self) -> str:
        if self.fail_at == "instrumentation":
            raise RuntimeError("synthetic secret=do-not-emit")
        return _digest("database-instrumentation")

    def execution_evidence(self) -> DatabaseExecutionEvidence:
        evidence = DatabaseExecutionEvidence(
            target_provider_identity_sha256=provider_identity_sha256(
                ProviderConnectionTuple(
                    "fixture_target",
                    "target.example.invalid",
                    5432,
                )
            ),
            observed_server_address=(
                "192.0.2.99" if self.fail_at == "evidence-endpoint" else "192.0.2.10"
            ),
            provider_resolved_server_addresses=("192.0.2.10",),
            sslmode="disable" if self.fail_at == "evidence-tls" else "verify-full",
            hostname_verified=self.fail_at != "evidence-tls",
            certificate_verified=self.fail_at != "evidence-tls",
            connect_timeout_seconds=(
                999 if self.fail_at == "evidence-timeout" else CONNECT_TIMEOUT_SECONDS
            ),
            session_default_read_only=True,
            begin_read_only=True,
            transaction_read_only_verified=True,
            search_path="pg_catalog",
            statement_timeout_ms=5000,
            lock_timeout_ms=1000,
            idle_transaction_timeout_ms=5000,
            fixed_sql_statement_ids=tuple(self.executed),
            fixed_sql_trace_sha256=(
                _digest("wrong-fixed-trace")
                if self.fail_at == "evidence-trace"
                else fixed_sql_trace_sha256()
            ),
            receipt_sha256=_digest("database-execution-evidence"),
            fixture_only=True,
        )
        return evidence

    def rollback_and_close(self) -> None:
        self.closed = True
        self.events.append("database:close")
        if self.fail_at == "close":
            raise RuntimeError("synthetic token=do-not-emit")


class _FakeSupervisor:
    implementation_sha256 = sha256_bytes(b"v5-self-test:supervisor-implementation")
    fixture_only = True

    def __init__(
        self,
        fail_at: str | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.fail_at = fail_at
        self.armed = False
        self.confirmed = False
        self.events = events if events is not None else []

    def arm_cleanup(
        self,
        binding_sha256: str,
        operator_ipv4_cidr_32: str,
        target_service_identifier_sha256: str,
        target_contract_identity_sha256: str,
    ) -> CleanupSupervisorReceipt:
        del operator_ipv4_cidr_32
        safe_sha256(target_service_identifier_sha256, "CLEANUP_SUPERVISOR_ARM")
        safe_sha256(target_contract_identity_sha256, "CLEANUP_SUPERVISOR_ARM")
        if self.fail_at == "arm":
            raise RuntimeError("synthetic supervisor key=do-not-emit")
        self.armed = True
        self.events.append("supervisor:arm")
        return CleanupSupervisorReceipt(
            binding_sha256=binding_sha256,
            receipt_sha256=_digest("supervisor-armed"),
            state="ARMED",
            authenticated=True,
            durable=True,
            fixture_only=True,
        )

    def confirm_cleanup(
        self,
        armed: CleanupSupervisorReceipt,
        final_observation_receipt_sha256: str,
    ) -> CleanupSupervisorReceipt:
        safe_sha256(final_observation_receipt_sha256, "CLEANUP_SUPERVISOR_FINALIZE")
        need(self.armed, "CLEANUP_SUPERVISOR_UNCERTAIN", "CLEANUP_SUPERVISOR_FINALIZE")
        if self.fail_at == "confirm":
            raise RuntimeError("synthetic supervisor token=do-not-emit")
        self.confirmed = True
        self.events.append("supervisor:confirm")
        return CleanupSupervisorReceipt(
            binding_sha256=armed.binding_sha256,
            receipt_sha256=_digest("supervisor-final"),
            state="CLEANUP_CONFIRMED",
            authenticated=True,
            durable=True,
            fixture_only=True,
        )


def _synthetic_provenance_hmac_key() -> bytearray:
    """Return a fresh, fixture-only key; never use this value for live execution."""

    return bytearray(range(1, RUNTIME_PROVENANCE_HMAC_KEY_BYTES + 1))


class _FakeProvenance:
    implementation_sha256 = sha256_bytes(b"v5-self-test:provenance-implementation")
    fixture_only = True

    def __init__(
        self,
        authorization: ExecutionAuthorization,
        events: list[str] | None = None,
        **overrides: object,
    ) -> None:
        self.authorization = authorization
        self.overrides = overrides
        self.events = events if events is not None else []

    def observe_local_runtime(self) -> RuntimeProvenance:
        self.events.append("provenance:observe")
        authorization = self.authorization
        derived_overrides = {
            name: self.overrides[name]
            for name in ("observation_receipt_sha256", "hmac_sha256")
            if name in self.overrides
        }
        values: dict[str, object] = {
            "authorization_record_sha256": authorization.authorization_record_sha256,
            "adapter_sha256": authorization.adapter_sha256,
            "reviewer_sha256": authorization.reviewer_sha256,
            "operational_collection_procedure_contract_sha256": authorization.operational_collection_procedure_contract_sha256,
            "runtime_observation_schema_sha256": authorization.runtime_observation_schema_sha256,
            "sanitized_result_schema_sha256": authorization.sanitized_result_schema_sha256,
            "package_manifest_sha256": authorization.package_manifest_sha256,
            "repository_commit_oid": authorization.repository_commit_oid,
            "repository_tree_oid": authorization.repository_tree_oid,
            "invocation_sha256": authorization.invocation_sha256,
            "execution_harness_sha256": authorization.execution_harness_sha256,
            "render_port_implementation_sha256": authorization.render_port_implementation_sha256,
            "database_port_implementation_sha256": authorization.database_port_implementation_sha256,
            "attempt_ledger_implementation_sha256": authorization.attempt_ledger_implementation_sha256,
            "supervisor_implementation_sha256": authorization.supervisor_implementation_sha256,
            "runtime_provenance_implementation_sha256": authorization.runtime_provenance_implementation_sha256,
            "runtime_provenance_hmac_key_id_sha256": authorization.runtime_provenance_hmac_key_id_sha256,
            "dependency_set_sha256": authorization.dependency_set_sha256,
            "independent_attestation_signer_implementation_sha256": authorization.independent_attestation_signer_implementation_sha256,
            "ledger_hmac_key_id_sha256": authorization.ledger_hmac_key_id_sha256,
            "independent_attestation_hmac_key_id_sha256": authorization.independent_attestation_hmac_key_id_sha256,
            "fixed_sql_trace_sha256": fixed_sql_trace_sha256(),
            "tls_readonly_contract_sha256": tls_readonly_contract_sha256(),
            "worktree_clean": True,
            "package_paths_regular_nonsymlink": True,
            "fixture_only": True,
            "observation_receipt_sha256": "0" * 64,
            "hmac_sha256": "0" * 64,
        }
        values.update(
            {
                name: value
                for name, value in self.overrides.items()
                if name not in derived_overrides
            }
        )
        draft = RuntimeProvenance(**values)  # type: ignore[arg-type]
        payload = canonical_json_bytes(runtime_provenance_payload(draft))
        values["observation_receipt_sha256"] = sha256_bytes(payload)
        signing_key = _synthetic_provenance_hmac_key()
        try:
            values["hmac_sha256"] = hmac.new(
                signing_key,
                RUNTIME_PROVENANCE_HMAC_DOMAIN + payload,
                hashlib.sha256,
            ).hexdigest()
        finally:
            clear_bytearray(signing_key)
        values.update(derived_overrides)
        return RuntimeProvenance(**values)  # type: ignore[arg-type]


def _synthetic_authorization() -> ExecutionAuthorization:
    target = ProviderConnectionTuple("fixture_target", "target.example.invalid", 5432)
    production = ProviderConnectionTuple(
        "fixture_production",
        "production.example.invalid",
        5432,
    )
    staging = ProviderConnectionTuple("fixture_staging", "staging.example.invalid", 5432)
    cidr = "192.0.2.1/32"
    provenance_hmac_key = _synthetic_provenance_hmac_key()
    try:
        provenance_hmac_key_id = hashlib.sha256(provenance_hmac_key).hexdigest()
    finally:
        clear_bytearray(provenance_hmac_key)
    return ExecutionAuthorization(
        authorization_record_sha256=_digest("authorization"),
        adapter_sha256=stable_relative_sha256(ADAPTER_RELATIVE),
        reviewer_sha256=stable_relative_sha256(REVIEWER_RELATIVE),
        operational_collection_procedure_contract_sha256=procedure_contract_sha256(),
        runtime_observation_schema_sha256=stable_relative_sha256(
            RUNTIME_SCHEMA_RELATIVE
        ),
        sanitized_result_schema_sha256=stable_relative_sha256(
            RESULT_SCHEMA_RELATIVE
        ),
        package_manifest_sha256=stable_relative_sha256(PACKAGE_MANIFEST_RELATIVE),
        repository_commit_oid="1" * 40,
        repository_tree_oid="2" * 40,
        invocation_sha256=_digest("invocation"),
        operator_run_id_sha256=_digest("operator-run"),
        operator_ipv4_cidr_32_sha256=sha256_bytes(cidr.encode("ascii")),
        target_service_identifier_sha256=_digest("service"),
        target_contract_identity_sha256=_digest("target-contract"),
        expected_target_provider_identity_sha256=provider_identity_sha256(target),
        expected_production_provider_identity_sha256=provider_identity_sha256(production),
        expected_staging_provider_identity_sha256=provider_identity_sha256(staging),
        execution_harness_sha256=_digest("execution-harness"),
        render_port_implementation_sha256=_FakeRender.implementation_sha256,
        database_port_implementation_sha256=_FakeDatabase.implementation_sha256,
        attempt_ledger_implementation_sha256=_FakeLedger.implementation_sha256,
        supervisor_implementation_sha256=_FakeSupervisor.implementation_sha256,
        runtime_provenance_implementation_sha256=_FakeProvenance.implementation_sha256,
        runtime_provenance_hmac_key_id_sha256=provenance_hmac_key_id,
        dependency_set_sha256=_digest("dependency-set"),
        independent_attestation_signer_implementation_sha256=_digest(
            "attestation-signer"
        ),
        ledger_hmac_key_id_sha256=_digest("ledger-key-id"),
        independent_attestation_hmac_key_id_sha256=_digest(
            "attestation-key-id"
        ),
        live_execution_authorized=True,
        collection_attempt_limit=1,
        collection_attempts_consumed=0,
    )


def _expect_hold(callback: Callable[[], object], error: str | None = None) -> None:
    try:
        callback()
    except Hold as exc:
        if error is not None:
            need(exc.error_code == error, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
        return
    raise Hold("INTERNAL_FAILURE", "OUTPUT_VALIDATION")


def run_self_tests() -> None:
    need(sha256_bytes(EXPECTED_EMPTY_MANIFEST_LINE) == EXPECTED_EMPTY_MANIFEST_SHA256, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(normalize_structural_manifest([]) == EXPECTED_EMPTY_MANIFEST_LINE, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")

    relation_a = {
        "namespace": "public",
        "name": "alpha",
        "kind": "r",
        "columns": [{"name": "id", "not_null": True, "ordinal": 1, "type_oid": 23}],
    }
    relation_b = {
        "namespace": "public",
        "name": "beta",
        "kind": "v",
        "columns": [],
    }
    need(
        normalize_structural_manifest([relation_b, relation_a])
        == normalize_structural_manifest([relation_a, relation_b]),
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    for invalid in (
        [relation_a, relation_a],
        [dict(relation_a, kind="x")],
        [dict(relation_a, name="alpha\nsecret")],
        [relation_a, dict(relation_a, name="ALPHA")],
        [dict(relation_a, name="e\u0301")],
        [dict(relation_a, extra=False)],
    ):
        _expect_hold(lambda invalid=invalid: normalize_structural_manifest(invalid), "DATABASE_OBSERVATION_INVALID")

    _expect_hold(
        lambda: provider_identity_sha256(
            ProviderConnectionTuple("db", "TARGET.EXAMPLE.TEST", 5432)
        ),
        "IDENTITY_DOMAIN_MISMATCH",
    )
    _expect_hold(
        lambda: provider_identity_sha256(
            ProviderConnectionTuple("db", "target.example.invalid.", 5432)
        ),
        "IDENTITY_DOMAIN_MISMATCH",
    )
    _expect_hold(
        lambda: provider_identity_sha256(ProviderConnectionTuple("db", "192.0.2.1", 5432)),
        "IDENTITY_DOMAIN_MISMATCH",
    )

    conservative = failure_envelope("CONTROLLED_EXECUTION_HOLD", "PRECHECK")
    need(set(conservative) == FAILURE_KEYS, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    for mutation in (
        {**conservative, "extra": False},
        {key: value for key, value in conservative.items() if key != "hold"},
        {**conservative, "hold": 1},
        {**conservative, "raw_connection_values_disclosed": True},
        {**conservative, "error_code": "password=secret"},
        {**conservative, "cleanup_completed": True},
    ):
        _expect_hold(lambda mutation=mutation: validate_failure_envelope(mutation), "INTERNAL_FAILURE")

    authorization = _synthetic_authorization()
    now = datetime(2026, 8, 28, 0, 0, 0, tzinfo=timezone.utc)
    events: list[str] = []
    render = _FakeRender(events=events)
    database = _FakeDatabase(events=events)
    ledger = _FakeLedger(events=events)
    supervisor = _FakeSupervisor(events=events)
    success_provenance_key = _synthetic_provenance_hmac_key()
    success = _collect_once_with_clock(
        authorization,
        "192.0.2.1/32",
        ledger,
        render,
        database,
        supervisor,
        _FakeProvenance(authorization, events),
        success_provenance_key,
        lambda: now,
    )
    validate_success_envelope(success)
    need(success["outcome"] == "SUCCESS", "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(success["fixture_only"] is True, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(
        not any(success_provenance_key),
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    need(render.remove_called and database.closed, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(
        render.add_count == 1
        and render.remove_count == 1
        and supervisor.armed
        and supervisor.confirmed,
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    need(
        events.index("provenance:observe") < events.index("ledger:reserve")
        < events.index("render:observe:1"),
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    need(
        events.index("supervisor:arm") < events.index("render:add")
        and events.index("database:close") < events.index("render:remove")
        and events.index("render:observe:3") < events.index("supervisor:confirm"),
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    need(
        ledger.transitions
        == [
            "PROVIDER_OBSERVE_INTENT",
            "PROVIDER_VERIFIED",
            "SUPERVISOR_ARM_INTENT",
            "SUPERVISOR_ARMED",
            "ALLOWLIST_ADD_INTENT",
            "ALLOWLIST_ADDED",
            "ALLOWLIST_REVALIDATE_INTENT",
            "ALLOWLIST_REVALIDATED",
            "CONNECTION_MATERIAL_INTENT",
            "CONNECTION_MATERIAL_ACQUIRED",
            "DATABASE_CONNECT_INTENT",
            "DATABASE_CONNECTED",
            "DATABASE_OBSERVED",
            "DATABASE_CLOSE_INTENT",
            "DATABASE_CLOSED",
            "ALLOWLIST_REMOVE_INTENT",
            "ALLOWLIST_REMOVED",
            "FINAL_RECHECK_INTENT",
            "FINAL_NETWORK_VERIFIED",
            "SUPERVISOR_CONFIRM_INTENT",
            "SUPERVISOR_CONFIRMED",
            "COMPLETED",
        ],
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    need(database.executed == [
        "SET_SESSION_READ_ONLY",
        "BEGIN_READ_ONLY",
        "SET_SEARCH_PATH",
        "SET_STATEMENT_TIMEOUT",
        "SET_LOCK_TIMEOUT",
        "SET_IDLE_TIMEOUT",
        "VERIFY_READ_ONLY",
        "DATABASE_IDENTITY",
        "STRUCTURAL_MANIFEST",
    ], "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    success_mutations = (
        {**success, "extra": False},
        {key: value for key, value in success.items() if key != "fixture_only"},
        {**success, "adapter_contract_sha256": str(success["adapter_contract_sha256"]).upper()},
        {**success, "adapter_contract_sha256": "0" * 64},
        {**success, "adapter_contract_sha256": UNBOUND},
        {**success, "fixture_only": 1},
        {**success, "evidence_complete": True},
        {**success, "collection_attempt_consumed": 1},
        {
            **success,
            "cleanup_receipt_sha256": success["provider_observation_sha256"],
        },
        {**success, "expected_post_restore_schema_manifest_sha256": _digest("illegal")},
    )
    for mutation in success_mutations:
        _expect_hold(
            lambda mutation=mutation: validate_success_envelope(mutation),
            "INTERNAL_FAILURE",
        )

    forbidden_sql_tokens = re.compile(
        r"\b(?:INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|COPY|CALL|DO)\b",
        re.IGNORECASE,
    )
    for statement_id, sql in FIXED_SQL.items():
        need(";" not in sql, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
        need(forbidden_sql_tokens.search(sql) is None, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
        if sql.startswith("SELECT"):
            need(
                statement_id in {"VERIFY_READ_ONLY", "DATABASE_IDENTITY", "STRUCTURAL_MANIFEST"},
                "INTERNAL_FAILURE",
                "OUTPUT_VALIDATION",
            )
    need("pg_catalog.pg_class" in SQL_STRUCTURAL_MANIFEST, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(" public." not in SQL_STRUCTURAL_MANIFEST.lower(), "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    _expect_hold(
        lambda: fixed_execute(_FakeDatabase(), "DELETE_FROM_USER_TABLE"),
        "INTERNAL_FAILURE",
    )

    secret = "postgres://operator:super-secret@target.example.invalid/fixture"
    fault_cases = (
        ("render", "observe-initial"),
        ("render", "add"),
        ("render", "observe-after-add"),
        ("render", "material"),
        ("database", "open"),
        ("database", "SET_SESSION_READ_ONLY"),
        ("database", "VERIFY_READ_ONLY"),
        ("database", "DATABASE_IDENTITY"),
        ("database", "STRUCTURAL_MANIFEST"),
        ("database", "instrumentation"),
        ("database", "evidence-endpoint"),
        ("database", "evidence-tls"),
        ("database", "evidence-timeout"),
        ("database", "evidence-trace"),
        ("database", "close"),
        ("render", "remove"),
        ("render", "observe-final"),
        ("ledger", "DATABASE_OBSERVED"),
        ("supervisor", "arm"),
        ("supervisor", "confirm"),
    )
    for component, point in fault_cases:
        fault_render = _FakeRender(point if component == "render" else None)
        fault_database = _FakeDatabase(point if component == "database" else None)
        fault_ledger = _FakeLedger(point if component == "ledger" else None)
        fault_supervisor = _FakeSupervisor(
            point if component == "supervisor" else None
        )
        result = _collect_once_with_clock(
            authorization,
            "192.0.2.1/32",
            fault_ledger,
            fault_render,
            fault_database,
            fault_supervisor,
            _FakeProvenance(authorization),
            _synthetic_provenance_hmac_key(),
            lambda: now,
        )
        validate_failure_envelope(result)
        serialized = canonical_json_bytes(result).decode("utf-8")
        need(secret not in serialized and "password" not in serialized and "token" not in serialized, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
        if point not in {"observe-initial", "arm"}:
            need(fault_render.remove_called, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")

    nonempty_result = _collect_once_with_clock(
        authorization,
        "192.0.2.1/32",
        _FakeLedger(),
        _FakeRender(),
        _FakeDatabase(nonempty=True),
        _FakeSupervisor(),
        _FakeProvenance(authorization),
        _synthetic_provenance_hmac_key(),
        lambda: now,
    )
    need(nonempty_result["error_code"] == "SCHEMA_MANIFEST_MISMATCH", "INTERNAL_FAILURE", "OUTPUT_VALIDATION")

    for render_mode in (
        "wrong-target",
        "swap-identities",
        "final-continuity",
        "stale-clock",
        "future-clock",
    ):
        identity_result = _collect_once_with_clock(
            authorization,
            "192.0.2.1/32",
            _FakeLedger(),
            _FakeRender(render_mode),
            _FakeDatabase(),
            _FakeSupervisor(),
            _FakeProvenance(authorization),
            _synthetic_provenance_hmac_key(),
            lambda: now,
        )
        validate_failure_envelope(identity_result)

    for overrides in (
        {"worktree_clean": False},
        {"repository_commit_oid": "3" * 40},
        {"invocation_sha256": _digest("wrong-invocation")},
    ):
        provenance_result = _collect_once_with_clock(
            authorization,
            "192.0.2.1/32",
            _FakeLedger(),
            _FakeRender(),
            _FakeDatabase(),
            _FakeSupervisor(),
            _FakeProvenance(authorization, **overrides),
            _synthetic_provenance_hmac_key(),
            lambda: now,
        )
        need(
            provenance_result["attempt_state"] == "KNOWN_NOT_STARTED",
            "INTERNAL_FAILURE",
            "OUTPUT_VALIDATION",
        )

    hmac_key_id_fields = (
        "ledger_hmac_key_id_sha256",
        "runtime_provenance_hmac_key_id_sha256",
        "independent_attestation_hmac_key_id_sha256",
    )
    for left_index, right_index in ((0, 1), (0, 2), (1, 2)):
        authorization_values = dict(authorization.__dict__)
        authorization_values[hmac_key_id_fields[right_index]] = (
            authorization_values[hmac_key_id_fields[left_index]]
        )
        collision_authorization = ExecutionAuthorization(**authorization_values)
        collision_events: list[str] = []
        collision_ledger = _FakeLedger(events=collision_events)
        collision_render = _FakeRender(events=collision_events)
        collision_database = _FakeDatabase(events=collision_events)
        collision_supervisor = _FakeSupervisor(events=collision_events)
        collision_key = _synthetic_provenance_hmac_key()
        collision_result = _collect_once_with_clock(
            collision_authorization,
            "192.0.2.1/32",
            collision_ledger,
            collision_render,
            collision_database,
            collision_supervisor,
            _FakeProvenance(collision_authorization, collision_events),
            collision_key,
            lambda: now,
        )
        validate_failure_envelope(collision_result)
        need(
            collision_result["error_code"] == "AUTHORIZATION_INVALID"
            and collision_result["attempt_state"] == "KNOWN_NOT_STARTED"
            and collision_result["attempt_reserved"] is False
            and not any(collision_key)
            and collision_events == []
            and collision_ledger.receipt is None
            and collision_render.observe_count == 0
            and collision_render.add_count == 0
            and collision_render.remove_count == 0
            and collision_database.executed == []
            and collision_database.closed is False
            and collision_supervisor.armed is False,
            "INTERNAL_FAILURE",
            "OUTPUT_VALIDATION",
        )

    wrong_key_id_authorization = ExecutionAuthorization(
        **{
            **authorization.__dict__,
            "runtime_provenance_hmac_key_id_sha256": _digest(
                "wrong-provenance-key-id"
            ),
        }
    )
    provenance_hmac_faults = (
        (
            authorization,
            {},
            bytearray([0xA5] * RUNTIME_PROVENANCE_HMAC_KEY_BYTES),
        ),
        (authorization, {}, bytearray(RUNTIME_PROVENANCE_HMAC_KEY_BYTES)),
        (
            authorization,
            {"observation_receipt_sha256": _digest("tampered-receipt")},
            _synthetic_provenance_hmac_key(),
        ),
        (
            authorization,
            {"hmac_sha256": _digest("tampered-hmac")},
            _synthetic_provenance_hmac_key(),
        ),
        (
            wrong_key_id_authorization,
            {},
            _synthetic_provenance_hmac_key(),
        ),
    )
    for fault_authorization, overrides, supplied_key in provenance_hmac_faults:
        fault_events: list[str] = []
        fault_ledger = _FakeLedger(events=fault_events)
        fault_render = _FakeRender(events=fault_events)
        fault_database = _FakeDatabase(events=fault_events)
        fault_supervisor = _FakeSupervisor(events=fault_events)
        provenance_hmac_result = _collect_once_with_clock(
            fault_authorization,
            "192.0.2.1/32",
            fault_ledger,
            fault_render,
            fault_database,
            fault_supervisor,
            _FakeProvenance(fault_authorization, fault_events, **overrides),
            supplied_key,
            lambda: now,
        )
        validate_failure_envelope(provenance_hmac_result)
        need(
            provenance_hmac_result["error_code"] == "RUNTIME_PROVENANCE_INVALID"
            and provenance_hmac_result["attempt_state"] == "KNOWN_NOT_STARTED"
            and provenance_hmac_result["attempt_reserved"] is False
            and not any(supplied_key)
            and fault_events == ["provenance:observe"]
            and fault_ledger.receipt is None
            and fault_render.observe_count == 0
            and fault_render.add_count == 0
            and fault_render.remove_count == 0
            and fault_database.executed == []
            and fault_database.closed is False
            and fault_supervisor.armed is False,
            "INTERNAL_FAILURE",
            "OUTPUT_VALIDATION",
        )

    uncertain_reservation = _collect_once_with_clock(
        authorization,
        "192.0.2.1/32",
        _FakeLedger(reserve_uncertain=True),
        _FakeRender(),
        _FakeDatabase(),
        _FakeSupervisor(),
        _FakeProvenance(authorization),
        _synthetic_provenance_hmac_key(),
        lambda: now,
    )
    need(
        uncertain_reservation["attempt_state"] == "UNCERTAIN"
        and uncertain_reservation["attempt_reserved"] is True
        and uncertain_reservation["collection_attempt_consumed"] is True
        and uncertain_reservation["cleanup_required"] is True,
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )

    public_provenance_key = _synthetic_provenance_hmac_key()
    public_fixture_rejection = collect_once(
        authorization,
        "192.0.2.1/32",
        _FakeLedger(),
        _FakeRender(),
        _FakeDatabase(),
        _FakeSupervisor(),
        _FakeProvenance(authorization),
        public_provenance_key,
    )
    need(
        public_fixture_rejection["error_code"] == "PORT_IMPLEMENTATION_UNBOUND"
        and public_fixture_rejection["attempt_state"] == "KNOWN_NOT_STARTED",
        "INTERNAL_FAILURE",
        "OUTPUT_VALIDATION",
    )
    need(not any(public_provenance_key), "INTERNAL_FAILURE", "OUTPUT_VALIDATION")

    bad_authorization = ExecutionAuthorization(
        **{**authorization.__dict__, "live_execution_authorized": False}
    )
    no_attempt = _collect_once_with_clock(
        bad_authorization,
        "192.0.2.1/32",
        _FakeLedger(),
        _FakeRender(),
        _FakeDatabase(),
        _FakeSupervisor(),
        _FakeProvenance(bad_authorization),
        _synthetic_provenance_hmac_key(),
        lambda: now,
    )
    need(no_attempt["attempt_reserved"] is False, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")

    with tempfile.TemporaryDirectory(prefix="pmai-v5-ledger-self-test-") as directory:
        ledger_path = Path(directory) / "attempt.json"
        file_ledger = SyntheticReferenceFileAttemptLedger(ledger_path)
        binding = _digest("file-ledger-binding")
        first = file_ledger.reserve_once(binding)
        validate_attempt_receipt(first, binding, "RESERVED")
        _expect_hold(lambda: file_ledger.reserve_once(binding), "ATTEMPT_ALREADY_CONSUMED")
        advanced = file_ledger.transition(first, "PROVIDER_OBSERVE_INTENT")
        validate_attempt_receipt(advanced, binding, "PROVIDER_OBSERVE_INTENT")
        _expect_hold(lambda: file_ledger.transition(first, "ALLOWLIST_ADD_INTENT"), "ATTEMPT_LEDGER_UNCERTAIN")
        ledger_path.with_name(ledger_path.name + ".next").write_text("crash", encoding="ascii")
        _expect_hold(lambda: file_ledger.transition(advanced, "PROVIDER_VERIFIED"), "ATTEMPT_LEDGER_UNCERTAIN")


def emit(value: Mapping[str, object]) -> None:
    if value.get("outcome") == "SUCCESS":
        validate_success_envelope(value)
    else:
        validate_failure_envelope(value)
    payload = canonical_json_bytes(value).decode("utf-8")
    sys.stdout.write(payload + "\n")
    sys.stdout.flush()


def dry_run() -> int:
    need(adapter_contract_sha256() == adapter_contract_sha256(), "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    need(sha256_bytes(EXPECTED_EMPTY_MANIFEST_LINE) == EXPECTED_EMPTY_MANIFEST_SHA256, "INTERNAL_FAILURE", "OUTPUT_VALIDATION")
    emit(failure_envelope("CONTROLLED_EXECUTION_HOLD", "PRECHECK"))
    return 0


def self_test() -> int:
    run_self_tests()
    emit(failure_envelope("CONTROLLED_EXECUTION_HOLD", "OUTPUT_VALIDATION"))
    return 0


def parser() -> SafeArgumentParser:
    value = SafeArgumentParser(add_help=False, description=__doc__)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--collect-once", action="store_true")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    validate_isolated_invocation()
    args = parser().parse_args(argv)
    if args.dry_run:
        return dry_run()
    if args.self_test:
        return self_test()
    emit(failure_envelope("LIVE_PORTS_NOT_INJECTED", "PRECHECK"))
    return 1


def entrypoint() -> int:
    try:
        return main()
    except Hold as exc:
        emit(failure_envelope(exc.error_code, exc.stage_code))
        return 1
    except BaseException:
        try:
            emit(failure_envelope("INTERNAL_FAILURE", "PRECHECK"))
        except BaseException:
            sys.stdout.write(
                '{"attempt_reserved":false,"attempt_state":"KNOWN_NOT_STARTED",'
                '"cleanup_completed":false,'
                '"cleanup_required":false,"collection_attempt_consumed":false,'
                '"error_code":"INTERNAL_FAILURE",'
                '"final_network_state_verified":false,"hold":true,'
                '"outcome":"HOLD","raw_connection_values_disclosed":false,'
                '"runtime_evidence_emitted":false,'
                '"schema":"PMAI_P0_04_SRBE_V5_SANITIZED_COLLECTION_RESULT_V1",'
                '"stage_code":"PRECHECK",'
                '"state_provenance":"ADAPTER_STATE_MACHINE"}\n'
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
