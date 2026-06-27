# Exotics Drug Dose Source Review Source Collection Controlled Pilot Report V1

## Purpose

This stage adds a controlled pilot report shell for exotic species drug-dose source review.

It is not a dose engine, not a prescription engine, and not a treatment-plan engine.

The report exists to summarize whether a future metadata-only source collection pilot is ready, what rows would be covered, which reviewer controls are required, and which unsafe value-capture paths remain blocked.

## Scope

Allowed:

- define controlled pilot report rows by species group and review domain
- summarize source registry readiness
- summarize evidence table readiness
- summarize source collection execution status
- require collector and second reviewer assignment
- require source access and copyright access review
- require metadata-only workspace controls
- document that collection execution has not started

Forbidden:

- source collection execution
- numeric dose value capture
- dose unit capture
- route text capture
- frequency text capture
- duration text capture
- prescription direction
- treatment protocol
- client instruction
- copied table text
- copyrighted full text
- database writes
- external provider calls
- final diagnosis
- treatment plan
- prescription

## Current status

```text
current_level=controlled_pilot_report_shell_only_not_collection_execution
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
source_review_status=controlled_pilot_report_shell_ready_no_collection_results
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
pilot_execution_allowed_now=false
collection_execution_started=false
```

## Matrix

The matrix is stored at:

```text
docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_MATRIX_V1.csv
```

Rows cover:

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

Review domains:

- analgesia_and_pain_control_source_review
- antimicrobial_source_review
- antiparasitic_source_review
- fluid_and_supportive_care_source_review
- sedation_anesthesia_risk_source_review
- emergency_stabilization_source_review

## Safety

```text
read_only=true
writes_database=false
no final diagnosis
no treatment plan
no prescription
no drug dose
no drug route
no drug frequency
requires_human_review=true
clinician_signoff_required=true
```

## Decision

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_GOVERNANCE_GO_NO_GO_V1
```
