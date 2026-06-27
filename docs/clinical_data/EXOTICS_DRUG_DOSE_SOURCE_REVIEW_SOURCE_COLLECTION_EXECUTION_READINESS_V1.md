# Exotics Drug Dose Source Review Source Collection Execution Readiness V1

## Purpose

This stage defines execution readiness gates for future exotics drug-dose source collection.

It does not start source collection. It does not collect medication values. It does not capture route, frequency, duration, prescription directions, treatment protocols, or client-facing instructions.

The output is a metadata-only execution-readiness matrix for reviewer assignment, source access checks, copyright access checks, workspace setup, and human-review controls.

## Current level

```text
current_level=source_collection_execution_readiness_only_not_execution
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
source_review_status=execution_readiness_defined_not_started
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
```

## In scope

- reviewer assignment readiness
- second reviewer requirement
- source access readiness
- copyright access readiness
- metadata-only workspace readiness
- source collection execution Go / No-Go
- source registry and evidence table cross-reference
- validation that source collection has not started

## Out of scope

- source collection execution
- usable medication instruction capture
- dose engine
- prescription engine
- treatment plan engine
- final diagnosis
- client-facing output
- database writes
- external provider calls

## Species groups

```text
rabbit
bird
ferret
turtle
lizard
snake
amphibian
fish
guinea_pig
hamster
chinchilla
rat_mouse
hedgehog
sugar_glider
```

## Review domains

```text
analgesia_and_pain_control_source_review
antimicrobial_source_review
antiparasitic_source_review
fluid_and_supportive_care_source_review
sedation_anesthesia_risk_source_review
emergency_stabilization_source_review
```

## Required gate before any later collection execution

```text
collector_assignment_status=approved
second_reviewer_status=approved
source_access_status=verified
copyright_access_status=verified
workspace_status=approved_metadata_only
collection_execution_status=not_started_until_next_stage_go
```

## Prohibited content

```text
numeric_dose_value
dose_unit
route_text
frequency_text
duration_text
prescription_direction
treatment_protocol
client_instruction
copied_table_text
copyrighted_full_text
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_execution_readiness.py
bash scripts/ci_static_checks.sh
```

## Decision

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_V1
```
