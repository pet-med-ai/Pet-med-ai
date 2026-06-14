# Commercial Launch Backup / Restore Drill V2

## Purpose

This drill verifies that Pet-Med-AI production data can be backed up and restored
before Commercial Final Go / No-Go.

Commercial Launch Backup / Restore Drill V2 is a hard launch evidence gate. It
must prove that a recent production backup exists, a restore can be performed
into a non-production target, the restored database has the expected Alembic
revision, and smoke can pass against a restored environment or documented
restore-verification environment.

This stage creates the runbook, checklist, command template, evidence template
and validator. It does not perform a live database restore automatically.

## Strict safety boundary

This stage must not:

```txt
restore over the production database
run destructive commands on production
print DATABASE_URL
commit database dumps
commit credentials
commit PHI / client personal data
create Alembic migrations
change application schema
enable EMR real import
enable EMR case update
enable automated reminder live delivery
send SMS
send WeChat
send email
create provider credentials
create background workers
```

## Required owners

```txt
release_owner       owns drill scheduling and Go / No-Go decision
security_owner      owns secret handling and PHI leakage checks
backend_owner       owns database restore validation
clinical_ops_owner  owns clinic workflow verification after restore
```

One person may hold multiple roles in a pilot, but every evidence row must still
record an owner.

## Target environments

Production source:

```txt
Render PostgreSQL: pet-med-ai-db
Backend service: pet-med-ai-backend
Frontend static site: pet-med-ai-frontend-static
```

Restore target:

```txt
temporary Render PostgreSQL database
or local temporary PostgreSQL instance
or other explicitly non-production restore target
```

Hard rule:

```txt
Never restore directly into production pet-med-ai-db during this drill.
```

## Required pre-drill checks

Before restore work:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz

curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool

curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool

BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required pre-drill state:

```txt
healthz OK
online smoke ALL PASS
schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
all_dangerous_features_disabled=true
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
```

If pre-drill state fails, stop and record **NO-GO**.

## Backup verification

Record evidence for at least one recent backup:

```txt
backup provider/source
backup timestamp
backup age
backup identifier or dashboard reference
backup retention notes
who verified the backup
```

Do not record secret URLs or credentials.

## Optional manual export verification

A manual export may be performed only by an authorized operator.

Allowed evidence:

```txt
export command template used
export started_at
export finished_at
export duration
export file size
checksum
storage location class
operator
```

Forbidden evidence:

```txt
raw DATABASE_URL
password
secret token
dump contents
client PHI
owner phone numbers
customer names
```

## Restore drill procedure

1. Create or identify a non-production restore target.
2. Confirm the target is empty or disposable.
3. Restore the selected backup or manual export into the target.
4. Record restore start and finish time.
5. Validate that the restored database contains the expected schema.
6. Validate Alembic state.
7. Run smoke against a restore-verification backend when available.
8. If a full backend against restored DB is not available, record the limitation
   and run SQL/Alembic verification against the restored target.
9. Preserve evidence without secrets or PHI.
10. Destroy or lock down the temporary restore target after review.

## Restored database validation

Required validation:

```txt
alembic_version table exists
database_revision == 0008_auto_delivery
database_revision == expected production revision at backup time
core tables exist
users table exists
cases table exists
consult_sessions table exists
preventive care tables exist
automated delivery tables exist
no migration errors
```

If a restored backend environment is available, also verify:

```txt
/api/system/version schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
online smoke ALL PASS
```

## RTO / RPO evidence

Record:

```txt
backup timestamp
restore start time
restore finish time
restore duration minutes
backup age at restore start
RTO observed
RPO observed
whether RTO/RPO are acceptable for Commercial V1
```

Suggested initial Commercial V1 targets:

```txt
RTO target: restore procedure understood and evidence recorded
RPO target: recent backup available before clinic-facing launch
```

V2 does not require automated failover. It requires that restore is tested and
not merely assumed.

## Failure conditions

The drill is **NO-GO** if any occurs:

```txt
no recent backup exists
backup cannot be exported or located
restore target cannot be created
restore fails
restored database has no alembic_version
database_revision mismatch
database_revision != 0008_auto_delivery
schema validation fails
smoke against restored environment fails without accepted explanation
secret appears in evidence
PHI appears in committed evidence
restore duration not recorded
owner signoff missing
```

## Recovery and rollback notes

If a production incident later requires restore:

```txt
1. Stop clinic-facing use if data correctness is at risk.
2. Capture current /api/system/version.
3. Capture current /api/system/feature-flags.
4. Confirm latest known good backup.
5. Restore to non-production target first when time allows.
6. Verify schema and smoke.
7. Decide whether production restore is necessary.
8. Preserve incident and restore evidence.
9. Resume only after release_owner and security_owner signoff.
```

## Evidence storage policy

Commit only:

```txt
completed evidence CSV with non-secret values
timestamps
status values
operator names/roles
restore duration
sanitized references
decisions
```

Never commit:

```txt
database dump files
DATABASE_URL
passwords
tokens
client names
client phone numbers
pet owner personal data
raw production records
screenshots containing PHI or secrets
```

## Final Go dependency

Commercial Launch Final Go / No-Go V1 cannot pass unless Backup / Restore Drill
V2 has evidence showing:

```txt
backup exists
restore path tested
restore duration recorded
schema validation passed
database_revision == 0008_auto_delivery
dangerous flags remained closed
secrets were not exposed
owner signoff recorded
```

## Decision

Default decision:

```txt
NO-GO until evidence is filled
```

Passing the validator means the drill package exists and is wired into CI/smoke.
It does not mean the real restore drill has been performed.
