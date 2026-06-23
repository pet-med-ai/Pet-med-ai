# DiagnosticReport AI Summary Persistence V1

## Purpose

This stage opens a controlled persistence path for clinician-reviewed `DiagnosticReport.ai_summary` content.

It is not an AI generation stage and it does not call an external provider. The input must already be reviewed by a clinician and must stay inside diagnostic-summary language. It is still not a final diagnosis, not a treatment plan, not a prescription, and not client-facing.

## API

```text
POST /api/diagnostic-data/diagnostic-reports/{report_id}/ai-summary/persistence/apply
```

## Preconditions for non-dry-run write

- authenticated owner-scoped case access
- existing DiagnosticReport row
- DiagnosticReport.status already reviewed
- clinician reviewer supplied through `reviewed_by`
- existing Diagnostic Summary Audit Log V1 row supplied through `audit_log_id`
- explicit confirmation string:

```text
I_UNDERSTAND_THIS_WRITES_DIAGNOSTICREPORT_AI_SUMMARY_ONLY
```

## Allowed write scope

```text
DiagnosticReport.ai_summary
DiagnosticReport.ai_summary_status
DiagnosticReport.reviewed_by
DiagnosticReport.reviewed_at
```

## Blocked scope

```text
Case write
new DiagnosticReport creation
Observation write
ImagingStudy write
DiagnosticReport.abnormal_summary write
AuditLog write
problem list persistence
differential diagnosis candidate persistence
reasoning trace persistence
final diagnosis
confirmed diagnosis
definitive diagnosis
diagnostic conclusion
treatment plan
prescription
drug dose / route / frequency
probability / numeric confidence
client-facing release
external AI/provider call
real EMR / lab / DICOM / device ingest
```

## Safety flags

Required response flags:

```text
requires_human_review=true
clinician_signoff_required=true
not_client_facing=true
generates_final_diagnosis=false
generates_diagnostic_conclusion=false
creates_treatment_plan=false
writes_prescription=false
returns_drug_dose=false
writes_audit_log=false
persists_reasoning_trace=false
```

Dry-run responses must also return:

```text
writes_database=false
writes_ai_summary=false
```

Non-dry-run controlled writes may return:

```text
writes_database=true
updates_diagnostic_report=true
writes_ai_summary=true
writes_ai_summary_status=true
```

## Validation

```bash
python3 scripts/validate_diagnosticreport_ai_summary_persistence.py
bash scripts/ci_static_checks.sh
```

## Smoke

Default smoke validates the stage and skips the endpoint unless a token and report id are provided.

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Endpoint dry-run smoke:

```bash
PETMED_AUTH_TOKEN=... \
PETMED_DIAGNOSTIC_REPORT_ID=... \
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Controlled write smoke requires an existing Diagnostic Summary Audit Log V1 row and an already-reviewed DiagnosticReport:

```bash
PETMED_AI_SUMMARY_WRITE_SMOKE=1 \
PETMED_AUTH_TOKEN=... \
PETMED_DIAGNOSTIC_REPORT_ID=... \
PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID=... \
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

## Decision

```text
DiagnosticReport AI Summary Persistence V1 is complete only after validator PASS, CI PASS, online smoke PASS, controlled write PASS, and production schema remains 0009_diag_data.
decision=GO_TO_OBSERVATION_ABNORMAL_FLAG_REVIEW_V1
```
