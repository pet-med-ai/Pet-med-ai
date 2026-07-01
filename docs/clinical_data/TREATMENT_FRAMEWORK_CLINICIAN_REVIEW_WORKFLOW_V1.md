# Treatment Framework Clinician Review Workflow V1

stage_id: TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_V1
status: draft_ready
mode: treatment_framework_clinician_review_workflow_v1
next_decision: GO_TO_TREATMENT_FRAMEWORK_AUDIT_LOG_V1

## Purpose

This stage adds a dry-run clinician review workflow for the confirmed-diagnosis treatment framework preview.
It lets a clinician mark the preview as approved for internal clinician use, request revision, or reject it.

The workflow is intentionally preview-only. It does not persist review state, does not update the Case row, does not write `Case.treatment`, does not write any prescription data, does not return drug dose, route, or frequency, and does not produce client-facing treatment instructions.

## Input contract

Required fields:

- `case_id`
- `confirmed_diagnosis_label`
- `confirmed_by`
- `confirmation_source=clinician`
- `ai_generated=false`
- `treatment_framework_preview`
- `reviewed_by` or `reviewer_id`
- `review_decision`

Allowed `review_decision` values:

- `approve_for_clinician_use`
- `request_revision`
- `reject`

## Output contract

The endpoint returns:

- `message=treatment_framework_clinician_review_workflow_built`
- `mode=treatment_framework_clinician_review_workflow_v1`
- `review_workflow.review_decision`
- `review_workflow.review_status`
- `review_workflow.dry_run=true`
- `review_workflow.review_decision_preview_only=true`
- `review_workflow.final_signoff_persisted=false`
- `review_workflow.review_status_persisted=false`
- `review_workflow.client_release_allowed=false`
- `quality_gate.status=PASS`
- `safety.writes_database=false`
- `safety.writes_case_treatment=false`
- `safety.creates_prescription=false`
- `safety.writes_prescription=false`
- `safety.returns_drug_dose=false`
- `safety.returns_drug_route=false`
- `safety.returns_drug_frequency=false`
- `safety.not_client_facing=true`
- `safety.requires_human_review=true`
- `safety.clinician_signoff_required=true`

## Hard boundaries

The workflow must keep these gates:

- `requires_clinician_confirmed_diagnosis=true`
- `ai_does_not_confirm_diagnosis=true`
- `read_only=true`
- `writes_database=false`
- `writes_case_treatment=false`
- `creates_prescription=false`
- `writes_prescription=false`
- `returns_drug_dose=false`
- `returns_drug_route=false`
- `returns_drug_frequency=false`
- `not_client_facing=true`
- `requires_human_review=true`
- `clinician_signoff_required=true`

Forbidden output wording includes drug dose units, route/frequency strings, automatic prescription wording, and client-facing final treatment instructions.

## Go / No-Go

GO only if:

- local validator passes
- `scripts/ci_static_checks.sh` passes
- online `scripts/smoke_petmed.sh` passes
- production `database_revision=0009_diag_data`
- production `alembic_head=0009_diag_data`
- production `schema_ok=true`
- dangerous feature flags remain disabled
- cumulative legacy smoke remains active
- review workflow endpoint is registered and protected or authenticated 200 smoke passes

Decision when all gates pass:

`GO_TO_TREATMENT_FRAMEWORK_AUDIT_LOG_V1`
