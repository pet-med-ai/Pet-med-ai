# Exotics Drug Dose Source Review Pack V1

## Purpose

This stage creates a source-review pack for future exotics drug safety work.

It does **not** enable drug dose recommendations. It does **not** provide prescription text. It does **not** provide route, frequency, or numeric dosing guidance.

The only output is a review framework that says which source artifacts must be collected and reviewed before any future exotics dose work can be considered.

## Current level

```text
current_level=source_review_pack_only_not_dose_engine
is_dose_engine=false
is_prescription_engine=false
drug_dose_status=not_reviewed_not_enabled
source_review_status=required_not_started
```

## In scope

- species-group source review matrix
- review-domain source requirements
- required source metadata fields
- controlled Go / No-Go criteria
- validator coverage
- smoke coverage
- explicit blocked-dose boundary

## Out of scope

- numeric drug dose output
- dose range output
- route output
- frequency output
- prescription draft
- treatment plan
- client-facing medication instruction
- external AI / provider call
- real EMR / lab / DICOM / device ingest
- DB write

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

## Required source artifact fields

Every future source-review row must include:

```text
source_title
edition_or_revision_date
author_or_organization
species_scope
drug_or_domain_scope
contraindication_notes
reviewer_id
review_date
review_status
```

## Safety boundary

Required flags:

```text
read_only=true
dry_run=true
writes_database=false
creates_case=false
updates_case=false
creates_diagnostic_report=false
updates_diagnostic_report=false
creates_observation=false
updates_observation=false
creates_imaging_study=false
updates_imaging_study=false
creates_audit_log=false
writes_audit_log=false
generates_final_diagnosis=false
generates_diagnostic_conclusion=false
creates_treatment_plan=false
writes_treatment_plan=false
creates_prescription=false
writes_prescription=false
returns_drug_dose=false
returns_drug_route=false
returns_drug_frequency=false
dose_output_enabled=false
drug_dose_recommendation=false
client_facing=false
not_client_facing=true
calls_external_ai=false
calls_external_provider=false
requires_human_review=true
clinician_signoff_required=true
source_review_required=true
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_pack.py
bash scripts/ci_static_checks.sh
```

## Online smoke

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

## Completion criteria

```text
Exotics Drug Dose Source Review Pack V1：完成
validator=PASS
exotic_kb_validator=PASS
exotic_intake_templates_validator=PASS
ci_static_checks=PASS
online_smoke=ALL_PASS
source_review_pack_present=true
source_review_matrix_present=true
current_level=source_review_pack_only_not_dose_engine
is_dose_engine=false
is_prescription_engine=false
source_review_status=required_not_started
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
production database_revision=0009_diag_data
production alembic_head=0009_diag_data
production schema_ok=true
dangerous_feature_flags_disabled=true
read_only=true
no DB write
no treatment plan
no prescription
no drug dose
requires_human_review=true
clinician_signoff_required=true
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_V1
```
