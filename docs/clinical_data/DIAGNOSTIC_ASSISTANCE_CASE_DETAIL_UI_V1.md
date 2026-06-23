# Diagnostic Assistance Case Detail UI V1

## Stage goal

Diagnostic Assistance Case Detail UI V1 adds a clinician-only preview panel to the existing case detail page. The panel chains the already approved dry-run endpoints:

1. Diagnostic Assistance Problem List V1
2. Differential Diagnosis Candidates V1
3. Diagnostic Reasoning Evidence Trace V1

The output is a case-detail preview for clinician review only. It is not a diagnosis, not a treatment plan, not a prescription, and not client-facing.

## UI location

- Page: `frontend/src/pages/CaseDetail.jsx`
- Existing route: `/cases/:id`
- No new `frontend/src/components` files
- No new database migration
- No backend write endpoint

## Required boundary

The UI must show these guardrails:

- dry_run=true
- writes_database=false
- writes_audit_log=false
- persists_reasoning_trace=false
- not_a_diagnosis=true
- not_a_treatment_plan=true
- not_a_prescription=true
- not_client_facing=true
- requires_human_review=true
- clinician_signoff_required=true

## Allowed output

- problem list preview
- differential diagnosis candidates preview
- diagnostic reasoning evidence trace preview
- evidence source snippets
- qualitative severity_hint
- qualitative evidence_fit_hint
- clinician review questions
- quality gate statuses

## Forbidden output

- final diagnosis
- confirmed diagnosis
- definitive diagnosis
- diagnostic conclusion
- treatment plan
- prescription
- drug dose
- drug route
- drug frequency
- probability
- numeric confidence
- client-facing summary
- database write
- audit log write
- persisted signoff
- external AI/provider call

## Go / No-Go

GO only if:

- validator passes
- CI static checks pass
- frontend build passes
- online smoke passes
- authenticated endpoint chain passes
- production version remains on 0009_diag_data
- dangerous feature flags remain disabled

NO-GO if the UI writes any clinical decision data, exposes a final diagnosis, returns dose/route/frequency, or becomes client-facing.
