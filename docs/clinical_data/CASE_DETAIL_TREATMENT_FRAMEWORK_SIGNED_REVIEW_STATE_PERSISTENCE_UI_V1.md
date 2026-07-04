# CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_UI_V1

## Scope

Case Detail Treatment Framework Signed Review State Persistence UI V1 adds a clinician-facing UI panel to generate and display a signed review state persistence dry-run preview.

This stage is UI-only. It does not enable real persistence.

## Endpoint used

POST /api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/prepare

## Required upstream inputs

- clinician confirmed diagnosis
- confirmation_source=clinician
- ai_generated=false
- treatment_framework_preview
- signed_review_state_preview
- audit log reference
- reviewed_by
- review_decision
- signed_by
- signoff_decision
- persistence_requested_by

## Safety contract

case_detail_signed_review_state_persistence_ui_only=true
persistence_dry_run_only=true
persistence_enabled=false
signed_review_state_persistence_enabled=false
review_state_persistence_enabled=false
writes_database=false
no_case_treatment_write=true
no_case_treatment_persistence=true
no_prescription_write=true
no_dose_route_frequency=true
not_client_facing=true
requires_human_review=true
clinician_signoff_required=true
no_migration=true
no_backend_endpoint_change=true

## Explicit non-goals

- no real database write
- no case treatment field write
- no prescription write
- no drug dose, route, or frequency output
- no client-facing signed review state
- no migration
- no background worker
- no external provider call

## Go / No-Go

GO only if:

- validator passes
- ci_static_checks passes
- smoke_petmed passes online
- system version hard gate remains 0009_diag_data
- dangerous feature flags remain disabled
- UI static marker smoke passes
- persistence dry-run endpoint remains registered and protected
- writes_database=false
- not_client_facing=true

NO-GO to real persistence in this stage.

decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_READINESS_REVIEW_V1
