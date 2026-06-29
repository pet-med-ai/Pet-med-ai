# Confirmed Diagnosis Treatment Framework Boundary V1

Status: governance boundary / local validation stage  
Mode: documentation + validator only  
Runtime behavior: no backend endpoint, no frontend feature, no database write  
Clinical surface: clinician-facing only  
Next permitted stage after GO: Confirmed Diagnosis Treatment Framework Draft V1

## 1. Purpose

Pet-Med-AI is moving from a pure treatment / dose interception posture to a more clinically useful but still controlled capability: a treatment framework preview after a veterinarian has already confirmed the diagnosis.

This stage does not implement that preview. It defines the safe boundary for a later dry-run implementation.

The target capability is:

- accept a clinician-confirmed diagnosis as an input;
- combine that diagnosis with case context, diagnostic reports, observations, imaging metadata, and clinician review summaries;
- return a structured treatment framework preview for clinician review;
- avoid automatic prescribing, dose generation, route generation, frequency generation, and client-facing instructions.

## 2. Hard scope of Boundary V1

Boundary V1 is intentionally narrow.

Allowed in this stage:

- define the clinician-confirmed diagnosis requirement;
- define the future input contract;
- define the future output contract;
- define forbidden wording and forbidden structured fields;
- define validation and Go / No-Go evidence gates;
- add local static validation for this boundary.

Not allowed in this stage:

- no backend route;
- no API endpoint;
- no database migration;
- no database write;
- no Case.treatment write;
- no prescription write;
- no frontend rendering;
- no provider credentials;
- no external AI call;
- no real EMR import;
- no real lab / LIS / DICOM / PACS / device ingest;
- no client-facing treatment output.

## 3. Clinical precondition

The system must not confirm, infer, finalize, or upgrade a diagnosis.

A future treatment framework builder must require a clinician-confirmed diagnosis. If that requirement is not met, the future endpoint must reject the request before producing any framework preview.

Required future rejection behavior:

```text
422 confirmed diagnosis by clinician is required
```

This rejection is part of the safety boundary. The AI may summarize evidence or organize clinician-entered information, but it must not become the source of diagnostic confirmation.

## 4. Future input contract

The future dry-run builder may accept only clinician-scoped inputs similar to the following contract:

```json
{
  "case_id": 123,
  "confirmed_diagnosis_label": "clinician supplied diagnosis",
  "confirmed_by": "clinician-id",
  "confirmation_source": "clinician_entered",
  "ai_generated": false,
  "case_context": {
    "species": "optional species label",
    "signalment_summary": "optional clinician-reviewed case context",
    "problem_list": ["optional clinician-reviewed problem label"]
  },
  "diagnostic_context": {
    "diagnostic_report_summary": "optional clinician-reviewed summary",
    "observation_abnormal_summary": "optional clinician-reviewed summary",
    "imaging_review_summary": "optional clinician-reviewed summary"
  }
}
```

Mandatory future quality gates:

- `confirmed_diagnosis_label` must be present and non-empty;
- `confirmed_by` must be present and non-empty;
- `confirmation_source` must equal a clinician-entered or clinician-confirmed source;
- `ai_generated` must be `false`;
- AI-generated diagnostic candidates must not be accepted as confirmed diagnosis input.

## 5. Future output contract

The future output must be a treatment framework preview, not a treatment plan, not a prescription, and not a client instruction.

Allowed output fields:

- `treatment_goals`
- `care_priority_hint`
- `supportive_care_categories`
- `monitoring_parameters`
- `recheck_plan_categories`
- `contraindication_checks`
- `hospitalization_or_referral_triggers`
- `procedure_or_surgery_review_points`
- `nutrition_and_environment_support_points`
- `client_communication_topics_for_clinician_review`
- `medication_class_review_needed`
- `quality_gate`
- `safety`

Required output safety flags:

```json
{
  "writes_database": false,
  "creates_prescription": false,
  "writes_prescription": false,
  "writes_case_treatment": false,
  "returns_drug_dose": false,
  "returns_drug_route": false,
  "returns_drug_frequency": false,
  "not_client_facing": true,
  "requires_human_review": true,
  "clinician_signoff_required": true
}
```

## 6. Forbidden output content

The future builder must block all of the following:

