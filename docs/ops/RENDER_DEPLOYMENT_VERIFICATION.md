# Render Deployment Verification V1

## Services

```txt
Backend: pet-med-ai-backend
Backend URL: https://pet-med-ai-backend.onrender.com

Frontend Static Site: pet-med-ai-frontend-static
Frontend URL: https://pet-med-ai-frontend-static.onrender.com

PostgreSQL: pet-med-ai-db
```

## Backend health check

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz
```

Expected:

```json
{"ok": true}
```

## Frontend route check

Open the changed route directly.

Examples:

```txt
https://pet-med-ai-frontend-static.onrender.com/
https://pet-med-ai-frontend-static.onrender.com/kpi
https://pet-med-ai-frontend-static.onrender.com/webhooks/emr/inbox
https://pet-med-ai-frontend-static.onrender.com/emr/import-batches
```

If a direct route returns blank or 404, check Render Static Site rewrite:

```txt
Source: /*
Destination: /index.html
Action: Rewrite
```

## Render backend shell database check

Use backend service shell.

```bash
cd ~/project/src/backend

python3 -m alembic -c alembic.ini current
python3 -m alembic -c alembic.ini history
```

For new real migrations:

```bash
python3 -m alembic -c alembic.ini upgrade head
python3 -m alembic -c alembic.ini current
```

Do not use `stamp head` for new migrations that create tables or columns.

## Online smoke

Run from local Mac:

```bash
cd ~/Documents/Pet-med-ai

BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Expected:

```txt
ALL PASS
```

## Common failure: Alembic revision id too long

Symptom:

```txt
psycopg2.errors.StringDataRightTruncation:
value too long for type character varying(32)
```

Cause:

```txt
alembic_version.version_num is VARCHAR(32)
revision id exceeds 32 characters
```

Fix:

```txt
Shorten revision id to <=32 chars.
Rename migration file if needed.
Update validators/docs/smoke references.
Redeploy backend.
Run alembic upgrade head again.
```

Do not downgrade or stamp unless the runbook explicitly says so.

## Verification record

For each release, record:

```txt
commit SHA
backend deploy time
frontend deploy time
database current before
database current after
online smoke result
manual page result
rollback snapshot id if applicable
```
