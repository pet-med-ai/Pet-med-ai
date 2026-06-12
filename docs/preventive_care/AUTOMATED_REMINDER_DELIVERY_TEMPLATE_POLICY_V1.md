# Automated Reminder Delivery Template Policy V1

## Purpose

Defines future message template rules for automated preventive care reminders.

## Required template metadata

```txt
template_id
template_version
channel
language
category
approved_by
approved_at
review_status
clinical_safety_text
opt_out_text
```

## Required wording

Templates must include or imply:

```txt
This is a preventive care reminder, not a diagnosis or prescription.
Schedule and products must be confirmed by a veterinarian.
Rabies and regulated vaccines must follow local law and product label.
```

## Forbidden wording

Do not include:

```txt
confirmed diagnosis
prescription order
dose instruction
guaranteed vaccine legality
fear-based urgency language
private clinical details not needed for reminder
```

## First pilot template scope

Allowed first-pilot content:

```txt
annual wellness exam reminder
general parasite prevention review reminder
manual appointment reminder
```

Disallowed first-pilot content:

```txt
rabies reminders
regulated vaccine timing
drug dose reminders
diagnosis-specific content
```

## Template approval

Required reviewers:

```txt
clinical_ops_owner
clinic_owner or release_owner
```

## Current stage marker

```txt
no template is approved for automated delivery in this stage
sends_external_message=false
```
