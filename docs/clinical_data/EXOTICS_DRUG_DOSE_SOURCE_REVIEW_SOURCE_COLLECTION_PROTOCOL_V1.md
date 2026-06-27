# Exotics Drug Dose Source Review Source Collection Protocol V1

## Purpose

This stage defines the source collection protocol for future exotics drug dose source review.

It is not a dose engine, not a prescription engine, and not a treatment plan engine.

The stage only defines how source metadata may be collected for later review. It does not populate reviewed sources, does not extract numeric medication values, does not capture route or frequency instructions, and does not create any client-facing output.

## Current level

```text
current_level=source_collection_protocol_only_not_dose_engine
source_review_status=source_collection_protocol_ready_not_started
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
```

## Covered species groups

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

## Allowed collection fields

```text
source_collection_id
species_group
review_domain
source_type
source_locator
citation_key
publication_or_edition_metadata
retrieval_status
copyright_access_status
species_applicability_note
indication_category
contraindication_theme
monitoring_theme
source_conflict_note
reviewer_initials
second_reviewer_required
collection_status
abstraction_ready_without_values
```

## Forbidden capture

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

## In scope

- metadata-only source collection protocol
- allowed source type list
- collection controls
- reviewer requirements
- species group and review domain matrix
- copyright-safe collection boundary
- validator and smoke coverage

## Out of scope

- drug dose engine
- prescription engine
- treatment plan engine
- source evidence population
- numeric dose extraction
- route or frequency extraction
- client-facing instructions
- database writes
- external AI/provider calls

## Safety gates

```text
read_only=true
writes_database=false
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_protocol.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

```text
GO only if validator PASS, CI PASS, smoke PASS, and production schema remains 0009_diag_data.
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_V1
```
