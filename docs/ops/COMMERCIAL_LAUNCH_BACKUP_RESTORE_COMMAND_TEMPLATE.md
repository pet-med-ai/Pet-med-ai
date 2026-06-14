# Commercial Launch Backup / Restore Command Template V2

## Purpose

This file records sanitized command patterns for Backup / Restore Drill V2.

Do not commit real DATABASE_URL values, passwords, dump files, client data, or
screenshots containing PHI/secrets.

## Preflight

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz

curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool

curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool

BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

## Render Shell Alembic confirmation

Production Render Shell:

```bash
cd ~/project/src/backend

python3 -m alembic -c alembic.ini current
python3 -m alembic -c alembic.ini heads
```

Expected:

```txt
current == heads == 0008_auto_delivery
```

## Manual export pattern

Use placeholders only in committed docs:

```bash
pg_dump "$PRODUCTION_DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="/secure/local/path/petmed_backup_<YYYYMMDD_HHMM>.dump"
```

Optional checksum:

```bash
shasum -a 256 "/secure/local/path/petmed_backup_<YYYYMMDD_HHMM>.dump"
```

Do not commit the dump file.

## Restore target pattern

Never use production as restore target.

```bash
createdb petmed_restore_drill_v2
```

or use a temporary managed PostgreSQL restore target.

## Restore pattern

```bash
pg_restore \
  --dbname "$RESTORE_DATABASE_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  "/secure/local/path/petmed_backup_<YYYYMMDD_HHMM>.dump"
```

## Restored DB validation SQL

```bash
psql "$RESTORE_DATABASE_URL" -c "SELECT version_num FROM alembic_version;"
psql "$RESTORE_DATABASE_URL" -c "\dt"
```

Expected key tables include:

```txt
users
cases
consult_sessions
preventive_care_reminders
preventive_care_events
preventive_care_client_preferences
preventive_care_notification_queue
automated_reminder_delivery_templates
automated_reminder_delivery_attempts
```

## Restored backend smoke

If a temporary backend is pointed to the restore target:

```bash
BASE_URL="<RESTORE_BACKEND_URL>" bash scripts/smoke_petmed.sh
```

Record whether the restored backend smoke was:

```txt
PASS
FAIL
not_available_with_reason
```

## Cleanup

```bash
dropdb petmed_restore_drill_v2
```

or delete/lock the temporary managed restore target.

Record cleanup status in the evidence template.
