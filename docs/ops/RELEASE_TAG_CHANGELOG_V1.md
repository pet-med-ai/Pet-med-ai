# Pet-Med-AI Release Tag / Changelog V1

## Purpose

This stage adds a standard release tagging and changelog workflow for Pet-Med-AI.

It complements:

```txt
Release / Upgrade Framework V1
Version / Build Info V1
Feature Flag / Safety Gate V1
Ops Dashboard V1
```

The goal is to make every production update traceable:

```txt
what changed
which commit shipped
which database revision was expected
whether smoke passed
whether high-risk flags remained safe
whether rollback evidence exists
```

## Release tag format

Use date-based semantic tags:

```txt
release/YYYY.MM.DD-N
```

Examples:

```txt
release/2026.06.06-1
release/2026.06.06-2
```

For docs-only releases, optional suffix:

```txt
release/2026.06.06-docs-1
```

## Release record location

Each release should have a markdown record under:

```txt
docs/ops/releases/
```

Recommended filename:

```txt
YYYY-MM-DD_<short-release-name>.md
```

Example:

```txt
docs/ops/releases/2026-06-06_ops-dashboard-v1.md
```

## Required release record fields

Every record must include:

```txt
Release ID
Date
Owner
Risk class
Git commit
Git tag
Target files
Database revision before
Database revision after
Alembic head
Local smoke result
Online smoke result
Frontend manual checks
Feature flag state
Rollback plan
Final status
```

## Standard workflow

### 1. Prepare target files

```bash
cd ~/Documents/Pet-med-ai

git status --short -- <target files>
```

Do not run:

```bash
git add .
```

### 2. Validate release readiness

```bash
python3 scripts/validate_release_readiness.py
python3 scripts/validate_release_changelog.py
```

### 3. Run required build / smoke

Backend-only:

```bash
python3 -m py_compile <changed python files>
```

Frontend:

```bash
cd frontend
npm run build
```

Runtime change:

```bash
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

### 4. Commit

```bash
git add <target files>
git commit -m "<message>"
git push origin main
```

### 5. Tag after verification

After local checks and before or after deployment, depending on risk class:

```bash
git tag -a release/YYYY.MM.DD-1 -m "Pet-Med-AI release YYYY.MM.DD-1"
git push origin release/YYYY.MM.DD-1
```

For database or real-write releases, tag only after online smoke passes.

### 6. Online verification

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

### 7. Record result

Create or update the release record in:

```txt
docs/ops/releases/
```

## Risk classes

```txt
docs-only
frontend
backend-api
database-migration
real-write
emergency-fix
```

## Hard No-Go for tagging

Do not tag a release if any of these are true:

```txt
local smoke required but not run
online smoke required but failed
schema_ok=false
database_revision != alembic_head
dangerous feature flags unexpectedly enabled
git status includes unintended files
Alembic upgrade failed
rollback snapshot missing for database / real-write release
```

## Changelog rules

`CHANGELOG.md` should be short and human-readable.

Use sections:

```txt
Added
Changed
Fixed
Security
Safety
Docs
Migration
```

Do not paste raw terminal logs into `CHANGELOG.md`. Put logs into the release record or runbook evidence.

## Completion criteria

```txt
1. CHANGELOG.md exists.
2. Release tag runbook exists.
3. Release record template exists.
4. Release policy CSV exists.
5. validate_release_changelog.py exists.
6. smoke includes release changelog validation.
```
