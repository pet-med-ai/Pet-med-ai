# Pet-Med-AI Release Record Template

## Release identity

```txt
Release name:
Date:
Commit SHA:
Owner:
Stage:
Risk class: docs / frontend / backend / migration / real-write
```

## Target files

```txt
<file 1>
<file 2>
```

## Preflight

```txt
[ ] git status checked with target files only
[ ] validate_release_readiness.py passed
[ ] py_compile passed if Python changed
[ ] npm run build passed if frontend changed
[ ] Alembic current checked if DB changed
[ ] local smoke passed if runtime changed
```

## Deployment

```txt
[ ] commit pushed
[ ] Render backend deploy complete
[ ] Render frontend deploy complete if frontend changed
[ ] Alembic upgrade head done if migration changed
[ ] healthz ok
[ ] online smoke ALL PASS
```

## Manual verification

```txt
Route/API checked:
Result:
Screenshots/logs:
```

## Rollback plan

```txt
Rollback snapshot id:
Previous commit:
Rollback owner:
No-Go conditions:
```

## Final status

```txt
[ ] complete
[ ] paused
[ ] rolled back
```
