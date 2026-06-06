# Release tag examples

## Docs-only release

```bash
git tag -a release/2026.06.06-docs-1 -m "Docs release: EMR pilot checklist"
git push origin release/2026.06.06-docs-1
```

## Backend API release

```bash
git tag -a release/2026.06.06-1 -m "Backend release: system version endpoint"
git push origin release/2026.06.06-1
```

## Database migration release

Tag only after:

```txt
Render alembic upgrade head completed
/api/system/version shows schema_ok=true
online smoke ALL PASS
```

```bash
git tag -a release/2026.06.06-db-1 -m "DB release: EMR import execution result model"
git push origin release/2026.06.06-db-1
```

## Real-write pilot release

Tag only after post-execution checks:

```txt
ENABLE_EMR_REAL_IMPORT intentionally enabled
pilot executed
created cases 100% spot checked
online smoke after execution ALL PASS
rollback decision recorded
```

```bash
git tag -a release/2026.06.06-pilot0-1 -m "Pilot release: EMR create-only import pilot_0"
git push origin release/2026.06.06-pilot0-1
```
