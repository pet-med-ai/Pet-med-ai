# Automated Reminder Delivery Consent / Opt-out Design V1

## Purpose

Defines consent and opt-out requirements before any automated delivery is implemented.

## Required consent model

Every owner must have:

```txt
owner_id
allow_in_app
allow_sms
allow_wechat
allow_email
opt_out_all
preferred_channel
updated_at
updated_by
consent_source
```

## Channel-specific consent

Automated send is blocked if:

```txt
opt_out_all=true
selected channel allow_* is false
consent timestamp missing
consent source unknown
owner contact missing
```

## Opt-out snapshot

Every future delivery attempt must store:

```txt
opt_out_snapshot
channel_permission_snapshot
consent_updated_at_snapshot
contact_destination_hash
```

## Enforcement point

Opt-out must be checked:

```txt
when queue item is created
when manual review happens
immediately before provider send
when provider retries
```

## No override

Client opt-out cannot be bypassed by UI convenience.

Any override must require:

```txt
clinical_ops_owner approval
written reason
new audit event
no automated send until resolved
```

## Current stage marker

```txt
sends_external_message=false
auto_send=false
manual_review_required=true
```
