# Release record addendum: EMR pilot_0 final Go / No-Go

Copy this section into the relevant `docs/ops/releases/*.md` record.

## Final Go / No-Go evidence

```txt
final_review_id:
decision_id:
release_id:
git_commit:
github_actions_run_url:
ci_static_checks_result:
frontend_build_result:
online_smoke_before:
database_revision:
alembic_head:
schema_ok:
feature_flags_before:
security_hardening_complete:
security_check_result:
render_log_review_result:
backup_id:
rollback_snapshot_id:
restore_path_known:
rollback_owner:
receipt_id:
batch_id:
batch_status:
batch_receipt_count:
receipt_status:
clinical_signoff_id:
execution_dry_run_quality_gate:
would_create_count:
would_update_count:
blocked_count:
clinical_owner:
operator_id:
post_execution_reviewer:
```

## Final decision

```txt
GO / PAUSE / NO-GO / ROLLBACK-REVIEW:
Reason:
Decider:
Decision time:
```

## If GO

```txt
Approved controlled execution window:
Feature flag before: ENABLE_EMR_REAL_IMPORT=false
Feature flag during: ENABLE_EMR_REAL_IMPORT=true
Feature flag after: ENABLE_EMR_REAL_IMPORT=false
Max receipts: 1
Max cases to create: 1
Updates allowed: false
Attachments allowed: false
Prescriptions allowed: false
Billing allowed: false
```
