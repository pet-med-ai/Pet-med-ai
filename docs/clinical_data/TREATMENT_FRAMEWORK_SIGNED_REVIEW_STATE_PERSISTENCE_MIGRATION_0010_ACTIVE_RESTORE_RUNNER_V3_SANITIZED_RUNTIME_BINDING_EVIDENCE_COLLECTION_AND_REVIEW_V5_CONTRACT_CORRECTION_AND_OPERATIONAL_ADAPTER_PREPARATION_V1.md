# Treatment Framework Signed Review State Persistence Migration 0010
## Active Restore Runner V3 Sanitized Runtime Binding Evidence Collection and Review V5 Contract Correction and Operational Adapter Preparation V1

This repository-only package corrects the V4 sanitized runtime-binding
evidence (SRBE) collection contract and prepares a hash-lockable operational
adapter and offline reviewer. It does not authorize or perform live
collection. In particular, it does not access Render, obtain a credential or
connection value, connect to any database, change an inbound IP rule, create
or run a restore runner, access a backup, restore, migrate, deploy, or delete
anything.

The V4 repository records remain byte-exact historical evidence. The V4
action-time confirmation was never started, consumed zero attempts, is
superseded for all future live execution, and transfers no attempt entitlement
to V5. This package, its merge, a passing post-merge CI Gate, and even a new
single-use confirmation are each necessary but are not collectively
sufficient for live execution. A future action must also introduce, review,
publish, and hash-lock the concrete Render port, database port, credential
broker/execution harness, authenticated durable ledger, independent
attestation signer, crash-safe cleanup supervisor, runtime-provenance
implementation, dependency set, and independent anti-rollback witness. None
of those concrete live implementations or runtime authorities is supplied by
this package. Every current live entry point is a hard HOLD and the repository
CLI has no live mode.

## 1. Canonical package record

~~~text
stage_id=PMAI-P0-04
substage=ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1
work_bundle=PMAI-P0-04-ARR-V3-SRBE-V5-CONTRACT-ADAPTER-PREP
package_record_id=PMAI-P0-04-ARR-V3-SRBE-V5-CONTRACT-ADAPTER-PREP-REPLACEMENT-V2-20260829
package_record_id_sha256=d265596288da1729bcc428349d4491d1c87fbc02a03224281d2bcc0fd42b65ae
package_recorded_date=2026-08-29
package_status=REPOSITORY_ONLY_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION
review_status=PREPARED_FOR_STATIC_VALIDATION_ONLY
current_execution_decision=HOLD_NO_LIVE_EXECUTION
repository=pet-med-ai/Pet-med-ai
base_branch=main
base_commit=19327dd0c1c5141d391716d6844f230ec35efa6a
base_tree_sha=1c1a4cd8053b47107d47a9df3b281d1bac487e78
source_pull_request=21
base_github_ci_run_id=33245499297
base_github_ci_run_number=230
base_github_ci_status=PASS
base_github_ci_event=push
base_github_ci_run_attempt=1
base_github_ci_terminal_status=completed
base_github_ci_conclusion=success
head_branch=pmai-p0-04-arr-v3-srbe-v5-operational-adapter-prep-v2
commit_message=PMAI-P0-04: Rebuild V5 SRBE operational adapter
authorization_id=PMAI_P0_04_ACTIVE_RESTORE_RUNNER_V3_SRBE_V5_POST_V4_COMPATIBILITY_MERGE_REPLACEMENT_REBUILD_EXACT_13_PATH_REPOSITORY_PATCH_CONTROLLED_EXECUTION_V1
authorization_id_sha256=395d54b50459a7c392263fe4fe69bbd280ba272cc64c1be6e003e18dd498f253
replacement_revision=2
current_v4_owned_central_projection_sha256=be245ca676bc7b57aac2db164ac49bf2e7593834c7cdd63f4fe33faaf0c0fd21
held_v5_commit_must_not_be_replacement_ancestor=true
authorization_scope=EXACT_13_PATH_REMOTE_ANCHORED_REPOSITORY_PATCH_ONLY
authorization_is_new_single_use=true
repository_patch_consumes_no_collection_attempt=true
v5_live_execution_authorized=false
v5_current_attempts_authorized=0
~~~

The package-record hash is SHA-256 over the exact UTF-8 record ID without a
trailing LF. It is a public governance anchor, not a runtime identity.

## 2. V4 disposition and protected history

