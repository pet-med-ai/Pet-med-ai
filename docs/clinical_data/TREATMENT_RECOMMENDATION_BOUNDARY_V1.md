# Treatment Recommendation Boundary V1

## Purpose

Treatment Recommendation Boundary V1 defines the safety boundary before any treatment recommendation feature is built.

This stage does not generate a treatment plan. It does not recommend drugs, doses, routes, frequencies, anesthesia protocols, prescription writes, or external delivery.

It only provides a dry-run boundary check for proposed clinical-review text and returns whether the text stays inside the current allowed scope.

## Current position in the clinical core roadmap

Completed before this stage:

```text
Diagnostic Data Model Post-Migration Verification V1
Diagnostic Data Read-only API / Dry-run Fixtures V1
Lab Result Dry-run Fixture Parser V1
Imaging Metadata Dry-run Fixture Parser V1
Case Detail Diagnostic Data Display V1
AI Lab Abnormal Summary V1
AI Imaging Report Summary V1
```

This stage comes before:

```text
Drug Dose Safety Framework V1
Drug Dose Knowledge Base V1
```

## Endpoint

```text
POST /api/diagnostic-data/dry-run/treatment-boundary/check
```

## Example input

```json
{
  "case_id": 123,
  "source_summary": "Dry-run lab and imaging review requires clinician assessment.",
  "candidate_recommendation": "Clinician should review hydration status, abdominal imaging, and lab abnormalities before deciding any treatment."
}
```

## Required output markers

```text
message=treatment_recommendation_boundary_checked
mode=treatment_recommendation_boundary_v1
boundary.decision=review_only or blocked_drug_or_dose
writes_database=false
creates_treatment_plan=false
treatment_recommendation=false
drug_dose_recommendation=false
creates_prescription=false
writes_prescription=false
calls_external_ai=false
requires_human_review=true
```

## Explicit non-goals

This stage must not:

```text
write database rows
create or update Case
create DiagnosticReport
create Observation
create ImagingStudy
create prescription
write prescription
generate drug dose
recommend a drug
recommend dose route or frequency
generate anesthesia or sedation protocol
call external AI provider
call external drug database
send SMS WeChat email
execute real EMR import
execute real lab ingest
execute real DICOM ingest
execute real device ingest
```

## Allowed scope

The only allowed categories are:

```text
clinician review aid
problem-list framing
diagnostic follow-up category discussion without orders
monitoring or recheck considerations without protocols
emergency/referral consideration without treatment plan
client communication talking points without medication instructions
```

## Validation

```bash
python3 scripts/validate_treatment_recommendation_boundary.py
bash scripts/ci_static_checks.sh
```

## Online smoke

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Expected markers:

```text
PASS Treatment recommendation boundary dry-run
PASS Treatment recommendation boundary blocks dose
PASS Treatment recommendation boundary requires auth
PASS user B cannot check user A treatment boundary
PASS Treatment recommendation boundary checks
ALL PASS
```

## Go / No-Go

GO is allowed only if:

```text
validator=PASS
ci_static_checks=PASS
online_smoke=ALL_PASS
production database_revision=0009_diag_data
production alembic_head=0009_diag_data
production schema_ok=true
no DB write
no treatment plan generation
no drug or dose recommendation
no external AI provider call
requires_human_review=true
```

## Decision

```text
decision=GO_TO_DRUG_DOSE_SAFETY_FRAMEWORK_V1
```
