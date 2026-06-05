# EMR real import clinical approval UI V1

## Stage

This stage adds a frontend clinical Go / No-Go approval panel to the existing EMR import batch planning page.

It consumes the existing backend endpoint:

```txt
POST /api/emr/import-batches/{batch_id}/clinical-approval
```

## Scope

This UI is a clinical approval gate only.

It may call the API that writes:

```txt
emr_import_batches
audit_log
```

It must not trigger real import execution.

## Route

```txt
/emr/import-batches
```

The approval panel is shown inside the selected batch detail area.

## UI fields

```txt
operator_id
clinical_signoff_id
rollback_snapshot_id
approval_action
note
```

Supported approval actions:

```txt
approve
clinical_signed
needs_fix
reject
rejected
```

## Safety boundary

The page must explicitly show these safety markers:

```txt
writes_emr_import_batches=true
writes_audit_log=true
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
can_execute_import=false
```

## Behavior

1. User selects a batch from the EMR import batch planning page.
2. User reviews batch detail, receipts, safety markers and prior execution dry-run results.
3. User fills operator_id, clinical_signoff_id and rollback_snapshot_id.
4. User selects a Go / No-Go action.
5. User submits the clinical approval action.
6. The backend returns `audit_log_id` and `status_after`.
7. The page refreshes batch detail and batch list.

## Forbidden in V1

```txt
No Case creation
No Case update
No attachment download
No queue consumption
No real import execution button
No bypass of rollback_snapshot_id / clinical_signoff_id workflow
```

## Validation

```bash
python3 scripts/validate_emr_import_clinical_approval_ui.py
cd frontend && npm run build
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

## Manual acceptance

1. Open `/emr/import-batches`.
2. Log in.
3. Select an existing frozen batch.
4. Fill approval fields.
5. Submit `approve` or `clinical_signed`.
6. Confirm response displays `audit_log_id`.
7. Confirm status changes to `approved` or `clinical_signed`.
8. Confirm the page still shows `executes_real_import=false` and has no real import execution button.
