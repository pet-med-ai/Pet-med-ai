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
