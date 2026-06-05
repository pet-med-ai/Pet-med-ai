# EMR import execution result model V1

## Stage boundary

This phase adds database structures for recording future real EMR import execution results.

It does not implement a real import execution endpoint and it does not create or update `cases`.

## New tables

### `emr_import_execution_runs`

Records one future execution run for an approved EMR import batch.

Important fields:

- `execution_id`
- `batch_id`
- `status`
- `operator_id`
- `clinical_signoff_id`
- `rollback_snapshot_id`
- `approval_audit_log_id`
- `receipt_count`
- `created_count`
- `updated_count`
- `skipped_count`
- `failed_count`
- `rolled_back_count`
- `started_at`
- `completed_at`
- `rolled_back_at`

### `emr_import_execution_item_results`

Records the future per-receipt execution result inside an execution run.

Important fields:

- `execution_id`
- `batch_id`
- `receipt_id`
- `external_case_id`
- `external_encounter_id`
- `operation`
- `status`
- `created_case_id`
- `target_case_id`
- `failure_code`
- `failure_reason`
- `rollback_status`
- `rollback_note`
- `case_diff`
- `result_payload`

## Safety boundary

This model phase:

```txt
writes_schema=true
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

## Follow-up phase

A future real execution API may use these tables to record actual execution results. That future stage must still pass a separate implementation, smoke, rollback and clinical signoff review.
