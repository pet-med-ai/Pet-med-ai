# Preventive Care Reminder Rule Engine Dry-run V1

## Purpose

This stage adds a dry-run rule engine for vaccine, deworming, parasite prevention, fecal exam, and wellness reminder date calculations.

It is dry-run only.

It does not:

```txt
write database
create reminders
send SMS / WeChat / email
create notification queue rows
create Case
update Case
execute EMR import
```

## New files

```txt
backend/preventive_care_rules.py
scripts/preventive_care_rule_dry_run.py
docs/preventive_care/PREVENTIVE_CARE_RULE_DRY_RUN_SAMPLE_INPUT.json
scripts/validate_preventive_care_rule_engine_dry_run.py
```

## Input

Example:

```json
{
  "as_of_date": "2026-06-11",
  "pet": {
    "pet_name": "乐乐",
    "species": "dog",
    "life_stage": "adult",
    "last_core_vaccine_date": "2025-06-01",
    "last_deworming_date": "2026-02-01"
  }
}
```

## Output

The dry-run returns:

```txt
message=preventive_care_rule_engine_dry_run
mode=preventive_care_rule_engine_dry_run_v1
summary.total
summary.by_status
items[]
writes_database=false
creates_case=false
updates_case=false
sends_external_message=false
executes_real_import=false
```

Each item contains:

```txt
rule_id
category
status
due_date
due_window_start
due_window_end
requires_clinician_confirmation
allow_auto_send=false
sends_external_message=false
```

## Status calculation

```txt
active: due window has not started
due_soon: as_of date is inside lead window before due_date
due: as_of date is between due_date and due_window_end
overdue: as_of date is after due_window_end
```

If a trigger date is missing, the engine marks the item as due with:

```txt
reason=missing_trigger_date
```

This means the clinic should review and enter baseline preventive-care history.

## Command

```bash
python3 scripts/preventive_care_rule_dry_run.py \
  --input docs/preventive_care/PREVENTIVE_CARE_RULE_DRY_RUN_SAMPLE_INPUT.json \
  --as-of 2026-06-11
```

## Safety markers

```txt
writes_database=false
creates_case=false
updates_case=false
sends_external_message=false
executes_real_import=false
```

## Completion criteria

```txt
1. backend/preventive_care_rules.py exists.
2. CLI dry-run script exists.
3. Sample input exists.
4. Validator exists and is included in smoke.
5. CI static checks include the validator.
```
