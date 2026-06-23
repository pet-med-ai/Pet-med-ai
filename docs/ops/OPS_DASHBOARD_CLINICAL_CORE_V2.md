# Ops Dashboard Clinical Core V2

## Purpose

Ops Dashboard Clinical Core V2 adds a read-only clinical-core operations section to the existing Ops Dashboard. It surfaces Clinical QA Dashboard V2 data for operations review without turning the Ops Dashboard into a diagnostic, treatment, prescription, messaging, or ingest system.

## Scope

In scope:

- read Clinical QA Dashboard V2 summary
- show clinical review coverage
- show DiagnosticReport review coverage
- show abnormal Observation review gaps
- show ImagingStudy review gaps
- show Diagnostic Summary Audit Log evidence counts
- show QA queue preview for internal clinician review
- keep all dangerous feature flags closed
- keep output clinician-only and not client-facing

Out of scope:

- database writes
- Case updates
- DiagnosticReport updates
- Observation updates
- ImagingStudy updates
- AI summary writes
- audit log writes
- persisted reasoning trace
- final diagnosis
- diagnostic conclusion
- treatment plan
- prescription
- drug dose / route / frequency
- probability or numeric confidence
- PACS query or attachment download
- real EMR / lab / DICOM / device ingest
- external AI/provider calls

## Frontend

```text
frontend/src/pages/OpsDashboard.jsx
```

The existing Ops Dashboard calls:

```text
GET /api/diagnostic-data/clinical-qa-dashboard/v2/summary
```

and renders a clinician-only section:

```text
Ops Dashboard Clinical Core V2
```

## Safety gates

Required UI-visible safety:

```text
read_only=true
writes_database=false
not_client_facing=true
requires_human_review=true
clinician_signoff_required=true
no final diagnosis
no treatment plan
no prescription
no drug dose
```

## Validation

```bash
python3 scripts/validate_ops_dashboard_clinical_core_v2.py
bash scripts/ci_static_checks.sh
KEEP_TMP=1 BASE_URL=https://pet-med-ai-backend.onrender.com FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com bash scripts/smoke_petmed.sh
```

## Go / No-Go

GO only if validator, CI, frontend build, online smoke, production schema gate, and dangerous feature flag checks pass.

```text
next=LAB_RESULT_PARSER_EXPANSION_V2
```