~~~text
prior_v4_confirmation_external_access_started=false
prior_v4_collection_attempts_consumed=0
prior_v4_confirmation_superseded_for_all_future_live_execution=true
prior_v4_attempt_entitlement_carried_forward=false
prior_v4_confirmation_reuse_allowed=false
preserve_current_v4_immutable_package_members_byte_exact=true
current_v4_validator_sha256=75db3110bb2996a186ebe42c8e78985972ed37b6a1f775041d7dc9ef399be2c9
current_v4_manifest_sha256=6b95631a2adc707707e55af68045c47440a2ca0fd3b8fd75c20e8d24a3ca9362
current_v4_owned_central_projection_sha256=be245ca676bc7b57aac2db164ac49bf2e7593834c7cdd63f4fe33faaf0c0fd21
unique_historical_v4_repair_commit=e410804fd21aa0c7bf57040b088543190d442fc9
v4_compatibility_correction_commit=74ba74b2200870b0833e6f657b2f212747781ad6
v4_compatibility_merge_commit=19327dd0c1c5141d391716d6844f230ec35efa6a
replacement_commit_is_legitimate_successor_central_evolution=true
replacement_commit_is_second_historical_v4_repair=false
held_v5_commit=da4d347066c464b0ad8799acc9a26802469488ed
held_v5_tree=e55fa46f65562a82c44f4bc5524d45dcb4f5bd49
held_v5_parent=de93b4623e812a911445a4370dea40ec56b2098f
held_v5_patch_commit_and_postcommit_validation_entitlements_consumed=true
held_v5_live_collection_attempts_consumed=0
held_v5_attempt_entitlement_carried_forward=false
held_v5_commit_must_not_be_replacement_ancestor=true
held_v5_reuse_or_publication_allowed=false
v4_output_schema_live_use=false
v4_operational_procedure_live_use=false
v5_contract_correction_required=true
~~~

No V4 runtime fact may be inferred from its static repository package. The six
immutable V4 members and the current V4 validator and manifest remain byte
exact. The shared central validator may evolve only through a V5 successor
region outside the V4-owned markers while the V4-owned projection remains
exact. The V4 confirmation remains part of the audit history only.

## 3. Why V5 is required

V4 could not be executed truthfully under its own boundaries. It conflated
provider connection identity with database-observed identity, required a
post-restore schema value before a restore was permitted, and provided no
operational adapter or mutually exclusive sanitized failure result.

V5 makes three fail-closed corrections:

1. Target, production, and staging are compared only in one canonical Render
   provider connection-tuple domain. Database-observed identity is a separate
   domain and cannot substitute for a provider identity.
2. The only schema gate in this pre-restore collection phase is the exact
   canonical empty structural manifest. The post-restore manifest remains
   `UNBOUND` and is not observed.
3. Success means only that one future, separately authorized pre-restore
   read-only collection completed and cleanup was independently verified. It
   never means that post-restore evidence, SRBE, runtime binding, or aggregate
   evidence is complete.

The repository package implements only the static A-contract: canonical data
models, injected port interfaces, a non-live adapter, a non-live reviewer,
schemas, and offline synthetic tests. The B-contract is deliberately absent:
real provider/database/credential integrations, a live harness, authenticated
ledger deployment, independent signer, crash-safe supervisor, and external
anti-rollback witness. Every absent or unbound B-contract component is
`HOLD_NO_LIVE_EXECUTION`; it cannot be supplied by a Boolean, a self-asserted
digest, an environment value containing a secret, or an ad hoc wrapper.

## 4. Identity domains and canonicalization

### 4.1 Provider connection tuple

The target, production, and staging provider identities use the same canonical
JSON domain. The exact four-field object is:

~~~json
{"database":"<exact-provider-database-identifier>","domain":"PROVIDER_CONNECTION_TUPLE_V5","hostname":"<lowercase-ascii-dns-hostname>","port":5432}
~~~

It uses the same `ensure_ascii=True`, sorted-key, compact-separator,
`allow_nan=False`, UTF-8, no-LF canonicalization defined below. SHA-256 is
calculated only in memory. The hostname must already be lowercase ASCII IDNA
output and contain at least one dot. Credentials, a URI scheme, path, query,
fragment, whitespace, controls, IP literals, non-ASCII characters, empty
labels, consecutive dots, and every terminal dot are rejected rather than
silently normalized. Every DNS label must satisfy the lowercase LDH rules.
The database identifier must be nonempty NFC UTF-8 of at most 1024 bytes with
no control characters and is compared case-sensitively. The port is an integer
from 1 through 65535; boolean and string representations are rejected.

All three provider identity hashes must be pairwise distinct. A future live
authorization must contain
`expected_target_provider_identity_sha256`,
`expected_production_provider_identity_sha256`, and
`expected_staging_provider_identity_sha256`. The observed canonical hashes
must equal those three authorization values exactly before any allowlist
mutation or credential access; pairwise distinction alone is insufficient.
The exact target TLS `verify-full` hostname, port, and database must equal the
canonical target provider tuple. Production and staging databases are never
connected.

### 4.2 Database-observed identity and connection binding

The exact target database may expose identity metadata only after the provider
tuple gate passes and a read-only transaction has been established. Its
canonical record uses the separate domain `DATABASE_OBSERVED_IDENTITY_V5`;
its raw values remain in memory.

