# Client Data Opt-Out SOP V1

> Template only. Must be reviewed and adapted by qualified local legal/professional counsel before use.

## Purpose

This SOP defines how the clinic records and honors client opt-out requests for
reminder/contact workflows in Pet-Med-AI Commercial V1.

## Scope

Applies to:

```txt
preventive care reminder contact workflow
front-desk manual contact queue
non-essential follow-up reminders
future external communication channels if separately approved
```

Does not automatically apply to:

```txt
legally required records
clinical records needed for ongoing care
safety-critical direct communications
billing or contractual records if separately applicable
```

Local policy/legal review must define exact retention and deletion obligations.

## Opt-out intake

When a client requests opt-out, record:

```txt
client / owner identifier
pet identifier if applicable
request date/time
request channel
request type
staff member
notes
```

Request types:

```txt
opt_out_all_reminders
opt_out_sms
opt_out_wechat
opt_out_email
opt_out_nonessential_manual_contact
data_access_request
data_correction_request
data_deletion_request_review_needed
```

## Immediate action

For reminder/contact opt-out:

```txt
record opt_out_all=true or channel-specific preference
cancel or pause open non-essential queue items
do not create new non-essential contact tasks unless clinically necessary
document staff member and timestamp
confirm with client using approved clinic process
```

## Channel-specific Commercial V1 note

Commercial V1 has no live SMS/WeChat/email automated sending.

Still record channel preferences so that future stages do not accidentally
contact clients without review.

## Deletion / withdrawal requests

If a client requests deletion or withdrawal of consent:

```txt
do not delete clinical records automatically
record the request
escalate to clinic_owner / legal_review_owner
determine what must be retained for clinical, legal or audit reasons
document the decision
respond according to clinic policy
```

## Audit

Every opt-out handling record should include:

```txt
who recorded it
when it was recorded
what was changed
what queue items were affected
whether any contact occurred after the request
```

## Failure handling

If a client is contacted after opt-out:

```txt
treat as an incident
preserve evidence
identify affected client and queue item
stop further contact
notify clinical_ops_owner and security_owner
record corrective action
```

## Version

```txt
SOP version: Client Data Opt-Out SOP V1
Owner: clinical_ops_owner
Review required before Final Go / No-Go V1
```
