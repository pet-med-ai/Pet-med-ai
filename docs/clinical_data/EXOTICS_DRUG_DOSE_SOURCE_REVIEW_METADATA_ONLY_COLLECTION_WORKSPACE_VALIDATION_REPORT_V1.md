# Exotics Drug Dose Source Review Metadata-only Collection Workspace Validation Report V1

## Purpose

This stage creates a validation report shell for the metadata-only source collection workspace.

It does not execute source collection. It does not populate the workspace with collection results. It does not create any medication table. It does not create any dose, prescription, or treatment plan engine.

## Current level

```text
current_level=metadata_only_workspace_validation_report_shell_only_not_collection_execution
source_review_status=metadata_only_workspace_validation_report_defined_no_collection_results
drug_dose_status=not_reviewed_not_enabled
```

## Scope

Allowed:

```text
define validation report shell
summarize species/domain coverage
summarize metadata-only workspace status
summarize validation status
summarize forbidden value capture blockers
summarize collection execution Go/No-Go
```

Blocked:

```text
no DB write
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

## Validation report fields

Allowed report fields are metadata-only status fields:

```text
validation_report_id
species_group
review_domain
workspace_validation_scope
validation_report_status
workspace_status
validation_status
coverage_status
forbidden_value_capture_status
numeric_value_capture_status
route_frequency_capture_status
usable_medication_instruction_status
collection_execution_status
go_no_go_status
human_review_required
clinician_signoff_required
next_required_stage
```

Forbidden fields remain:

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

## Governance decision

```text
governance_decision=NO_GO_TO_COLLECTION_EXECUTION
collection_execution_started=false
collection_execution_allowed_now=false
metadata_only_workspace_defined=true
metadata_only_workspace_populated=false
metadata_only_workspace_validation_defined=true
metadata_only_workspace_validation_executed=false
metadata_only_workspace_validation_report_defined=true
metadata_only_workspace_validation_report_has_collection_results=false
```

## Completion gates

```bash
python3 scripts/validate_exotic_kb.py
python3 scripts/validate_exotic_intake_templates.py
python3 scripts/validate_exotics_drug_dose_source_review_pack.py
python3 scripts/validate_exotics_drug_dose_source_review_controlled_research.py
python3 scripts/validate_exotics_drug_dose_source_evidence_abstraction.py
python3 scripts/validate_exotics_drug_dose_source_review_evidence_tables.py
python3 scripts/validate_exotics_drug_dose_source_review_source_registry.py
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_protocol.py
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_execution_readiness.py
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_execution_controlled_pilot.py
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_controlled_pilot_report.py
python3 scripts/validate_exotics_drug_dose_source_review_source_collection_governance_go_no_go.py
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace.py
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_validation.py
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report.py
bash scripts/ci_static_checks.sh
```

## Decision

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_V1
```
