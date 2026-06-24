# Exotics Drug Dose Source Review Controlled Research V1

## Purpose

This stage creates a controlled research protocol for future exotic-species drug dose source review.

It is not a dose engine, not a prescription engine, and not a treatment plan engine.

## Scope

Allowed:

- define species-specific source review controls
- define evidence metadata fields
- define reviewer workflow requirements
- define contradiction / unresolved-gap handling
- generate source-review matrix rows without dose values
- preserve the source_review_status as required / not started

Forbidden:

- no numerical drug dose
- no drug route
- no drug frequency
- no prescription text
- no treatment plan
- no final diagnosis
- no client-facing instruction
- no external AI / provider call
- no database write

## Species groups

The controlled research matrix covers:

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

## Current decision

```text
current_level=controlled_research_protocol_only_not_dose_engine
is_dose_engine=false
is_prescription_engine=false
dose_output_enabled=false
source_review_status=controlled_research_protocol_ready_not_started
drug_dose_status=not_reviewed_not_enabled
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_EVIDENCE_ABSTRACTION_V1
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_controlled_research.py
bash scripts/ci_static_checks.sh
```
