# Exotics Drug Dose Source Review Source Collection Execution Controlled Pilot V1

## Purpose

This stage creates a controlled pilot shell for exotics drug-dose source collection.

It is not a dose engine, not a prescription engine, not a treatment-plan engine, and not a source-value collection run. It defines the manual, metadata-only pilot scope that must be satisfied before any real source collection can start.

## Scope

Allowed:

- define controlled pilot rows for species_group x review_domain
- define collector / second reviewer / source access / copyright access gates
- define metadata-only workspace requirements
- define allowed source metadata fields
- define prohibited medication-value fields
- generate review-only matrix and Go/No-Go evidence

Not allowed:

- no source collection execution
- no numeric dose capture
- no route or frequency capture
- no usable medication instruction
- no prescription direction
- no treatment protocol
- no client instruction
- no copied copyrighted full text
- no DB write

## Safety decision

```text
current_level=controlled_pilot_shell_only_not_collection_execution
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
source_review_status=controlled_pilot_shell_ready_not_started
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
pilot_execution_allowed_now=false
collection_execution_started=false
```

## Matrix

```text
docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_MATRIX_V1.csv
```

## Required validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_execution_controlled_pilot.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

```text
GO only if validator PASS, CI PASS, online smoke PASS, production schema remains 0009_diag_data, and no numeric dose, route, frequency, prescription, or treatment-plan content exists.
```

## Decision

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_CONTROLLED_PILOT_REPORT_V1
```
