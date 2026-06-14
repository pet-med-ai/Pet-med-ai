# Commercial Launch Final Go / No-Go V1

## Purpose

This document is the final Commercial Launch Go / No-Go gate for Pet-Med-AI
Commercial V1.

It consolidates the commercial readiness work, feature scope lock, operations
runbook, access review, monitoring plan, backup/restore drill status, and
legal/consent review into a single launch decision.

This stage creates the final decision package and validator. It does not declare
production commercial launch GO while any hard blocker remains open.

## Current decision

Current decision for production commercial launch:

```txt
NO-GO_PRODUCTION_COMMERCIAL_LAUNCH
```

Allowed decision:

```txt
GO_CONTINUED_INTERNAL_PRE_LAUNCH_PREPARATION
```

Current hard blocker:

```txt
BRD2_REAL_RESTORE_EVIDENCE_PENDING
```

Legal status:

```txt
LEGAL_CONSENT_PACK_DOCS_VALIDATION_COMPLETE
LEGAL_CONSENT_PACK_REAL_REVIEW_SIGNOFF_COMPLETE
```

Backup / Restore status:

```txt
BACKUP_RESTORE_DRILL_V2_DOCS_VALIDATION_COMPLETE
BACKUP_RESTORE_DRILL_V2_REAL_RESTORE_EVIDENCE_PENDING
```

## Production GO conditions

Production commercial launch can be marked GO only when all are true:

```txt
GitHub Actions latest main run green
bash scripts/ci_static_checks.sh PASS
Render backend live
Render frontend live
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
Commercial Launch Readiness Review V1 complete
Commercial Launch Feature Scope Lock V1 complete
Commercial Launch Ops Runbook V1 complete
Commercial Launch User Roles / Access Review V1 complete
Commercial Launch Monitoring / Alerting Plan V1 complete
Commercial Launch Backup / Restore Drill V2 docs + validation complete
Commercial Launch Backup / Restore Drill V2 real restore evidence complete
Commercial Launch Legal / Consent Pack V1 docs + validation complete
Commercial Launch Legal / Consent Pack V1 real review + signoff complete
no open P0 incident
no unresolved P1 launch blocker
no secret leak
no PHI/client data in committed evidence
no cross-user access failure
no automated external message sent unexpectedly
no EMR real write executed unexpectedly
release_owner signoff recorded
security_owner signoff recorded
clinical_ops_owner signoff recorded
```

## Current No-Go reason

Production commercial launch is currently blocked because:

```txt
Commercial Launch Backup / Restore Drill V2 real restore evidence is pending.
```

This means the project has the restore drill runbook and validation package, but
does not yet have completed evidence showing a real non-production restore,
restore duration, restored schema validation, revision validation, no secrets/PHI
exposure, cleanup status and owner signoff.

## Hard No-Go conditions

The decision must remain NO-GO if any are true:

```txt
GitHub Actions red
CI static checks fail
Render backend unavailable
Render frontend unavailable
online smoke fails
schema_ok=false
database_revision != alembic_head
database_revision != 0008_auto_delivery
dangerous feature flags enabled
ENABLE_PREVENTIVE_AUTO_DELIVERY=true
ENABLE_EMR_REAL_IMPORT=true
ENABLE_EMR_IMPORT_CASE_UPDATE=true
cross-user data access found
Backup / Restore Drill V2 real restore evidence missing
Legal / Consent Pack V1 real review + signoff missing
secret leak
PHI/client data leaked in repo or evidence
open P0 incident
unresolved P1 launch blocker
Feature Scope Lock violated
automated reminder live sending enabled
SMS/WeChat/email provider credentials created for Commercial V1
EMR real import enabled
EMR case update enabled
```

## Final verification commands

Before any future GO decision, run:

```bash
bash scripts/ci_static_checks.sh

curl -sS https://pet-med-ai-backend.onrender.com/healthz

curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool

curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool

BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Expected:

```txt
CI static checks PASS
healthz OK
schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
feature flags safe
online smoke ALL PASS
```

## Restore evidence required before GO

Backup / Restore real evidence must include:

```txt
backup exists
backup timestamp recorded
restore target is non-production
restore started_at recorded
restore finished_at recorded
restore duration recorded
restored alembic_version exists
restored database_revision == 0008_auto_delivery
core tables exist
restored smoke PASS or accepted limitation
no secrets exposed
no PHI exposed
temporary restore target cleaned or locked
release_owner signoff
security_owner signoff
backend_owner signoff
```

## Legal evidence status

Legal / Consent Pack V1 is recorded as complete for this decision package:

```txt
docs + validation complete
real review + signoff complete
```

Final GO still requires the evidence file to remain committed without PHI or
secrets and the legal consent validator to remain green.

## Commercial V1 launch scope reminder

Commercial V1 remains limited to:

```txt
AI consultation
dynamic consultation
structured intake
case management
Clinical Docs Word export
preventive care in-app reminders
front-desk manual contact queue
ops/release/system read-only checks
```

Commercial V1 does not include:

```txt
automated SMS sending
automated WeChat sending
automated email sending
provider credentials
background worker sending
EMR real import
EMR case update
device real ingest
DICOM real ingest
lab analyzer real integration
structured prescription writes
billing/invoice real writes
```

## Decision record

Current decision:

```txt
GO_CONTINUED_INTERNAL_PRE_LAUNCH_PREPARATION
NO-GO_PRODUCTION_COMMERCIAL_LAUNCH
```

Reason:

```txt
BRD2_REAL_RESTORE_EVIDENCE_PENDING
```

To convert this decision to production GO, complete Backup / Restore Drill V2
real restore evidence, update the final evidence/decision records, re-run CI and
online smoke, and obtain owner signoff.
