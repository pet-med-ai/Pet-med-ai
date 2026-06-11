# Preventive Care Reminder Safety SOP V1

## Purpose

This SOP defines how vaccine and deworming reminders must be presented safely in Pet-Med-AI.

## Required wording

Every reminder UI or message draft must include or imply:

```txt
This is a preventive care reminder, not a diagnosis or prescription.
Schedule and products must be confirmed by a veterinarian.
Rabies and regulated vaccines must follow local law and product label.
```

## No automatic external messaging in V1

V1 must not send:

```txt
SMS
WeChat
email
automated phone call
push notification outside the app
```

Allowed in future:

```txt
in-app reminder card
manual front desk call list
draft message pending human review
```

## Client opt-out

Future outbound messaging requires:

```txt
client consent
opt-out registry
channel preference
send history
unsubscribe path
```

## Clinician override

Every reminder must allow:

```txt
complete
snooze
dismiss
disable
change due date
change rule
override reason
```

## Hard No-Go

Do not implement automatic delivery if:

```txt
client consent not recorded
owner phone source uncertain
rabies local-law configuration missing
product label interval missing
no send log exists
no opt-out exists
```

## Safety markers

```txt
writes_database=false
creates_case=false
updates_case=false
sends_external_message=false
executes_real_import=false
```
