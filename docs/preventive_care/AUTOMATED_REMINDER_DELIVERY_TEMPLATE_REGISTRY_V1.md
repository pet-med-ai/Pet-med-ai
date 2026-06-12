# Automated Reminder Delivery Template Registry V1

## Purpose

This stage adds a backend template registry for future automated preventive care reminder delivery.

It supports:

```txt
list templates
create draft template
read one template
render preview
review / approve / reject template
retire template
```

This stage does not send any external message.

It does not:

```txt
send SMS
send WeChat
send email
call provider APIs
create provider credentials
create background workers
create cron jobs
create delivery attempts
create Case records
update Case records
execute EMR import
```

## Endpoint prefix

```txt
/api/automated-reminder-delivery/templates
```

## Endpoints

```txt
GET /api/automated-reminder-delivery/templates
POST /api/automated-reminder-delivery/templates
GET /api/automated-reminder-delivery/templates/{template_id}
POST /api/automated-reminder-delivery/templates/{template_id}/render-preview
POST /api/automated-reminder-delivery/templates/{template_id}/review
POST /api/automated-reminder-delivery/templates/{template_id}/retire
```

## Template statuses

```txt
draft
approved
changes_requested
rejected
retired
```

## Safety boundary

```txt
dry_run=true for render-preview
auto_send=false
sends_external_message=false
creates_case=false
updates_case=false
executes_real_import=false
```

Write endpoints may write the template registry:

```txt
writes_database=true
writes_template_registry=true
```

but they must not:

```txt
send external message
create delivery attempt
create Case
update Case
execute EMR import
```

## Approval note

Template approval in this stage means:

```txt
approved for registry / future dry-run use
```

It does not mean:

```txt
approved for live SMS / WeChat / email delivery
```

Live delivery remains disabled until future provider, dry-run, manual approval and pilot stages pass.

## Completion criteria

```txt
1. backend/automated_reminder_delivery_template_api.py exists.
2. backend/main.py includes automated_reminder_delivery_template_api_router.
3. validator exists and passes.
4. smoke covers create, list, render-preview, review, retire.
5. CI static checks include validator.
```
