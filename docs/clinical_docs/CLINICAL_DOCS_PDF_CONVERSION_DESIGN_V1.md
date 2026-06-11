# Clinical Docs PDF Conversion Design V1

## Purpose

This stage defines how Pet-Med-AI should convert generated clinical DOCX documents into PDF in a later implementation stage.

This is a design-only stage.

It does not:

```txt
generate PDF files
install LibreOffice
add backend PDF endpoints
change frontend UI
change database schema
write audit_log
create Case records
update Case records
open ENABLE_EMR_REAL_IMPORT
```

## Current baseline

Already completed:

```txt
Clinical Docs Export / Word Template Spec V1
Clinical Docs Template Assets V1
Clinical Docs Export API V1
Clinical Docs Export UI V1
Clinical Docs Export Smoke Coverage V1
Clinical Docs Export UI Online Verification V1
```

Current clinical docs export supports:

```txt
DOCX only
POST /api/clinical-docs/render
```

Future PDF conversion should preserve the current safety boundary:

```txt
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

## Recommended PDF pipeline

Preferred V1 implementation path:

```txt
Case context -> DOCX render -> LibreOffice headless -> PDF -> verify -> return PDF
```

Why:

```txt
1. DOCX remains the source of truth for editable clinical templates.
2. LibreOffice handles Word-compatible pagination better than hand-built PDF.
3. Existing DOCX export can be reused.
4. Later PDF/A or print preflight can be added as a separate stage.
```

## Render service options

### Option A: In-process LibreOffice on backend

```txt
FastAPI backend calls soffice --headless
```

Pros:

```txt
simple
no separate service
easy local testing
```

Cons:

```txt
Render runtime image must include LibreOffice
cold start / memory cost
possible concurrency contention
```

### Option B: Separate PDF worker service

```txt
Backend writes temp DOCX
Worker converts DOCX to PDF
Backend returns PDF
```

Pros:

```txt
better isolation
can scale independently
conversion crashes do not kill main backend
```

Cons:

```txt
more infrastructure
more operational complexity
```

### Option C: Client-side browser print to PDF

```txt
Frontend print view
User prints to PDF manually
```

Pros:

```txt
no backend dependency
already close to current print flow
```

Cons:

```txt
not deterministic
hard to audit
cannot return standardized PDF files
```

## Recommended decision

For V1 implementation later:

```txt
Use Option A only if Render image can reliably include LibreOffice.
Otherwise use Option B.
Do not use Option C as clinical export standard.
```

## Future endpoint design

Existing:

```txt
POST /api/clinical-docs/render
```

Future extension:

```json
{
  "case_id": 123,
  "template_id": "admission_hospitalization_record_bilingual",
  "output": "pdf"
}
```

Future PDF response headers:

```txt
Content-Type: application/pdf
Content-Disposition: attachment; filename="..."
X-PMAI-Document-Hash: ...
X-PMAI-Template-Id: ...
X-PMAI-Source-Format: docx
X-PMAI-Writes-Database: false
X-PMAI-Creates-Case: false
```

## Temporary file policy

PDF conversion must use a per-request temporary directory:

```txt
/tmp/petmed-clinical-docs/<request-id>/
```

Required rules:

```txt
no shared filenames
no user-supplied path names
no persistent raw DOCX/PDF unless explicitly requested later
cleanup after response
KEEP_TMP-like debug mode only for local testing
```

## Security boundary

PDF conversion must not:

```txt
read external URLs
download attachments
embed real official stamp unless explicitly provided by approved secure asset flow
execute macros
preserve active content
include secrets
log document context
log DATABASE_URL
log SECRET_KEY
```

## Clinical safety boundary

PDF conversion is presentation only.

It must not:

```txt
modify Case
create Case
write audit_log in V1
change EMR import state
change clinical approval state
```

## Verification requirements

Future implementation must validate:

```txt
PDF opens successfully
PDF page count > 0
PDF contains patient name
PDF contains case_id
PDF contains clinician_id
PDF contains timestamp
PDF contains hash
PDF has no unreplaced {{placeholder}}
PDF file size is reasonable
DOCX source remains valid
```

## Failure behavior

If conversion fails:

```txt
return 500 with message clinical_doc_pdf_conversion_failed
do not delete audit evidence if debug mode is active
do not return partial PDF
do not write database
do not retry indefinitely
```

## Future implementation stages

Recommended next stages:

```txt
Clinical Docs PDF Conversion Local Prototype V1
Clinical Docs PDF Conversion API V1
Clinical Docs PDF Conversion Smoke Coverage V1
Clinical Docs PDF Online Verification V1
Clinical Docs Export Audit Log V1
```

## Completion criteria

```txt
1. PDF conversion design document exists.
2. Engine decision matrix exists.
3. Render/LibreOffice runbook exists.
4. PDF conversion test matrix exists.
5. Failure triage template exists.
6. Validator exists and is included in smoke.
7. CI static checks include validator.
```
