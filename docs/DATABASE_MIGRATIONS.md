# Pet-Med-AI Database Migrations

This document defines the first safe Alembic workflow for Pet-Med-AI.

## Current state

Pet-Med-AI historically created and patched database tables at application startup using:

- `Base.metadata.create_all(bind=engine)`
- small `ensure_*_columns()` helpers in `backend/main.py`

Alembic V1 does **not** remove those bootstrap helpers yet. It only adds a formal migration environment and a baseline revision for the current schema.

## Files

- `backend/alembic.ini`
- `backend/migrations/env.py`
- `backend/migrations/script.py.mako`
- `backend/migrations/versions/0001_baseline_current_schema.py`
- `scripts/validate_alembic_setup.py`

## Local validation

From the repository root:

```bash
python3 scripts/validate_alembic_setup.py
```

From the backend directory:

```bash
cd backend
alembic -c alembic.ini history
```

## Existing database workflow

For an existing database that already contains the current tables, do **not** run `upgrade head` as the first step.

Use:

```bash
cd backend
alembic -c alembic.ini stamp head
```

This creates or updates the Alembic version marker without attempting to create tables that already exist.

## New empty database workflow

For a new empty database:

```bash
cd backend
alembic -c alembic.ini upgrade head
```

## Production safety

Before any production migration action:

1. Confirm Render PostgreSQL backup / snapshot status.
2. Confirm the deployed code commit.
3. Run local smoke.
4. Prefer `alembic current` and `alembic history` before changing version state.
5. For the current existing Render database, the safe first action is `stamp head`, not `upgrade head`.

## Next phase

Alembic V2 can remove startup schema mutation from `backend/main.py` after both local and production databases have been stamped and verified.

---

## Alembic V2: runtime schema mutation removed

Alembic V2 moves Pet-Med-AI from early-stage startup schema bootstrapping to explicit migration ownership.

### What changed

The FastAPI application must no longer perform schema changes during import/startup:

- no `Base.metadata.create_all(bind=engine)` in `backend/main.py`
- no ad-hoc `ensure_consult_session_columns()` helper
- no ad-hoc `ensure_case_extra_columns()` helper
- no startup `ALTER TABLE` patching

The database schema is now owned by Alembic migrations.

### Operational rule

For existing databases, confirm the baseline before deploying runtime that no longer bootstraps tables:

```bash
cd backend
python3 -m alembic -c alembic.ini current
```

Expected existing baseline:

```txt
0001_baseline (head)
```

If an existing database has the current schema but no Alembic version row, run exactly once in that environment:

```bash
cd backend
python3 -m alembic -c alembic.ini stamp head
python3 -m alembic -c alembic.ini current
```

Do not run `upgrade head` against an existing database that already has the baseline tables.

### New-schema workflow

Future schema changes must follow this pattern:

```bash
cd backend
python3 -m alembic -c alembic.ini revision -m "describe change"
# edit generated migration
python3 -m alembic -c alembic.ini upgrade head
```

### Runtime validation

Smoke now runs:

```bash
python3 scripts/validate_alembic_runtime.py
```

This prevents accidental reintroduction of runtime table creation or startup column patching.

