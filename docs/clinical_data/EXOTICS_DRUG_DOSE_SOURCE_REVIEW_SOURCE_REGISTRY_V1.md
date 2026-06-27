# Exotics Drug Dose Source Review Source Registry V1

## Purpose

This stage creates a source metadata registry shell for future exotics drug safety source review.

It is not a dose engine, not a prescription engine, and not a treatment plan engine.

## Current level

```text
current_level=source_registry_schema_only_not_dose_engine
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
source_review_status=source_registry_schema_ready_not_populated
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
```

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

## Allowed registry scope

Allowed source registry work is limited to metadata and review controls:

```text
source_type
citation_key
publication_or_edition_metadata
species_applicability_note
indication_category
evidence_role
qualitative evidence_strength_hint
qualitative contraindication_theme
qualitative monitoring_theme
source_conflict_note
reviewer_initials
review_status
```

## Explicitly blocked

```text
numeric dose values
dose units
route instructions
frequency instructions
duration instructions
prescription directions
treatment protocols
client instructions
```

## Safety boundary

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
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1
```
