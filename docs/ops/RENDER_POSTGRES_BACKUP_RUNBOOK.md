# Render PostgreSQL Backup Runbook

## Target service

```txt
Render PostgreSQL: pet-med-ai-db
Backend service: pet-med-ai-backend
Backend URL: https://pet-med-ai-backend.onrender.com
```

## When to verify backup

Verify backup before:

```txt
database migration
real EMR import pilot
bulk Case creation
feature flag enabling for real writes
manual data correction
```

## Operator steps

1. Open Render dashboard.
2. Navigate to PostgreSQL service:

```txt
pet-med-ai-db
```

3. Confirm latest available backup or snapshot.
4. Record:

```txt
backup_id
created_at
database_name
restore option
retention window
operator_id
screenshot/log reference
```

5. Confirm backend system version:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool
```

6. Confirm feature flags:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool
```

7. Run online smoke:

```bash
cd ~/Documents/Pet-med-ai
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

## Required healthy result

```txt
schema_ok=true
database_revision == alembic_head
writes_database=false for /api/system/version
all_dangerous_features_disabled=true before intentionally enabling real pilot
online smoke ALL PASS
```

## Restore rehearsal

A restore rehearsal must be performed before the first real EMR import pilot.

Record in:

```txt
docs/ops/ROLLBACK_REHEARSAL_TEMPLATE.csv
```

## If migration fails

Stop.

Do not run:

```txt
alembic stamp head
alembic downgrade
manual UPDATE alembic_version
```

unless a specific rollback plan says to do so.

Capture:

```txt
full terminal output
database current revision after failure
migration id
git commit
operator_id
```

Then decide:

```txt
fix migration and redeploy
or restore snapshot
or pause release
```
