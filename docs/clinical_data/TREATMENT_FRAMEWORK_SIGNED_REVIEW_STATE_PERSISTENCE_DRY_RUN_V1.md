# Treatment Framework Signed Review State Persistence Dry Run V1

stage=TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DRY_RUN_V1
mode=treatment_framework_signed_review_state_persistence_dry_run_v1
decision=GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_UI_V1

## Purpose

Build a clinician-facing dry-run preview for future persistence of a treatment
framework signed review state. This stage does not write a signed review state,
does not write Case.treatment, does not write prescriptions, and does not enable
client-facing output.

## Endpoint

POST /api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/prepare

## Required input contract

- case_id
- confirmed_diagnosis_label
- confirmed_by
- confirmation_source=clinician
- ai_generated=false
- treatment_framework_preview
- signed_review_state_preview
- reviewed_by
- review_decision
- signed_by
- signoff_decision
- audit_log_result / audit_event / audit_log_id / audit_request_id / request_id
- persistence_requested_by

## Safety contract

persistence_dry_run_only=true
persistence_enabled=false
signed_review_state_persistence_enabled=false
review_state_persistence_enabled=false
signed_review_state_persistence_dry_run_required_first=true
migration_readiness_required=true
writes_database=false
no_case_treatment_write=true
no_case_treatment_persistence=true
no_prescription_write=true
no_dose_route_frequency=true
not_client_facing=true
requires_human_review=true
clinician_signoff_required=true

## Explicit NO-GO

NO_GO_TO_SIGNED_REVIEW_STATE_DATABASE_WRITE
NO_GO_TO_CASE_TREATMENT_PERSISTENCE
NO_GO_TO_PRESCRIPTION_WRITE
NO_GO_TO_DOSE_ROUTE_FREQUENCY_OUTPUT
NO_GO_TO_CLIENT_FACING_RELEASE

## Go / No-Go

Go only if all are true:

- validator PASS
- ci_static_checks PASS
- online smoke ALL PASS
- database_revision=0009_diag_data
- alembic_head=0009_diag_data
- schema_ok=true
- migration_errors=[]
- dangerous feature flags disabled
- treatment_framework_signed_review_state_persistence_dry_run_smoke=PASS
- writes_database=false
- no_case_treatment_write=true
- no_prescription_write=true
- no_dose_route_frequency=true
- not_client_facing=true

Next stage:
GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_UI_V1
