# Treatment Framework Audit Log V1

stage_id: TREATMENT_FRAMEWORK_AUDIT_LOG_V1
status: ready_for_validation
mode: treatment_framework_audit_log_v1
next_decision: GO_TO_TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1

## Purpose

Treatment Framework Audit Log V1 records a clinician review decision for a confirmed-diagnosis treatment framework preview as an append-only audit event. The feature is scoped to audit evidence only.

The endpoint may append exactly one `AuditLog` row only when `dry_run=false`, the caller owns the case, the payload passes safety validation, and `audit_log_confirmation=I_UNDERSTAND_THIS_APPENDS_TREATMENT_FRAMEWORK_AUDIT_LOG_ONLY` is supplied. The default path remains dry-run and does not write the database.

## Endpoint

`POST /api/diagnostic-data/confirmed-diagnosis/treatment-framework/audit-log/append`

## Required boundary

- requires_clinician_confirmed_diagnosis=true
- ai_does_not_confirm_diagnosis=true
- append_only_audit_log=true
- writes_case_treatment=false
- creates_prescription=false
- writes_prescription=false
- returns_drug_dose=false
- returns_drug_route=false
- returns_drug_frequency=false
- not_client_facing=true
- requires_human_review=true
- clinician_signoff_required=true

## Decision

GO_TO_TREATMENT_FRAMEWORK_PERSISTENCE_RISK_REVIEW_V1
