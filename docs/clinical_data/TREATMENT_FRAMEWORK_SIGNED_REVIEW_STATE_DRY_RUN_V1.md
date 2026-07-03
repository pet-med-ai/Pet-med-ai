# Treatment Framework Signed Review State Dry Run V1

stage_id: TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1

## Purpose

Build a clinician-facing signed review state **preview** for a previously reviewed
confirmed-diagnosis treatment framework.

This stage introduces a dry-run contract and endpoint only. It does not persist a
signed review state. It does not write `Case.treatment`. It does not create or
write prescriptions. It does not output dose, route, or frequency.

## Endpoint

`POST /api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/build`

## Required input contract

- `case_id`
- `confirmed_diagnosis_label`
- `confirmed_by`
- `confirmation_source=clinician`
- `ai_generated=false`
- `treatment_framework_preview`
- `reviewed_by`
- `review_decision`
- `signed_by`
- `signoff_decision`
- an audit log reference, such as `audit_log_result`, `audit_event`, `audit_log_id`, `audit_request_id`, or `request_id`

## Allowed signoff decisions

- `sign_internal_review`
- `request_revision`
- `reject`

## Output contract

The endpoint returns a `signed_review_state_preview` object with:

- `dry_run=true`
- `persisted=false`
- `signed_review_state_persisted=false`
- `case_treatment_persisted=false`
- `prescription_created=false`
- `client_release_allowed=false`
- `not_client_facing=true`
- `review_state_persistence_enabled=false`

## Hard boundaries

- requires_clinician_confirmed_diagnosis=true
- ai_does_not_confirm_diagnosis=true
- signed_review_state_dry_run_only=true
- signed_review_state_persistence_enabled=false
- review_state_persistence_enabled=false
- writes_database=false
- no_case_treatment_write=true
- no_case_treatment_persistence=true
- no_prescription_write=true
- no_dose_route_frequency=true
- not_client_facing=true
- requires_human_review=true
- clinician_signoff_required=true

## Explicit non-goals

This stage does not:

- add a database migration
- create a signed review state table
- write signed review state persistence
- write `Case.treatment`
- create a prescription
- return drug dose, route, or frequency
- expose client-facing treatment instructions
- call an external AI provider

## Go / No-Go

GO only if:

- validator passes
- `scripts/ci_static_checks.sh` passes
- online smoke passes
- production hard gate remains `database_revision=0009_diag_data`
- dangerous feature flags remain disabled
- signed review state endpoint is registered and protected
- no database write occurs in dry-run mode

decision=GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_UI_V1