~~~json
{"database":"<observed-current-database>","domain":"DATABASE_OBSERVED_IDENTITY_V5","port":5432,"server_address":"<canonical-compressed-ip-address>"}
~~~

This object uses the same no-LF canonical JSON rule. The observed database is
nonempty NFC UTF-8 of at most 1024 bytes without controls; the port is an
integer from 1 through 65535; and the server address must already equal the
canonical compressed IPv4 or IPv6 spelling. Any alias or parse ambiguity is
HOLD.
The target database-observed identity hash cannot be compared with, or
substituted for, any provider identity hash.

`target_connection_binding_sha256` is SHA-256 over the following exact
V2 canonical JSON object. The angle-bracket values are lowercase
SHA-256 values already derived under their own contracts:

~~~json
{"attempt_binding_sha256":"<attempt>","authorization_record_sha256":"<authorization>","database_execution_evidence_sha256":"<database-execution-evidence>","database_observed_identity_sha256":"<target-database-observed-identity>","instrumentation_receipt_sha256":"<instrumentation>","provider_identity_sha256":"<target-provider-identity>","runtime_provenance_observation_receipt_sha256":"<runtime-provenance>","schema":"PMAI_P0_04_SRBE_V5_TARGET_CONNECTION_BINDING_V2","tls_contract_sha256":"4f9afb65990161559a449bc2ceef49804e90c6da6583060cc35a3dffbca94129"}
~~~

The exact fixed TLS/read-only contract bytes without an LF are:

~~~json
{"begin_read_only":true,"connect_timeout_seconds":10,"idle_transaction_timeout_ms":5000,"lock_timeout_ms":1000,"schema":"PMAI_P0_04_SRBE_V5_TLS_READONLY_CONTRACT_V2","search_path":"pg_catalog","session_default_read_only":true,"sslmode":"verify-full","statement_timeout_ms":5000,"verify_certificate":true,"verify_hostname":true}
~~~

Their SHA-256 is
`4f9afb65990161559a449bc2ceef49804e90c6da6583060cc35a3dffbca94129`.
Both objects use `json.dumps` semantics with `ensure_ascii=True`, sorted keys,
compact `,` and `:` separators, `allow_nan=False`, UTF-8 encoding, and no
trailing LF. The binding proves association within this attempt; it does not
turn either identity domain into the other. The binding object's
`database_observed_identity_sha256` maps to the result field
`target_database_observed_identity_sha256`, and its
`provider_identity_sha256` maps to `target_provider_identity_sha256`.

The in-memory `PMAI_P0_04_SRBE_V5_DATABASE_EXECUTION_EVIDENCE_V2` canonical
record has exactly 19 fields: `begin_read_only`, `certificate_verified`,
`connect_timeout_seconds`, `fixed_sql_statement_ids`,
`fixed_sql_trace_sha256`, `fixture_only`, `hostname_verified`,
`idle_transaction_timeout_ms`, `lock_timeout_ms`,
`observed_server_address`, `provider_resolved_server_addresses`,
`receipt_sha256`, `schema`, `search_path`, `session_default_read_only`,
`sslmode`, `statement_timeout_ms`, `target_provider_identity_sha256`, and
`transaction_read_only_verified`. The observed address and resolved-address
set are canonical IP values retained only in memory; only
`database_execution_evidence_sha256` is emitted.

`instrumentation_receipt_sha256` is the hash of the exact ten-field canonical
`PMAI_P0_04_SRBE_V5_INSTRUMENTATION_BINDING_V2` record:

~~~json
{"adapter_sha256":"<adapter>","attempt_binding_sha256":"<attempt>","database_execution_evidence_sha256":"<database-execution-evidence>","database_instrumentation_receipt_sha256":"<database-instrumentation>","fixed_sql_trace_sha256":"<fixed-sql-trace>","provider_allowlist_recheck_receipt_sha256":"<allowlist-recheck>","provider_observation_receipt_sha256":"<provider-observation>","runtime_provenance_observation_receipt_sha256":"<runtime-provenance>","schema":"PMAI_P0_04_SRBE_V5_INSTRUMENTATION_BINDING_V2","tls_readonly_contract_sha256":"4f9afb65990161559a449bc2ceef49804e90c6da6583060cc35a3dffbca94129"}
~~~

Both V2 evidence records and the V2 target-connection binding are checked
against the authenticated independent sidecar; a digest supplied by the
adapter without that cross-check is not evidence.

Raw URLs, hostnames, database identifiers, addresses, connection values,
credentials, exception strings, HTTP or database bodies, relation names, or
other arbitrary observations must not be emitted or persisted. They also must
not be hashed as an error-reporting shortcut. Only explicitly defined
canonical records may be hashed.

