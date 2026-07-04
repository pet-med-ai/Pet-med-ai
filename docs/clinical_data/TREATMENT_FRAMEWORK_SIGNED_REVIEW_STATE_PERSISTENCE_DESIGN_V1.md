# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1

## Purpose

This stage defines the future persistence contract for Treatment Framework signed review state.

It is a design-only stage. It does not create a migration, does not change backend
business logic, does not change frontend UI, and does not enable real persistence.

## Current upstream state

The completed signed review state dry-run and case-detail UI stages produce only
doctor-facing preview data. The current signed review state remains dry-run only.

## Non-negotiable design boundary

```text
persistence_design_only=true
persistence_enabled=false
signed_review_state_persistence_enabled=false
review_state_persistence_enabled=false
signed_review_state_persistence_dry_run_required_first=true
migration_readiness_required=true
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
requires_human_review=true
clinician_signoff_required=true
```

## Explicit NO-GO decisions

```text
NO_GO_TO_CASE_TREATMENT_PERSISTENCE
NO_GO_TO_PRESCRIPTION_WRITE
NO_GO_TO_DRUG_DOSE_ROUTE_FREQUENCY_OUTPUT
NO_GO_TO_CLIENT_FACING_TREATMENT_OUTPUT
NO_GO_TO_SIGNED_REVIEW_STATE_DATABASE_WRITE
NO_GO_TO_MIGRATION_IN_THIS_STAGE
```

## Future persistence object design

Future persistence, if approved in a separate stage, must be a dedicated signed
review state object or table. It must not write to `Case.treatment`.

A future object may include only metadata and state markers such as:

```text
case_id
confirmed_diagnosis_label
confirmed_by
confirmation_source=clinician
ai_generated=false
review_decision
reviewed_by
signoff_decision
signed_by
audit_log_id or audit_request_id
signed_review_status
created_at
updated_at
```

It must not include:

```text
drug dose
dose unit
route
frequency
prescription instruction
client-facing treatment instruction
Case.treatment payload
final treatment plan text
```

## State machine design

Allowed future state names are intentionally conservative:

```text
draft_preview_built
clinician_review_previewed
audit_log_previewed
signed_review_state_previewed
signed_internal_review_pending_persistence
revision_requested_pending_persistence
rejected_pending_persistence
```

No state in this design authorizes:

```text
case_treatment_write
prescription_write
dose_output
route_output
frequency_output
client_release
```

## Required future gates before any persistence implementation

Before any future signed review state persistence can be implemented, the project
must complete a separate Go/No-Go chain:

```text
signed_review_state_persistence_dry_run_v1
migration_readiness_review_v1
migration_design_v1
rollback_plan_v1
authenticated_200_payload_smoke_v1
audit_evidence_review_v1
```

## Audit relationship

Append-only audit log remains the only currently allowed persistence-related
supporting layer. The signed review state may reference an audit event, but this
stage does not write or update that event.

```text
append_only_audit_allowed_only=true
updates_audit_log=false
deletes_audit_log=false
```

## Output decision

```text
decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DRY_RUN_V1
```
