# Clinical Docs Export UI Online Verification V1

## Purpose

This stage defines the manual online verification procedure for Clinical Docs Export UI after deployment.

It validates that the production frontend and backend together can:

```txt
open Case detail page
show DOCX export buttons
download admission DOCX
download discharge DOCX
keep the flow authenticated
keep export read-only
```

This stage is verification documentation and validation only.

It does not:

```txt
change backend code
change frontend code
change database schema
run Alembic
create Case records
update Case records
write audit_log
generate PDF
open ENABLE_EMR_REAL_IMPORT
execute EMR import
```

## Production URLs

```txt
Frontend: https://pet-med-ai-frontend-static.onrender.com
Backend: https://pet-med-ai-backend.onrender.com
```

## Required previous stages

All must be complete:

```txt
Clinical Docs Export / Word Template Spec V1
Clinical Docs Template Assets V1
Clinical Docs Export API V1
Clinical Docs Export UI V1
Clinical Docs Export Smoke Coverage V1
GitHub Actions CI Gate V1
Render / GitHub Security Hardening V1
```

## Pre-verification gates

Before opening the browser:

```bash
cd ~/Documents/Pet-med-ai

git pull origin main
bash scripts/ci_static_checks.sh
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Required:

```txt
CI static checks PASS
online smoke ALL PASS
GitHub Actions CI Gate latest run green
frontend Render deploy live
backend Render deploy live
```

## Browser verification steps

### 1. Login

Open:

```txt
https://pet-med-ai-frontend-static.onrender.com
```

Login with a valid user.

Do not use local `localhost` token for production verification.

### 2. Open an owned Case

From the case list, open a Case owned by the current user.

Do not directly guess:

```txt
/cases/1
```

because the Case may not belong to the current user.

Expected:

```txt
Case detail loads successfully
No 401
No 404
```

### 3. Confirm buttons

Expected buttons:

```txt
打印病例
导出入院/住院记录 DOCX
导出出院小结 DOCX
```

### 4. Download admission DOCX

Click:

```txt
导出入院/住院记录 DOCX
```

Expected:

```txt
DOCX downloads
filename contains admission or case id
browser does not navigate away
status message shows success
```

### 5. Download discharge DOCX

Click:

```txt
导出出院小结 DOCX
```

Expected:

```txt
DOCX downloads
filename contains discharge or case id
browser does not navigate away
status message shows success
```

### 6. Open downloaded files

Open both files in Word / Pages / LibreOffice.

Expected:

```txt
file opens without corruption warning
patient name appears
case id appears
clinician_id appears
timestamp appears
hash appears
no unreplaced {{placeholder}} remains
right-top electronic stamp placeholder remains placeholder only
```

### 7. Check browser console

Open DevTools Console / Network.

Expected:

```txt
POST /api/clinical-docs/render returns 200
Content-Type is DOCX
X-PMAI-Document-Hash exists
X-PMAI-Writes-Database=false
X-PMAI-Creates-Case=false
no secret values in console
```

## Failure handling

### 401

Likely cause:

```txt
login token missing or expired
```

Action:

```txt
clear localStorage token
login again
open Case from case list
```

### 404

Likely cause:

```txt
Case does not belong to current user
or guessed case id
```

Action:

```txt
open a Case from the authenticated user's case list
```

### DOCX fails to open

Action:

```txt
save downloaded file
record browser network response headers
run online smoke
pause release
```

### Placeholder remains

Action:

```txt
record template id and case id
pause release
fix template / backend mapping
repeat smoke and online verification
```

## Safety boundary

Clinical Docs Export UI must remain:

```txt
writes_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
```

## Completion criteria

This stage is complete when:

```txt
1. online verification runbook exists.
2. online checklist exists.
3. evidence template exists.
4. issue triage template exists.
5. validator exists and is included in smoke.
6. CI static checks include validator.
7. GitHub Actions latest run green.
8. online smoke ALL PASS.
9. manual browser verification completed.

```
