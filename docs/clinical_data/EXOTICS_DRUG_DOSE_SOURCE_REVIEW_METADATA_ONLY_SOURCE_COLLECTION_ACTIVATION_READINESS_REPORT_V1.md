# Exotics Drug Dose Source Review Metadata-only Source Collection Activation Readiness Report V1

## Purpose

This stage defines a metadata-only activation readiness report shell for exotics drug dose source review.

It does not activate source collection, does not execute source collection, does not create a dose engine,
does not create a prescription engine, and does not produce treatment plans.

## Current level

```text
current_level=metadata_only_source_collection_activation_readiness_report_shell_only_not_activation
source_review_status=metadata_only_source_collection_activation_readiness_report_defined_no_activation
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
activation_readiness_defined=true
activation_readiness_passed=false
activation_readiness_report_defined=true
activation_readiness_report_has_collection_results=false
collection_activation_allowed_now=false
collection_execution_started=false
collection_execution_allowed_now=false
pilot_execution_allowed_now=false
governance_decision=NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION
```

## Scope

The report covers all supported exotics species groups and source review domains. It records only readiness
status fields such as clinical-owner readiness, second-reviewer readiness, source access, copyright access,
metadata-only workspace status, forbidden-value scanner status, halt rules, and Go/No-Go status.

## Explicitly forbidden

The activation readiness report must not contain or enable:

- numeric_dose_value
- dose_unit
- route_text
- frequency_text
- duration_text
- prescription_direction
- treatment_protocol
- client_instruction
- copied_table_text
- copyrighted_full_text

## Safety boundary

```text
no DB write
no Case write
no DiagnosticReport write
no Observation write
no ImagingStudy write
no ai_summary write
no audit log write
no source collection activation
no source collection execution
no final diagnosis
no diagnostic conclusion
no treatment plan
no prescription
no drug dose
no drug route
no drug frequency
no client-facing output
no external AI/provider call
no real EMR/lab/DICOM/device ingest
```

## Required validators

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_readiness_report.py
bash scripts/ci_static_checks.sh
```

## Decision

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_READINESS_REPORT_FINAL_GO_NO_GO_V1
```
