# Alembic Release Guardrails V1

## Revision id length

Alembic's default `alembic_version.version_num` column is often `VARCHAR(32)`.

Therefore every revision id must be:

```txt
<= 32 characters
```

Bad example:

```txt
0006_emr_import_execution_results
```

Good example:

```txt
0006_emr_import_results
```

## Naming rules

```txt
Use short names.
Keep numeric prefix.
Avoid redundant words.
Keep file name and revision id aligned when possible.
```

Examples:

```txt
0001_baseline
0002_kpi_data_models
0003_audit_log
0004_webhook_inbox_receipts
0005_emr_import_batches
0006_emr_import_results
```

## Upgrade vs stamp

Use `upgrade head` when a migration actually creates or changes schema.

Use `stamp head` only for baselining an already-existing schema when explicitly instructed.

## Required local checks before migration release

```bash
cd ~/Documents/Pet-med-ai

python3 scripts/validate_release_readiness.py
python3 scripts/validate_alembic_setup.py

cd backend
python3 -m alembic -c alembic.ini current
python3 -m alembic -c alembic.ini upgrade head
python3 -m alembic -c alembic.ini current
```

## Required Render checks

```bash
cd ~/project/src/backend

python3 -m alembic -c alembic.ini current
python3 -m alembic -c alembic.ini upgrade head
python3 -m alembic -c alembic.ini current
```

## Do not reintroduce startup schema mutation

Forbidden in application startup:

```txt
Base.metadata.create_all
ensure_*_columns
ALTER TABLE
CREATE TABLE
```

Schema is controlled by Alembic only.

## If migration fails

```txt
1. Stop.
2. Capture full error.
3. Run current.
4. Do not stamp.
5. Do not downgrade unless rollback plan says so.
6. Check if PostgreSQL transactional DDL rolled back.
7. Fix migration or revision id.
8. Redeploy.
9. Re-run upgrade head.
10. Run online smoke.
```
