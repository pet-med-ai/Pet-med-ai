# Diagnostic Data Model Rollback Plan V1

## 1. 目标

为下一阶段 Diagnostic Data Model Migration V1 预先制定 rollback 思路。

本阶段不执行 rollback。

## 2. Rollback 原则

Migration V1 rollback 必须只影响新增对象：

```text
diagnostic_reports
observations
imaging_studies
```

不得影响：

- cases
- users
- consultation sessions
- preventive care tables
- automated reminder delivery tables
- webhook inbox
- EMR batch / execution result tables
- audit log
- KPI tables

## 3. Downgrade 方向

若 migration 失败，应能：

```text
alembic downgrade 0008_auto_delivery
```

并回到：

```text
database_revision=0008_auto_delivery
schema_ok=true
```

## 4. 生产保护

生产升级前必须：

- 备份确认
- maintenance window 或 controlled deploy
- system version check
- smoke before migration
- migration
- system version check
- smoke after migration
- rollback command documented

## 5. No PHI in rollback evidence

Rollback evidence 只能记录 schema 和 revision，不记录真实诊断报告内容。
