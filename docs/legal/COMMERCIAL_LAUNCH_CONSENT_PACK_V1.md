# Commercial Launch Legal / Consent Pack V1

## Purpose

This package defines the legal and consent materials required before Pet-Med-AI
is used in a clinic-facing commercial workflow.

This is not jurisdiction-specific legal advice. It is a launch template package
that must be reviewed by a qualified local legal/professional advisor and by the
clinic owner before external commercial use.

## Commercial V1 product boundary

Commercial V1 may include:

```txt
AI consultation assistance
dynamic consultation
structured dog/cat and exotic intake
case creation / list / detail / edit
AI suggestion human review audit
Clinical Docs Word export
preventive care in-app reminders
front-desk manual contact queue
ops/release read-only support checks
```

Commercial V1 does not include:

```txt
automated SMS sending
automated WeChat sending
automated email sending
provider credentials
background worker sending
EMR real import
EMR case update
device real ingest
DICOM real ingest
lab analyzer real integration
structured prescription writes
billing/invoice real writes
```

## Required documents in this pack

```txt
CLIENT_DATA_USE_CONSENT_TEMPLATE_V1.md
AI_ASSISTED_CLINICAL_NOTICE_V1.md
PREVENTIVE_CARE_REMINDER_NOTICE_V1.md
CLIENT_DATA_OPT_OUT_SOP_V1.md
PRIVACY_DATA_HANDLING_SOP_V1.md
COMMERCIAL_LAUNCH_LEGAL_CONSENT_CHECKLIST.csv
COMMERCIAL_LAUNCH_LEGAL_RISK_REGISTER.csv
COMMERCIAL_LAUNCH_LEGAL_REVIEW_EVIDENCE_TEMPLATE.csv
```

## Required signoffs

Before final commercial launch:

```txt
clinic_owner_signoff
legal_review_signoff
clinical_director_signoff
security_owner_signoff
release_owner_signoff
```

## Hard rules

Commercial launch is **NO-GO** if any of the following is true:

```txt
no client data use consent template
no AI assisted clinical notice
no veterinarian final responsibility statement
no preventive care reminder notice
no opt-out SOP
no privacy/data handling SOP
legal review missing
clinic owner signoff missing
AI described as replacing veterinarian judgment
preventive reminders described as diagnosis or prescription
real external messaging described as enabled
EMR real import described as enabled
client data can be shared with third parties without review
secrets or PHI appear in committed evidence
```

## Required client-facing principles

All client-facing material must make clear:

```txt
Pet-Med-AI is an assistant used by veterinary professionals.
AI output is not a final diagnosis by itself.
The attending veterinarian / clinic clinician remains responsible for clinical judgment.
Emergency or worsening cases require direct veterinary care and must not rely on software output alone.
Preventive care reminders are convenience reminders, not diagnosis, prescription or emergency triage.
Commercial V1 external client contact remains manual.
Clients may request opt-out for reminder/contact workflows.
Client data should be handled with access limitation, confidentiality and security controls.
```

## Required clinic-facing principles

Clinic-facing staff must understand:

```txt
Do not paste unnecessary client personal information into free-text fields.
Do not use AI output without clinical review.
Do not send AI-generated medical advice directly to clients without clinician review.
Do not promise PDF, device, DICOM, lab analyzer or EMR live integrations in Commercial V1.
Do not enable automated external sending in Commercial V1.
Do not bypass opt-out.
Do not export or share client data without a documented reason and proper authorization.
```

## AI safety boundary

Pet-Med-AI can support:

```txt
structured history collection
draft summaries
risk prompts
differential diagnosis suggestions
suggested checks
treatment discussion drafts
clinical document drafts
preventive care reminder suggestions
```

Pet-Med-AI must not be represented as:

```txt
the final diagnosing veterinarian
a substitute for physical examination
a substitute for emergency care
an autonomous prescribing system
a system that automatically contacts clients with medical advice
```

## Data categories

Commercial V1 may process:

```txt
clinic user account data
client/pet owner contact data
pet information
case history
structured intake answers
AI consultation context
case notes
preventive care reminder records
manual contact queue records
audit/review records
release and operational logs
```

Do not collect unless necessary:

```txt
human medical information
unrelated identity documents
unrelated financial information
unrelated sensitive personal information
secrets or credentials in case text
```

## Third-party and provider boundary

Commercial V1 does not require:

```txt
SMS provider credentials
WeChat provider credentials
email provider credentials
EMR provider credentials for real write
device gateway credentials
payment provider credentials
```

If a future stage adds third-party providers, a separate legal/security review
must be completed before credentials are created or client data is shared.

## Evidence requirements

Before Final Go / No-Go V1:

```txt
all documents exist
legal/professional review completed
clinic owner signoff recorded
AI notice approved
client data consent approved
preventive reminder notice approved
opt-out SOP approved
privacy handling SOP approved
no secrets in evidence
no PHI in committed docs/evidence
```

## Decision

Default decision:

```txt
NO-GO until legal/professional review and clinic signoff are recorded
```

Validator PASS means this consent pack exists and is wired into CI/smoke. It does
not mean a licensed legal/professional review has been completed.
