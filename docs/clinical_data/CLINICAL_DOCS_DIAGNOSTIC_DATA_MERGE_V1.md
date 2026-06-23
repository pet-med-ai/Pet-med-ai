# Clinical Docs Diagnostic Data Merge V1

## Purpose

Clinical Docs Diagnostic Data Merge V1 adds a read-only diagnostic data context merge into clinician clinical document rendering.

It allows the clinical docs preview and DOCX render path to include reviewed diagnostic data context from existing 0009 diagnostic data tables:

- DiagnosticReport
- Observation
- ImagingStudy

This stage does not create or update diagnostic data. It only reads owner-scoped records and builds clinician-review document context.

## API surface

Existing endpoints are extended with an optional request field:

```text
POST /api/clinical-docs/render-preview
POST /api/clinical-docs/render
```

Request addition:

```json
{
  "include_diagnostic_data": true
}
```

When enabled, the API returns or embeds:

```text
diagnostic_data_merge.mode=clinical_docs_diagnostic_data_merge_v1
diagnostic.reports.summary
diagnostic.observations.summary
diagnostic.imaging.summary
diagnostic.data.safety
```

## In scope

- Read existing DiagnosticReport rows for the case.
- Read existing Observation rows for the case.
- Read existing ImagingStudy rows for the case.
- Merge reviewed or abnormal diagnostic context into clinician clinical documents.
- Preserve owner-scoped case access.
- Preserve DOCX export behavior.
- Append a diagnostic data section to rendered DOCX when include_diagnostic_data=true.
- Keep safety markers in preview responses.

## Out of scope

- No Case write.
- No DiagnosticReport write.
- No Observation write.
- No ImagingStudy write.
- No ai_summary write.
- No abnormal_summary write.
- No audit log write.
- No persisted reasoning trace.
- No final diagnosis.
- No confirmed diagnosis.
- No definitive diagnosis.
- No diagnostic conclusion.
- No treatment plan.
- No prescription.
- No drug dose, route, or frequency output.
- No client-facing release.
- No external AI/provider call.
- No real EMR/lab/DICOM/device ingest.
- No PACS query.
- No attachment download.

## Safety contract

Required response flags:

```text
writes_database=false
creates_case=false
updates_case=false
updates_diagnostic_report=false
updates_observation=false
updates_imaging_study=false
writes_ai_summary=false
writes_audit_log=false
persists_reasoning_trace=false
generates_final_diagnosis=false
creates_treatment_plan=false
writes_prescription=false
returns_drug_dose=false
requires_human_review=true
clinician_signoff_required=true
not_client_facing=true
```

## Validation

```bash
python3 scripts/validate_clinical_docs_diagnostic_data_merge.py
bash scripts/ci_static_checks.sh
```

## Online smoke

```bash
KEEP_TMP=1 \
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

## Go / No-Go

GO only when validator, CI static checks, online smoke, and production 0009 schema gate all pass.

```text
decision=GO_TO_CLINICAL_QA_DASHBOARD_V2
```
