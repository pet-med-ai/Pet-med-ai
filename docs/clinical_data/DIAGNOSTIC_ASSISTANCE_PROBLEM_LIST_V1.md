# Diagnostic Assistance Problem List V1

## Stage purpose

Diagnostic Assistance Problem List V1 adds a clinician-only, dry-run problem-list preview for Pet-Med-AI's clinical diagnostic assistance path.

This stage is not automatic diagnosis. It is not a treatment plan. It is not a prescription workflow. It only organizes reviewable clinical problems from already available case context and diagnostic-summary previews so a veterinarian can decide what deserves further review.

## Endpoint

`POST /api/diagnostic-data/dry-run/problem-list/build`

The endpoint is authenticated through the existing diagnostic-data router. It may read the owned case for context when `case_id` is provided, but it must not write any database row.

## Input sources allowed

- case chief complaint
- history or dynamic intake
- lab abnormal summary
- imaging report summary
- clinician review workflow output
- treatment recommendation boundary output
- drug dose safety framework output
- drug dose knowledge-base safety-shell review output

## Output allowed

The response may return `problem_list_preview`, `evidence_sources`, `severity_hint`, and clinician-review boundary flags.

Required flags: `requires_clinician_review=true`, `clinician_signoff_required=true`, `not_a_diagnosis=true`, `not_a_treatment_plan=true`, `not_a_prescription=true`, and `not_client_facing=true`.

## Output forbidden

No final diagnosis. No confirmed diagnosis. No definitive diagnosis. No treatment plan. No prescription. No drug dose. No drug route. No drug frequency. No client-facing diagnostic conclusion. No audit log write. No Case, DiagnosticReport, Observation, or ImagingStudy write. No external AI/provider call.

## Safety model

The builder is deterministic Python logic. It does not call OpenAI, Anthropic, HTTP APIs, LIS, DICOM, PACS, EMR, devices, background workers, or notification providers.

Medication and dosing text from source inputs is redacted in evidence snippets. This keeps the stage inside problem-list preview boundaries even when upstream safety-shell payloads contain medication terms.

## Example request

```json
{
  "chief_complaint": "Vomiting for 2 days",
  "history": {"appetite": "reduced", "energy": "quiet"},
  "lab_summary": {"abnormal_findings": [{"display_name": "ALT", "abnormal_flag": "high", "interpretation": "elevated liver enzyme; clinician review required"}]},
  "imaging_summary": {"summary": {"impression": "abdominal imaging finding requires clinician review"}},
  "clinician_review_workflow": {"review_workflow": {"status": "pending_clinician_review"}}
}
```

## Go / No-Go

GO requires validator PASS, static checks PASS, online smoke PASS, production `database_revision=0009_diag_data`, production `alembic_head=0009_diag_data`, production `schema_ok=true`, no DB write, no final diagnosis, no treatment plan, no prescription, no drug dose, and `requires_human_review=true`.

The next allowed stage after GO is Differential Diagnosis Candidates V1.
