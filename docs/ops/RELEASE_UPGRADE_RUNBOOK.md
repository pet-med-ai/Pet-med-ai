# Pet-Med-AI Release / Upgrade Runbook V1

## Purpose

This runbook standardizes Pet-Med-AI updates, releases, Alembic upgrades, Render deployment checks, smoke tests, and rollback decisions.

This framework exists because Pet-Med-AI now has production services, PostgreSQL, Alembic migrations, KPI models, audit logs, EMR webhook inboxes, batch planning, execution dry-run, clinical approval, and migration-heavy workflows.

## Current known services

```txt
Repository: pet-med-ai / Pet-med-ai
Local root: ~/Documents/Pet-med-ai

Backend service: pet-med-ai-backend
Backend URL: https://pet-med-ai-backend.onrender.com

Frontend service: pet-med-ai-frontend-static
Frontend URL: https://pet-med-ai-frontend-static.onrender.com

Database: pet-med-ai-db
Local backend: http://127.0.0.1:8000
Local frontend: http://127.0.0.1:5173
```

## Release classes

### Class A: docs/templates only

Examples:

```txt
runbooks
checklists
CSV templates
design specs
integration specs
```

Required checks:

```txt
target files generated
git status --short -- target files only
commit / push successful
```

Smoke is usually not required.

### Class B: static validator / scripts only

Examples:

```txt
scripts/validate_*.py
dry-run CLI scripts
smoke script static additions
```

Required checks:

```txt
python3 script.py
python3 -m py_compile changed Python files
local smoke if smoke changed
```

### Class C: frontend only

Examples:

```txt
new pages
route changes
UI review panels
dashboard pages
```

Required checks:

```txt
python3 any relevant validate script
cd frontend && npm run build
local smoke if scripts/smoke_petmed.sh changed
online smoke after deployment if runtime behavior changed
manual browser verification
```

### Class D: backend API only

Examples:

```txt
new FastAPI routers
read-only review APIs
dry-run endpoints
append-only audit APIs
```

Required checks:

```txt
python3 relevant validate script
python3 -m py_compile changed backend files
local smoke ALL PASS
online smoke ALL PASS
```

### Class E: database migration

Examples:

```txt
new tables
new columns
new indexes
Alembic revisions
```

Required checks:

```txt
python3 scripts/validate_alembic_setup.py
python3 relevant validate script
python3 -m alembic -c backend/alembic.ini current
python3 -m alembic -c backend/alembic.ini upgrade head
python3 -m alembic -c backend/alembic.ini current
local smoke ALL PASS
commit / push
Render deploy
Render shell alembic upgrade head
online smoke ALL PASS
```

## Standard local release flow

```bash
cd ~/Documents/Pet-med-ai

git status --short -- <target files>

python3 scripts/validate_release_readiness.py
```

If backend or validators changed:

```bash
python3 -m py_compile <changed python files>
```

If frontend changed:

```bash
cd ~/Documents/Pet-med-ai/frontend
npm run build
```

If runtime changed:

```bash
cd ~/Documents/Pet-med-ai/backend
python3 -m uvicorn main:app --reload --port 8000
```

In another terminal:

```bash
cd ~/Documents/Pet-med-ai
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

## Standard commit flow

Never run:

```bash
git add .
```

Always run:

```bash
cd ~/Documents/Pet-med-ai

git status --short -- <target files>

git add <target files>

git commit -m "<message>"

git push origin main
```

## Standard Render release flow

After Render deploy completes:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz
```

For database migrations, use Render backend shell:

```bash
cd ~/project/src/backend

python3 -m alembic -c alembic.ini current
python3 -m alembic -c alembic.ini upgrade head
python3 -m alembic -c alembic.ini current
```

Then local terminal:

```bash
cd ~/Documents/Pet-med-ai

BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Expected:

```txt
ALL PASS
```

## Alembic rules

```txt
1. New schema changes require Alembic migrations.
2. Do not reintroduce Base.metadata.create_all at app startup.
3. Do not reintroduce startup ALTER TABLE / ensure_*_columns logic.
4. Use upgrade head for real new migrations.
5. Use stamp only when explicitly baselining an already-existing schema.
6. Alembic revision ids must be <=32 characters for default alembic_version.version_num compatibility.
7. Keep down_revision correct and linear unless intentionally branching.
```

## Hard No-Go release conditions

Stop the release if any condition is true:

```txt
local smoke fails
online smoke fails
Render backend healthz fails
Alembic current is not the expected pre-upgrade revision
Alembic upgrade fails
Alembic head is not reached after upgrade
migration revision id exceeds 32 chars
frontend build fails
unknown files would be included by git add .
database backup / rollback snapshot missing for real write phases
```

## Rollback principle

```txt
Docs-only release: revert commit if needed.
Frontend-only release: revert commit or redeploy previous commit.
Backend API release: revert commit and redeploy previous backend.
Database migration release: stop, inspect, restore snapshot or apply designed downgrade only after explicit approval.
Real import release: stop execution, preserve logs, run rollback runbook, smoke after rollback, clinical spot check.
```

## Completion criteria for this framework

```txt
1. Release runbook committed.
2. Release checklist committed.
3. Rollback checklist committed.
4. Render verification doc committed.
5. Alembic guardrails committed.
6. validate_release_readiness.py committed and included in smoke.
```
