# ImagingStudy Review Workflow V1

## Purpose

ImagingStudy Review Workflow V1 opens a tightly bounded clinician-only persistence step for existing `ImagingStudy` records.

This stage lets a clinician review and persist only:

```text
ImagingStudy.review_status
ImagingStudy.reviewed_by
ImagingStudy.reviewed_at
ImagingStudy.abnormal_flag
```

It is not a diagnosis engine. It is not an imaging report generator. It is not a treatment engine. It is not a prescription engine.

## API

```text
POST /api/diagnostic-data/imaging-studies/{imaging_study_id}/review-workflow/apply
```

## Required non-dry-run safeguards

Non-dry-run writes require all of the following:

```text
existing ImagingStudy
authenticated owner-scoped Case access
reviewed_by
audit_log_id from Diagnostic Summary Audit Log V1
imagingstudy_review_confirmation=I_UNDERSTAND_THIS_WRITES_IMAGINGSTUDY_REVIEW_WORKFLOW_ONLY
```

## Allowed writes

```text
ImagingStudy.review_status
ImagingStudy.reviewed_by
ImagingStudy.reviewed_at
ImagingStudy.abnormal_flag
```

## Explicitly blocked

```text
Case write
no DiagnosticReport write
no Observation write
new ImagingStudy
ImagingStudy.report_text write
ImagingStudy.ai_summary write
no AuditLog write
problem list persistence
differential candidate persistence
reasoning trace persistence
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
client-facing release
external AI/provider call
real EMR/lab/DICOM/device ingest
PACS query
attachment download
```

## Response safety contract

Every response must expose:

```text
requires_human_review=true
clinician_signoff_required=true
not_a_diagnosis=true
not_a_treatment_plan=true
not_a_prescription=true
not_client_facing=true
```

Dry-run responses must expose:

```text
dry_run=true
writes_database=false
updates_imaging_study=false
writes_audit_log=false
```

Non-dry-run responses may expose:

```text
dry_run=false
writes_database=true
updates_imaging_study=true
writes_audit_log=false
```

## Validation

```bash
python3 scripts/validate_imagingstudy_review_workflow.py
bash scripts/ci_static_checks.sh
```

## Online smoke

Default smoke validates static gates and skips live ImagingStudy endpoint if no imaging study id is supplied.

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Dry-run endpoint smoke:

```bash
export PETMED_AUTH_TOKEN="..."
export PETMED_IMAGING_STUDY_ID="existing imaging study id"

KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh

unset PETMED_AUTH_TOKEN PETMED_IMAGING_STUDY_ID
```

Controlled non-dry-run write smoke requires an existing Diagnostic Summary Audit Log V1 `audit_log_id` for the same case:

```bash
export PETMED_AUTH_TOKEN="..."
export PETMED_IMAGING_STUDY_ID="existing imaging study id"
export PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID="existing audit log id"

PETMED_IMAGINGSTUDY_REVIEW_WRITE_SMOKE=1 \
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh

unset PETMED_AUTH_TOKEN PETMED_IMAGING_STUDY_ID PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID
```

## Go / No-Go

```text
ImagingStudy Review Workflow V1 is GO only if validator PASS, CI PASS, online smoke PASS, production schema remains 0009_diag_data, and controlled DB write evidence shows ImagingStudy.review_status/reviewed_by/reviewed_at/abnormal_flag only.
decision=GO_TO_CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_V1
```
