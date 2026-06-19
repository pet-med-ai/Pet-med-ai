# DiagnosticReport / Observation / ImagingStudy Design V1

## 1. 阶段定位

本阶段是 Pet-Med-AI 临床诊断数据模型的设计阶段。

目标是把未来检验、影像、设备、EMR dry-run 等诊断数据统一落到三个核心对象：

```text
DiagnosticReport
Observation
ImagingStudy
```

本阶段只做设计和校验，不做数据库迁移，不改 ORM，不改生产数据库。

---

## 2. 设计目标

建立能够支撑以下临床能力的数据模型设计：

- 检验报告结构化
- 单项检验值 / 设备读数结构化
- 影像检查元数据结构化
- 病例详情展示检验 / 影像
- AI 检验异常摘要
- AI 影像报告摘要
- 医生审核和最终负责
- 后续 dry-run / read-only API / migration readiness

---

## 3. 核心关系

建议关系：

```text
Case
 ├── DiagnosticReport
 │    └── Observation
 └── ImagingStudy
```

说明：

- DiagnosticReport 表示一次诊断报告，例如 CBC、生化、尿检、设备报告、EMR 诊断报告等。
- Observation 表示报告里的单项指标，例如 WBC、ALT、CREA、体温、心率等。
- ImagingStudy 表示一次影像检查，例如 X-ray、超声、CT、MRI 等。
- 三者都必须通过 Case 做 owner-scope / tenant-scope 安全控制。
- AI 摘要必须是 draft / reviewed 状态，不允许直接成为最终诊断。

---

## 4. 本阶段明确不做

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
不下载附件
不写结构化处方
不做药物剂量推荐
```

---

## 5. 设计输出

本阶段输出：

- entity relationship 设计
- DiagnosticReport schema 设计
- Observation schema 设计
- ImagingStudy schema 设计
- status workflow
- source type policy
- AI summary boundary
- read-only API plan
- dry-run fixtures plan
- migration readiness checklist
- validator

---

## 6. 下一阶段建议

本阶段完成后，不直接进入 migration。

建议下一阶段：

```text
Diagnostic Data Model Migration Readiness Review V1
```

只有 readiness review 通过后，才进入：

```text
Diagnostic Data Model Migration V1
```

预期完成决策：

```text
decision=GO_TO_DIAGNOSTIC_DATA_MODEL_MIGRATION_READINESS_REVIEW_V1
```