A future independently instrumented execution must additionally produce four
sanitized, domain-separated evidence hashes:
`tls_connect_parameters_sha256`, `tls_negotiated_session_sha256`,
`endpoint_verification_sha256`, and `fixed_sql_trace_sha256`. The first binds
the exact no-secret connect options, verify-full hostname, port, database, and
connect timeout; the second binds the negotiated verified TLS session facts;
the third binds the independently observed peer endpoint to the authorized
target tuple; and the fourth binds the exact ordered fixed-statement IDs and
outcomes without SQL parameters or returned values. These hashes are carried
by the independently authenticated sidecar described below;
`fixed_sql_trace_sha256` is also an exact SUCCESS/runtime-observation field.
An adapter
self-assertion, connection-library configuration object, or successful query
is not a substitute for negotiated-session, endpoint, or fixed-SQL evidence.

## 5. Exact pre-restore structural schema contract

The structural manifest is derived only from fixed, fully qualified
`pg_catalog` metadata queries. It contains non-system relation structure, not
rows. Dynamic SQL, stored or volatile functions, user-table queries, DML,
DDL, `COPY`, `CALL`, and `DO` are forbidden.

The exact expected empty manifest line, including its final LF, is:

~~~json
{"relations":[],"schema":"PMAI_P0_04_SRBE_STRUCTURAL_SCHEMA_MANIFEST_V5_V1"}
~~~

~~~text
expected_pre_restore_empty_schema_manifest_hash_normalization=SHA256_UTF8_EXACT_CANONICAL_JSON_LINE_WITH_TRAILING_LF
expected_pre_restore_empty_schema_manifest_sha256=f87acbf36011fa8656e82f1cb6067614a59d019e32ea36781fe1dc2ceb4fc010
observed_pre_restore_schema_manifest_must_equal_expected=true
expected_post_restore_schema_manifest_sha256=UNBOUND
post_restore_schema_evidence_collected=false
~~~

For a nonempty observation the manifest format is reserved for a later
contract. This V5 phase must HOLD on any relation, duplicate, unexpected
namespace or relation kind, control character, ambiguous Unicode or case,
truncation, missing structural field, or additional structural field. It must
not emit raw relation or namespace names.

## 6. Sanitized observation and result contracts

The package contains two operative Draft 2020-12 JSON Schemas:

- `PMAI_P0_04_SRBE_V5_SANITIZED_RUNTIME_OBSERVATION_V1` defines the exact
  in-memory hash-and-boolean observation passed to result construction.
- `PMAI_P0_04_SRBE_V5_SANITIZED_COLLECTION_RESULT_V1` defines mutually
  exclusive `SUCCESS` and `HOLD` envelopes emitted by the adapter and checked
  by the offline reviewer.

The runtime-observation schema's required and property keys are exactly the
`SUCCESS` result keys with `outcome` removed; the adapter must construct and
validate that exact in-memory observation before wrapping it in the result
envelope. Both schemas reject extra or duplicate keys, type confusion, uppercase or
malformed hashes, and raw fields. JSON is emitted using `ensure_ascii=True`,
sorted keys, compact `,` and `:` separators, `allow_nan=False`, UTF-8 encoding,
and exactly one trailing LF. Live collection stdout contains exactly one
result object and stderr is empty. Synthetic `--dry-run` and `--self-test`
also emit one schema-valid
`HOLD` object; their exit code zero is the test-pass signal, not runtime
evidence.

A `SUCCESS` result requires all of the following:

~~~text
outcome=SUCCESS
runtime_provenance_observation_receipt_sha256=<authorized-sanitized-receipt-hash>
database_execution_evidence_sha256=<sanitized-execution-evidence-hash>
fixed_sql_trace_sha256=<exact-ordered-fixed-statement-trace-hash>
tls_readonly_contract_sha256=4f9afb65990161559a449bc2ceef49804e90c6da6583060cc35a3dffbca94129
cleanup_supervisor_armed_receipt_sha256=<authenticated-durable-armed-receipt-hash>
cleanup_supervisor_final_receipt_sha256=<authenticated-final-confirmed-receipt-hash>
pre_restore_schema_manifest_sha256=f87acbf36011fa8656e82f1cb6067614a59d019e32ea36781fe1dc2ceb4fc010
expected_pre_restore_schema_manifest_sha256=f87acbf36011fa8656e82f1cb6067614a59d019e32ea36781fe1dc2ceb4fc010
expected_post_restore_schema_manifest_sha256=UNBOUND
target_status_available=true
target_lifecycle_within_72h=true
target_application_attachment_count_zero=true
target_open_connection_count_zero=true
initial_inbound_ip_rule_set_empty=true
final_inbound_ip_rule_set_empty=true
public_external_access_blocked=true
collection_attempt_consumed=true
pre_restore_readonly_collection_complete=true
post_restore_schema_evidence_collected=false
runtime_binding_contract_complete=false
srbe_collection_evidence_complete=false
evidence_complete=false
raw_connection_values_disclosed=false
fixture_only=false
~~~

