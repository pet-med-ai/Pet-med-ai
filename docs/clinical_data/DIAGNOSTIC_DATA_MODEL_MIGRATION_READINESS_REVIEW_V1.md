# Diagnostic Data Model Migration Readiness Review V1

## 1. 阶段定位

本阶段是 DiagnosticReport / Observation / ImagingStudy 进入数据库迁移前的 readiness review。

它的目标是回答：

```text
现在是否已经具备创建 DiagnosticReport / Observation / ImagingStudy Alembic migration 的条件？
```

本阶段不是 migration。

本阶段不创建表、不改 ORM、不改生产数据库。

---

## 2. 前置阶段

已完成：

```text
Clinical Core Roadmap Refresh V1 docs + validation
Diagnostic Data Model Gap Review V1 docs + validation
DiagnosticReport / Observation / ImagingStudy Design V1 docs + validation
```

当前建议：

```text
decision=GO_TO_DIAGNOSTIC_DATA_MODEL_MIGRATION_V1
```

只有本 readiness review 通过后，才允许进入 Diagnostic Data Model Migration V1。

---

## 3. 本阶段允许做什么

允许：

- migration readiness checklist
- Alembic plan
- rollback plan
- PostgreSQL identifier safety review
- SQLite / PostgreSQL compatibility review
- owner-scope test plan
- smoke coverage plan
- risk register
- Go / No-Go decision
- validator
- CI hook

---

## 4. 本阶段不允许做什么

```text
不新增 Alembic migration
不新增数据库表
不改 backend/models/*
不改 backend/migrations/*
不改生产数据库
不接真实检验仪
不接真实 DICOM / PACS
不接真实设备网关
不启用 EMR real import
不启用 EMR case update
不下载附件
不写结构化处方
不做药物剂量推荐
```

---

## 5. Readiness Gates

### Gate 1: 模型设计稳定

必须已经锁定：

- DiagnosticReport schema
- Observation schema
- ImagingStudy schema
- Case relationship
- source_type policy
- status workflow
- AI summary boundary
- attachment_ref boundary

### Gate 2: Alembic 风险可控

必须明确：

- revision id 不超过 alembic_version.version_num 限制
- index / constraint 名称不超过 PostgreSQL identifier 63 字符限制
- migration 支持 SQLite 本地和 PostgreSQL 生产
- downgrade / rollback plan 存在
- 不破坏现有 0008_auto_delivery head

### Gate 3: 安全边界可控

必须保持：

- real EMR import disabled
- EMR case update disabled
- EMR attachment download disabled
- device real ingest disabled
- DICOM real ingest disabled
- lab equipment real ingest disabled
- structured prescription write disabled
- automatic delivery disabled

### Gate 4: 测试和 smoke 有计划

Migration V1 必须准备：

- model metadata validator
- Alembic migration validator
- API dry-run validator
- owner-scope tests
- smoke coverage
- local SQLite upgrade check
- production PostgreSQL upgrade readiness check
- system version / schema_ok check

---

## 6. Migration V1 允许范围

如果本阶段通过，下一阶段 Migration V1 只允许：

- 新增 DiagnosticReport ORM
- 新增 Observation ORM
- 新增 ImagingStudy ORM
- 新增 Alembic migration
- 新增只读 / dry-run validator
- 新增 smoke coverage

Migration V1 仍然不允许：

- 真实 lab ingest
- 真实 imaging / DICOM ingest
- 真实 device ingest
- 真实 EMR import
- 结构化处方写入
- 自动外发消息
- provider credentials

---

## 7. 预期决策

无 blocker 时：

```text
decision=GO_TO_DIAGNOSTIC_DATA_MODEL_MIGRATION_V1
next=Diagnostic Data Model Migration V1
```

有 blocker 时：

```text
decision=NO_GO_REWORK_DESIGN_OR_READINESS
```
