# Release record addendum: Automated Reminder Delivery Pilot Runbook

Copy this section into the current release record before any future pilot.

## Pilot evidence

```txt
pilot_id:
date:
operator_id:
clinical_ops_owner:
release_owner:
rollback_owner:
security_owner:
git_commit:
github_actions_run_url:
online_smoke_before:
database_revision:
alembic_head:
schema_ok:
channel:
candidate_count:
template_ids:
dry_run_attempt_ids:
manual_approval_ids:
kill_switch_tested:
provider_sandbox_result:
```

## Safety statement

```txt
This stage did not send SMS.
This stage did not send WeChat.
This stage did not send email.
This stage did not call provider APIs.
This stage did not create provider credentials.
This stage did not create background workers.
This stage did not create or update Case.
This stage did not execute EMR import.
Automated delivery remains disabled.
```

## Pilot decision

```txt
GO / PAUSE / NO-GO / ROLLBACK-REVIEW:
Reason:
Required next stage:
```

## Required next stage if GO

```txt
Automated Reminder Delivery Provider Adapter Sandbox V1
```
