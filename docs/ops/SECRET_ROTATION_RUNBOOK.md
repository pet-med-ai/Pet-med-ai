# Secret Rotation Runbook

## Scope

Secrets covered:

```txt
GitHub PAT / fine-grained token
GitHub Actions repository secrets
Render SECRET_KEY
Render DATABASE_URL
PMAI_WEBHOOK_SECRET
third-party API keys
```

## Rotation triggers

Rotate immediately if:

```txt
secret appears in GitHub
secret appears in Render logs
secret appears in terminal output shared externally
classic PAT is long-lived and broad scoped
team member offboarding
unknown GitHub Actions failure exposes env
```

## GitHub PAT rotation

1. Open:

```txt
GitHub -> Settings -> Developer settings -> Personal access tokens
```

2. Revoke unused or over-scoped tokens.
3. Prefer GitHub App or fine-grained token.
4. If a token is used by Actions, store it in:

```txt
Repo -> Settings -> Secrets and variables -> Actions
```

5. Update workflow to reference:

```txt
${{ secrets.GH_TOKEN }}
```

6. Re-run GitHub Actions CI Gate.

## Render secret rotation

1. Open Render service environment.
2. Add new secret value.
3. Deploy service.
4. Verify:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

5. Remove old value.
6. Record rotation in release record.

## Webhook secret rotation

For `PMAI_WEBHOOK_SECRET`:

```txt
1. Coordinate sender and receiver.
2. Add new secret to sender.
3. Add new secret to Render.
4. Run signed dry-run test.
5. Remove old secret from sender and receiver.
6. Record receipt_id and smoke result.
```

## No-Go

Do not rotate during:

```txt
active EMR import pilot window
active database migration
ongoing incident without rollback owner
```
