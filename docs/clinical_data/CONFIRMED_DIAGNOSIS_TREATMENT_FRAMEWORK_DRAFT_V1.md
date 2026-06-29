# Confirmed Diagnosis Treatment Framework Draft V1

## Purpose

Confirmed Diagnosis Treatment Framework Draft V1 introduces a dry-run, clinician-facing treatment framework preview for cases where the diagnosis has already been confirmed by a clinician.

This stage is meant to make Pet-Med-AI more clinically useful after diagnosis while still keeping the critical safety boundary intact:

- AI does not confirm diagnosis.
- Clinician confirmed diagnosis is mandatory input.
- The output is a doctor-side framework preview only.
- The system does not write database state.
- The system does not write `Case.treatment`.
- The system does not create or write prescriptions.
- The system does not output drug dose, route, or frequency.
- The system does not create client-facing treatment instructions.

## Endpoint

```text
POST /api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/build
```

The endpoint is mounted under the existing diagnostic-data dry-run API. It must remain authenticated and owner-scoped through the existing `get_current_user` and case ownership checks.

## Required Input Contract

```json
{
  "case_id": 123,
  "confirmed_diagnosis_label": "clinician supplied diagnosis",
  "confirmed_by": "clinician-id",
  "confirmation_source": "clinician",
  "ai_generated": false
}
```

Rules:

- `case_id` is required and must refer to a case owned by the current authenticated user.
- `confirmed_diagnosis_label` is required.
- `confirmed_by` is required.
- `confirmation_source` must be clinician supplied or clinician entered.
- `ai_generated` must be explicitly `false`.
- Missing clinician confirmation must fail with `422`.
- AI-generated diagnosis input must fail with `422`.

## Output Contract

The output must include:

```json
{
  "message": "confirmed_diagnosis_treatment_framework_built",
  "mode": "confirmed_diagnosis_treatment_framework_draft_v1",
  "case_id": 123,
  "confirmed_diagnosis": {
    "label": "clinician supplied diagnosis",
    "confirmed_by": "clinician-id",
    "confirmation_source": "clinician_entered",
    "ai_generated": false
  },
  "treatment_framework_preview": {
    "treatment_goals": [],
    "care_priority_hint": "clinician_review_required",
    "supportive_care_categories": [],
    "monitoring_parameters": [],
    "recheck_plan_categories": [],
    "contraindication_checks": [],
    "referral_or_hospitalization_triggers": [],
    "procedure_or_surgery_review_points": [],
    "nutrition_and_environment_support_points": [],
    "client_communication_topics_for_clinician_review": [],
    "medication_class_review_needed": []
  },
  "quality_gate": {
    "status": "PASS",
    "requires_confirmed_diagnosis": true,
    "requires_clinician_confirmed_diagnosis": true,
    "ai_does_not_confirm_diagnosis": true,
    "blocks_prescription": true,
    "blocks_dose": true,
    "blocks_route_frequency": true,
    "not_client_facing": true
  },
  "safety": {
    "read_only": true,
    "dry_run": true,
    "writes_database": false,
    "writes_case_treatment": false,
    "creates_prescription": false,
    "writes_prescription": false,
    "returns_drug_dose": false,
    "returns_drug_route": false,
    "returns_drug_frequency": false,
    "not_client_facing": true,
    "requires_human_review": true,
    "clinician_signoff_required": true,
    "external_ai_provider_call": false
  }
}
```

## Allowed Preview Buckets

The preview may include only high-level clinician-review buckets:

- treatment goals
- care priority hint
- supportive care categories
- monitoring parameters
- recheck plan categories
- contraindication checks
- referral or hospitalization triggers
- procedure or surgery review points
- nutrition and environment support points
- client communication topics for clinician review
- medication class review needed

## Forbidden Output

The preview must not include:

- automatic prescription
- prescription write
- drug dose
- dose unit
- route instruction
- frequency instruction
- duration instruction
- final client-facing treatment instruction
- treatment plan persistence by default
- medication product recommendation
- external AI/provider call
- specific drug plus usage combination
- prescription draft write

Forbidden examples include numeric dose formats, common schedule abbreviations, and administration-route abbreviations. These are blocked by the builder and validator.

## Safety Flags

Required hard flags:

```text
requires_clinician_confirmed_diagnosis=true
ai_does_not_confirm_diagnosis=true
read_only=true
writes_database=false
writes_case_treatment=false
creates_prescription=false
writes_prescription=false
returns_drug_dose=false
returns_drug_route=false
returns_drug_frequency=false
not_client_facing=true
requires_human_review=true
clinician_signoff_required=true
external_ai_provider_call=false
```

## Go / No-Go

GO only if:

- validator passes
- ci_static_checks passes
- online smoke passes
- production system version hard gate remains at `0009_diag_data`
- dangerous feature flags remain disabled
- endpoint route exists and does not return `404`
- valid builder output has no DB write, no prescription write, no dose, no route, no frequency
- missing clinician confirmation is rejected

Decision after completion:

```text
decision=GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_PREVIEW_UI_V1
```
