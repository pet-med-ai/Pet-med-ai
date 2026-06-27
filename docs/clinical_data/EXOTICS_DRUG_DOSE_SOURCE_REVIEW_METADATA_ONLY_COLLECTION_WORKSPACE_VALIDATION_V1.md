# Exotics Drug Dose Source Review Metadata-only Collection Workspace Validation V1

## Purpose

This stage defines static validation gates for the metadata-only collection workspace shell created in the previous stage.

It is not source collection execution. It is not a drug dose engine, prescription engine, treatment plan engine, or client-facing workflow.

## Scope

Allowed:

- validate metadata-only workspace row coverage by species group and review domain
- validate required workspace fields are present
- validate forbidden medication value fields are absent
- validate numeric dose capture, route/frequency capture, usable medication instruction capture, and source collection execution remain blocked
- validate named collector, second reviewer, source access, copyright access, human review, and clinician signoff gates are present

Forbidden:

- source collection execution
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
current_level=metadata_only_workspace_validation_schema_only_not_collection_execution
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
source_review_status=metadata_only_workspace_validation_defined_not_run
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
writes_database=false
collection_execution_started=false
collection_execution_allowed_now=false
metadata_only_workspace_defined=true
metadata_only_workspace_populated=false
metadata_only_workspace_validation_defined=true
metadata_only_workspace_validation_executed=false
static_workspace_validation_available=true
writes_database=false
requires_human_review=true
clinician_signoff_required=true
```

## Matrix

```text
docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_MATRIX_V1.csv
```

## Static validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_validation.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

```text
Exotics Drug Dose Source Review Metadata-only Collection Workspace Validation V1 is GO only for static validation of the metadata-only workspace schema.
It is NO-GO for source collection execution, dose capture, route/frequency capture, prescription drafting, treatment plan generation, and client-facing use.
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_V1
```