The three provider identity hashes must be pairwise distinct. Authorization,
attempt, ledger, provider observation, database observation, database identity,
connection binding, procedure, adapter, reviewer, instrumentation, and cleanup
hashes must be independently recomputable from the exact approved domains and
receipts. Booleans and self-asserted hashes alone are not independent proof.
`adapter_contract_sha256` is the SHA-256 of the exact operational adapter
source bytes and must equal the future authorization's adapter-source binding;
it is not a hash of a self-described adapter descriptor. `reviewer_sha256` is
likewise the exact operational reviewer source-byte hash.

A `HOLD` result contains only fixed public schema, outcome, error code, stage
code, `attempt_state`, `state_provenance`, attempt and cleanup booleans, and
disclosure booleans. It contains no runtime evidence hashes or arbitrary text.
`attempt_state` is exactly one of `KNOWN_NOT_STARTED`, `CONSUMED`, or
`UNCERTAIN`; `state_provenance` is exactly `ADAPTER_STATE_MACHINE` or
`UNVERIFIED_REVIEW_INPUT`. For adapter-state results,
`attempt_reserved == collection_attempt_consumed`; completed cleanup implies
cleanup was required and final network state was verified; final-network
verification implies cleanup was required. The schema further locks the
valid state combinations.

A reviewer-generated rejection cannot truthfully reconstruct attempt or
cleanup state from malformed or unauthenticated input. It therefore emits the
single conservative `UNVERIFIED_REVIEW_INPUT` combination:
`attempt_state=UNCERTAIN`, `attempt_reserved=true`,
`collection_attempt_consumed=true`, `cleanup_required=true`,
`cleanup_completed=false`, and `final_network_state_verified=false`. Those
values are conservative safety claims, not assertions that an external action
was observed. `runtime_evidence_emitted` and
`raw_connection_values_disclosed` are always false. Failure, ambiguity,
cleanup uncertainty, or invalid output is `HOLD_NO_RETRY`.

## 7. Future authorization, provenance, and durable attempt ledger

This repository patch creates no ledger and consumes no attempt. A future
authorization must bind the following exact fields before a live harness can
exist. Every `*_sha256` value is lowercase 64-hex and neither all-zero nor
all-`f`; `repository_commit_oid` and `repository_tree_oid` are lowercase
40-hex Git object IDs and are never mislabeled as SHA-256 values.

~~~text
authorization_record_sha256
repository_commit_oid
repository_tree_oid
package_manifest_sha256
adapter_sha256
reviewer_sha256
runtime_observation_schema_sha256
sanitized_result_schema_sha256
operational_collection_procedure_contract_sha256
invocation_sha256
operator_run_id_sha256
operator_ipv4_cidr_32_sha256
target_service_identifier_sha256
target_contract_identity_sha256
expected_target_provider_identity_sha256
expected_production_provider_identity_sha256
expected_staging_provider_identity_sha256
execution_harness_sha256
render_port_implementation_sha256
database_port_implementation_sha256
attempt_ledger_implementation_sha256
supervisor_implementation_sha256
runtime_provenance_implementation_sha256
dependency_set_sha256
independent_attestation_signer_implementation_sha256
ledger_hmac_key_id_sha256
runtime_provenance_hmac_key_id_sha256
independent_attestation_hmac_key_id_sha256
~~~

The raw operator run ID and the exact operator IPv4 `/32` may exist only in
the future controlled process memory. Their authorized hashes, never their raw
values, enter the binding. The canonical `PMAI_P0_04_SRBE_V5_ATTEMPT_BINDING_V2`
record contains every field above plus
`runtime_provenance_observation_receipt_sha256`. Its no-LF canonical JSON
SHA-256 is `attempt_binding_sha256`. Omitting, relabeling, substituting, or
reordering a domain is HOLD before any external call.

Before ledger reservation, a separately hash-locked runtime-provenance port
must independently observe and match the exact adapter, reviewer, both
schemas, procedure contract, package manifest, concrete ports, harness,
ledger, supervisor, signer, dependency set, Git HEAD commit/tree, clean
worktree, isolated interpreter/import path, and exact invocation. It emits the
sanitized `runtime_provenance_observation_receipt_sha256` included in Attempt
Binding V2. A caller-supplied dataclass, the adapter's own file hash, or a
Boolean `clean=true` is insufficient.

