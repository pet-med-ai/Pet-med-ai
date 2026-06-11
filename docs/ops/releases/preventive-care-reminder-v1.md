# Release: preventive-care-reminder-v1

## Summary

```txt
release_name: preventive-care-reminder-v1
risk_class: clinical_workflow_in_app
owner: HS-0001
status: draft
decision: NO-GO
```

## Included stages

```txt
Preventive Care Reminder Spec V1
Preventive Care Reminder Data Model V1
Preventive Care Reminder Rule Engine Dry-run V1
Preventive Care Reminder API V1
Preventive Care Reminder UI V1
Preventive Care Reminder Notification Queue V1
Preventive Care Reminder Notification Queue UI V1
Preventive Care Reminder Online Verification V1
Preventive Care Reminder Release Record V1
```

## Evidence

```txt
git_commit:
github_actions_run_url:
ci_static_checks_result:
online_smoke_result:
database_revision:
alembic_head:
schema_ok:
online_case_detail_verified:
online_notification_queue_verified:
auto_send_false_verified:
sends_external_message_false_verified:
client_opt_out_verified:
```

## Safety statement

```txt
Preventive Care Reminder V1 is in-app/manual-contact only.
No automatic SMS was sent.
No automatic WeChat was sent.
No automatic email was sent.
No Case was created.
No Case was updated.
No EMR import was executed.
```

## Final decision

```txt
GO / PAUSE / NO-GO / ROLLBACK-REVIEW:
Reason:
Decider:
Decision time:
```
