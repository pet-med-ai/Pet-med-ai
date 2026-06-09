# Clinical Docs Export Smoke Coverage V1

## Purpose

This stage adds runtime smoke coverage for the Clinical Docs Export API and UI chain.

It verifies that an authenticated smoke user can:

```txt
create / own a Case
preview clinical document context
render admission DOCX
render discharge DOCX
download valid DOCX files
confirm unreplaced placeholders are absent
confirm API remains read-only
```

## Covered endpoints

```txt
GET /api/clinical-docs/templates
POST /api/clinical-docs/render-preview
POST /api/clinical-docs/render
```

## Runtime assertions

The smoke test verifies:

```txt
render-preview returns clinical_doc_render_preview
document_hash exists
context.pet.name includes Smoke case pet name
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
render returns HTTP 200
render returns valid DOCX zip
DOCX contains word/document.xml
DOCX has no unreplaced {{placeholder}}
DOCX contains Smoke case pet name
```

## Safety boundary

This coverage must stay read-only:

```txt
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

It must not:

```txt
create new Case beyond the existing smoke case
update Case
write audit_log
generate PDF
open ENABLE_EMR_REAL_IMPORT
download external attachments
```

## Completion criteria

```txt
1. scripts/smoke_petmed.sh includes clinical docs render-preview checks.
2. scripts/smoke_petmed.sh includes clinical docs DOCX render checks.
3. scripts/smoke_petmed.sh validates admission and discharge DOCX outputs.
4. scripts/validate_clinical_docs_export_smoke.py exists.
5. smoke and ci_static_checks include validator.
```
