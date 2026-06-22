# Differential Diagnosis Candidates V1

## Stage purpose

Differential Diagnosis Candidates V1 adds a clinician-only, dry-run candidate preview after Diagnostic Assistance Problem List V1.

This stage is not automatic diagnosis. It does not create a final diagnosis, confirmed diagnosis, definitive diagnosis, diagnostic conclusion, treatment plan, prescription, drug dose, route, frequency, client-facing summary, or persistent review status.

The only purpose is to organize possible differential candidate categories for veterinarian review, using the problem list preview and its evidence sources.

## Endpoint

`POST /api/diagnostic-data/dry-run/differential-diagnosis/candidates/build`

The endpoint is authenticated through the existing diagnostic-data router. It may read an owned case for context when `case_id` is provided, but it must not write any database row.

## Input sources allowed

- `problem_list_preview` from Diagnostic Assistance Problem List V1
- `evidence_sources` from the problem-list stage
- case chief complaint
- history or dynamic intake
- lab abnormal summary
- imaging report summary
- clinician review workflow output
- treatment recommendation boundary output
- drug dose safety framework output
- drug dose knowledge-base safety-shell review output

## Output allowed

The response may return:

- `differential_diagnosis_candidates_preview`
- `candidate_label`
- `system_category`
- `evidence_fit_hint`
- `review_priority_hint`
- `severity_hint`
- `related_problem_ids`
- `matched_signal_terms`
- `supporting_evidence_sources`
- `contradicting_or_missing_evidence`

Required flags: `requires_clinician_review=true`, `clinician_signoff_required=true`, `not_a_diagnosis=true`, `not_a_final_diagnosis=true`, `not_a_confirmed_diagnosis=true`, `not_a_definitive_diagnosis=true`, `not_a_treatment_plan=true`, `not_a_prescription=true`, and `not_client_facing=true`.

`evidence_fit_hint` is a qualitative review signal only. It is not probability, not numeric confidence, not a final ranking, and not a diagnostic conclusion.

## Output forbidden

No final diagnosis. No confirmed diagnosis. No definitive diagnosis. No diagnostic conclusion. No automatic "most likely diagnosis" ranking. No numeric probability. No numeric confidence. No treatment plan. No prescription. No drug dose. No drug route. No drug frequency. No client-facing conclusion. No Case, DiagnosticReport, Observation, ImagingStudy, or audit-log write. No external AI/provider call.

## Safety model

The builder is deterministic Python logic. It does not call OpenAI, Anthropic, HTTP APIs, LIS, DICOM, PACS, EMR, devices, background workers, or notification providers.

Medication and dosing text from source inputs is redacted in evidence snippets. Candidate output uses preview language and keeps every item pending clinician review.

## Example request

```json
{
  "problem_list_preview": [
    {
      "problem_id": "problem-001",
      "category": "presenting_complaint",
      "title": "Vomiting requires clinician review",
      "severity_hint": "medium",
      "evidence_sources": [
        {"source_type": "case", "field": "chief_complaint", "snippet": "Vomiting for 2 days"}
      ]
    },
    {
      "problem_id": "problem-002",
      "category": "lab_abnormality",
      "title": "Laboratory abnormality requires clinician review: ALT",
      "severity_hint": "medium",
      "evidence_sources": [
        {"source_type": "lab_abnormal_summary", "field": "interpretation", "snippet": "ALT high; clinician review required"}
      ]
    }
  ]
}
```

## Go / No-Go

GO requires validator PASS, static checks PASS, online smoke PASS, production `database_revision=0009_diag_data`, production `alembic_head=0009_diag_data`, production `schema_ok=true`, no DB write, no final diagnosis, no treatment plan, no prescription, no drug dose, qualitative review hints only, and `requires_human_review=true`.

The next allowed stage after GO is Diagnostic Reasoning Evidence Trace V1.
