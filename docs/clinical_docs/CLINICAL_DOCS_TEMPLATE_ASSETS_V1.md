# Clinical Docs Template Assets V1

## Stage

This stage adds the first real Word template assets for Pet-Med-AI clinical document export.

It creates two editable DOCX templates:

```txt
templates/clinical_docs/admission_hospitalization_record_bilingual.docx
templates/clinical_docs/discharge_summary_bilingual.docx
```

This stage does not:

```txt
generate patient-specific documents
add backend export API
add frontend export UI
convert to PDF
write database
create Case records
update Case records
download attachments
execute EMR import
```

## Template assets

### Admission / Hospitalization Record

File:

```txt
templates/clinical_docs/admission_hospitalization_record_bilingual.docx
```

Visual format:

```txt
A4 portrait
2.54 cm page margins
dark green header #0F3B2E
bilingual Chinese / English labels
right-top electronic stamp placeholder
editable placeholder keys
signature section
audit footer
```

Required placeholder keys:

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
{{clinician.name}}
{{generator}}
{{clinician_id}}
{{timestamp}}
{{hash}}
```

### Discharge Summary

File:

```txt
templates/clinical_docs/discharge_summary_bilingual.docx
```

Visual format:

```txt
A4 portrait
2.54 cm page margins
dark green header #0F3B2E
bilingual Chinese / English labels
right-top electronic stamp placeholder
editable placeholder keys
signature section
audit footer
```

Required placeholder keys:

```txt
{{case_id}}
{{pet.name}}
{{species}}
{{dob}}
{{owner.name}}
{{contact}}
{{vitals}}
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

## Safety boundary

```txt
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

## Stamp boundary

The DOCX contains a placeholder slot only.

```txt
Do not commit a real official clinic seal image.
Do not embed legal stamp artwork in source control.
Future renderers may insert a stamp image only from controlled runtime storage.
```

## Rendering QA

The templates were rendered for visual QA before packaging:

```txt
Admission template: 1 page
Discharge summary template: 2 pages, with signature section on page 2
```

## Future stages

Recommended next stages:

```txt
Clinical Docs Export API V1
Clinical Docs Export UI V1
Clinical Docs PDF Conversion V1
Clinical Docs Export Audit V1
```

## Completion criteria

```txt
1. DOCX assets committed.
2. Template manifest committed.
3. Sample context committed.
4. Validator committed and included in smoke.
5. CI static checks include the validator.
```

## Static validation safety markers

These exact markers are intentionally kept for CI/static validation.

```txt
contains_real_stamp=false
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

