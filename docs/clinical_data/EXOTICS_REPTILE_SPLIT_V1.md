# Exotics Reptile Split V1

## Purpose

Exotics Reptile Split V1 splits the prior broad reptile/amphibian/fish scaffold into concrete triage scaffolds:

- turtle / tortoise / terrapin
- lizard
- snake
- amphibian
- fish

The generic `reptile` rule remains as a legacy fallback, but common concrete species now route to dedicated KB and structured-intake templates.

## Current level

```text
current_level=reptile_split_triage_scaffold_not_comprehensive_clinical_kb
is_comprehensive=false
source_review_status=required_not_started
drug_dose_status=not_reviewed_not_enabled
```

## In scope

- Split `knowledge-base/exotics/index.json` mappings.
- Add `turtle.json`, `lizard.json`, `snake.json`, `amphibian.json`, and `fish.json`.
- Add matching structured intake templates.
- Add static validator and smoke hook.
- Keep all outputs clinician-review-only and non-client-facing.

## Out of scope

- Final diagnosis.
- Treatment plan.
- Prescription.
- Drug dose, route, or frequency.
- Client-facing conclusion.
- Lab reference ranges.
- Imaging interpretation.
- PACS / DICOM / device ingest.
- Database writes.

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
generates_diagnostic_conclusion=false
creates_treatment_plan=false
writes_prescription=false
returns_drug_dose=false
returns_drug_route=false
returns_drug_frequency=false
client_facing=false
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotic_kb.py
python3 scripts/validate_exotic_intake_templates.py
python3 scripts/validate_exotics_reptile_split.py
bash scripts/ci_static_checks.sh
```

## Decision

```text
decision=GO_TO_EXOTICS_SMALL_MAMMAL_SPLIT_V1
```
