# Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff V1

## Purpose

This stage defines a governance signoff shell for future metadata-only exotics drug-dose source collection activation.

It is not source collection activation, not source collection execution, not a dose engine, not a prescription engine, and not a treatment-plan engine.

## Current decision

```text
governance_decision=NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION
collection_activation_allowed_now=false
collection_execution_started=false
collection_execution_allowed_now=false
pilot_execution_allowed_now=false
```

## Scope

Allowed:

```text
metadata-only activation governance signoff matrix
clinical owner signoff requirement shell
second reviewer signoff requirement shell
source access signoff requirement shell
copyright access signoff requirement shell
metadata-only workspace signoff requirement shell
forbidden value scanner signoff requirement shell
value capture blocker signoff requirement shell
```

Blocked:

```text
source collection activation
source collection execution
collection pilot execution
dose engine
prescription engine
treatment plan engine
client-facing medication instruction
external AI/provider calls
real EMR/lab/DICOM/device ingest
```

## Forbidden value capture

The matrix and helper must not capture or store these fields as source values:

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

These labels may appear only as forbidden-field documentation and validator checks. They must not appear as matrix columns intended to collect values.

## Coverage

Species groups:

```text
rabbit, bird, ferret, turtle, lizard, snake, amphibian, fish, guinea_pig, hamster, chinchilla, rat_mouse, hedgehog, sugar_glider
```

Review domains:

```text
analgesia_and_pain_control_source_review, antimicrobial_source_review, antiparasitic_source_review, fluid_and_supportive_care_source_review, sedation_anesthesia_risk_source_review, emergency_stabilization_source_review
```

## Safety status

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
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

This stage is complete only if the validator, CI static checks, and online smoke pass while production schema remains at `0009_diag_data`.

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_V1
```
