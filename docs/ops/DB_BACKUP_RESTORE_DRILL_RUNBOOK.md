# Database Backup / Restore Drill Runbook

## Purpose

Prove that Pet-Med-AI backups can be restored before a real-write pilot.

## Production database

```txt
Render PostgreSQL: pet-med-ai-db
```

## Required evidence

Record in:

```txt
docs/ops/DB_RESTORE_DRILL_LOG.csv
```

Fields:

```txt
drill_id
date
backup_id
rollback_snapshot_id
restore_target
restore_duration_minutes
schema_ok_after_restore
smoke_after_restore
operator_id
result
notes
```

## Render managed restore

Manual process:

```txt
1. Open Render dashboard.
2. Select pet-med-ai-db.
3. Locate latest backup / snapshot.
4. Confirm restore workflow and target.
5. Record backup_id and created_at.
6. Do not restore over production without incident approval.
```

## Local rehearsal option

If a dump exists:

```bash
docker run -d --name pg-restore -e POSTGRES_PASSWORD=pass -p 5433:5432 postgres:16
pg_restore -h 127.0.0.1 -p 5433 -U postgres -d postgres /backups/petmed_latest.dump
```

Then point local backend to temporary DB for read-only checks only.

## No-Go

Do not perform real write pilot if:

```txt
no backup_id
restore path unknown
rollback owner unavailable
schema_ok=false
online smoke fails
```
