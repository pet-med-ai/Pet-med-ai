# Exotics Ferret Deepening V1

## Purpose

This stage deepens the ferret branch of the exotics triage scaffold.

It expands the ferret knowledge rule and structured intake template around:

- hypoglycemia / insulinoma-like weakness triage
- gastrointestinal foreign body / partial obstruction triage
- diarrhea / dehydration review
- adrenal / skin / endocrine clues
- urinary and reproductive review prompts
- respiratory and exposure review prompts
- mass / weight loss / neuro / trauma review prompts

## Current level

```text
current_level=ferret_deepened_triage_scaffold_not_comprehensive_clinical_kb
source_review_status=required_not_started
drug_dose_status=not_reviewed_not_enabled
```

This stage is not a comprehensive ferret medicine knowledge base. It is a safer, deeper triage and history capture scaffold.

## In scope

- update `knowledge-base/exotics/ferret.json`
- update `knowledge-base/exotics/intake/ferret.json`
- add a read-only helper for coverage validation
- add checklist / go-no-go documentation
- add static validator and smoke validator hooks

## Out of scope

- final diagnosis
- treatment plan
- prescription
- drug dose, route, or frequency
- client-facing conclusions
- lab / imaging interpretation rules
- external AI/provider calls
- database writes

## Safety boundary

```text
read_only=true
writes_database=false
no final diagnosis
no treatment plan
no prescription
no drug dose
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotic_kb.py
python3 scripts/validate_exotic_intake_templates.py
python3 scripts/validate_exotics_ferret_deepening.py
bash scripts/ci_static_checks.sh
```

## Decision

```text
Exotics Ferret Deepening V1 complete only after validator PASS, exotic KB validator PASS, exotic intake templates validator PASS, CI PASS, online smoke ALL PASS, and production schema gate remains 0009_diag_data.
decision=GO_TO_EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_V1
```
