# Case Detail Treatment Framework Signed Review State UI V1

stage: CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_UI_V1

## Purpose

Add a clinician-only Case Detail UI panel for building a signed review state preview from an existing confirmed-diagnosis treatment framework preview.

This stage is UI-only. It does not add backend business logic, does not add a migration, and does not enable signed review state persistence.

## Endpoint used

POST /api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/build

## Required clinician inputs

- case_id
- confirmed_diagnosis_label
- confirmed_by
- confirmation_source=clinician
- ai_generated=false
- treatment_framework_preview from the existing Case Detail treatment framework preview
- reviewed_by
- review_decision
- signed_by
- signoff_decision
- audit_request_id or dry-run audit reference

## Safety contract

- signed_review_state_ui_only=true
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

## Explicitly forbidden

- Writing Case.treatment
- Persisting treatment framework as a treatment plan
- Writing prescription
- Returning drug dose
- Returning route
- Returning frequency
- Client-facing release
- Enabling signed review state persistence
- Alembic migration
- New frontend component directory

## Completion gates

- validator PASS
- ci_static_checks PASS
- online smoke ALL PASS
- system version hard gate stays database_revision=0009_diag_data and alembic_head=0009_diag_data
- dangerous feature flags disabled
- case_detail_treatment_framework_signed_review_state_ui=PASS
- signed review state endpoint remains dry-run/protected
- no DB write

## Decision

GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_V1
