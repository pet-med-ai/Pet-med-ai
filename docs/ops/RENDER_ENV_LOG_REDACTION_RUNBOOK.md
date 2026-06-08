# Render Environment / Log Redaction Runbook

## Purpose

Prevent Render environment variable and application log leaks.

## Services

```txt
Backend: pet-med-ai-backend
Frontend: pet-med-ai-frontend-static
Database: pet-med-ai-db
```

## Manual Render environment check

Check:

```txt
SECRET_KEY
DATABASE_URL
PMAI_WEBHOOK_SECRET
CORS_ORIGINS
ENVIRONMENT
VITE_API_BASE
```

Rules:

```txt
SECRET_KEY must not appear in render.yaml
DATABASE_URL must not appear in render.yaml as raw value
PMAI_WEBHOOK_SECRET must not appear in source files
frontend static site must not receive backend secrets
```

## Log search

In Render Logs, search:

```txt
SECRET
TOKEN
KEY
PASSWORD
DATABASE_URL
PMAI_WEBHOOK_SECRET
```

If value appears:

```txt
1. Stop rollout.
2. Rotate affected secret.
3. Remove logging source.
4. Redeploy.
5. Re-run online smoke.
6. Record incident in release record.
```

## Code scan

Run:

```bash
bash scripts/security_check.sh
```

The scan reports:

```txt
print(...SECRET/TOKEN/KEY/PASSWORD)
echo ...SECRET/TOKEN/KEY/PASSWORD
ghp_ token pattern
AWS key pattern
JWT-like token pattern
render.yaml secret markers
```

## Logging guideline

Do not log:

```txt
os.environ
request Authorization header
DATABASE_URL
SECRET_KEY
PMAI_WEBHOOK_SECRET
raw token values
```

Safe logging:

```txt
secret configured: true/false
token prefix: first 4 chars only if necessary
hash of token, never raw token
```
