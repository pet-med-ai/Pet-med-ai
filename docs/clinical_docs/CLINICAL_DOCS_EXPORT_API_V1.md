# Clinical Docs Export API V1

## Purpose

This stage adds the first backend API for exporting Pet-Med-AI clinical documents as DOCX files.

It uses the existing Word template assets:

```txt
templates/clinical_docs/admission_hospitalization_record_bilingual.docx
templates/clinical_docs/discharge_summary_bilingual.docx
```

## Scope

This V1 supports:

```txt
list templates
render preview context
render DOCX download
```

This V1 does not:

```txt
generate PDF
write database
write audit_log
create Case
update Case
download attachments
execute EMR import
embed real clinic stamp
```

## Endpoints

```txt
GET /api/clinical-docs/templates
POST /api/clinical-docs/render-preview
POST /api/clinical-docs/render
```

## Request body

```json
{
  "case_id": 123,
  "template_id": "admission_hospitalization_record_bilingual",
  "output": "docx",
  "clinician_name": "赵海生",
  "clinician_id": "HS-0001"
}
```

Supported template ids:

```txt
admission_hospitalization_record_bilingual
discharge_summary_bilingual
```

## Render preview

`POST /api/clinical-docs/render-preview` returns:

```txt
message=clinical_doc_render_preview
template_id
case_id
document_hash
missing_required_keys
context
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

## DOCX render

`POST /api/clinical-docs/render` returns a DOCX attachment.

Response headers include:

```txt
Content-Disposition
X-PMAI-Document-Hash
X-PMAI-Template-Id
X-PMAI-Writes-Database=false
X-PMAI-Creates-Case=false
```

## Security model

The endpoint is authenticated and scoped to the current user.

Rules:

```txt
User can render only their own Case.
Output is DOCX only.
No PDF conversion in V1.
No database write.
No audit write in V1.
No real clinic stamp embedded.
No attachment download.
```

## Template rendering strategy

V1 uses a lightweight standard-library DOCX XML placeholder replacement.

Supported placeholders:

```txt
{{case_id}}
{{pet.name}}
{{species}}
{{dob}}
{{owner.name}}
{{contact}}
{{vitals}}
{{admission_reason}}
{{provisional_dx}}
{{treatment_plan}}
{{meds}}
{{hospital_course}}
{{final_dx}}
{{discharge_instructions}}
{{home_meds}}
{{follow_up_plan}}
{{clinician.name}}
{{generator}}
{{clinician_id}}
{{timestamp}}
{{hash}}
```

Future implementation may replace this with:

```txt
docxtpl
python-docx
LibreOffice PDF conversion
audit log export tracking
```

## Completion criteria

```txt
1. backend/clinical_docs_api.py exists.
2. backend/main.py includes clinical_docs_api_router.
3. GET /api/clinical-docs/templates is present.
4. POST /api/clinical-docs/render-preview is present.
5. POST /api/clinical-docs/render is present.
6. API safety markers remain false for database writes and Case mutation.
7. Validator is included in smoke and CI static checks.
```

## Template operational defaults

The DOCX template assets may include non-clinical operational placeholders.

Clinical Docs Export API V1 fills them with safe defaults:

```txt
{{clinic.name}} = 瀚森宠物医院 / Hanson Veterinary Clinic
{{clinic.address}} = 地址待填写 / Address TBD
{{clinic.phone}} = 电话待填写 / Phone TBD
{{clinic.hours}} = 营业时间待填写 / Hours TBD
{{stamp.image}} = 电子章位 / Stamp placeholder
```

Safety:

```txt
contains_real_stamp=false
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