The runtime-provenance observation must itself be authenticated with a third,
independent exact 32-byte HMAC key supplied by the future execution harness
only through an anonymous pipe FD. Before ledger reservation and before every
external call, the adapter must read that key only into mutable process memory,
derive and compare its domain-separated key ID with
`runtime_provenance_hmac_key_id_sha256`, verify the HMAC over the exact
canonical provenance record, close the FD, and best-effort overwrite the key
buffer. Missing, short, long, all-zero, non-pipe, replayed, mismatched, or
unauthenticated input is HOLD before the attempt is reserved. This repository
package and its CLI never read a runtime-provenance key.

Before its first Render, database, credential, or other external call, a
future live controller must atomically and durably reserve its single attempt
in an authenticated ledger outside the repository. The ledger uses a future
independent 32-byte HMAC key delivered only over an anonymous FD and bound by
`ledger_hmac_key_id_sha256`. It must use an owner-private no-follow directory,
an immutable `O_EXCL` consumption lock, authenticated canonical records,
file-and-directory fsync, readback, compare-and-swap transitions, durable
intent states before every external effect, and no delete, unlock, reset,
resume, recovery, or reuse API.

The reservation is consumption: success, failure, ambiguity, interruption,
or cleanup failure does not restore the attempt. An existing, concurrent,
partially written, restarted, unreadable, unauthenticated, or uncertain ledger
is `HOLD_NO_RETRY`. In-memory state is insufficient. HMAC authentication does
not by itself prevent a same-identity rollback of the entire ledger directory;
therefore a future one-shot key issuer or external append-only anti-rollback
witness must durably consume the authorization and must never reissue the key
to a restarted process. That witness and its concrete binding are absent here.

## 8. Operational adapter contract

~~~text
operational_collection_procedure_contract_id=PMAI_P0_04_ARR_V3_SRBE_OPERATIONAL_COLLECTION_PROCEDURE_V5_V1
operational_collection_procedure_contract_hash_normalization=SHA256_UTF8_EXACT_ORDERED_LINES_WITH_TRAILING_LF
operational_collection_procedure_contract_sha256=17e15afbf3aa75f0dde528174f654a3da8fd1a0907c82e8cec9527ebf35c4e11
operational_collection_procedure_contract_defined=true
operational_collection_procedure_contract_live_execution_authorized=false
~~~

operational_collection_procedure_contract_begin

~~~text
contract=PMAI_P0_04_ARR_V3_SRBE_OPERATIONAL_COLLECTION_PROCEDURE_V5_V1
current_live_execution_authorized=false
future_attempt_limit=1
step_01=VERIFY_EXACT_PUBLISHED_COMMIT_TREE_CI_AUTHORIZATION_AND_ALL_BYTE_HASHES
step_02=VERIFY_ALL_CONCRETE_HARNESS_PORT_LEDGER_SUPERVISOR_PROVENANCE_DEPENDENCY_SIGNER_KEY_AND_WITNESS_HASH_LOCKS
step_03=READ_DISTINCT_RUNTIME_PROVENANCE_KEY_FROM_ANONYMOUS_FD_AUTHENTICATE_CLEAN_GIT_PROVENANCE_ZEROIZE_KEY_AND_BUILD_ATTEMPT_BINDING_V2
step_04=ATOMICALLY_RESERVE_AUTHENTICATED_DURABLE_SINGLE_USE_ATTEMPT_BEFORE_FIRST_EXTERNAL_CALL
step_05=READ_ONLY_REVALIDATE_EXACT_RENDER_TARGET_STATUS_LIFECYCLE_ATTACHMENTS_CONNECTIONS_AND_NETWORK
step_06=REQUIRE_AVAILABLE_AGE_AT_MOST_72_HOURS_ZERO_ATTACHMENTS_ZERO_CONNECTIONS_EMPTY_RULES_AND_BLOCKED_PUBLIC_ACCESS
step_07=CANONICALIZE_TARGET_PRODUCTION_STAGING_PROVIDER_TUPLES_REQUIRE_AUTHORIZED_EXACT_HASHES_AND_PAIRWISE_DISTINCT
step_08=DURABLY_RECORD_ALLOWLIST_ADD_INTENT_THEN_ADD_ONLY_AUTHORIZED_OPERATOR_IPV4_CIDR_32_AT_MOST_ONCE
step_09=REVALIDATE_THE_EXACT_TEMPORARY_RULE_BEFORE_ACCESSING_EPHEMERAL_CONNECTION_MATERIAL
step_10=CONNECT_ONLY_TO_EXACT_TARGET_WITH_TLS_VERIFY_FULL_FIXED_TIMEOUTS_AND_INDEPENDENT_CONNECT_NEGOTIATED_ENDPOINT_EVIDENCE
step_11=SET_SESSION_DEFAULT_READ_ONLY_BEGIN_READ_ONLY_SET_SEARCH_PATH_PG_CATALOG_AND_VERIFY_TRANSACTION_READ_ONLY_ON
step_12=RUN_ONLY_FIXED_FULLY_QUALIFIED_PG_CATALOG_IDENTITY_AND_STRUCTURAL_METADATA_QUERIES_WITH_FIXED_SQL_TRACE_EVIDENCE
step_13=REQUIRE_EXACT_EMPTY_PRE_RESTORE_MANIFEST_AND_KEEP_POST_RESTORE_MANIFEST_UNBOUND
step_14=DURABLY_RECORD_DATABASE_CLOSE_INTENT_THEN_ROLL_BACK_AND_CLOSE_BEFORE_NETWORK_CLEANUP
step_15=CRASH_SAFE_SUPERVISOR_DURABLY_RECORDS_REMOVE_INTENT_AND_REMOVES_ONLY_ADDED_CIDR_AT_MOST_ONCE
step_16=INDEPENDENTLY_RECHECK_FINAL_EMPTY_RULES_AND_BLOCKED_PUBLIC_ACCESS
step_17=INDEPENDENT_SIGNER_EMITS_HMAC_AUTHENTICATED_SIDECAR_BOUND_TO_RESULT_AND_ALL_RUNTIME_EVIDENCE
step_18=REVIEW_EXACT_RESULT_AND_SIDECAR_THEN_EMIT_ONE_CANONICAL_SANITIZED_SUCCESS_OR_HOLD_AND_STOP
production_database_connection=false
staging_database_connection=false
target_database_write=false
table_data_read=false
database_export=false
dynamic_sql=false
stored_or_volatile_function_execution=false
raw_value_output_or_persistence=false
runner_backup_restore_migration_deployment_or_deletion=false
retry_rule=NO_MANUAL_OR_AUTOMATIC_RETRY
failure_rule=HOLD_NO_RETRY_WITH_CRASH_SAFE_SUPERVISOR_CLEANUP
~~~

