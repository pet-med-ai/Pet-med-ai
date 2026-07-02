# Treatment Framework Persistence Risk Review V1

stage: TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1
status: risk_review_only
previous_stage_decision: GO_TO_TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1
decision: GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1

## Purpose

This stage reviews whether a confirmed-diagnosis treatment framework can safely
move toward any form of persistence.

The answer for V1 is deliberately narrow:

- persistence_enabled=false
- no_business_logic_change=true
- writes_database=false
- no_case_treatment_write=true
- no_case_treatment_persistence=true
- no_prescription_write=true
- no_dose_route_frequency=true
- not_client_facing=true
- append_only_audit_allowed_only=true
- signed_review_state_requires_future_design=true

The system may continue to generate clinician-facing treatment framework
previews after a clinician-supplied confirmed diagnosis. It must not transform
that preview into a persisted treatment plan, prescription, drug dose, route,
frequency, or client-facing instruction.

## Scope

In scope:

- risk review document
- checklist
- Go / No-Go table
- validator
- CI static guard update
- smoke static marker update

Out of scope:

- backend persistence implementation
- database migration
- frontend UI modification
- writing Case.treatment
- writing prescription
- writing medication dose, route, frequency, or duration
- changing treatment framework builder behavior
- changing audit log persistence behavior
- client-facing release

## Current allowed state

The existing treatment framework chain is allowed to remain:

1. confirmed diagnosis treatment framework preview dry-run
2. case detail clinician-only preview UI
3. clinician review workflow dry-run
4. treatment framework audit log endpoint, with dry-run default and append-only
   audit semantics when explicitly confirmed in a separate stage

This V1 risk review does not enable any new write path.

## Persistence risk categories

### 1. Case.treatment persistence risk

Risk: writing framework preview text into `Case.treatment` can be mistaken for a
final treatment plan.

Decision:

- NO_GO_TO_CASE_TREATMENT_PERSISTENCE
- Case.treatment must remain untouched.
- No endpoint in this stage may write Case.treatment.
- No validator may accept Case.treatment assignment.

Required future evidence before reconsideration:

- signed clinician review state design
- separate rollback plan
- authenticated payload smoke
- audit evidence proving prescription and dose are still blocked
- explicit Go / No-Go record

### 2. Prescription risk

Risk: a clinician review label can be misunderstood as approval to prescribe.

Decision:

- no_prescription_write=true
- creates_prescription=false
- writes_prescription=false
- ENABLE_PRESCRIPTION_STRUCTURED_WRITE must remain false
- any future prescription module must be a separate controlled pilot

### 3. Dose / route / frequency risk

Risk: persisted framework text can drift into drug directions.

Decision:

- returns_drug_dose=false
- returns_drug_route=false
- returns_drug_frequency=false
- blocks_dose=true
- blocks_route_frequency=true
- no `mg/kg`, `ml/kg`, `q12h`, `BID`, `SID`, `PO`, `IV`, `IM`, `SC`, or
  equivalent drug-direction wording is allowed in persisted framework preview
  or review state.

### 4. Client-facing risk

Risk: treatment framework preview can be shown to clients without clinician
finalization.

Decision:

- not_client_facing=true
- client_release_allowed=false
- no client message
- no discharge instruction
- no external message

### 5. Review-state persistence risk

Risk: even non-treatment review state can become operationally meaningful.

Decision:

- review_state_persistence_enabled=false in this stage
- signed_review_state_requires_future_design=true
- any future review-state persistence must be a separate stage and must still
  avoid Case.treatment, prescription, dose, route, frequency, and client-facing
  release.

### 6. Audit log risk

Risk: audit log events can be confused with treatment plan approval.

Decision:

- append_only_audit_allowed_only=true
- audit events may record what was previewed/reviewed, but must not become the
  treatment plan itself.
- audit log is not Case.treatment.
- audit log is not prescription.
- audit log is not client-facing instruction.

## Required next-stage constraints

If the project proceeds, the next stage must be only:

GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1

The next stage must design a signed review-state model and still prove:

- no Case.treatment write
- no prescription write
- no drug dose output
- no route output
- no frequency output
- no client-facing output
- requires_human_review=true
- clinician_signoff_required=true
- dangerous feature flags disabled
- production database remains at 0009_diag_data
- schema_ok=true

## Hard NO-GO conditions

The stage is NO-GO if any of the following appear:

- Case.treatment write
- treatment plan persistence enabled
- prescription write
- drug dose output
- route/frequency output
- client-facing treatment output
- database migration
- dangerous feature flag enabled
- schema drift
- unauthenticated endpoint acceptance
- online smoke failure

## Completion criteria

- validator PASS
- ci_static_checks PASS
- smoke_petmed ALL PASS
- treatment_framework_audit_log_smoke=PASS remains present
- treatment_framework_persistence_risk_review=PASS
- production database_revision=0009_diag_data
- production alembic_head=0009_diag_data
- production schema_ok=true
- migration_errors=[]
- dangerous_feature_flags_disabled=true
- writes_database=false
- decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_DESIGN_V1
