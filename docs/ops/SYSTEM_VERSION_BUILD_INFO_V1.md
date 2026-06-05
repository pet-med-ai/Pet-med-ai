# Pet-Med-AI Version / Build Info V1

## Purpose

This stage adds a read-only system version endpoint so operators can verify:

```txt
current app version
deployment environment
git commit when available
database backend
current Alembic database revision
current Alembic head from migration files
schema_ok
upgrade_ready
```

This supports safer release and upgrade operations after the Release / Upgrade Framework V1.

## Endpoint

```txt
GET /api/system/version
```

## Response fields

```txt
message=system_version
app_name=Pet-Med-AI
app_version
environment
service_name
git_commit
git_commit_short
database_backend
database_revision
alembic_head
alembic_heads
schema_ok
migration_errors
release_framework
upgrade_ready
writes_database=false
exposes_database_url=false
```

## Health endpoint

```txt
GET /api/system/health
```

This is a more compact system health endpoint based on the same version logic.

## Safety boundary

This stage is read-only.

```txt
No database writes
No Alembic upgrade
No schema mutation
No exposure of DATABASE_URL
No secret exposure
No frontend changes
```

## Usage

Local:

```bash
curl -sS http://127.0.0.1:8000/api/system/version | python3 -m json.tool
```

Production:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool
```

Expected production result after a healthy release:

```txt
schema_ok=true
database_revision == alembic_head
writes_database=false
exposes_database_url=false
```

## Environment variables

Optional:

```txt
APP_VERSION
ENVIRONMENT
RENDER_SERVICE_NAME
RENDER_GIT_COMMIT
GIT_COMMIT
COMMIT_SHA
SOURCE_VERSION
```

If no git commit environment variable exists, local deployments may attempt `git rev-parse HEAD`.

## Completion criteria

```txt
1. backend/system_info.py exists.
2. backend/main.py includes system_info_router.
3. GET /api/system/version returns 200.
4. Response includes database_revision and alembic_head.
5. Response includes writes_database=false.
6. Response does not expose DATABASE_URL.
7. smoke verifies the endpoint.
```
