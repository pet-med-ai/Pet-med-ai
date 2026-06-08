# Release record addendum: EMR pilot_0 controlled execution window

Copy this section into the relevant `docs/ops/releases/*.md` record.

## Pre-window evidence

```txt
final_go_no_go_decision:
git_commit:
github_actions_run_url:
online_smoke_before:
database_revision:
alembic_head:
schema_ok:
feature_flags_before:
backup_id:
rollback_snapshot_id:
receipt_id:
batch_id:
clinical_signoff_id:
execution_dry_run_quality_gate:
would_create_count:
would_update_count:
blocked_count:
```

## Execution window

```txt
window_id:
window_start:
window_end:
operator_id:
clinical_reviewer:
rollback_owner:
ENABLE_EMR_REAL_IMPORT before:
ENABLE_EMR_REAL_IMPORT during:
ENABLE_EMR_REAL_IMPORT after:
```

## Execution result

```txt
execution_id:
audit_log_id:
created_case_id:
receipt_count:
created_count:
updated_count:
skipped_count:
failed_count:
raw_response_path:
```

## Post-window

```txt
online_smoke_after:
clinical_spot_check:
duplicate_check:
rollback_required:
closeout_decision:
```

## Safety statement

```txt
Exactly one receipt was executed.
At most one Case was created.
No Case update was performed.
No attachment was downloaded.
No prescription was written.
No billing row was written.
ENABLE_EMR_REAL_IMPORT was disabled after execution.
```
