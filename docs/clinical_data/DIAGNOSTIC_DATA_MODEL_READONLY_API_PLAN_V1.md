# Diagnostic Data Model Read-only API Plan V1

## 1. 目标

先设计 read-only / preview API，再进入写入实现。

## 2. 候选 API

```text
GET /api/cases/{case_id}/diagnostic-reports
GET /api/cases/{case_id}/diagnostic-reports/{report_id}
GET /api/cases/{case_id}/observations
GET /api/cases/{case_id}/imaging-studies
GET /api/cases/{case_id}/imaging-studies/{study_id}
POST /api/diagnostic-data/dry-run/lab-result
POST /api/diagnostic-data/dry-run/imaging-study
```

## 3. 安全要求

- owner-scoped through Case
- read-only endpoints must not write database
- dry-run endpoints must not write database
- no secret external URLs
- no PHI fixtures committed to repo
- AI summary draft only

## 4. Smoke 覆盖计划

Smoke 应覆盖：

- user A can read own diagnostic preview
- user B cannot read user A diagnostic preview
- dry-run does not write database
- schema response contains report / observation / imaging keys
- AI summary remains draft
