# Diagnostic Data Model Migration V1

## Purpose

This stage introduces the local implementation for Pet-Med-AI clinical diagnostic data models.

It adds:

- DiagnosticReport ORM and table
- Observation ORM and table
- additive nullable diagnostic fields on the existing ImagingStudy table

## Important correction

ImagingStudy already exists from 0002_kpi_data_models.

Therefore this migration must not create a second imaging_studies table.

It only extends the existing imaging_studies table additively.

## Revision

```text
revision=0009_diag_data
down_revision=0008_auto_delivery
```

## Safety boundary

This migration does not enable:

- real EMR import
- EMR case update
- EMR attachment download
- real lab equipment ingest
- real device ingest
- real DICOM / PACS ingest
- structured prescription write
- automatic outbound messaging

## Validation

Required validation:

```text
python3 scripts/validate_diagnostic_data_model_migration.py
bash scripts/ci_static_checks.sh
cd backend && python3 -m alembic -c alembic.ini heads
cd backend && python3 -m alembic -c alembic.ini upgrade head
cd backend && python3 -m alembic -c alembic.ini current
```
