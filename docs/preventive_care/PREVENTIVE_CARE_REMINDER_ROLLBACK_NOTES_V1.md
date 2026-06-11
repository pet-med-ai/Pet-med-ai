# Preventive Care Reminder Rollback Notes V1

## Purpose

This document defines rollback/pause handling for Preventive Care Reminder V1.

## Scope

Applies to:

```txt
preventive care reminder tables
preventive care API
preventive care UI
manual notification queue
```

## Feature rollback

If UI behavior is wrong but database is safe:

```txt
1. Disable frontend navigation link in a hotfix.
2. Keep backend API available only if smoke still passes.
3. Record issue in release record.
4. Do not delete reminder data.
```

## API rollback

If API creates wrong records but no external message is sent:

```txt
1. Stop using UI/API.
2. Deploy hotfix disabling write endpoints.
3. Keep read-only list endpoints for inspection if safe.
4. Preserve records for audit.
```

## Database rollback

Do not drop preventive care tables casually after production data exists.

Preferred:

```txt
mark feature paused
preserve data
patch API/UI
```

Only consider Alembic downgrade if:

```txt
release is not yet used by real users
backup verified
rollback owner online
online smoke plan ready
```

## P0 rollback trigger

```txt
system sends external SMS / WeChat / email unexpectedly
client opt-out ignored
secret leaked in console/logs
Case records created or updated unexpectedly
EMR import executed unexpectedly
```

Immediate action:

```txt
1. Stop release.
2. Disable affected UI/API route if needed.
3. Rotate notification credentials if any exist.
4. Run online smoke.
5. Record incident and rollback decision.
```

## Safety markers

```txt
sends_external_message=false
auto_send=false
manual_review_required=true
creates_case=false
updates_case=false
executes_real_import=false
```
