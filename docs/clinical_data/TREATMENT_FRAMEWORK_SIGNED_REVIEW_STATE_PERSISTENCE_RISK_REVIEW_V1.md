# Treatment Framework Signed Review State Persistence Risk Review V1

stage_id=TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_RISK_REVIEW_V1
status=RISK_REVIEW_ONLY

## Purpose

This stage reviews whether the signed review state preview for the confirmed-diagnosis treatment framework is safe to persist.

The conclusion is intentionally conservative: signed review state persistence is **not enabled** in this stage. This stage creates documentation, checklist, Go/No-Go evidence, CI checks, and smoke markers only.

## Current decision

persistence_enabled=false
signed_review_state_persistence_enabled=false
review_state_persistence_enabled=false
signed_review_state_persistence_design_required=true
signed_review_state_persistence_dry_run_required_before_write=true
migration_readiness_required=true
no_business_logic_change=true
no_backend_endpoint_change=true
no_frontend_ui_change=true
no_migration=true
read_only=true
writes_database=false
no_case_treatment_write=true
no_case_treatment_persistence=true
no_prescription_write=true
no_dose_route_frequency=true
not_client_facing=true
requires_human_review=true
clinician_signoff_required=true

The Go/No-Go decision is:

NO_GO_TO_SIGNED_REVIEW_STATE_PERSISTENCE
GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1

## Scope

Allowed in this stage:

- Document signed review state persistence risks.
- Keep the existing signed review state dry-run endpoint protected and unchanged.
- Keep the existing Case Detail signed review state UI as dry-run only.
- Keep append-only audit log as the only previously approved write-adjacent support layer.
- Preserve production hard gates and cumulative smoke coverage.

Not allowed in this stage:

- No database writes.
- No migration.
- No backend endpoint change.
- No frontend UI change.
- No Case treatment persistence.
- No prescription creation or prescription write.
- No dose, route, frequency, or duration output.
- No client-facing signed review state release.
- No automatic treatment plan persistence.

## Persistence risk findings

1. A persisted signed review state would become a clinical legal record. It needs a dedicated persistence model, immutable event semantics, audit linkage, rollback story, and signed clinician identity contract.
2. The current dry-run endpoint proves a safe preview contract, but it does not prove persistence readiness.
3. Persisting signed review state must not imply treatment plan persistence.
4. Persisting signed review state must not write Case.treatment or prescription records.
5. Any future persistence must be explicitly append-only or versioned; update/delete semantics are not acceptable without a separate risk review.
6. A future persistence design must define signed_by, signed_at, signoff_decision, reviewed_by, review_decision, audit_log_reference, and immutable state status.
7. A future persistence stage must include authenticated 200 payload smoke with an owned case id before any write path is considered.

## Required future stage before persistence

The next allowed stage is design-only:

GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1

That design stage must still avoid real persistence, migrations, and Case.treatment writes unless a later explicit migration readiness and controlled persistence stage passes.

## Completion criteria

validator=PASS
ci_static_checks=PASS
online_smoke=ALL_PASS
production database_revision=0009_diag_data
production alembic_head=0009_diag_data
production schema_ok=true
dangerous_feature_flags_disabled=true
persistence_enabled=false
signed_review_state_persistence_enabled=false
review_state_persistence_enabled=false
no_case_treatment_write=true
no_case_treatment_persistence=true
no_prescription_write=true
no_dose_route_frequency=true
not_client_facing=true
requires_human_review=true
clinician_signoff_required=true
decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_DESIGN_V1