operational_collection_procedure_contract_end

The procedure-contract hash is SHA-256 over the exact ordered contract lines
inside the text fence, encoded as UTF-8 with one LF after every line. The two
markers and the Markdown fence are excluded. The package validator recomputes
and locks this hash. Future live authorization must name it explicitly.

The adapter must use fixed SQL only, TLS verify-full, session default
read-only, `BEGIN READ ONLY`, verification that `transaction_read_only=on`,
`search_path=pg_catalog`, bounded connect/statement/lock/idle timeouts,
rollback, and fully qualified catalog metadata reads. Tests must prove that
DML, DDL, `COPY`, `CALL`, `DO`, multiple statements, dynamic SQL, user-table
reads, volatile functions, disabled read-only mode, and a wrong endpoint are
rejected.

An in-process `finally` block remains required but is not crash-safe. Before
any allowlist mutation, a future independently running cleanup supervisor must
durably authenticate the attempt binding, ledger intent, exact CIDR ownership,
and target identity. It must remain able to perform the one authorized removal
and independent final empty-rule/public-block recheck after adapter process
death, while never removing a pre-existing or foreign rule. Supervisor
absence, stale evidence, uncertain ownership, duplicate removal, or ambiguous
save/recheck is `HOLD_NO_RETRY`. This repository package contains no such
supervisor and therefore cannot cross the live gate.

The offline reviewer must independently authenticate the entire runtime
evidence bundle, not compare adapter-controlled environment hashes. A future
independent signer writes one exact canonical JSON-LF sidecar with schema
`PMAI_P0_04_SRBE_V5_INDEPENDENT_RUNTIME_ATTESTATION_V1`. It HMAC-SHA256 signs a
domain-separated canonical payload covering the authorization and operator
hashes; Git OIDs; manifest, adapter, reviewer, schemas, procedure, invocation,
harness, port, ledger, supervisor, provenance, dependency, signer, and key-ID
bindings; expected and observed provider identities; target service and
contract; Attempt Binding V2 and authenticated ledger receipt/final state;
runtime-provenance receipt; TLS connect, negotiated-session, endpoint, and
fixed-SQL evidence; instrumentation and cleanup receipts; database observation
and connection binding; pre-restore schema hashes; final network state; and
the SHA-256 of the exact runtime-observation line reconstructed from the
SUCCESS result.

The independent HMAC key is exactly 32 nonzero bytes supplied only through an
anonymous pipe FD whose decimal descriptor number is named in
`PMAI_P0_04_V5_INDEPENDENT_ATTESTATION_HMAC_KEY_FD`. The FD cannot be 0, 1, or
2, a regular file, TTY, or socket. The key value never appears in argv,
environment, disk, output, or exception text; its domain-separated key ID must
equal `independent_attestation_hmac_key_id_sha256`, and it must be distinct
from the ledger and runtime-provenance keys. The ledger,
runtime-provenance, and independent-attestation key IDs must be pairwise
distinct and their key material must come from three separate anonymous FDs.
Future file review requires both
`--review-file ABSOLUTE_PATH` and
`--independent-attestation-file ABSOLUTE_PATH`. Missing, malformed, duplicate,
noncanonical, mismatched, unauthenticated, replayed, or self-signed sidecar
input is conservative `UNVERIFIED_REVIEW_INPUT` and `HOLD_NO_RETRY`. The old
two receipt-hash environment variables are not part of V5 and must not be
read.

