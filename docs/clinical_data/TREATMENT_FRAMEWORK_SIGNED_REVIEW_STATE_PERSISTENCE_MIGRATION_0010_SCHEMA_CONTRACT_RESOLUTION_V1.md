# PMAI-P0-04 Signed Review State Schema Contract Resolution V1

stage_id=PMAI-P0-04
contract_id=PMAI-P0-04-SCHEMA-CONTRACT-RESOLUTION-V1
contract_resolution_baseline_commit_sha=5262f1438c7a36137c930301c36f82ed05dc56ff
schema_contract_resolution_recorded=true
migration_schema_review_approved=true
approval_scope=GOVERNANCE_ONLY_NOT_EXECUTION_AUTHORIZATION
corrected_migration_implementation_authorized=false
active_0010_migration_file_created=false
staging_0010_apply_authorized=false
p0_04_execution_authorized=false
decision=HOLD_PMAI_P0_04_PENDING_DEPLOYMENT_ISOLATION_BACKUP_REHEARSAL_AND_EXTERNAL_EVIDENCE

## Immutable source finding

The inactive `.py.txt` draft stays unchanged and is not approved for activation.
Its revision is 45 characters, its audit reference is nullable `String(120)`
without a foreign key, it lacks an idempotency constraint, it permits mutable
rows, and it does not state case deletion behavior. This resolution records a
replacement governance contract only.

inactive_draft_sha256=bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d
inactive_draft_activation_authorized=false

## Approved future schema contract

