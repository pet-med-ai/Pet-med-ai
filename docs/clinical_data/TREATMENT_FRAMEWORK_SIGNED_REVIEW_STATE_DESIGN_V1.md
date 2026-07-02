# Treatment Framework Signed Review State Design V1

stage_id: TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1
stage_type: design_only
persistence_enabled=false
review_state_persistence_enabled=false
no_business_logic_change=true
no_backend_endpoint_change=true
no_frontend_ui_change=true
no_migration=true
writes_database=false
no_case_treatment_write=true
no_case_treatment_persistence=true
no_prescription_write=true
no_dose_route_frequency=true
not_client_facing=true
append_only_audit_allowed_only=true
requires_human_review=true
clinician_signoff_required=true
previous_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1
next_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1

## Purpose

This stage defines a future signed review state contract for clinician-reviewed treatment framework previews.
It does not implement state persistence. It does not write Case.treatment. It does not create a prescription.
It does not add drug dose, route, frequency, duration, or client-facing treatment instructions.

The signed review state is intended to separate three concepts that must not be mixed:

1. clinician-confirmed diagnosis input;
2. clinician-facing treatment framework preview;
3. future signed review state proving that a clinician reviewed the preview.

## Non-goals

This stage does not:

- create or modify backend endpoints;
- create or modify frontend UI;
- create migrations;
- write database rows;
- persist review state;
- write Case.treatment;
- write prescriptions;
- output drug dose, route, or frequency;
- release content to clients.

## Future signed review state contract

Allowed future state fields are deliberately narrow:

```json
{
  "case_id": 123,
  "confirmed_diagnosis_label": "clinician supplied diagnosis",
  "confirmed_by": "clinician-id",
  "confirmation_source": "clinician_entered",
  "ai_generated": false,
  "reviewed_by": "clinician-id",
  "review_decision": "approve_for_clinician_use | request_revision | reject",
  "signed_review_state": "unsigned_preview | signed_internal_review | revision_requested | rejected",
  "signed_at": "future timestamp after dedicated persistence review",
  "client_release_allowed": false,
  "persistence_contract_version": "future-only"
}
```

Required invariants:

- requires_clinician_confirmed_diagnosis=true
- ai_does_not_confirm_diagnosis=true
- review_state_persistence_enabled=false in this stage
- no_case_treatment_write=true
- no_case_treatment_persistence=true
- no_prescription_write=true
- no_dose_route_frequency=true
- not_client_facing=true
- requires_human_review=true
- clinician_signoff_required=true

## Allowed signed review state values for future design

The future state machine may only use clinician-facing internal statuses:

- unsigned_preview
- signed_internal_review
- revision_requested
- rejected
- superseded_by_new_review

Forbidden states:

- final_treatment_plan
- client_released
- prescription_ready
- dose_approved
- route_frequency_approved
- auto_persisted

## Persistence guard

This stage explicitly says NO-GO to direct treatment persistence:

NO_GO_TO_CASE_TREATMENT_PERSISTENCE
NO_GO_TO_PRESCRIPTION_WRITE
NO_GO_TO_DOSE_ROUTE_FREQUENCY_OUTPUT
NO_GO_TO_CLIENT_FACING_RELEASE

Only a future dry-run signed review state endpoint may be designed next.
That future endpoint must still default to dry_run=true and writes_database=false until a separate persistence readiness review is completed.

## Go / No-Go decision

GO only if all checks pass:

- validator PASS;
- ci_static_checks PASS;
- online smoke ALL PASS;
- production database_revision=0009_diag_data;
- production alembic_head=0009_diag_data;
- production schema_ok=true;
- dangerous feature flags disabled;
- no backend endpoint changes;
- no frontend UI changes;
- no migration;
- no database write;
- no Case.treatment write;
- no prescription write;
- no dose / route / frequency;
- not client-facing.

Decision:

GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DRY_RUN_V1
