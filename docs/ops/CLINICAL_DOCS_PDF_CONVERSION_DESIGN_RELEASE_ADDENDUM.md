# Release record addendum: Clinical Docs PDF Conversion Design

Copy this section into the release record when this design is completed.

## Design decision

```txt
stage: Clinical Docs PDF Conversion Design V1
recommended_pipeline:
selected_engine:
reason:
fallback:
```

## Safety boundary

```txt
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

## Before implementation

```txt
[ ] LibreOffice availability checked
[ ] CJK fonts checked
[ ] temp directory policy checked
[ ] no shell=True policy accepted
[ ] timeout policy accepted
[ ] PDF smoke matrix accepted
```