approved_revision=0010_signed_review_states
approved_revision_length=25
approved_down_revision=0009_diag_data
approved_table=treatment_framework_signed_review_states
approved_table_creation_mode=ADDITIVE_ONLY
approved_case_id_type=Integer
approved_case_id_nullable=false
approved_case_fk_name=fk_tfsrs_case_id_cases
approved_case_fk_target=cases.id
approved_case_fk_ondelete=RESTRICT
approved_audit_log_id_type=String(64)
approved_audit_log_id_nullable=false
approved_audit_log_composite_fk_name=fk_tfsrs_audit_log_same_case
approved_audit_log_composite_fk_local_columns=audit_log_id|case_id
approved_audit_log_composite_fk_target=audit_log.log_id|audit_log.case_id
approved_audit_log_composite_fk_ondelete=RESTRICT
approved_audit_log_composite_fk_expression=ForeignKeyConstraint([audit_log_id|case_id],[audit_log.log_id|audit_log.case_id])
approved_audit_log_composite_unique_name=uq_audit_log_log_id_case_id
approved_audit_log_id_unique_name=uq_tfsrs_audit_log_id
approved_audit_log_index_name=ix_tfsrs_audit_log_id
approved_audit_event_type=treatment_framework_signed_review_state_persisted
approved_audit_source=treatment_framework_signed_review_state_persistence_v1
approved_audit_action_taken=signed_review_state_persisted
approved_audit_clinician_match=signed_by
approved_audit_request_id_match=idempotency_key
approved_audit_payload_hash_storage_column=metadata
approved_audit_payload_hash_sql_expression=metadata->>'payload_sha256'
approved_audit_payload_hash_non_null=true
approved_audit_payload_hash_match=payload_sha256
approved_audit_semantics_trigger_name=trg_tfsrs_validate_audit_semantics
approved_audit_semantics_lock=SELECT_AUDIT_ROW_FOR_SHARE
approved_audit_link_protection_trigger_name=trg_audit_log_protect_tfsrs_link
approved_audit_link_protection_trigger_requirement=REJECT_REFERENCED_AUDIT_UPDATE_AND_DELETE
approved_idempotency_key_type=String(64)
approved_idempotency_key_nullable=false
approved_idempotency_key_unique_name=uq_tfsrs_idempotency_key
approved_idempotency_key_format=cryptographically_random_32_bytes_lowercase_hex_64
approved_payload_sha256_type=String(64)
approved_payload_sha256_nullable=false
approved_payload_sha256_format=lowercase_hex_sha256_64
approved_supersedes_state_id_type=Integer
approved_supersedes_state_id_nullable=true
approved_supersedes_same_case_fk_name=fk_tfsrs_supersedes_same_case
approved_supersedes_same_case_ondelete=RESTRICT
approved_state_id_case_unique_name=uq_tfsrs_id_case_id
approved_supersedes_state_id_unique_name=uq_tfsrs_supersedes_state_id
approved_supersedes_not_self_check_name=ck_tfsrs_supersedes_not_self
approved_one_root_per_case_index_name=uq_tfsrs_one_root_per_case
approved_one_root_per_case_index_predicate=supersedes_state_id_IS_NULL
approved_row_lifecycle=IMMUTABLE_VERSIONED_APPEND_ONLY
approved_append_only_trigger_name=trg_tfsrs_append_only
approved_append_only_trigger_requirement=REJECT_UPDATE_AND_DELETE
approved_active_case_insert_trigger_name=trg_tfsrs_require_active_case
approved_active_case_insert_trigger_requirement=REJECT_INSERT_WHEN_CASE_DELETED_AT_IS_NOT_NULL
approved_active_case_insert_lock=SELECT_CASE_WHERE_DELETED_AT_NULL_FOR_SHARE
approved_created_at_type=DateTime(timezone=True)
approved_created_at_nullable=false
approved_signed_at_type=DateTime(timezone=True)
approved_signed_at_nullable=false
approved_updated_at_present=false
approved_case_soft_delete_behavior=RETAIN_EXISTING_ROWS_AND_REJECT_NEW_WRITES
approved_confirmation_source_vocabulary=clinician_entered|clinician_confirmed
approved_confirmation_source_input_mapping=clinician->clinician_entered|clinician_entered->clinician_entered|clinician_confirmed->clinician_confirmed
approved_review_decision_vocabulary=approve_for_clinician_use|request_revision|reject
approved_review_decision_input_mapping=approve_for_clinician_use->approve_for_clinician_use|request_revision->request_revision|reject->reject
approved_signed_review_status_vocabulary=signed_internal_review|revision_requested|rejected
approved_signed_review_status_input_mapping=signed_internal_review_preview->signed_internal_review|revision_requested_preview->revision_requested|rejected_preview->rejected
approved_signoff_decision_vocabulary=sign_internal_review|request_revision|reject
approved_signoff_decision_input_mapping=sign_internal_review->sign_internal_review|signed_internal_review->sign_internal_review|approve_signed_review->sign_internal_review|request_revision->request_revision|revision_requested->request_revision|reject->reject|rejected->reject
approved_finite_vocabulary_enforcement=DATABASE_CHECK_CONSTRAINTS_REQUIRED
approved_clinical_payload_scope=SIGNED_INTERNAL_REVIEW_STATE_ONLY
case_treatment_column_write_allowed=false
prescription_write_allowed=false
dose_route_frequency_storage_allowed=false
client_facing_release_allowed=false

The future active migration must add a unique constraint on
`audit_log(log_id, case_id)` before creating the composite foreign key
`(audit_log_id, case_id) -> audit_log(log_id, case_id)`. This prevents a signed
review state from pointing to an audit row for another case. Audit rows with a
null case cannot be used for this table. `audit_log_id` is unique in the new
table, so one append-only audit event cannot authorize two state rows.

The linked audit row must have exactly the approved event type, source, and
action; `audit_log.clinician_id` must equal the authenticated `signed_by`,
`audit_log.request_id` must equal `idempotency_key`, and
the physical PostgreSQL expression
`audit_log.metadata->>'payload_sha256'` must return a non-null string equal to
the state's `payload_sha256`. (`extra_data` is the ORM attribute, but
`metadata` is the physical database column.) The future migration must install
a state INSERT trigger that verifies these values while selecting the audit row
`FOR SHARE`, closing the race with an audit UPDATE. It must also install a
trigger on `audit_log` that rejects UPDATE or DELETE of any row referenced by a
signed review state. This preserves the semantic link after the state insert;
changing only `log_id` or `case_id` is not the complete threat model.

