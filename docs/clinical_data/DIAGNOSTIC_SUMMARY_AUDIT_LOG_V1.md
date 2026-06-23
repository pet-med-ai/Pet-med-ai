# Diagnostic Summary Audit Log V1

## Purpose

Diagnostic Summary Audit Log V1 adds a bounded, append-only audit trail for clinician review of diagnostic summary previews.

This stage follows Clinician Review Persistence V1. It records that a clinician reviewed or rejected a diagnostic summary preview, or that review-status persistence was reviewed, without changing the clinical diagnostic data itself.

## Why this stage exists

The diagnostic assistance workflow now has:

- problem list preview
- differential diagnosis candidates preview
- diagnostic reasoning evidence trace preview
- case detail UI preview
- bounded DiagnosticReport review-status persistence

The next required safety layer is audit evidence for clinician review actions.

## Existing data model

This stage uses the existing `AuditLog` model and `audit_log` table.

No Alembic migration is required.

Production database gate remains:

```text
database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
```

## API

```text
POST /api/diagnostic-data/diagnostic-summary/audit-log/append
```

The endpoint is implemented in `backend/audit_log_api.py` under the existing `/api` router.

It is intentionally not added to `backend/diagnostic_data_api.py` because that module still contains earlier read-only diagnostic-data API gates.

## Allowed write

Only this write is allowed when `dry_run=false` and the exact confirmation string is present:

```text
append one AuditLog row
```

Required confirmation:

```text
I_UNDERSTAND_THIS_APPENDS_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ONLY
```

## Dry-run behavior

When `dry_run=true`, the endpoint validates and previews the audit event but does not write any database row.

Required dry-run flags:

```text
writes_database=false
writes_audit_log=false
creates_audit_log=false
append_only_audit_log=true
updates_case=false
updates_diagnostic_report=false
updates_observation=false
updates_imaging_study=false
writes_ai_summary=false
persists_reasoning_trace=false
requires_human_review=true
clinician_signoff_required=true
not_client_facing=true
```

## Controlled append behavior

When `dry_run=false`, the endpoint may append exactly one `AuditLog` row.

Required write flags:

```text
writes_database=true
creates_audit_log=true
writes_audit_log=true
append_only_audit_log=true
updates_audit_log=false
deletes_audit_log=false
updates_case=false
updates_diagnostic_report=false
updates_observation=false
updates_imaging_study=false
writes_ai_summary=false
persists_reasoning_trace=false
requires_human_review=true
clinician_signoff_required=true
not_client_facing=true
```

## Blocked

This stage must not:

- create or update Case
- create or update DiagnosticReport
- create or update Observation
- create or update ImagingStudy
- no AI summary write
- write DiagnosticReport.ai_summary
- write DiagnosticReport.abnormal_summary
- persist problem list preview
- persist differential diagnosis candidates
- persist reasoning trace
- create treatment plan
- write prescription
- return drug dose
- return drug route
- return drug frequency
- return probability
- return numeric confidence
- generate final diagnosis
- generate confirmed diagnosis
- generate definitive diagnosis
- generate diagnostic conclusion
- release client-facing content
- call external AI/provider
- execute real EMR / lab / DICOM / device ingest

## Input shape

Minimal dry-run example:

```json
{
  "case_id": 123,
  "dry_run": true,
  "clinician_id": "CLINICIAN-ID",
  "action_taken": "summary_reviewed",
  "review_status": "reviewed",
  "target_type": "case_diagnostic_assistance",
  "source_preview_ids": ["problem-list-preview", "ddx-preview", "evidence-trace-preview"],
  "note": "Audit preview only; no diagnosis or treatment plan."
}
```

Controlled append example:

```json
{
  "case_id": 123,
  "dry_run": false,
  "clinician_id": "CLINICIAN-ID",
  "action_taken": "summary_reviewed",
  "review_status": "reviewed",
  "target_type": "case_diagnostic_assistance",
  "source_preview_ids": ["problem-list-preview", "ddx-preview", "evidence-trace-preview"],
  "note": "Clinician reviewed diagnostic assistance preview.",
  "audit_log_confirmation": "I_UNDERSTAND_THIS_APPENDS_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ONLY"
}
```

## Target support

Allowed targets:

```text
case_diagnostic_assistance
clinical_review_workflow
diagnostic_report
```

Observation and ImagingStudy audit targets remain blocked until their own review stages.

## Static validation

```bash
python3 scripts/validate_diagnostic_summary_audit_log.py
bash scripts/ci_static_checks.sh
```

## Smoke

Default smoke verifies dry-run behavior only.

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Controlled audit append smoke is opt-in:

```bash
PETMED_DIAGNOSTIC_SUMMARY_AUDIT_WRITE_SMOKE=1 \
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

## Completion gate

```text
Diagnostic Summary Audit Log V1：完成
validator=PASS
ci_static_checks=PASS
online_smoke=ALL_PASS
diagnostic_summary_audit_log_dry_run_endpoint_smoke=PASS
controlled_audit_log_append=PASS
production database_revision=0009_diag_data
production alembic_head=0009_diag_data
production schema_ok=true
dangerous_feature_flags_disabled=true
limited DB write only
writes AuditLog row only
append_only_audit_log=true
no Case write
no DiagnosticReport write
no Observation write
no ImagingStudy write
no ai_summary write
no persisted reasoning trace
no final diagnosis
no treatment plan
no prescription
no drug dose
requires_human_review=true
clinician_signoff_required=true
decision=GO_TO_DIAGNOSTICREPORT_AI_SUMMARY_PERSISTENCE_V1
```
