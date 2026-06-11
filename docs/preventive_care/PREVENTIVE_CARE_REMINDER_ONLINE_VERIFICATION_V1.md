# Preventive Care Reminder Online Verification V1

## Purpose

This stage defines the manual online verification procedure for the full Preventive Care Reminder flow after deployment.

It verifies that production frontend and backend can support:

```txt
Case detail preventive care reminder panel
dry-run vaccine/deworming reminder preview
in-app reminder creation
reminder complete / snooze / dismiss / disable
front desk manual notification queue
queue draft creation
queue manual review
queue manual contact marker
queue cancel
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
create Case records
update Case records
open ENABLE_EMR_REAL_IMPORT
execute EMR import
```

## Production URLs

```txt
Frontend: https://pet-med-ai-frontend-static.onrender.com
Backend: https://pet-med-ai-backend.onrender.com
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
```

## Browser verification A: Case detail reminder panel

### 1. Login

Open:

```txt
https://pet-med-ai-frontend-static.onrender.com
```

Login with a valid production user.

Do not use local `localhost` token for production verification.

### 2. Open owned Case

Open a Case from the authenticated user's own case list.

Do not directly guess:

```txt
/cases/1
```

Expected:

```txt
Case detail loads successfully
No 401
No 404
```

### 3. Confirm panel exists

Expected section:

```txt
预防保健提醒 / Preventive Care
```

Expected controls:

```txt
刷新站内提醒
生成疫苗/驱虫提醒预览
```

### 4. Generate dry-run preview

Click:

```txt
生成疫苗/驱虫提醒预览
```

Expected:

```txt
preview items appear or clear empty-state appears
writes_database=false
sends_external_message=false
no SMS / WeChat / email sent
```

### 5. Create in-app reminder

From a preview item, click:

```txt
创建站内提醒
```

Expected:

```txt
new reminder appears in existing reminder list
sends_external_message=false
creates_case=false
updates_case=false
```

### 6. Reminder actions

Test at least one reminder action:

```txt
完成
延后14天
关闭
禁用提醒
```

Expected:

```txt
status changes correctly
no external message sent
no Case created
no Case updated
```

## Browser verification B: Notification queue page

Open:

```txt
https://pet-med-ai-frontend-static.onrender.com/preventive-care/notification-queue
```

Expected title:

```txt
预防保健前台待联系队列
```

Expected visible safety markers:

```txt
auto_send=false
sends_external_message=false
```

### 1. Create draft queue item

Use a `reminder_id` created from the Case detail reminder panel or from smoke test output.

Click:

```txt
创建人工联系草稿
```

Expected:

```txt
draft queue item created
manual_review_required=true
auto_send=false
sends_external_message=false
```

### 2. Manual review

Click:

```txt
人工审核
```

Expected status:

```txt
reviewed
```

### 3. Mark manually contacted

Click:

```txt
标记已人工联系
```

Expected status:

```txt
contacted_manually
```

Important:

```txt
This records that a staff member manually contacted the owner.
The system itself must not send SMS / WeChat / email.
```

### 4. Cancel queue item

Create another draft or select an unused item, then click:

```txt
取消
```

Expected status:

```txt
canceled
```

## DevTools verification

Open browser DevTools Network tab.

For preventive care reminder API calls, verify:

```txt
HTTP 200 or 201 for successful actions
sends_external_message=false
creates_case=false
updates_case=false
executes_real_import=false
```

For notification queue API calls, verify:

```txt
manual_review_required=true
auto_send=false
sends_external_message=false
```

## Failure handling

### 401

Likely cause:

```txt
login token missing or expired
```

Action:

```txt
clear localStorage token
login again
open Case from case list
```

### 404

Likely cause:

```txt
case/reminder/queue item belongs to another user
or guessed id
```

Action:

```txt
open owned Case from list
use reminder_id created by the current logged-in user
```

### 500

Action:

```txt
pause verification
run online smoke
check backend Render logs
do not proceed to notification automation
```

### External message sent unexpectedly

Severity:

```txt
P0
```

Action:

```txt
stop release
disable affected feature
rotate/disable notification credentials if any exist
record security incident
```

## Hard No-Go

Any condition below means stop:

```txt
online smoke fails
GitHub Actions red
case detail cannot load owned Case
preventive care panel missing
dry-run writes database
in-app reminder creates or updates Case
notification queue sends external message
queue item auto-sends without human action
client opt-out is ignored
secret appears in browser console
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
