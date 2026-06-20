# Diagnostic Data Model Post-Migration Verification V1

## Purpose

This stage verifies that the production 0009 diagnostic data model upgrade is safe after deployment.

The target production hard gate is:

```text
database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
```

This stage is a verification and evidence stage only. It does not introduce a new Alembic migration, a new write API, or any real external integration.

## Current model boundary

The 0009 diagnostic data model state is:

```text
Case
 ├── DiagnosticReport
 │    └── Observation
 └── ImagingStudy
```

Important correction:

```text
imaging_studies already existed from 0002_kpi_data_models.
0009 must not recreate imaging_studies.
0009 only adds diagnostic_reports, observations, and nullable additive imaging_studies fields.
```

## In scope

This stage verifies:

- production healthz OK
- production system version reports `database_revision=0009_diag_data`
- production system version reports `alembic_head=0009_diag_data`
- production system version reports `schema_ok=true`
- dangerous feature flags remain disabled
- online smoke test still passes
- `diagnostic_reports` exists
- `observations` exists
- imaging_studies additive columns exist
- old KPI / imaging paths are not broken
- old case / intake / Word export paths are not broken
- cross-user isolation still passes
- no real outbound messaging is enabled
- no real EMR write is enabled
- no real lab / DICOM / device ingest is enabled

## Explicit non-goals

This stage must not enable or add:

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

## Required evidence files

```text
docs/clinical_data/DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_CHECKLIST_V1.csv
docs/clinical_data/DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_SCHEMA_EVIDENCE_V1.csv
docs/clinical_data/DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_SMOKE_EVIDENCE_V1.csv
docs/clinical_data/DIAGNOSTIC_DATA_MODEL_POST_MIGRATION_GO_NO_GO_V1.csv
```

## Production runtime verification commands

Run from the repository root unless otherwise noted.

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz | python3 -m json.tool

curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool
```

The version endpoint must show:

```text
database_revision == 0009_diag_data
alembic_head == 0009_diag_data
schema_ok == true
```

Dangerous feature flags must remain disabled:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -c 'import sys,json; data=json.load(sys.stdin); flags=data.get("flags",{}); keys=["ENABLE_EMR_REAL_IMPORT","ENABLE_EMR_IMPORT_CASE_UPDATE","ENABLE_EMR_ATTACHMENT_DOWNLOAD","ENABLE_PREVENTIVE_AUTO_DELIVERY","ENABLE_PREVENTIVE_SMS_DELIVERY","ENABLE_PREVENTIVE_WECHAT_DELIVERY","ENABLE_PREVENTIVE_EMAIL_DELIVERY","ENABLE_PRESCRIPTION_STRUCTURED_WRITE","ENABLE_DEVICE_REAL_INGEST","ENABLE_BILLING_REAL_WRITE"]; bad=[]; missing=[];
for k in keys:
    if k not in flags:
        print(k, "MISSING")
        missing.append(k)
    else:
        v=flags[k].get("enabled") if isinstance(flags[k],dict) else flags[k]
        print(k, v)
        if v is not False:
            bad.append(k)
print("MISSING=", missing)
print("NOT_FALSE=", bad)
raise SystemExit(1 if bad or missing else 0)' ; echo "FLAGS_EXIT=$?"
```

Required result:

```text
MISSING=[]
NOT_FALSE=[]
FLAGS_EXIT=0
```

Run the online smoke gate:

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required result:

```text
CI/static validations PASS
healthz PASS
system version database revision schema alignment gate PASS
system feature flags PASS
legacy cases / case payload dry-run PASS
clinical docs export smoke PASS
KPI / imaging smoke PASS
cross-user isolation PASS
no real outbound delivery PASS
```

## Schema verification commands

Use a trusted shell that has access to the target database environment. Do not print or commit database URLs or credentials.

Example SQLAlchemy inspector check:

```bash
python3 - <<'PY'
from sqlalchemy import create_engine, inspect
from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

required_tables = {"diagnostic_reports", "observations", "imaging_studies"}
tables = set(inspector.get_table_names())
missing_tables = sorted(required_tables - tables)
print("missing_tables=", missing_tables)

imaging_required = {
    "study_uid",
    "accession_number",
    "source_type",
    "source_system",
    "report_text",
    "abnormal_flag",
    "ai_summary",
    "ai_summary_status",
    "review_status",
    "reviewed_by",
    "reviewed_at",
    "attachment_ref",
    "updated_at",
}
imaging_columns = {c["name"] for c in inspector.get_columns("imaging_studies")}
missing_columns = sorted(imaging_required - imaging_columns)
print("missing_imaging_columns=", missing_columns)

raise SystemExit(1 if missing_tables or missing_columns else 0)
PY
```

Required result:

```text
missing_tables=[]
missing_imaging_columns=[]
```

## Static validation

```bash
python3 scripts/validate_diagnostic_data_model_post_migration_verification.py
bash scripts/ci_static_checks.sh
```

Required result:

```text
PASS: Diagnostic data model post-migration verification V1 docs and gates are present
CI static checks PASS
```

## Go / No-Go rule

`GO_TO_DIAGNOSTIC_DATA_READONLY_API_DRY_RUN_V1` is allowed only if every blocking gate in the checklist, schema evidence, smoke evidence, and Go / No-Go table passes.

Any of the following is P0 / NO-GO:

- `database_revision != 0009_diag_data`
- `alembic_head != 0009_diag_data`
- `schema_ok != true`
- `database_revision != alembic_head`
- dangerous feature flag missing or enabled
- online smoke failure
- missing `diagnostic_reports`
- missing `observations`
- missing additive `imaging_studies` columns
- cross-user isolation failure
- evidence of real EMR write, real lab / DICOM / device ingest, or automatic outbound delivery

## Decision

```text
decision=GO_TO_DIAGNOSTIC_DATA_READONLY_API_DRY_RUN_V1
next=Diagnostic Data Read-only API / Dry-run Fixtures V1
```
