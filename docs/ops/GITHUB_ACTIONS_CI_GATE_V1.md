# GitHub Actions CI Gate V1

## Purpose

This stage adds a GitHub Actions CI gate for Pet-Med-AI pull requests and pushes to `main`.

The gate is intentionally static and offline. It does not connect to Render, does not run Alembic upgrade, and does not enable real import feature flags.

## Files

```txt
.github/workflows/ci-gate.yml
scripts/ci_static_checks.sh
scripts/validate_ci_gate.py
docs/ops/GITHUB_ACTIONS_CI_GATE_V1.md
```

## Workflow triggers

```txt
pull_request
push to main
workflow_dispatch
```

## Jobs

### Static backend and release validators

Runs:

```txt
bash scripts/ci_static_checks.sh
```

The static script runs:

```txt
Release readiness validation
Release changelog validation
System version validation
Feature flag validation
Ops dashboard validation
Alembic setup validation
EMR import safety validators
KPI / audit validators
Python py_compile across backend and scripts
```

### Frontend build gate

Runs:

```txt
cd frontend
npm install
npm run build
```

## Safety boundaries

The CI gate:

```txt
does not run Alembic upgrade
does not connect to production PostgreSQL
does not call Render backend
does not run online smoke
does not set DATABASE_URL
does not set SECRET_KEY
does not enable ENABLE_EMR_REAL_IMPORT
does not create Case
does not execute EMR import
```

## What this catches

```txt
Python syntax errors
missing validator files
Alembic revision id length problems
startup schema mutation regressions
missing release/changelog assets
missing Ops Dashboard route
missing feature flag safety gates
frontend build failures
```

## What this does not replace

This does not replace:

```txt
local smoke
Render deployment verification
Render Alembic upgrade for real migrations
online smoke
manual browser checks
clinical approval
rollback runbook
```

## Required repository settings

Recommended GitHub branch protection:

```txt
Require a pull request before merging
Require status checks to pass before merging
Require Pet-Med-AI CI Gate jobs to pass
Require branch to be up to date before merging
Restrict force pushes
Require conversation resolution
```

## Completion criteria

```txt
1. .github/workflows/ci-gate.yml exists.
2. scripts/ci_static_checks.sh exists and is executable.
3. scripts/validate_ci_gate.py exists.
4. smoke includes validate_ci_gate.py.
5. CI workflow runs validators and frontend build.
6. Workflow contains no production DB secrets and no real import flags.

```
