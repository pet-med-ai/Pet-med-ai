# Render / GitHub Security Hardening V1

## Purpose

This runbook turns the current Render + GitHub deployment into a repeatable lightweight security check before real clinical-data write operations.

This stage is safety hardening only.

It does not:

```txt
rotate tokens automatically
change Render environment variables
modify GitHub repository settings automatically
change database schema
run Alembic
open ENABLE_EMR_REAL_IMPORT
create Case records
execute EMR import
```

## Why now

Pet-Med-AI already has:

```txt
Render backend
Render frontend static site
Render PostgreSQL
GitHub Actions CI Gate
Feature Flag / Safety Gate V1
Version / Build Info V1
Ops Dashboard V1
EMR create-only import implementation protected by feature flag
Backup / Rollback Verification V1
pilot_0 readiness and rehearsal documents
```

Before any real pilot writes Case records, the team must verify:

```txt
GitHub tokens are not long-lived or over-scoped
Render environment variables are not exposed
Render logs do not echo secrets
database backup and restore drill evidence exists
CI blocks obvious secret leaks
```

## Scope

This applies before:

```txt
real EMR import pilot_0
any feature flag window
database migrations
external EMR integration
device real ingest
attachment ingest
billing write
prescription structured write
```

## 1. GitHub token / PAT review

Manual checks:

```txt
GitHub -> Settings -> Developer settings -> Fine-grained tokens
GitHub -> Settings -> Developer settings -> Personal access tokens
Repository -> Settings -> Secrets and variables -> Actions
```

Required:

```txt
classic PATs revoked unless explicitly justified
fine-grained tokens have short expiry
repository secrets used instead of hardcoded tokens
GitHub App preferred for bots
Actions workflows do not embed tokens in plain text
```

No-Go:

```txt
ghp_ token found in repository
classic PAT with broad repo scope
token in workflow YAML
token in shell script
token printed to logs
```

## 2. Render environment and log review

Manual checks:

```txt
Render -> pet-med-ai-backend -> Environment
Render -> pet-med-ai-backend -> Logs
Render -> pet-med-ai-frontend-static -> Environment
```

Required:

```txt
SECRET_KEY stored only in Render environment
DATABASE_URL stored only in Render managed integration / environment
PMAI_WEBHOOK_SECRET stored only in Render environment
values hidden by dashboard
startup logs do not print secrets
error logs do not include raw env dumps
```

Search Render logs for:

```txt
SECRET
TOKEN
KEY
PASSWORD
DATABASE_URL
PMAI_WEBHOOK_SECRET
```

No-Go:

```txt
secret value appears in logs
render.yaml contains raw secret value
backend prints os.environ
scripts echo secret values
```

## 3. Database backup and restore drill

Manual checks:

```txt
Render -> pet-med-ai-db -> backups / restore options
```

Required before real writes:

```txt
backup_id recorded
rollback_snapshot_id recorded
restore path known
restore rehearsal recorded
online smoke command known
clinical verification owner assigned
```

## Static local security check

Run:

```bash
cd ~/Documents/Pet-med-ai
bash scripts/security_check.sh
```

The script reports possible secret echo, hardcoded token, and render.yaml secret markers. V1 is report-only to reduce false positives.

## CI behavior

CI validates that the security runbook and script exist.

CI does not:

```txt
connect to Render
read GitHub secrets
rotate tokens
run restore drill
open feature flags
```

## Hard No-Go before pilot_0 real execution

Any one means stop:

```txt
GitHub Actions latest CI Gate is red
security_check.sh shows unreviewed token pattern
Render logs expose secret values
Render backup not verified
restore path unknown
rollback_snapshot_id missing
all_dangerous_features_disabled is false before window
DATABASE_URL or SECRET_KEY appears in repository file
```

## Completion criteria

```txt
1. SECURITY.md exists.
2. Render/GitHub security hardening runbook exists.
3. Security checklist exists.
4. Secret rotation runbook exists.
5. Render env/log redaction runbook exists.
6. DB backup restore drill runbook exists.
7. DB restore drill log template exists.
8. scripts/security_check.sh exists.
9. scripts/validate_security_hardening.py exists.
10. smoke and ci_static_checks include validate_security_hardening.py.
```
