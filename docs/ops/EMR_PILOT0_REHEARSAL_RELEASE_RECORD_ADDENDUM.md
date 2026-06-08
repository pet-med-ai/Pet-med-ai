# Release record addendum: EMR pilot_0 dry-run rehearsal

Copy this section into the relevant `docs/ops/releases/*.md` record.

## EMR pilot_0 dry-run rehearsal evidence

```txt
rehearsal_id:
receipt_id:
batch_id:
clinical_signoff_id:
rollback_snapshot_id:
execution_dry_run_request_id:
clinical_approval_audit_log_id:
database_revision:
alembic_head:
schema_ok:
online_smoke_before:
online_smoke_after:
feature_flags_before:
feature_flags_after:
execute_blocked_status:
final_decision:
```

## Required conclusion

```txt
ENABLE_EMR_REAL_IMPORT remained false throughout rehearsal.
No Case was created.
No Case was updated.
No attachment was downloaded.
No prescription was written.
No billing row was written.
```

## Decision

```txt
GO / PAUSE / NO-GO / ROLLBACK-REVIEW:
Reason:
Decider:
Date:
```
