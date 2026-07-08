# Treatment Framework Signed Review State Persistence Migration Implementation V1

stage=TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_V1
status=IMPLEMENTATION_DRAFT_ONLY

## Purpose

Create an inactive Alembic implementation draft for the future signed review state
persistence table. This is not a database migration apply stage.

The draft is stored under `docs/clinical_data/` as a `.py.txt` implementation
artifact so Alembic will not discover it as a live migration head. Production must
remain at `database_revision=0009_diag_data` and `alembic_head=0009_diag_data`.

## Fixed safety boundary

migration_implementation_draft_only=true
migration_apply_allowed=false
migration_enabled=false
active_migration_file_created=false
inactive_migration_draft_created=true
schema_change_enabled=false
persistence_enabled=false
signed_review_state_persistence_enabled=false
review_state_persistence_enabled=false
writes_database=false
no_case_treatment_write=true
no_case_treatment_persistence=true
no_prescription_write=true
no_dose_route_frequency=true
not_client_facing=true
rollback_plan_required=true
backup_restore_evidence_required=true
authenticated_smoke_required_before_write=true
append_only_audit_linkage_required=true
requires_human_review=true
clinician_signoff_required=true

## Implementation artifact

Inactive draft file:

`docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt`

Draft revision metadata:

- revision: `0010_treatment_framework_signed_review_states`
- down_revision: `0009_diag_data`
- table preview: `treatment_framework_signed_review_states`

## Not allowed in this stage

- Do not create `backend/migrations/versions/0010_treatment_framework_signed_review_states.py`.
- Do not apply migration.
- Do not change SQLAlchemy production metadata.
- Do not write database rows.
- Do not write case treatment fields.
- Do not create or write prescriptions.
- Do not output drug dose, route, or frequency.
- Do not expose this to clients.

## Decision

decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_APPLY_READINESS_REVIEW_V1
