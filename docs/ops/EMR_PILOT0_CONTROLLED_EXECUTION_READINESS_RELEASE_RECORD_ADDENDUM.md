# Release record addendum: pilot_0 controlled execution readiness review

Copy this section into the release record before any real pilot_0 execution.

## Readiness evidence

```txt
release_id:
git_commit:
github_actions_run_url:
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
clinical_approval_audit_log_id:
online_smoke_before:
operator_id:
clinical_owner:
rollback_owner:
```

## Decision

```txt
GO / PAUSE / NO-GO / ROLLBACK-REVIEW:
Reason:
Decider:
Decision time:
```

## If GO

Record the approved controlled window:

```txt
window_start:
window_end:
ENABLE_EMR_REAL_IMPORT before:
ENABLE_EMR_REAL_IMPORT during:
ENABLE_EMR_REAL_IMPORT after:
post-execution smoke owner:
clinical spot-check owner:
rollback owner:
```

## Safety statement

```txt
Only ENABLE_EMR_REAL_IMPORT may be temporarily enabled.
Case updates remain disabled.
Attachment downloads remain disabled.
Prescription writes remain disabled.
Billing writes remain disabled.
Case deletes remain disabled.
```
