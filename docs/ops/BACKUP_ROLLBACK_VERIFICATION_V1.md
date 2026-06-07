# Backup / Rollback Verification V1

## Purpose

This runbook defines the minimum backup and rollback verification gate before Pet-Med-AI performs any high-risk database operation, especially real EMR import execution that can create `Case` records.

This stage is documentation and validation only.

It does not:

```txt
change backend code
change frontend code
change database schema
run Alembic
enable ENABLE_EMR_REAL_IMPORT
create Case records
execute real import
```

## Why this gate exists

Pet-Med-AI now has:

```txt
Release / Upgrade Framework V1
Version / Build Info V1
Feature Flag / Safety Gate V1
Ops Dashboard V1
Release Tag / Changelog V1
GitHub Actions CI Gate V1
EMR real import create-only pilot implementation
```

Before a real pilot writes clinical records, the operator must prove that:

```txt
a rollback snapshot exists
the target database revision is known
the code Alembic head is known
feature flags are safe
the pilot batch is approved
the rollback owner knows the procedure
post-rollback smoke and clinical checks are defined
```

## Scope

This applies before:

```txt
Alembic migrations on Render PostgreSQL
EMR real import pilot execution
any Case write from external systems
device real ingest
attachment ingest
billing write
prescription structured write
```

## Required identifiers

Every backup / rollback record must include:

```txt
backup_id
rollback_snapshot_id
release_id
git_commit
git_tag if available
database_revision_before
alembic_head
operator_id
rollback_owner
clinical_owner
created_at
evidence_url_or_log_path
```

## Standard pre-write backup verification

Before any real-write pilot:

```bash
cd ~/Documents/Pet-med-ai

curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool
curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Required:

```txt
schema_ok=true
database_revision == alembic_head
all_dangerous_features_disabled=true before intentionally enabling pilot flag
online smoke ALL PASS
rollback_snapshot_id recorded
```

## Render PostgreSQL backup verification

Use Render dashboard to confirm the backup/snapshot exists.

Minimum evidence:

```txt
service/database name = pet-med-ai-db
snapshot or backup id
created_at
retention window
restore target or restore workflow known
operator screenshot/log reference
```

Do not proceed on verbal confirmation only.

## Real import pilot backup gate

For EMR create-only pilot, before enabling `ENABLE_EMR_REAL_IMPORT=true`:

```txt
[ ] Backup/snapshot exists.
[ ] rollback_snapshot_id is written in the approved batch.
[ ] clinical_signoff_id is written in the approved batch.
[ ] execution dry-run quality_gate.passed=true.
[ ] batch size is within pilot limit.
[ ] online smoke ALL PASS before execution.
[ ] rollback owner is available during execution window.
[ ] 100% clinical spot-check reviewer assigned.
[ ] Ops dashboard shows schema aligned.
```

## Hard No-Go

Stop if any condition is true:

```txt
No backup/snapshot evidence
rollback_snapshot_id empty
clinical_signoff_id empty
schema_ok=false
database_revision != alembic_head
online smoke fails
GitHub Actions CI Gate not green
unknown feature flag state
pilot batch exceeds approved limit
rollback owner unavailable
post-execution spot-check unavailable
```

## Rollback decision principle

Use this order:

```txt
1. Stop further writes.
2. Preserve logs and execution IDs.
3. Check whether failure is isolated or systemic.
4. If systemic or clinical data wrong, restore snapshot according to Render runbook.
5. Run online smoke after rollback.
6. Run clinical spot-check after rollback.
7. Record final decision in release record.
```

## What not to do

Do not:

```txt
stamp head to hide a failed migration
run downgrade without explicit rollback plan
manually edit clinical rows to hide failed import
delete audit logs
delete execution result rows
enable real import without snapshot
continue pilot after first P0 mismatch
```

## Evidence storage

Recommended evidence locations:

```txt
docs/ops/releases/<release-record>.md
docs/ops/BACKUP_ROLLBACK_CHECKLIST.csv
docs/ops/ROLLBACK_REHEARSAL_TEMPLATE.csv
terminal log file under /tmp for immediate sharing
Render screenshot or dashboard note
```

## Completion criteria

```txt
1. Backup / rollback runbook exists.
2. Render PostgreSQL backup runbook exists.
3. Backup checklist exists.
4. Rollback rehearsal template exists.
5. Decision matrix exists.
6. Validator exists and is included in smoke.
```
