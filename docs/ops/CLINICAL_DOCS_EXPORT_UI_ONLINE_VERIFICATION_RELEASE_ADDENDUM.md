# Release record addendum: Clinical Docs Export UI Online Verification

Copy this section into the current release record.

## Online verification evidence

```txt
verification_id:
date:
operator_id:
frontend_url:
backend_url:
git_commit:
github_actions_run_url:
online_smoke_result:
case_id:
admission_filename:
discharge_filename:
render_status_code:
document_hash_present:
writes_database_false:
creates_case_false:
console_secret_leak_absent:
result:
```

## Manual checks

```txt
[ ] Case detail loaded without 401/404
[ ] Admission DOCX button visible
[ ] Discharge DOCX button visible
[ ] Admission DOCX downloaded and opened
[ ] Discharge DOCX downloaded and opened
[ ] No unreplaced {{placeholder}}
[ ] X-PMAI-Document-Hash exists
[ ] X-PMAI-Writes-Database=false
[ ] X-PMAI-Creates-Case=false
[ ] Online smoke ALL PASS
```

## Final decision

```txt
PASS / PAUSE / FAIL:
Reason:
Operator:
Date:
```
