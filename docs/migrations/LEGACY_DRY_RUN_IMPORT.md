# Legacy Case Import Dry-run V1

This stage maps a validated legacy case CSV into Pet-Med-AI `CaseCreate` JSONL payloads without writing to the database.

## Scope

Included:

- Reuse `scripts/validate_legacy_cases_csv.py` before mapping.
- Produce one JSONL line per valid legacy row.
- Produce a machine-readable dry-run report.
- Produce validation error CSV when the input is invalid.
- Preserve legacy metadata and idempotency key in the JSONL record.

Excluded:

- No database writes.
- No Pet-Med-AI API calls.
- No Alembic changes.
- No attachment or imaging file migration.
- No production import.

## Command

```bash
python3 scripts/legacy_cases_to_case_payloads.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv \
  --jsonl-out legacy_case_payloads.jsonl \
  --errors-out migration_errors.csv \
  --report-out legacy_case_payload_report.json
```

## JSONL record shape

Each line is shaped as:

```json
{
  "operation": "case_create",
  "dry_run": true,
  "source": "legacy_cases_csv",
  "source_file": "docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv",
  "source_row_number": 2,
  "legacy_case_id": "HS-2026-000123",
  "idempotency_key": "...",
  "case_create": {
    "patient_name": "咪咪",
    "species": "cat",
    "sex": null,
    "age_info": null,
    "breed": null,
    "weight": "3.20kg",
    "coat_color": null,
    "owner_name": null,
    "owner_phone": null,
    "chief_complaint": "旧系统导入病例：Acute gastroenteritis（就诊日期：2026-05-25）",
    "history": "...",
    "exam_findings": "..."
  },
  "legacy": {
    "case_id": "HS-2026-000123",
    "visit_date": "2026-05-25",
    "clinician": "Dr.Zhao",
    "primary_dx": "Acute gastroenteritis",
    "status": "active"
  }
}
```

The nested `case_create` object intentionally matches the current backend `CaseCreate` payload shape. This makes the next stage easier, but this V1 still does not post to `/api/cases`.

## Failure behavior

If validation fails:

- JSONL is not produced.
- The script writes an error CSV.
- The script writes a failed report JSON.
- Exit code is `2`.

## Next stage

The next stage should be `旧病例导入 API mock V1`, where JSONL payloads may be replayed against a local mock or explicit dry-run API. Do not write to production until clinical sampling and rollback planning are complete.
