# Exotics Lab / Imaging Interpretation Readiness V1

## Purpose

This stage is a readiness review for future exotic-pet lab and imaging interpretation.

It does **not** enable interpretation. It does **not** return final diagnosis, treatment plan, prescription, drug dose, drug route, drug frequency, probability, numeric confidence, client-facing conclusion, or external provider output.

The goal is to identify what must exist before any future exotic `Observation`, `DiagnosticReport`, or `ImagingStudy` interpretation can be safely opened.

## Current conclusion

```text
current_level=exotics_lab_imaging_readiness_only_not_interpretation_engine
is_interpretation_engine=false
is_comprehensive_clinical_kb=false
lab_reference_ranges_enabled=false
imaging_ai_interpretation_enabled=false
source_review_status=required_not_started
drug_dose_status=not_reviewed_not_enabled
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1
```

## In scope

- Read existing exotic KB rule index.
- Build readiness matrix for exotic lab and imaging interpretation.
- Identify missing species-specific reference ranges.
- Identify diagnostic report and observation mapping gaps.
- Identify imaging report readiness gaps.
- Preserve all clinical safety boundaries.
- Provide validator and smoke hooks.

## Out of scope

- No lab interpretation.
- No imaging interpretation.
- No species-specific reference range activation.
- No DICOM / PACS access.
- No device or water-quality real ingest.
- No final diagnosis.
- No treatment plan.
- No prescription.
- No drug dose, route, or frequency.
- No client-facing output.
- No database write.
- No external AI/provider call.

## Matrix

The matrix lives in:

```text
docs/clinical_data/EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_MATRIX_V1.csv
```

It covers:

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
reptile legacy fallback
rodent legacy fallback
```

## Safety flags

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
writes_ai_summary=false
writes_abnormal_summary=false
writes_audit_log=false
persists_reasoning_trace=false
generates_final_diagnosis=false
generates_diagnostic_conclusion=false
creates_treatment_plan=false
writes_prescription=false
returns_drug_dose=false
returns_drug_route=false
returns_drug_frequency=false
calls_external_ai=false
requires_human_review=true
clinician_signoff_required=true
lab_reference_ranges_enabled=false
imaging_ai_interpretation_enabled=false
```

## Validation

```bash
python3 scripts/validate_exotic_kb.py
python3 scripts/validate_exotic_intake_templates.py
python3 scripts/validate_exotics_lab_imaging_interpretation_readiness.py
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
Exotics Lab / Imaging Interpretation Readiness V1: complete only after validator PASS, CI PASS, online smoke ALL PASS, production schema remains 0009_diag_data, no DB write, no final diagnosis, no treatment plan, no prescription, no drug dose, and decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1.
```
