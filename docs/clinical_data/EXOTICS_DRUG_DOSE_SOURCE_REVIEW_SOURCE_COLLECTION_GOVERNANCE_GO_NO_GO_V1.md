# Exotics Drug Dose Source Review Source Collection Governance Go/No-Go V1

## Purpose

This stage defines the governance Go/No-Go gate before any exotics drug-dose source collection execution can begin.

This is not a dose engine, not a prescription engine, and not a treatment plan engine. It only defines governance gates for future metadata-only source collection.

## Current decision

```text
current_level=source_collection_governance_go_no_go_only_not_execution
source_review_status=governance_go_no_go_defined_no_collection_execution
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
collection_execution_started=false
collection_execution_allowed_now=false
pilot_execution_allowed_now=false
governance_decision=NO_GO_TO_COLLECTION_EXECUTION
```

## Required governance gates before any future collection execution

- named collector assignment
- second reviewer assignment
- source access verification
- copyright access verification
- metadata-only workspace approval
- value-capture blocker approval
- explicit human review requirement
- clinician signoff requirement
- no client-facing use

## Allowed in this stage

- define source collection governance gates
- build species-group / review-domain Go-No-Go matrix
- record metadata-only policy
- block collection execution until a later explicitly approved stage

## Forbidden in this stage

- no DB write
- no Case write
- no DiagnosticReport write
- no Observation write
- no ImagingStudy write
- no ai_summary write
- no audit log write
- no source collection execution
- no final diagnosis
- no diagnostic conclusion
- no treatment plan
- no prescription
- no drug dose
- no drug route
- no drug frequency
- no client-facing output
- no external AI/provider call
- no real EMR/lab/DICOM/device ingest

Forbidden fields:

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

## Static validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_governance_go_no_go.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

This stage is complete only after validator PASS, CI PASS, online smoke ALL PASS, production schema remains 0009_diag_data, and all dangerous feature flags remain disabled.

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_V1
```
