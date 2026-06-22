# Drug Dose Safety Framework V1

## Purpose

Drug Dose Safety Framework V1 establishes a safety boundary before any future dose knowledge base or dose calculation work.

This stage does not calculate a dose, does not recommend a drug, does not write a prescription, and does not create a treatment plan.

It only evaluates whether a candidate drug/dose text or request would be blocked by the current safety policy.

## Endpoint

```text
POST /api/diagnostic-data/dry-run/drug-dose-safety/check
```

## Required safety behavior

```text
read_only=true
dry_run=true
writes_database=false
creates_prescription=false
writes_prescription=false
creates_treatment_plan=false
treatment_recommendation=false
drug_recommendation=false
drug_dose_recommendation=false
dose_calculation=false
dose_calculation_enabled=false
returns_numeric_dose=false
returns_route_frequency=false
calls_external_ai=false
calls_external_provider=false
sends_external_message=false
requires_human_review=true
clinician_signoff_required=true
```

## Explicit non-goals

This stage must not provide:

- numeric dose output
- mg/kg calculation
- route / frequency / duration instruction
- prescription write
- automatic treatment plan
- client-facing medication instruction
- external AI provider call
- real EMR write
- real lab / DICOM / device ingest

## Expected decision

If a candidate contains drug, dose, route, or frequency content such as:

```text
Medication text containing mg/kg PO q24h must be blocked.
```

The framework must return:

```text
framework.decision=blocked_dose_calculation_disabled
framework.blocked=true
framework.dose_calculation_enabled=false
returns_numeric_dose=false
requires_human_review=true
```

## Validation

```bash
python3 scripts/validate_drug_dose_safety_framework.py
bash scripts/ci_static_checks.sh
```

## Online smoke

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required result:

```text
PASS Drug dose safety framework dry-run
PASS Drug dose safety framework blocks dose
PASS Drug dose safety framework requires auth
PASS user B cannot check user A drug dose safety
PASS Drug dose safety framework checks
ALL PASS
```

## Go / No-Go

GO only if all static validation, CI static checks, production schema gates, and online smoke pass.

```text
decision=GO_TO_DRUG_DOSE_KNOWLEDGE_BASE_V1
```
