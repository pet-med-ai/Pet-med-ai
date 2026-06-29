# CI Smoke Cumulative Guard Restore V1

## Stage identity

- stage_name: CI Smoke Cumulative Guard Restore V1
- stage_slug: CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1
- baseline_commit: 0c8fd5d
- baseline_smoke_path: scripts/smoke_petmed.sh
- restore_strategy: embedded_legacy_cumulative_smoke_plus_current_hard_gates
- read_only: true
- writes_database: false
- no_business_code_change: true
- no_backend_app_change: true
- no_backend_ai_engine_change: true
- no_frontend_components_change: true

## Why this stage exists

Confirmed Diagnosis Treatment Framework Boundary V1 passed its local validator, CI static checks, and online smoke, but it also reduced `scripts/smoke_petmed.sh` from the previous cumulative smoke surface to a small current-stage smoke script. That was not an immediate production NO-GO because the hard gates still passed, but it weakened cumulative regression coverage.

This stage restores the smoke guard before the next treatment framework draft endpoint stage.

## Scope

This stage is intentionally infrastructure-only. It may write only these target files:

```text
docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_V1.md
docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_CHECKLIST_V1.csv
docs/clinical_data/CI_SMOKE_CUMULATIVE_GUARD_RESTORE_GO_NO_GO_V1.csv
scripts/validate_ci_smoke_cumulative_guard_restore.py
scripts/ci_static_checks.sh
scripts/smoke_petmed.sh
```

It must not modify any business implementation file, endpoint, database model, migration, frontend component, AI engine, EMR integration, device integration, billing integration, or prescription integration.

## Smoke strategy

`scripts/smoke_petmed.sh` now has two layers:

1. Current production hard gates:
   - `/api/system/version`
   - `database_revision=0009_diag_data`
   - `alembic_head=0009_diag_data`
   - `schema_ok=true`
   - `migration_errors=[]`
   - `writes_database=false`
   - `exposes_database_url=false`
   - `/api/system/feature-flags`
   - all dangerous feature flags present and false
   - frontend reachable

2. Embedded legacy cumulative smoke:
   - source: `0c8fd5d:scripts/smoke_petmed.sh`
   - embedded directly inside the current smoke script
   - executed after current hard gates
   - executed as a separate temporary shell file
   - no runtime dependency on reading git history

This prevents future stages from silently shrinking smoke coverage again.

## CI strategy

`scripts/ci_static_checks.sh` now enforces:

- `git diff --check`
- required target files exist
- Python syntax for this validator and all local `scripts/validate_*.py`
- shell syntax for `scripts/ci_static_checks.sh` and `scripts/smoke_petmed.sh`
- this stage validator passes
- the previous Confirmed Diagnosis Treatment Framework Boundary validator passes when present
- tracked diff is limited to this stage target files
- sensitive staged paths are blocked
- dangerous feature flags are not enabled in target files
- the smoke script includes the embedded legacy cumulative smoke marker
- the smoke script line count is high enough to reject accidental re-shrinking

## Non-goals

This stage does not:

- add or enable a treatment framework endpoint
- write database rows
- modify `Case.treatment`
- write prescriptions
- return drug dose
- return route
- return frequency
- enable real EMR import
- enable real lab, DICOM, PACS, device, or billing integration
- change frontend UI
- call external AI or provider services

## Dangerous flags that must remain disabled

```text
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
```

## Go / No-Go

GO requires:

- validator=PASS
- ci_static_checks=PASS
- smoke script contains embedded legacy cumulative smoke
- smoke line count remains above the cumulative minimum
- online smoke=ALL_PASS
- production database_revision=0009_diag_data
- production alembic_head=0009_diag_data
- production schema_ok=true
- migration_errors=[]
- writes_database=false
- exposes_database_url=false
- dangerous_feature_flags_disabled=true
- no business code change
- no backend/app change
- no backend/ai_engine change
- no frontend/src/components change

NO-GO if:

- embedded legacy cumulative smoke is missing
- smoke line count collapses again
- production hard gate fails
- any dangerous flag is missing or not false
- any non-target tracked file is modified
- any sensitive path is staged
- endpoint or business logic is changed in this stage

## Decision

decision=GO_TO_CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_DRAFT_V1_AFTER_CUMULATIVE_GUARD_RESTORE
