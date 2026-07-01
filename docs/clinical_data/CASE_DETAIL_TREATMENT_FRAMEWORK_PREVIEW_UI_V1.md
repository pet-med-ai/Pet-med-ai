# Case Detail Treatment Framework Preview UI V1

stage: CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_V1
status: draft_ui_guarded
owner: clinician-facing case detail workflow
decision: GO_TO_TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1

## Purpose

Expose the Confirmed Diagnosis Treatment Framework Draft V1 dry-run endpoint from the case detail page as a clinician-only preview workflow.

The UI must require a clinician confirmed diagnosis before it calls the endpoint. The UI must not let AI confirm diagnosis.

## User flow

1. Clinician opens a case detail page.
2. Clinician enters the already-confirmed diagnosis label.
3. Clinician enters the confirming clinician identifier.
4. UI sends a dry-run request to:
   `/api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/build`
5. UI renders the returned `treatment_framework_preview` in the case detail page.
6. UI shows quality gate and safety flags.

## Input contract

Required UI inputs:

- `case_id`
- `confirmed_diagnosis_label`
- `confirmed_by`
- `confirmation_source=clinician`
- `ai_generated=false`

Optional UI context:

- case snapshot
- diagnostic data counts
- lab abnormal summary preview
- imaging summary preview
- diagnostic assistance preview counts

## Output allowed in UI

Allowed clinician-facing preview fields:

- treatment goals
- care priority hint
- supportive care categories
- monitoring parameters
- recheck plan categories
- contraindication checks
- hospitalization or referral triggers
- procedure or surgery review points
- nutrition and environment support points
- client communication topics for clinician review
- medication class review needed

## Hard boundaries

This stage must keep:

- requires_clinician_confirmed_diagnosis=true
- ai_does_not_confirm_diagnosis=true
- read_only=true
- writes_database=false
- writes_case_treatment=false
- creates_prescription=false
- writes_prescription=false
- returns_drug_dose=false
- returns_drug_route=false
- returns_drug_frequency=false
- not_client_facing=true
- requires_human_review=true
- clinician_signoff_required=true

## Explicit non-goals

This stage does not:

- persist treatment framework results
- write `Case.treatment`
- create or write prescription
- display numeric drug dose
- display medication route
- display medication frequency
- release content to the client
- call an external AI provider
- enable any dangerous feature flag

## Production hard gates

Deployment remains GO only if:

- validator PASS
- ci_static_checks PASS
- online smoke ALL PASS
- frontend reachable
- treatment framework endpoint remains registered and protected
- production database_revision=0009_diag_data
- production alembic_head=0009_diag_data
- production schema_ok=true
- migration_errors=[]
- dangerous feature flags disabled
- no DB write
