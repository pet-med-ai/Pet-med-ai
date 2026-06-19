# Diagnostic Data Model Smoke Coverage Plan V1

## 1. 目标

下一阶段 migration 后必须有 smoke 覆盖，证明新增诊断数据模型不破坏 Commercial V1，也不引入高风险真实接入。

## 2. 必测项目

Migration V1 smoke 应覆盖：

- system version returns new revision
- schema_ok=true
- existing AI consultation works
- existing case save/detail works
- existing Clinical Docs Word export works
- feature flags remain disabled
- no real EMR import
- no real device ingest
- no real DICOM ingest
- no real lab equipment ingest

## 3. 诊断模型新增 smoke

新增 smoke 应覆盖：

- model metadata includes DiagnosticReport
- model metadata includes Observation
- model metadata includes ImagingStudy
- dry-run fixture parser does not write database
- read-only preview does not write database
- user B cannot read user A diagnostic data
- AI summary remains draft/review status, not final diagnosis

## 4. 禁止事项

Smoke 不允许：

- 真实 lab ingest
- 真实 DICOM ingest
- 真实 device connection
- external attachment download
- PHI fixture
- provider credential