The independent signer cannot share a trust boundary with the adapter,
reviewer, provider port, database port, or cleanup supervisor. This package's
self-tests use only synthetic anonymous pipes and synthetic HMAC keys; they do
not read inherited live values or create a live signer.

## 9. Current repository patch scope

~~~text
risk_lane=ORANGE_REPOSITORY_ONLY_HASH_LOCKED_OPERATIONAL_ADAPTER_PREPARATION
changed_path_scope=EXACT_13_PATHS
changed_path_sequence_normalization=UTF8_EACH_PATH_PLUS_LF_IN_DECLARED_ORDER
changed_path_sequence_sha256=59e58e5f3511fe8f666b3f9391d61a1814b140b4f73e4d437c5816ef97042a31
maximum_changed_path_count=13
maximum_new_file_count=12
maximum_existing_file_modification_count=1
package_path_count=12
manifest_member_count=11
manifest_self_excluded=true
maximum_commit_count=1
maximum_fast_forward_push_count=1
pull_request_creation_authorized=false
merge_authorized=false
force_push_authorized=false
branch_deletion_authorized=false
manual_ci_dispatch_or_retry_authorized=false
~~~

The exact ordered paths are:

1. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1.md`
2. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1_ACTIVE_POINTER_V1.json`
3. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1_CHECKLIST_V1.csv`
4. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1_GO_NO_GO_V1.csv`
5. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1_LOCKED_BASELINE_V1.json`
6. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1_PACKAGE_MANIFEST_V1.json`
7. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1_RUNTIME_OBSERVATION_SCHEMA_V1.json`
8. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1_SANITIZED_RESULT_SCHEMA_V1.json`
9. `docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ACTIVE_RESTORE_RUNNER_V3_SANITIZED_RUNTIME_BINDING_EVIDENCE_COLLECTION_AND_REVIEW_V5_CONTRACT_CORRECTION_AND_OPERATIONAL_ADAPTER_PREPARATION_V1_TEST_MATRIX_V1.csv`
10. `scripts/collect_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_sanitized_runtime_binding_evidence_collection_and_review_v5_operational_adapter_v1.py`
11. `scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_sanitized_runtime_binding_evidence_collection_and_review_v5_contract_correction_and_operational_adapter_preparation_v1.py`
12. `scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_active_restore_runner_v3_sanitized_runtime_binding_evidence_review_v5_operational_v1.py`
13. `scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py`

The manifest is one of the twelve package paths and excludes itself from its
eleven-member byte-hash inventory. Path 13 is the only existing file that may
change. It is the sole V4/V5 overlap: the current V4-owned marker block and
projection remain exact, and only the independent V5 successor-owned regions
outside that block are additive.

## 10. Repository-only validation and publication boundary

Locally authorized activity is limited to the exact thirteen-path source
rebuild, static validation, synthetic offline adapter/reviewer tests with all
external effects injected or mocked, one commit, and one post-commit
clean-worktree validation run. Push, bundle export, remote branch creation,
pull-request creation, merge, CI dispatch/retry, and every live V5 operation
remain outside this authorization.

~~~text
local_offline_synthetic_adapter_reviewer_tests_authorized=true
external_provider_database_and_network_calls_in_tests=false
live_adapter_mode_execution=false
Render_access=false
database_connection=false
credential_access=false
allowlist_mutation_execution=false
dependency_install_or_lockfile_change=false
runner_creation_activation_import_or_execution=false
backup_access=false
restore_execution=false
migration_creation_or_execution=false
deployment=false
target_deletion=false
pull_request_creation=false
merge=false
~~~

Any remote-base drift, branch collision, path collision, protected-byte drift,
unexpected active runner or migration 0010, validator failure, live-mode start,
external access, unexpected output, cleanup uncertainty, or publication
ambiguity is HOLD. There is no amend, retry, force-push, PR, or merge authority.

After merge, a new CI pass and a separate V5 single-use live confirmation are
still insufficient until all concrete B-contract components named in sections
7 and 8 are published, independently reviewed, and hash-locked; the
authenticated ledger and crash-safe supervisor have passed kill/restart and
filesystem fault tests; the independent signer and separate anonymous keys
exist; and an external anti-rollback witness has durably granted exactly one
attempt. The repository adapter and reviewer CLI remain hard-HOLD until a
separately authorized, exact, non-repository live harness satisfies every
gate. Until then, the global decision remains:

~~~text
HOLD_NO_LIVE_EXECUTION
~~~
