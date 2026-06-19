# Diagnostic Data Model Alembic Plan V1

## 1. 目标

为下一阶段 Diagnostic Data Model Migration V1 制定 Alembic 计划。

本文件不创建 migration。

## 2. 推荐 revision

建议下一阶段使用短 revision：

```text
revision = "0009_diag_data"
down_revision = "0008_auto_delivery"
```

原因：

- 避免 alembic_version.version_num 长度问题
- 明确接在 Commercial V1 0008_auto_delivery 后
- 名称短，便于生产 PostgreSQL 记录

## 3. 候选表

下一阶段候选表：

```text
diagnostic_reports
observations
imaging_studies
```

## 4. PostgreSQL identifier 安全

索引和约束名必须短于 63 字符。

建议短名称：

```text
ix_diag_reports_case_id
ix_diag_reports_status
ix_diag_reports_source
ix_observations_case_id
ix_observations_report_id
ix_observations_code
ix_observations_abnormal
ix_imaging_studies_case_id
ix_imaging_studies_modality
ix_imaging_studies_status
```

禁止长名称自动生成：

```text
ix_diagnostic_reports_source_system_identifier_and_case_relationship
ix_observations_diagnostic_report_id_observation_code_abnormal_flag
```

## 5. 类型策略

保守类型策略：

- Integer primary keys
- String for controlled vocabulary
- Text for report text / AI summary
- Float for numeric values
- JSON for metadata_json only if current stack already supports it safely
- DateTime for audit timestamps

## 6. Downgrade 原则

Downgrade 应删除新增表和索引，不触碰既有 Commercial V1 表。

## 7. 下一阶段前置检查

进入 migration 前必须确认：

- validator PASS
- CI PASS
- local upgrade test plan exists
- PostgreSQL identifier review PASS
- rollback plan exists
- smoke coverage plan exists
