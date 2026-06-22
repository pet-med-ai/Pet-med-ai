# Clinician Review Workflow for Diagnostic Summaries V1

## Purpose

This stage adds a dry-run clinician review workflow preview for diagnostic summaries.

It consumes review inputs such as:

- AI Lab Abnormal Summary V1
- AI Imaging Report Summary V1
- Treatment Recommendation Boundary V1
- Drug Dose Safety Framework V1
- Drug Dose Knowledge Base V1 review metadata

It does not persist review status, does not sign a report, does not write DiagnosticReport.ai_summary, does not write audit rows, and does not release client-facing content.

## In scope

- dry-run review workflow preview
- owner-scoped case access through the diagnostic data API
- review item checklist
- allowed review-only actions
- blocked persistent / client-facing actions
- clinician signoff required flag
- human review required flag
- smoke coverage
- static validator

## Out of scope

- real report signoff
- persistent review state
- audit log append
- client-facing release
- prescription write
- treatment plan generation
- drug dose recommendation
- numeric dose output
- external AI provider calls
- real EMR / lab / DICOM / device ingest

## API

```text
POST /api/diagnostic-data/dry-run/clinician-review/diagnostic-summaries/check
```

Required response safety:

```text
writes_database=false
creates_diagnostic_report=false
updates_diagnostic_report=false
writes_ai_summary=false
creates_audit_log=false
writes_audit_log=false
signs_report=false
persists_review_status=false
releases_to_client=false
creates_prescription=false
writes_prescription=false
creates_treatment_plan=false
drug_dose_recommendation=false
calls_external_ai=false
requires_human_review=true
clinician_signoff_required=true
```

## Static validation

```bash
python3 scripts/validate_clinician_review_workflow_for_diagnostic_summaries.py
bash scripts/ci_static_checks.sh
```

## Online smoke

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required smoke markers:

```text
PASS Clinician review diagnostic summaries dry-run
PASS Clinician review workflow requires auth
PASS user B cannot check user A clinician review workflow
PASS Clinician review diagnostic summaries checks
```

## Decision

```text
Clinician Review Workflow for Diagnostic Summaries V1: complete only after validator PASS, CI PASS, online smoke ALL PASS, and production schema gate remains 0009_diag_data.
decision=GO_TO_DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_V1
```
