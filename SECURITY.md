# Security Policy

## Pet-Med-AI security baseline

Pet-Med-AI handles clinical workflow data, EMR webhook payloads, audit logs, and future controlled import flows. Security changes must be treated as release-gated work.

## Supported security practices

```txt
No hardcoded production secrets
No long-lived personal access token in code
No DATABASE_URL in repository files
No SECRET_KEY in repository files
No webhook secret in repository files
No secret echo in scripts
No secret print in backend logs
High-risk feature flags default off
Render environment variables stored only in Render Dashboard
Database backup / rollback evidence required before real writes
```

## Reporting

For internal security findings, record:

```txt
finding_id
date
component
severity
suspected_secret_type
affected_file_or_service
rotation_required
owner
status
notes
```

Recommended evidence location:

```txt
docs/ops/releases/<release-record>.md
docs/ops/SECURITY_CHECKLIST.csv
docs/ops/DB_RESTORE_DRILL_LOG.csv
```

## Secret handling

Secrets must live in provider-managed secret stores:

```txt
GitHub Actions repository secrets
Render service environment variables
Render PostgreSQL managed credentials
```

Do not commit secrets to:

```txt
render.yaml
.env
frontend/.env.development
source files
shell scripts
docs
test fixtures
```

## Feature flag safety

Dangerous flags must remain disabled unless a runbook explicitly opens a short approved window:

```txt
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

## Weekly security check

Recommended cadence:

```txt
Weekly Friday 10 minutes
```

Run:

```bash
cd ~/Documents/Pet-med-ai
bash scripts/security_check.sh
python3 scripts/validate_security_hardening.py
```

Then review:

```txt
GitHub PAT / tokens
GitHub Actions secrets
Render environment variables
Render logs for SECRET/TOKEN/KEY/PASSWORD
Render PostgreSQL backups
Restore drill log
```
