# Observation Abnormal Flag Review V1

## Purpose

Observation Abnormal Flag Review V1 opens a tightly bounded clinician-only persistence step for existing `Observation` records.

This stage lets a clinician review and persist only:

```text
Observation.abnormal_flag
Observation.review_status
```

It is not a diagnosis engine. It is not a treatment engine. It is not a prescription engine.

## API

```text
POST /api/diagnostic-data/observations/{observation_id}/abnormal-flag/review/apply
```

## Required non-dry-run safeguards

Non-dry-run writes require all of the following:

```text
existing Observation
authenticated owner-scoped Case access
reviewed_by
audit_log_id from Diagnostic Summary Audit Log V1
abnormal_flag_review_confirmation=I_UNDERSTAND_THIS_WRITES_OBSERVATION_ABNORMAL_FLAG_REVIEW_ONLY
```

## Allowed writes

```text
Observation.abnormal_flag
Observation.review_status
```

## Explicitly blocked

```text
Case write
no DiagnosticReport write
DiagnosticReport.ai_summary write
DiagnosticReport.abnormal_summary write
new DiagnosticReport
new Observation
ImagingStudy write
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
updates_observation=false
writes_observation_abnormal_flag_only=false
writes_audit_log=false
```

Non-dry-run responses may expose:

```text
dry_run=false
writes_database=true
updates_observation=true
writes_observation_abnormal_flag_only=true
writes_audit_log=false
```

## Validation

```bash
python3 scripts/validate_observation_abnormal_flag_review.py
bash scripts/ci_static_checks.sh
```

## Online smoke

Default smoke validates static gates and skips live Observation endpoint if no observation id is supplied.

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Dry-run endpoint smoke:

```bash
export PETMED_AUTH_TOKEN="..."
export PETMED_OBSERVATION_ID="existing observation id"

KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh

unset PETMED_AUTH_TOKEN PETMED_OBSERVATION_ID
```

Controlled non-dry-run write smoke requires an existing Diagnostic Summary Audit Log V1 `audit_log_id` for the same case:

```bash
export PETMED_AUTH_TOKEN="..."
export PETMED_OBSERVATION_ID="existing observation id"
export PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID="existing audit log id"

PETMED_OBSERVATION_ABNORMAL_FLAG_WRITE_SMOKE=1 \
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh

unset PETMED_AUTH_TOKEN PETMED_OBSERVATION_ID PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID
```

## Go / No-Go

```text
Observation Abnormal Flag Review V1 is GO only if validator PASS, CI PASS, online smoke PASS, production schema remains 0009_diag_data, and controlled DB write evidence shows Observation.abnormal_flag/review_status only.
decision=GO_TO_IMAGINGSTUDY_REVIEW_WORKFLOW_V1
```
