# Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record Final Go/No-Go V1

## Purpose

This stage creates the final Go/No-Go shell after the metadata-only source collection activation governance signoff record validation report.

It is not source collection activation, not source collection execution, not a dose engine, not a prescription engine, and not a treatment-plan engine.

The required governance decision remains:

```text
NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION
```

## Scope

Allowed:

- define a final Go/No-Go matrix for every exotics species group and source-review domain
- record metadata-only governance status labels
- keep human review and clinician signoff requirements explicit
- keep collection activation and execution blocked

Blocked:

- database writes
- source collection activation
- source collection execution
- medication value capture
- route or frequency capture
- usable medication instructions
- prescription direction
- treatment protocol
- client-facing output
- external AI/provider calls

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

## Forbidden fields

The final Go/No-Go shell must not introduce or accept these fields:

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

## Required status

```text
current_level=metadata_only_source_collection_activation_governance_signoff_record_final_go_no_go_schema_only_not_activation
source_review_status=metadata_only_source_collection_activation_governance_signoff_record_final_go_no_go_defined_no_activation
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
collection_activation_allowed_now=false
collection_execution_started=false
collection_execution_allowed_now=false
pilot_execution_allowed_now=false
governance_decision=NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_final_go_no_go.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

This stage is complete only when validator, CI static checks, online smoke, and production system version gates pass.

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_REPORT_V1
```
