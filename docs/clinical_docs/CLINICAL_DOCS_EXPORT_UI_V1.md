# Clinical Docs Export UI V1

## Purpose

This stage adds a low-risk frontend entry point for clinical document DOCX export from the Case detail page.

It connects to the already completed backend API:

```txt
POST /api/clinical-docs/render
```

## Scope

The UI adds two buttons on Case detail:

```txt
导出入院/住院记录 DOCX
导出出院小结 DOCX
```

The buttons use the existing templates:

```txt
admission_hospitalization_record_bilingual
discharge_summary_bilingual
```

## Safety boundary

This UI is a download-only frontend integration.

```txt
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

It does not create or update cases, write audit logs, generate PDF, open real-import flags, or download external attachments.

## User flow

```txt
1. User opens Case detail.
2. User clicks one DOCX export button.
3. Frontend POSTs to /api/clinical-docs/render with responseType=blob.
4. Browser downloads the DOCX attachment.
5. UI shows status success / failure.
```

## Request body

```json
{
  "case_id": 123,
  "template_id": "admission_hospitalization_record_bilingual",
  "output": "docx"
}
```

## Completion criteria

```txt
1. CaseDetail.jsx includes Clinical Docs Export UI V1.
2. CaseDetail.jsx calls /api/clinical-docs/render.
3. UI includes two DOCX export buttons.
4. UI uses responseType=blob.
5. Validator is included in smoke and CI static checks.
6. frontend npm run build passes.
```
