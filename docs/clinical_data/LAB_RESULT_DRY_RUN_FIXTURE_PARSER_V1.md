# Lab Result Dry-run Fixture Parser V1

## Purpose

This stage adds a dry-run parser for synthetic lab result fixtures.

It converts a fixture into:

```text
DiagnosticReport preview
Observation previews
abnormal observation list
quality gate
```

The parser is not a real lab equipment integration.

## Stage boundary

This stage is allowed to:

- parse synthetic JSON fixtures
- map lab values into DiagnosticReport / Observation preview shapes
- compute simple high / low / normal abnormal flags from reference ranges
- return read-only dry-run previews through authenticated API routes
- validate owner-scoped case access when a case_id is supplied

This stage must not:

- write `diagnostic_reports`
- write `observations`
- call a real lab / LIS provider
- ingest real device files
- download attachments
- update Case records
- trigger AI summary generation
- send SMS / WeChat / email
- enable EMR real import
- introduce a new Alembic migration

## API routes

```text
GET  /api/diagnostic-data/dry-run/lab-results/fixtures
GET  /api/diagnostic-data/dry-run/lab-results/fixtures/{fixture_id}
POST /api/diagnostic-data/dry-run/lab-results/parse
```

All routes require authentication.

## Fixture

```text
docs/clinical_data/fixtures/lab_result_dry_run_fixture_v1.json
```

The fixture is synthetic and includes CBC / chemistry values:

```text
WBC high
ALT high
CREA normal
GLU low
```

## Parser output

The parser returns:

```text
message=lab_result_dry_run_parsed
mode=lab_result_dry_run_fixture_parser_v1
quality_gate.status=PASS
report_preview.report_type=lab_panel
observations_preview[*]
abnormal_observations[*]
writes_database=false
executes_real_lab_ingest=false
sends_external_message=false
```

## Static validation

```bash
python3 scripts/validate_lab_result_dry_run_fixture_parser.py
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
PASS lab result dry-run fixture list
PASS lab result dry-run fixture get
PASS lab result dry-run fixture parse
PASS lab result dry-run parser requires auth
PASS user B cannot parse user A lab dry-run fixture
PASS lab result dry-run fixture parser checks
```

## Go / No-Go

`GO_TO_IMAGING_METADATA_DRY_RUN_FIXTURE_PARSER_V1` is allowed only if:

```text
validator PASS
ci_static_checks PASS
online smoke ALL PASS
database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
dangerous flags disabled
no real lab ingest
no DB writes from parser
```

## Decision

```text
decision=GO_TO_IMAGING_METADATA_DRY_RUN_FIXTURE_PARSER_V1
next=Imaging Metadata Dry-run Fixture Parser V1
```
