# Automated Reminder Delivery Incident Playbook V1

## Scope

This playbook applies to any future automated reminder delivery attempt.

It is included in the risk review stage before any implementation.

## P0 incidents

```txt
message sent after client opt-out
message sent to wrong owner
secret/provider credential leaked
system sends SMS / WeChat / email unexpectedly
automated message includes diagnosis or prescription language
delivery creates or updates Case
delivery executes EMR import
```

## Immediate actions

```txt
1. Stop release.
2. Set ENABLE_PREVENTIVE_AUTO_DELIVERY=false.
3. Set all channel flags false.
4. Disable provider credentials if needed.
5. Preserve delivery logs.
6. Run online smoke.
7. Check Render logs for secrets.
8. Notify release_owner, security_owner, clinical_ops_owner.
9. Record incident in release record.
```

## Investigation checklist

```txt
delivery_id
reminder_id
notification_id
owner_id
channel
provider_message_id
template_id
template_version
consent_snapshot
opt_out_snapshot
who approved send
feature flag state
provider credential access
logs redacted
```

## Client communication

Use clinic-approved language only.

Do not blame automation or disclose internal secrets.

## Recovery gate

Do not resume delivery until:

```txt
root cause documented
fix reviewed
smoke passes
manual test passes
client impact reviewed
release_owner approves
security_owner approves for P0 security issues
clinical_ops_owner approves for client/clinical issues
```

## Safety markers

```txt
auto_send=false
sends_external_message=false
manual_review_required=true
creates_case=false
updates_case=false
executes_real_import=false
```
