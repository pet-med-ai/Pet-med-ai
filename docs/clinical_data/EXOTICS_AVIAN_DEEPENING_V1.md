# Exotics Avian Deepening V1

## Purpose

Deepen the existing bird branch of the exotics knowledge base from a basic triage scaffold into a richer avian triage and structured-intake scaffold.

This stage remains clinical-review-only. It does not create final diagnoses, treatment plans, prescriptions, drug doses, client-facing conclusions, or external provider calls.

## Scope

In scope:

- deepen `knowledge-base/exotics/bird.json`
- deepen `knowledge-base/exotics/intake/bird.json`
- add read-only Avian Deepening review helper
- add static validator and smoke hook
- preserve existing exotics KB and intake validators

Out of scope:

- avian species-specific split by psittacine / passerine / pigeon / poultry
- avian lab reference intervals
- imaging interpretation rules
- pathogen-specific diagnostic conclusions
- treatment plan generation
- prescription writing
- drug dose, route, or frequency output
- external AI/provider calls
- database writes

## Clinical coverage added

Avian Deepening V1 expands review prompts around:

- low-stress respiratory triage
- tail bobbing, open-mouth breathing, cyanosis and perch intolerance
- ruffled feathers, collapse, weight loss and systemic illness
- droppings triad: feces / urates / urine
- crop, regurgitation and vomiting-like presentations
- egg binding and reproductive risk
- trauma, blood feather injury and bleeding
- neurologic or toxin exposure presentations
- PTFE, smoke, aerosol, fragrance and disinfectant exposure
- quarantine, new bird and flock context
- diet and husbandry review

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
not_client_facing=true
```

## Current level

```text
current_level=avian_deepened_triage_scaffold_not_comprehensive_clinical_kb
is_comprehensive=false
source_review_status=required_not_started
drug_dose_status=not_reviewed_not_enabled
```

## Validation

```bash
python3 scripts/validate_exotic_kb.py
python3 scripts/validate_exotic_intake_templates.py
python3 scripts/validate_exotics_avian_deepening.py
bash scripts/ci_static_checks.sh
```

## Decision

```text
Exotics Avian Deepening V1 is complete only after validator PASS, exotic KB validator PASS, exotic intake templates validator PASS, CI PASS, online smoke ALL PASS, and production schema gate remains 0009_diag_data.
decision=GO_TO_EXOTICS_REPTILE_SPLIT_V1
```
