# Drug Dose Knowledge Base V1

## Purpose

Drug Dose Knowledge Base V1 creates a gated medication monograph shell for future dose safety work.

This stage does not calculate dose, does not recommend medication, does not generate a treatment plan, and does not write prescriptions.

It only exposes clinician-review metadata, species constraints, contraindication screening prompts, and explicit safety flags showing that numeric dose output is disabled.

## Scope

In scope:

- read-only drug monograph shell
- species constraint metadata
- minimum input checklist
- contraindication / warning checklist
- source-review status
- numeric dose values redacted
- dry-run review endpoint
- owner-scoped case access check
- no database writes
- no prescription writes
- no treatment recommendation
- no numeric dose output
- no route/frequency output

Out of scope:

- automatic drug selection
- numeric dose calculation
- mg/kg dose output
- route or frequency instruction
- duration instruction
- client-facing medication instructions
- prescription write
- product-label interpretation
- external AI/provider calls
- treatment plan generation

## API

```text
GET  /api/diagnostic-data/dry-run/drug-dose-kb/monographs
GET  /api/diagnostic-data/dry-run/drug-dose-kb/monographs/{drug_key}
POST /api/diagnostic-data/dry-run/drug-dose-kb/review
```

## Required safety flags

Every endpoint must return:

```text
writes_database=false
creates_prescription=false
writes_prescription=false
creates_treatment_plan=false
treatment_recommendation=false
drug_recommendation=false
drug_dose_recommendation=false
dose_calculation_enabled=false
dose_lookup_enabled=false
returns_numeric_dose=false
returns_route_frequency=false
client_facing_dose_output=false
calls_external_ai=false
calls_external_provider=false
requires_human_review=true
clinician_signoff_required=true
numeric_dose_values_redacted=true
```

## Go / No-Go

GO only if:

- validator PASS
- CI static checks PASS
- online smoke ALL PASS
- production database_revision=0009_diag_data
- production alembic_head=0009_diag_data
- production schema_ok=true
- no numeric dose values are exposed
- no route or frequency instruction is exposed
- no prescription write is possible
- no external AI/provider is called

## Decision

```text
decision=GO_TO_CLINICIAN_REVIEW_WORKFLOW_FOR_DIAGNOSTIC_SUMMARIES_V1
```
