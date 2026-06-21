# AI Imaging Report Summary V1

## Purpose

This stage adds a deterministic dry-run imaging report summary for synthetic imaging metadata fixtures.

It converts the existing imaging metadata dry-run parse output into a clinician review aid.

## Scope

This stage is limited to:

- synthetic imaging metadata fixtures
- dry-run parsed ImagingStudy previews
- read-only summary output
- clinician review aid language
- strict safety markers

## Explicit non-goals

This stage must not:

- query PACS
- ingest raw DICOM
- read DICOM pixels
- download imaging attachments
- create ImagingStudy rows
- update Case rows
- call an external AI provider
- generate a radiologist report
- generate a diagnosis
- generate a treatment plan
- generate drug dose recommendations
- send outbound messages

## API

```text
POST /api/diagnostic-data/dry-run/imaging-metadata/report-summary
```

Example request:

```json
{
  "case_id": 123,
  "fixture_id": "imaging_metadata_dry_run_fixture_v1"
}
```

Required response markers:

```text
message=ai_imaging_report_summary_dry_run
mode=ai_imaging_report_summary_v1
summary.human_review_required=true
summary.not_a_diagnosis=true
summary.not_a_treatment_plan=true
summary.not_a_drug_dose_recommendation=true
summary.not_a_radiologist_report=true
writes_database=false
creates_imaging_study=false
queries_pacs=false
reads_raw_dicom=false
executes_real_dicom_ingest=false
executes_real_device_ingest=false
calls_external_ai=false
calls_external_provider=false
```

## Validation

```bash
python3 scripts/validate_ai_imaging_report_summary.py
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
PASS AI imaging report summary dry-run
PASS AI imaging report summary requires auth
PASS user B cannot summarize user A imaging report
PASS AI imaging report summary checks
ALL PASS
```

## Decision

```text
decision=GO_TO_TREATMENT_RECOMMENDATION_BOUNDARY_V1
```
