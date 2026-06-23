# Diagnostic Reasoning Evidence Trace V1

## Status

Diagnostic Reasoning Evidence Trace V1 adds a clinician-only dry-run reasoning trace preview after Problem List V1 and Differential Diagnosis Candidates V1.

This stage is not automatic diagnosis. It is not final diagnosis. It is not confirmed diagnosis. It is not definitive diagnosis. It is not a diagnostic conclusion. It is not a treatment plan. It is not a prescription. It must not return drug dose, drug route, drug frequency, probability, numeric confidence, or client-facing conclusions.

## Purpose

The purpose is to connect each differential candidate preview to visible evidence sources so the clinician can see why the candidate is present on the review list and what evidence is missing or contradicting it.

The output is a preview-only evidence trace:

1. evidence source index
2. qualitative support mapping
3. missing or contradicting evidence list
4. clinician review questions
5. boundary and quality gate flags

## Endpoint

```text
POST /api/diagnostic-data/dry-run/diagnostic-reasoning/evidence-trace/build
```

The endpoint is authenticated and dry-run only.

## Inputs

Allowed inputs are preview objects from earlier clinical-core stages:

- case chief complaint and structured history context
- dynamic intake history
- lab abnormal summary
- imaging report summary
- clinician review workflow output
- treatment boundary output
- drug dose safety framework shell
- drug dose knowledge base safety shell
- problem_list_preview
- differential_diagnosis_candidates_preview

## Outputs

Allowed outputs:

- `diagnostic_reasoning_evidence_trace_preview`
- `evidence_source_index`
- `source_readiness`
- qualitative `evidence_fit_hint`
- qualitative `severity_hint`
- `supporting_evidence_sources`
- `contradicting_or_missing_evidence`
- `reasoning_trace_steps`
- `review_questions`
- `requires_clinician_review=true`
- `clinician_signoff_required=true`
- `not_a_diagnosis=true`
- `not_a_treatment_plan=true`
- `not_a_prescription=true`
- `not_client_facing=true`

## Forbidden outputs

This stage must not output:

- final diagnosis
- confirmed diagnosis
- definitive diagnosis
- diagnostic conclusion
- diagnosis ranking as confirmed or final
- probability
- numeric confidence
- treatment plan
- prescription
- drug dose
- drug route
- drug frequency
- client-facing conclusion

## Data persistence boundary

This stage must not write any database row.

It must not write:

- Case
- DiagnosticReport
- Observation
- ImagingStudy
- audit log
- clinician signoff
- diagnostic summary persistence
- prescription
- treatment plan

## Provider boundary

This stage must not call external AI providers, EMR providers, LIS, PACS, DICOM, device gateways, messaging providers, billing providers, or background workers.

## Safety flags

Required safety flags:

```text
read_only=true
dry_run=true
writes_database=false
persists_reasoning_trace=false
creates_audit_log=false
writes_audit_log=false
generates_final_diagnosis=false
generates_confirmed_diagnosis=false
generates_definitive_diagnosis=false
generates_diagnostic_conclusion=false
returns_probability=false
returns_numeric_confidence=false
creates_treatment_plan=false
writes_treatment_plan=false
creates_prescription=false
writes_prescription=false
returns_drug_dose=false
returns_drug_route=false
returns_drug_frequency=false
client_facing=false
requires_human_review=true
clinician_signoff_required=true
```

## Boundary checklist phrases

- No final diagnosis
- No treatment plan
- No drug dose
- No probability

## Go / No-Go

GO requires:

- validator PASS
- ci_static_checks PASS
- online smoke ALL_PASS
- authenticated endpoint smoke PASS
- production `database_revision=0009_diag_data`
- production `alembic_head=0009_diag_data`
- production `schema_ok=true`
- no DB write
- no final diagnosis
- no confirmed diagnosis
- no definitive diagnosis
- no diagnostic conclusion
- no treatment plan
- no prescription
- no drug dose, route, or frequency
- no probability
- no numeric confidence
- requires human review

Decision when complete:

```text
GO_TO_DIAGNOSTIC_ASSISTANCE_CASE_DETAIL_UI_V1
```
