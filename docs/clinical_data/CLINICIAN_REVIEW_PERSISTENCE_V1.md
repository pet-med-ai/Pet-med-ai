# Clinician Review Persistence V1

## Stage status

Clinician Review Persistence V1 introduces a bounded persistence API for clinician review status on existing diagnostic data records.

This is not diagnosis persistence, not AI summary persistence, not reasoning-trace persistence, not audit-log persistence, and not client release.

## Endpoint

```text
POST /api/diagnostic-data/clinician-review/persistence/apply
```

## Allowed persistence scope

The endpoint may update only review status fields on diagnostic-data records that already belong to the authenticated clinician's case.

Allowed target in this stage:

```text
diagnostic_report
```

Observation and ImagingStudy review workflows remain closed until their own later stages.

Allowed persisted fields:

```text
DiagnosticReport.status
DiagnosticReport.reviewed_by
DiagnosticReport.reviewed_at
```

The API does not create DiagnosticReport, Observation, ImagingStudy, Case, audit-log, prescription, treatment-plan, EMR, lab-ingest, DICOM, or device-ingest records.

## Confirmation boundary

The endpoint supports `dry_run=true` previews. Real persistence requires:

```text
persistence_confirmation=I_UNDERSTAND_THIS_WRITES_REVIEW_STATUS_ONLY
```

This confirmation is intentionally narrow. It authorizes review-status persistence only.

## Explicitly blocked

```text
final diagnosis
confirmed diagnosis
definitive diagnosis
diagnostic conclusion
treatment plan
prescription
drug dose
drug route
drug frequency
probability
numeric confidence
AI summary write
abnormal summary write
problem list persistence
differential diagnosis candidate persistence
reasoning trace persistence
audit log write
final signoff persistence
client-facing release
external AI/provider call
real EMR import
real lab ingest
real DICOM/PACS ingest
real device ingest
```

## Safety flags

Required response flags:

```text
requires_human_review=true
clinician_signoff_required=true
not_client_facing=true
client_release_allowed=false
final_signoff_persisted=false
writes_audit_log=false
persists_reasoning_trace=false
generates_final_diagnosis=false
generates_diagnostic_conclusion=false
creates_treatment_plan=false
writes_prescription=false
returns_drug_dose=false
returns_drug_route=false
returns_drug_frequency=false
```

For real persistence with valid targets:

```text
writes_database=true
updates_diagnostic_report=true, only if DiagnosticReport target exists
updates_observation=false
updates_imaging_study=false
```

For dry-run or no targets:

```text
writes_database=false
```

## Go / No-Go

GO only if:

```text
validator=PASS
ci_static_checks=PASS
online_smoke=ALL_PASS
production database_revision=0009_diag_data
production alembic_head=0009_diag_data
production schema_ok=true
dangerous_feature_flags_disabled=true
no Case write
no new DiagnosticReport
no Observation write
no ImagingStudy write
no AI summary write
no audit log write
no persisted reasoning trace
no final diagnosis
no treatment plan
no prescription
no drug dose
requires_human_review=true
clinician_signoff_required=true
```

Next stage:

```text
GO_TO_DIAGNOSTIC_SUMMARY_AUDIT_LOG_V1
```
