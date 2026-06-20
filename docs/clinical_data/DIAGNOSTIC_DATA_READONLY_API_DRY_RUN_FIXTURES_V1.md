# Diagnostic Data Read-only API / Dry-run Fixtures V1

## Purpose

This stage exposes a read-only, owner-scoped diagnostic data API for the 0009 diagnostic data model and adds synthetic dry-run fixtures for downstream parser and UI work.

This is the first post-0009 implementation stage after `Diagnostic Data Model Post-Migration Verification V1`.

## Entry gate

This stage may start only after:

```text
Diagnostic Data Model Post-Migration Verification V1：完成
decision=GO_TO_DIAGNOSTIC_DATA_READONLY_API_DRY_RUN_V1
database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
online smoke PASS
```

## Scope

Adds read-only API coverage for:

```text
Case
 ├── DiagnosticReport
 │    └── Observation
 └── ImagingStudy
```

API endpoints:

```text
GET /api/diagnostic-data/cases/{case_id}/summary
GET /api/diagnostic-data/cases/{case_id}/reports
GET /api/diagnostic-data/reports/{report_id}
GET /api/diagnostic-data/cases/{case_id}/observations
GET /api/diagnostic-data/cases/{case_id}/imaging-studies
GET /api/diagnostic-data/dry-run/fixtures
GET /api/diagnostic-data/dry-run/fixtures/{fixture_id}
```

All endpoints are authenticated and owner-scoped. A user must not be able to read diagnostic data for another user's case.

## Dry-run fixture boundary

Dry-run fixtures are synthetic JSON files stored in:

```text
docs/clinical_data/fixtures/
```

They are for parser, UI and smoke testing only. They are not real patient data and must not be transmitted to a real lab, PACS, device gateway or EMR.

## Safety boundary

This stage must not add or enable:

- real EMR import
- EMR case update
- EMR attachment download
- real lab equipment ingest
- real DICOM / PACS ingest
- real device gateway ingest
- structured prescription write
- drug dose auto-recommendation
- automatic SMS / WeChat / email delivery
- provider credentials
- background worker delivery
- invoice real writes

Every endpoint must return read-only safety markers:

```text
read_only=true
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
sends_external_message=false
executes_real_import=false
executes_real_lab_ingest=false
executes_real_dicom_ingest=false
executes_real_device_ingest=false
```

The dry-run fixture endpoint additionally returns:

```text
dry_run=true
```

## Static validation

```bash
python3 scripts/validate_diagnostic_data_readonly_api_dry_run_fixtures.py
bash scripts/ci_static_checks.sh
```

Required result:

```text
PASS: Diagnostic data read-only API / dry-run fixtures V1 files and gates are present
CI static checks PASS
```

## Online smoke coverage

The smoke test must check:

```text
diagnostic data case summary
diagnostic data reports read-only
diagnostic data observations read-only
diagnostic data imaging studies read-only
diagnostic data dry-run fixtures list
diagnostic data dry-run fixture get
diagnostic data fixture requires auth
user B cannot read user A diagnostic data
```

All smoke checks must pass without database writes from diagnostic data endpoints.

## Go / No-Go

GO requires:

- authenticated owner-scoped read-only API exists
- dry-run fixture endpoint exists
- fixture JSON is synthetic
- smoke covers user A read-only access
- smoke covers user B access denial
- no database write path exists in diagnostic data API
- CI static checks pass
- production database remains `0009_diag_data / 0009_diag_data / schema_ok=true`

## Decision

```text
decision=PENDING_VALIDATION
next=Lab Result Dry-run Fixture Parser V1
```
