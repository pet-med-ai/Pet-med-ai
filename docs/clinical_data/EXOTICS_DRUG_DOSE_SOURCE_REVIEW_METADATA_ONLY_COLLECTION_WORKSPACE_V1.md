# Exotics Drug Dose Source Review Metadata-only Collection Workspace V1

## Purpose

This stage defines a metadata-only collection workspace shell for future exotics drug dose source review.

It is not source collection execution. It is not a drug dose engine, prescription engine, treatment plan engine, or client-facing workflow.

## Scope

Allowed:

- define metadata-only workspace rows by species group and review domain
- require named collector and second reviewer before any future collection execution
- require source access and copyright access checks
- require value-capture blockers before any future source review workspace is populated
- define deidentification and clinician signoff gates

Forbidden:

- numeric dose values
- dose units
- drug route text
- drug frequency text
- duration text
- prescription directions
- treatment protocols
- client instructions
- copied copyrighted full text
- database writes

## Species groups

- rabbit
- bird
- ferret
- turtle
- lizard
- snake
- amphibian
- fish
- guinea_pig
- hamster
- chinchilla
- rat_mouse
- hedgehog
- sugar_glider

## Review domains

- analgesia_and_pain_control_source_review
- antimicrobial_source_review
- antiparasitic_source_review
- fluid_and_supportive_care_source_review
- sedation_anesthesia_risk_source_review
- emergency_stabilization_source_review

## Required safety flags

```text
current_level=metadata_only_collection_workspace_schema_only_not_execution
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
source_review_status=metadata_only_workspace_defined_not_populated
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
collection_execution_started=false
collection_execution_allowed_now=false
metadata_only_workspace_defined=true
metadata_only_workspace_populated=false
writes_database=false
requires_human_review=true
clinician_signoff_required=true
```

## Matrix

```text
docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_MATRIX_V1.csv
```

## Static validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

```text
Exotics Drug Dose Source Review Metadata-only Collection Workspace V1 is GO only for metadata-only workspace schema definition.
It is NO-GO for source collection execution, dose capture, route/frequency capture, prescription drafting, treatment plan generation, and client-facing use.
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_V1
```
