# Case Detail Diagnostic Data Display V1

## Purpose

This stage adds a Case Detail UI panel for the 0009 diagnostic data model.

The panel reads the existing read-only diagnostic data endpoint and displays:

- DiagnosticReport count and recent report previews
- Observation count and recent / abnormal observation previews
- ImagingStudy count and imaging metadata previews
- explicit read-only safety markers

## Boundary

This stage is display-only.

It must not add:

- a new Alembic migration
- database writes from Case Detail
- DiagnosticReport creation
- Observation creation
- ImagingStudy creation
- real lab equipment ingest
- real LIS connection
- real DICOM / PACS ingest
- raw DICOM image retrieval
- real device gateway ingest
- EMR real write
- automatic outbound SMS / WeChat / email
- drug dose auto-recommendation

## UI data source

The Case Detail page uses:

```text
GET /api/diagnostic-data/cases/{case_id}/summary
```

The endpoint is authenticated and owner-scoped. User B must not be able to view User A diagnostic data.

## Required UI safety markers

The UI must visibly preserve these markers:

```text
read_only=true
writes_database=false
creates_case=false
executes_real_lab_ingest=false
executes_real_dicom_ingest=false
executes_real_device_ingest=false
```

## Validation

```bash
python3 scripts/validate_case_detail_diagnostic_data_display.py
bash scripts/ci_static_checks.sh
```

## Online smoke

Run:

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required result:

```text
case detail diagnostic data display validation PASS
ALL PASS
```

## Go / No-Go

`GO_TO_AI_LAB_ABNORMAL_SUMMARY_V1` is allowed only after static validation, CI static checks, production schema gate, and online smoke all pass.

## Decision

```text
decision=GO_TO_AI_LAB_ABNORMAL_SUMMARY_V1
next=AI Lab Abnormal Summary V1
```
