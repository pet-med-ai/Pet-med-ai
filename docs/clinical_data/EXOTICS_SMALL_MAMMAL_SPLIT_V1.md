# Exotics Small Mammal Split V1

## Purpose

Exotics Small Mammal Split V1 separates the old generic `rodent` scaffold into species-focused small mammal triage scaffolds:

- guinea_pig
- hamster
- chinchilla
- rat_mouse
- hedgehog
- sugar_glider

The stage keeps `rodent` as a legacy fallback, but exact species should now map to the new rule keys.

## Current level

```text
current_level=small_mammal_split_triage_scaffold_not_comprehensive_clinical_kb
source_review_status=required_not_started
drug_dose_status=not_reviewed_not_enabled
```

This is not a comprehensive exotic mammal clinical knowledge base. It only improves triage, red-flag prompts, differential-direction labels, recommended check categories, and structured intake prompts.

## In scope

- split small mammal rules from generic rodent fallback
- species-to-rule mapping updates
- group-to-rule mapping updates
- new structured intake templates
- static validation
- smoke validation hook
- no database migration

## Out of scope

- final diagnosis
- diagnostic conclusion
- treatment plan
- prescription
- drug dose, route, or frequency
- lab reference intervals
- imaging interpretation
- source-reviewed drug policy
- client-facing output
- external AI/provider calls
- real EMR/lab/DICOM/device ingest

## Safety boundary

```text
read_only=true
writes_database=false
creates_case=false
updates_case=false
creates_diagnostic_report=false
updates_diagnostic_report=false
creates_observation=false
updates_observation=false
creates_imaging_study=false
updates_imaging_study=false
writes_ai_summary=false
writes_audit_log=false
generates_final_diagnosis=false
creates_treatment_plan=false
writes_prescription=false
returns_drug_dose=false
calls_external_ai=false
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotic_kb.py
python3 scripts/validate_exotic_intake_templates.py
python3 scripts/validate_exotics_small_mammal_split.py
bash scripts/ci_static_checks.sh
```

## Decision

```text
decision=GO_TO_EXOTICS_FERRET_DEEPENING_V1
```
