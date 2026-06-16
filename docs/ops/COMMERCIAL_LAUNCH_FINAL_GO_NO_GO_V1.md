# Commercial Launch Final Go / No-Go V1

## Final decision

```txt
GO_PRODUCTION_COMMERCIAL_LAUNCH
GO_CONTINUED_INTERNAL_PRE_LAUNCH_PREPARATION
```

Decision date: `YES`

Git commit reviewed: `YES`

## Closed blocker

```txt
BRD2_REAL_RESTORE_EVIDENCE_PENDING -> CLOSED
BACKUP_RESTORE_DRILL_V2_REAL_RESTORE_EVIDENCE_COMPLETE
LEGAL_CONSENT_PACK_REAL_REVIEW_SIGNOFF_COMPLETE
```

## Required production GO evidence

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
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
Commercial Launch Backup / Restore Drill V2 real restore evidence complete
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

## Commercial V1 scope

Commercial V1 includes AI consultation, dynamic consultation, structured intake, case management, Clinical Docs Word export, preventive care in-app reminders, front-desk manual contact queue, and ops/release/system read-only checks.

Commercial V1 does not include automated SMS sending, automated WeChat sending, automated email sending, provider credentials, background worker sending, EMR real import, EMR case update, device real ingest, DICOM real ingest, lab analyzer real integration, structured prescription writes, or billing/invoice real writes.

## Rollback conditions after GO

Pause rollout immediately if schema_ok=false, database_revision != alembic_head, database_revision != 0008_auto_delivery, dangerous feature flags become enabled, cross-user access is found, secrets/PHI leak, automated external send occurs unexpectedly, EMR real write occurs unexpectedly, or online smoke fails during active launch.