- automatic prescription;
- prescription write;
- structured prescription draft;
- medication product recommendation;
- drug dose;
- dose unit;
- route;
- frequency;
- duration;
- final client-facing treatment instruction;
- treatment plan persistence by default;
- Case.treatment persistence;
- external AI/provider call as an uncontrolled source;
- client-facing diagnosis;
- client-facing dose output.

Forbidden scanner patterns for future generated preview text and structured fields:

```text
mg/kg
ml/kg
mcg/kg
IU/kg
q12h
q24h
BID
SID
TID
QID
PO
IV
IM
SC
SQ
subcutaneous
intravenous
intramuscular
oral
per os
dose
dosage
frequency
route
prescription
rx
refill
```

The scanner must treat these as forbidden output patterns, not as clinical recommendations.

## 7. Allowed wording style

The future builder may use clinician-review wording such as:

- clinician should evaluate whether analgesia support is needed;
- clinician should evaluate whether antimicrobial direction is relevant;
- clinician should evaluate whether fluid, nutrition, nursing, hospitalization, or referral support is needed;
- clinician should determine the concrete plan based on physical examination, diagnostic results, imaging review, patient stability, contraindications, and hospital protocol.

The future builder must not convert these categories into medication instructions.

## 8. Human review and signoff

Every future preview must remain behind clinician review.

Required state:

```text
requires_human_review=true
clinician_signoff_required=true
not_client_facing=true
```

A future UI must label the preview as clinician review material. It must not display as a client instruction, discharge instruction, invoice item, prescription, or final treatment plan.

## 9. Persistence boundary

Boundary V1 allows no persistence.

Future persistence requires a separate risk review stage before writing any treatment framework preview to database tables.

Explicitly blocked in this stage and the next dry-run stage:

- no treatment framework persistence;
- no Case.treatment write;
- no prescription table write;
- no audit-log write unless separately approved in a later audit stage;
- no delivery to client channels.

## 10. Feature flag boundary

The following dangerous capabilities must remain disabled while this stage is active:

- `ENABLE_EMR_REAL_IMPORT`
- `ENABLE_EMR_IMPORT_CASE_UPDATE`
- `ENABLE_EMR_ATTACHMENT_DOWNLOAD`
- `ENABLE_PREVENTIVE_AUTO_DELIVERY`
- `ENABLE_PREVENTIVE_SMS_DELIVERY`
- `ENABLE_PREVENTIVE_WECHAT_DELIVERY`
- `ENABLE_PREVENTIVE_EMAIL_DELIVERY`
- `ENABLE_PRESCRIPTION_STRUCTURED_WRITE`
- `ENABLE_DEVICE_REAL_INGEST`
- `ENABLE_BILLING_REAL_WRITE`

No Boundary V1 file may instruct operators to enable these flags.

## 11. Production hard gate

Deployment Go / No-Go must keep the existing diagnostic data production hard gate:

```text
database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false
```

Any mismatch is a No-Go for this stage.

## 12. Validation commands

Run locally from the project root:

```bash
git diff --check
python3 scripts/validate_confirmed_diagnosis_treatment_framework_boundary.py
bash scripts/ci_static_checks.sh
```

Run after deployment or against production:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool

KEEP_TMP=1 BASE_URL=https://pet-med-ai-backend.onrender.com FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com bash scripts/smoke_petmed.sh
```

## 13. Go / No-Go summary

Go to Confirmed Diagnosis Treatment Framework Draft V1 only when all of the following are true:

```text
validator=PASS
ci_static_checks=PASS
online_smoke=ALL_PASS
requires_clinician_confirmed_diagnosis=true
ai_does_not_confirm_diagnosis=true
blocks_prescription=true
blocks_dose=true
blocks_route_frequency=true
not_client_facing=true
production database_revision=0009_diag_data
production alembic_head=0009_diag_data
production schema_ok=true
dangerous_feature_flags_disabled=true
read_only=true
no DB write
no final diagnosis by AI
no treatment plan persistence
no prescription
no drug dose
requires_human_review=true
clinician_signoff_required=true
decision=GO_TO_CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_DRAFT_V1
```

## 14. Boundary V1 decision

Boundary V1 is a local governance and validation stage. It is Go only for creating the next dry-run draft stage after local validation, online smoke, production revision verification, and dangerous feature flag verification pass.
