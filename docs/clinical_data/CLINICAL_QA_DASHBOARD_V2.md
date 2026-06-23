# Clinical QA Dashboard V2

## Purpose

Clinical QA Dashboard V2 adds a read-only clinician QA dashboard for the diagnostic-data clinical core.

It aggregates existing owner-scoped clinical records:

- Case
- DiagnosticReport
- Observation
- ImagingStudy
- Diagnostic Summary Audit Log entries

The dashboard is for internal clinical review only. It is not a diagnosis engine, not a treatment planner, not a prescription writer, and not client-facing content.

## API

```text
GET /api/diagnostic-data/clinical-qa-dashboard/v2/summary
GET /api/diagnostic-data/clinical-qa-dashboard/v2/summary?case_id={case_id}
```

## In scope

- read-only QA summary cards
- diagnostic report review coverage
- abnormal observation review gaps
- imaging study review gaps
- diagnostic summary audit-log coverage signal
- clinician QA queue preview
- owner-scoped access
- no database writes

## Out of scope

- final diagnosis generation
- confirmed or definitive diagnosis
- treatment plan generation
- prescription write
- drug dose / route / frequency output
- AI summary writes
- audit log writes
- reasoning trace persistence
- client-facing release
- external AI/provider calls
- EMR/lab/DICOM/device real ingest
- PACS query or image download

## Required safety flags

```text
read_only=true
writes_database=false
creates_case=false
updates_case=false
updates_diagnostic_report=false
updates_observation=false
updates_imaging_study=false
writes_ai_summary=false
writes_audit_log=false
persists_reasoning_trace=false
generates_final_diagnosis=false
creates_treatment_plan=false
writes_prescription=false
returns_drug_dose=false
requires_human_review=true
clinician_signoff_required=true
not_client_facing=true
```

## Validation

```bash
python3 scripts/validate_clinical_qa_dashboard_v2.py
bash scripts/ci_static_checks.sh
```

## Smoke

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required smoke markers:

```text
[smoke] Clinical QA Dashboard V2 validator
[smoke] Clinical QA Dashboard V2 endpoint PASS
```

## Go / No-Go

```text
Clinical QA Dashboard V2 is complete only after validator PASS, CI PASS, online smoke ALL PASS, production schema gate remains 0009_diag_data, and dangerous feature flags remain disabled.
decision=GO_TO_OPS_DASHBOARD_CLINICAL_CORE_V2
```