Each new state creation uses a cryptographically random 32-byte opaque token
encoded as 64 lower-case hexadecimal characters for `idempotency_key`; it is
not a content hash. The key is copied to `audit_log.request_id`. The audit
append and state insert must be one transaction. A retry with the same key and
same `payload_sha256` returns the existing state and audit row without another
write. The same key with a different hash returns HTTP 409 and performs no
write. A concurrent unique-constraint loser must roll back its candidate audit
row before reading the winner. Owner scope, actor identity, audit semantics,
and authentication must be checked again before returning an idempotent replay.

`payload_sha256` is the lower-case 64-character SHA-256 of the canonical state
payload. Version replacement inserts a new immutable row with
`supersedes_state_id`; it never updates or deletes an existing row. A
predecessor may be consumed by at most one successor, preventing branching
histories. The composite self-reference must enforce the same `case_id` and a
check constraint must reject self-reference. The migration must also create the
PostgreSQL partial unique index
`uq_tfsrs_one_root_per_case ON treatment_framework_signed_review_states(case_id)
WHERE supersedes_state_id IS NULL`, so concurrent inserts cannot establish
multiple roots for one case.

The future migration must install database triggers that reject UPDATE and
DELETE and reject INSERT when `cases.deleted_at` is non-null. There is no
`updated_at` column. Existing state rows remain attached to a soft-deleted
case. Physical deletion of a referenced case, audit row, or predecessor is
blocked by `RESTRICT`. The active-case INSERT trigger must perform
`SELECT id FROM cases WHERE id = NEW.case_id AND deleted_at IS NULL FOR SHARE`
and fail when no row is returned. `FOR SHARE`, rather than `FOR KEY SHARE`,
closes the race with a concurrent `deleted_at` update: a state committed before
the soft delete may remain, while every insert after the soft delete commits
must fail.

Downgrade is permitted only in a disposable rehearsal database after a
verified zero-row check. Recovery for any populated environment is backup
restore, not destructive downgrade.

## Finite values required in the future migration

confirmation_source_vocabulary=clinician_entered|clinician_confirmed
review_decision_vocabulary=approve_for_clinician_use|request_revision|reject
signed_review_status_vocabulary=signed_internal_review|revision_requested|rejected
signoff_decision_vocabulary=sign_internal_review|request_revision|reject
finite_vocabulary_enforcement=DATABASE_CHECK_CONSTRAINTS_REQUIRED

These are persisted canonical values. The future persistence adapter must
implement the exact input-to-persisted mappings recorded above, including
`clinician -> clinician_entered` and removal of the three preview-only status
suffixes. The adapter mapping and database CHECK constraints require review
together before any write endpoint is authorized. No free-form value outside
these exact persisted vocabularies may be stored.
`confirmed_by`, `reviewed_by`, and `signed_by` must come from authenticated
actor context, never unchecked request-body identity strings.

The persisted row is an internal clinical review state. It must not store or
write `Case.treatment`, prescriptions, medication names, dose, route,
frequency, or client-facing instructions.

## Unresolved gates

deployment_isolation_verified=false
fresh_post_p0_03_staging_backup_verified=false
disposable_restore_rehearsal_complete=false
source_staging_fresh_backup_verified=false
source_commit_sha_pinned=false
active_migration_sha256_pinned=false
exact_target_upgrade_command_approved=false
staging_0010_migration_executed=false
production_remains_0009_verified=false
external_execution_evidence_complete=false

P0-04 remains IN_PROGRESS. The approved contract does not authorize an active
file, `alembic upgrade`, `alembic stamp`, a database connection, staging deploy,
or production deployment. The remaining deployment isolation, backup, restore
rehearsal, source apply, and post-apply evidence gates continue to be
NO_GO_TO_PMAI_P0_04_EXECUTION.
