# Exotics Drug Dose Source Review Metadata-only Source Collection Activation Readiness V1

## Purpose

This stage defines the activation-readiness shell for future metadata-only exotics source collection.

It does **not** activate source collection. It does **not** start source collection execution. It does **not** populate the source registry, evidence tables, or collection workspace. It does **not** capture medication values. It does **not** create a dose engine, prescription engine, or treatment plan engine.

## Activation readiness decision

```text
governance_decision=NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION
collection_activation_allowed_now=false
collection_execution_started=false
collection_execution_allowed_now=false
pilot_execution_allowed_now=false
```

## Current level

```text
current_level=metadata_only_source_collection_activation_readiness_schema_only_not_activation
source_review_status=metadata_only_source_collection_activation_readiness_defined_no_activation
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
```

## In scope

- metadata-only activation readiness matrix
- species group coverage
- source review domain coverage
- clinical owner activation gate
- second reviewer activation gate
- source access activation gate
- copyright access activation gate
- metadata-only workspace readiness gate
- forbidden value scanner readiness gate
- pilot sample-limit readiness gate
- halt-rule readiness gate
- explicit NO-GO to metadata-only source collection activation

## Out of scope

- source collection activation
- source collection execution
- source registry population
- evidence table population
- medication value capture
- route/frequency capture
- copied table text or copyrighted full text
- dose engine
- prescription engine
- treatment plan engine
- client-facing instructions
- real EMR/lab/DICOM/device ingest

## Forbidden capture fields

The activation readiness matrix and any future workspace derived from it must not contain these usable medication instruction fields:

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

## Required safety flags

```text
read_only=true
writes_database=false
source_collection_activation=false
source_collection_execution=false
collection_activation_allowed_now=false
collection_execution_started=false
collection_execution_allowed_now=false
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
no final diagnosis
no treatment plan
no prescription
no drug dose
requires_human_review=true
clinician_signoff_required=true
```

## Decision

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_V1
```
