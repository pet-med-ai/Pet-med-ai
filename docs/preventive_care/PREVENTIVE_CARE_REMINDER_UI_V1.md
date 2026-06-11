# Preventive Care Reminder UI V1

## Purpose

This stage adds in-app preventive care reminder UI on the Case detail page.

It connects to the completed backend API:

```txt
GET /api/preventive-care/reminders
POST /api/preventive-care/dry-run
POST /api/preventive-care/reminders
POST /api/preventive-care/reminders/{reminder_id}/complete
POST /api/preventive-care/reminders/{reminder_id}/snooze
POST /api/preventive-care/reminders/{reminder_id}/dismiss
POST /api/preventive-care/reminders/{reminder_id}/disable
```

## Scope

The UI supports:

```txt
view reminders for the current Case
run vaccine/deworming dry-run preview
create an in-app reminder from preview
complete reminder
snooze reminder
dismiss reminder
disable reminder / client opt-out for that reminder
```

## Safety boundary

This UI is in-app only.

```txt
sends_external_message=false
creates_case=false
updates_case=false
executes_real_import=false
```

It does not:

```txt
send SMS
send WeChat
send email
create Case
update Case
open ENABLE_EMR_REAL_IMPORT
create notification worker
```

## User flow

```txt
1. User opens Case detail.
2. Preventive care panel loads existing reminders for that Case.
3. User clicks 生成疫苗/驱虫提醒预览.
4. UI shows due/overdue/due_soon reminders.
5. User can create an in-app reminder from a preview item.
6. Existing reminders can be completed, snoozed, dismissed, or disabled.
```

## Required UI labels

```txt
预防保健提醒 / Preventive Care
生成疫苗/驱虫提醒预览
创建站内提醒
完成
延后14天
关闭
禁用提醒
```

## Completion criteria

```txt
1. CaseDetail.jsx includes preventive care reminder panel.
2. UI calls /api/preventive-care/dry-run.
3. UI calls /api/preventive-care/reminders.
4. UI has no external messaging behavior.
5. Validator is included in smoke and CI static checks.
6. Frontend build passes.
```
