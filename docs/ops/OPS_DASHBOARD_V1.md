# Pet-Med-AI Release Status / Admin Ops Dashboard V1

## Purpose

This stage adds a read-only frontend operations dashboard for release and upgrade verification.

Route:

```txt
/ops
```

## Data sources

The page reads:

```txt
GET /healthz
GET /api/system/version
GET /api/system/feature-flags
```

## What it shows

```txt
Backend healthz
schema_ok
database_revision
alembic_head
database_revision == alembic_head
upgrade_ready
app_version
environment
service_name
git_commit_short
all_dangerous_features_disabled
dangerous_features_enabled
feature flag table
raw system version JSON
raw feature flags JSON
```

## Safety boundary

This UI is read-only.

```txt
writes_database=false
creates_case=false
updates_case=false
executes_real_import=false
```

It does not:

```txt
modify feature flags
run Alembic
trigger deploy
execute EMR import
create Case
update Case
download attachments
```

## Manual verification

Local:

```txt
http://localhost:5173/ops
```

Production:

```txt
https://pet-med-ai-frontend-static.onrender.com/ops
```

Expected safe state:

```txt
Backend healthz = OK
schema alignment = aligned
Dangerous flags = all off
Upgrade ready = true
```

## Why this matters

This dashboard gives operators a single visual checkpoint before and after releases.

It is especially useful for database-heavy releases because previous Alembic failures, such as overly long revision ids, can leave production database revision behind the code head. The dashboard should expose that mismatch through `schema_ok=false`.

## Completion criteria

```txt
1. frontend/src/pages/OpsDashboard.jsx exists.
2. /ops route exists.
3. Page calls /healthz, /api/system/version and /api/system/feature-flags.
4. Page displays schema_ok, database_revision, alembic_head.
5. Page displays dangerous feature flag state.
6. npm run build passes.
7. smoke includes static validator.
```
