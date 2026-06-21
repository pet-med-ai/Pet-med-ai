# AI Lab Abnormal Summary V1

## Purpose

This stage adds a dry-run, deterministic abnormal lab summary layer for synthetic lab-result fixtures.

It consumes parsed lab dry-run output and produces a clinician-facing abnormality summary preview.

It does not write `DiagnosticReport.ai_summary`, does not create `DiagnosticReport`, does not create `Observation`, and does not call external AI providers.

## Endpoint

```text
POST /api/diagnostic-data/dry-run/lab-results/abnormal-summary
```

Request shape:

```json
{
  "case_id": 123,
  "fixture_id": "lab_result_dry_run_fixture_v1"
}
```

The endpoint also accepts an inline `fixture` object or an already parsed `parsed_lab_result` object for dry-run testing.

## Safety boundary

This stage must remain:

```text
writes_database=false
creates_diagnostic_report=false
creates_observation=false
writes_diagnostic_report=false
writes_observation=false
executes_real_lab_ingest=false
calls_external_ai=false
calls_external_provider=false
treatment_recommendation=false
drug_dose_recommendation=false
requires_human_review=true
```

## Explicit non-goals

This stage must not enable:

- real lab equipment ingest
- LIS integration
- provider credentials
- external AI calls
- automatic diagnostic conclusions
- treatment recommendation
- drug dose recommendation
- EMR writes
- outbound messaging

## Expected dry-run output

The synthetic CBC + chemistry fixture should produce abnormal findings including:

```text
WBC high
ALT high
GLU low
```

The summary is a review aid only. It must clearly mark:

```text
not_a_diagnosis=true
not_a_treatment_plan=true
not_a_drug_dose_recommendation=true
human_review_required=true
```

## Validation

```bash
python3 scripts/validate_ai_lab_abnormal_summary.py
bash scripts/ci_static_checks.sh
```

## Online smoke

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required smoke markers:

```text
PASS AI lab abnormal summary dry-run
PASS AI lab abnormal summary requires auth
PASS user B cannot summarize user A lab abnormal summary
PASS AI lab abnormal summary checks
```

## Decision

```text
decision=GO_TO_AI_IMAGING_REPORT_SUMMARY_V1
```
