# Imaging Metadata Dry-run Fixture Parser V1

## Purpose

This stage adds a dry-run parser for synthetic imaging metadata fixtures.

It converts an imaging metadata fixture into an `ImagingStudy` preview that can be inspected by the existing diagnostic data read-only API surface.

## Scope

This stage adds:

```text
backend/imaging_metadata_parser.py
docs/clinical_data/fixtures/imaging_metadata_dry_run_fixture_v1.json
GET /api/diagnostic-data/dry-run/imaging-metadata/fixtures
GET /api/diagnostic-data/dry-run/imaging-metadata/fixtures/{fixture_id}
POST /api/diagnostic-data/dry-run/imaging-metadata/parse
```

The parser returns:

```text
study_preview
quality_gate
safety
```

## Safety boundary

This stage is dry-run only.

It must not:

```text
write database rows
create ImagingStudy rows
query PACS
read raw DICOM pixels
download attachments
connect to devices
perform real DICOM / PACS ingest
perform real device ingest
send SMS / WeChat / email
perform EMR real import
generate treatment or drug-dose recommendations
```

## Expected parser result

The parser must produce:

```text
message=imaging_metadata_dry_run_parse
mode=imaging_metadata_dry_run_fixture_parser_v1
quality_gate.status=PASS
study_preview.modality=XR
study_preview.body_part=abdomen
study_preview.abnormal_flag=abnormal
writes_database=false
creates_imaging_study=false
queries_pacs=false
downloads_attachments=false
executes_real_dicom_ingest=false
executes_real_device_ingest=false
```

## Validation

```bash
python3 scripts/validate_imaging_metadata_dry_run_fixture_parser.py
bash scripts/ci_static_checks.sh
KEEP_TMP=1 BASE_URL=https://pet-med-ai-backend.onrender.com FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com bash scripts/smoke_petmed.sh
```

## Go / No-Go

`GO_TO_CASE_DETAIL_DIAGNOSTIC_DATA_DISPLAY_V1` is allowed only when:

```text
validator PASS
CI static checks PASS
online smoke ALL PASS
production database_revision=0009_diag_data
production alembic_head=0009_diag_data
production schema_ok=true
no DB writes from parser
no real DICOM / PACS ingest
no real device ingest
no external delivery
```

## Decision

```text
decision=GO_TO_CASE_DETAIL_DIAGNOSTIC_DATA_DISPLAY_V1
next=Case Detail Diagnostic Data Display V1
```
