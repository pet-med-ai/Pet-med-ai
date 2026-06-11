# Preventive Care Reminder Ops Dashboard Online Verification V1

## Purpose

This stage defines the manual online verification procedure for the Preventive Care Reminder Ops Dashboard after deployment.

It verifies that production frontend and backend can show a read-only operational summary for:

```txt
open preventive reminders
due-today reminders
due-soon reminders
overdue reminders
manual notification queue items
queue items needing review
manual contacted queue items
blocked opt-out queue items
recent preventive-care events
read-only safety gates
```

This stage is verification documentation and validation only.

It does not:

```txt
change backend code
change frontend code
change database schema
run Alembic
send SMS
send WeChat
send email
create background worker
auto-contact clients
create reminders
create queue items
create Case records
update Case records
open ENABLE_EMR_REAL_IMPORT
execute EMR import
```

## Production URLs

```txt
Frontend: https://pet-med-ai-frontend-static.onrender.com
Backend: https://pet-med-ai-backend.onrender.com
Ops Dashboard: https://pet-med-ai-frontend-static.onrender.com/ops
Queue page: https://pet-med-ai-frontend-static.onrender.com/preventive-care/notification-queue
```

## Required previous stages

All must be complete:

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
Preventive Care Reminder Ops Dashboard V1
GitHub Actions CI Gate V1
Render / GitHub Security Hardening V1
Backup / Rollback Verification V1
```

## Pre-verification gates

Before browser testing:

```bash
cd ~/Documents/Pet-med-ai

git pull origin main
bash scripts/ci_static_checks.sh
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Required result:

```txt
CI static checks PASS
online smoke ALL PASS
GitHub Actions CI Gate latest run green
frontend Render deploy live
backend Render deploy live
database_revision == alembic_head
database_revision == 0007_preventive_care
schema_ok=true
```

## Browser verification

### 1. Login

Open:

```txt
https://pet-med-ai-frontend-static.onrender.com
```

Login with a valid production user.

Do not use local `localhost` token for production verification.

### 2. Prepare data

The Ops Dashboard can show zeros if the current user has no reminders or queue items.

For a meaningful verification, either:

```txt
run online smoke first
or create one in-app preventive reminder from a real owned Case
or create one notification queue draft from the queue page
```

Expected if no user data exists:

```txt
cards show 0
safety gates still show OK
```

### 3. Open Ops Dashboard

Open:

```txt
https://pet-med-ai-frontend-static.onrender.com/ops
```

Expected section:

```txt
Preventive Care Reminder Ops Dashboard V1
```

Expected cards:

```txt
Preventive attention
Reminders open
Due today
Queue needs review
Manual contacted
Blocked opt-out
Recent events 30d
```

Expected safety table:

```txt
read_only / writes_database
auto_send / sends_external_message
manual review
```

### 4. Verify safety markers

The visible section must include:

```txt
read_only=true
writes_database=false
auto_send=false
sends_external_message=false
manual_review_required=true
```

### 5. Network verification

Open DevTools Network and refresh `/ops`.

Find:

```txt
GET /api/preventive-care/ops/summary
```

Expected:

```txt
HTTP 200
message=preventive_care_ops_summary
mode=preventive_care_reminder_ops_dashboard_v1
safety.read_only=true
safety.writes_database=false
safety.auto_send=false
safety.sends_external_message=false
safety.manual_review_required=true
creates_case=false
updates_case=false
executes_real_import=false
```

### 6. Cross-link verification

From Ops Dashboard, click:

```txt
Preventive Queue
```

Expected route:

```txt
/preventive-care/notification-queue
```

Expected page title:

```txt
预防保健前台待联系队列
```

Return to:

```txt
/ops
```

### 7. Zero-data behavior

If the logged-in user has no reminders or queue items, the dashboard may show:

```txt
Reminders open = 0
Queue needs review = 0
Manual contacted = 0
Blocked opt-out = 0
Recent events 30d = 0
```

This is acceptable if safety gates are OK and API returns `HTTP 200`.

## Failure handling

### Ops section missing

Likely cause:

```txt
frontend deploy stale
frontend build failed
wrong Render static deploy
```

Action:

```txt
check GitHub Actions frontend build
check Render frontend deploy
hard refresh browser
```

### `/api/preventive-care/ops/summary` returns 401

Likely cause:

```txt
login token missing or expired
```

Action:

```txt
clear localStorage token
login again
refresh /ops
```

### `/api/preventive-care/ops/summary` returns 500

Likely cause:

```txt
backend deploy mismatch
database migration not applied
table missing
```

Action:

```txt
run online smoke
check Render backend logs
confirm /api/system/version schema_ok=true
confirm database_revision == alembic_head == 0007_preventive_care
```

### Safety gate shows CHECK

If any of the following is not as expected:

```txt
read_only=true
writes_database=false
auto_send=false
sends_external_message=false
manual_review_required=true
```

Action:

```txt
pause release
do not proceed to notification automation
capture screenshot and Network response
```

## Hard No-Go

Any condition below means stop:

```txt
online smoke fails
GitHub Actions red
schema_ok=false
database_revision != alembic_head
database_revision != 0007_preventive_care
Preventive Care Ops section missing after confirmed frontend deploy
summary endpoint writes database
summary endpoint sends external message
summary endpoint creates or updates Case
auto_send is true
manual_review_required is false
secret appears in browser console or Render logs
```

## Completion criteria

This stage is complete when:

```txt
1. Online verification runbook exists.
2. Checklist exists.
3. Evidence template exists.
4. Triage template exists.
5. Release record addendum exists.
6. Validator exists and is included in smoke.
7. CI static checks include validator.
8. GitHub Actions latest run green.
9. Online smoke ALL PASS.
10. Manual browser verification completed.

```
