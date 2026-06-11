# Clinical Docs PDF Conversion Render / LibreOffice Runbook V1

## Purpose

This runbook defines how to evaluate LibreOffice-based DOCX to PDF conversion for Pet-Med-AI on Render.

This V1 is a design runbook only.

## Local smoke command draft

Future local prototype should test:

```bash
mkdir -p /tmp/petmed-pdf-test
soffice --headless --convert-to pdf --outdir /tmp/petmed-pdf-test input.docx
```

Expected output:

```txt
/tmp/petmed-pdf-test/input.pdf
```

## Render considerations

Before implementing PDF conversion on Render backend, confirm:

```txt
LibreOffice can be installed in the build image
soffice command is available at runtime
font rendering supports Chinese
temporary directory is writable
memory usage is acceptable
conversion latency is acceptable
concurrent conversions are bounded
```

## Fonts

PDF output must support Chinese and English text.

Recommended future font packages:

```txt
Noto Sans CJK
Noto Serif CJK
DejaVu Sans
Liberation fonts
```

Do not commit font files into the repository unless license and distribution are explicitly approved.

## Headless conversion guardrails

Future backend should use:

```txt
subprocess.run(..., timeout=30)
```

and enforce:

```txt
one temp directory per request
no shell=True
no user-controlled path
cleanup after conversion
max input DOCX size
max output PDF size
```

## Render fallback

If Render backend cannot reliably run LibreOffice:

```txt
create separate PDF worker service
or keep DOCX-only export until worker is ready
```

Do not ship unreliable PDF conversion into clinical workflow.
