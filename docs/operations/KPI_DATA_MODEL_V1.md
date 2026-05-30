# KPI 数据模型 V1

本阶段目标：为一页运维 KPI 仪表建立最小数据模型，但不做 KPI API、不做前端仪表、不导入真实数据。

## 新增表

### imaging_studies

用途：影像元数据与影像质控，不保存 DICOM 原始大文件。

关键字段：

- `case_id`
- `modality`
- `body_part`
- `taken_at`
- `is_planned_review`
- `tag`
- `report_url`
- `viewer_url`
- `thumbnail_url`
- `metadata`

支持 KPI：

- 影像复拍率
- 影像异常触发表
- 影像外链可达率

### imaging_billing

用途：影像收费维度摘要，不替代诊所财务系统。

关键字段：

- `case_id`
- `imaging_id`
- `fee`
- `tag`
- `bill_date`

支持 KPI：

- 重复影像占比
- 重复成像金额占比

### followups

用途：随访计划与完成情况。

关键字段：

- `case_id`
- `due_date`
- `done_at`
- `channel`
- `owner`
- `status`
- `note`

支持 KPI：

- 回访合规率
- 逾期回访责任人看板

### qa_audit

用途：病例抽检、医疗记录质控、影像/用药 QA。

关键字段：

- `case_id`
- `auditor`
- `audit_type`
- `findings`
- `severity`
- `status`
- `metadata`
- `created_at`

支持 KPI：

- 审计覆盖率
- QA 抽检清单

## Alembic

本阶段新增迁移：

```txt
backend/migrations/versions/0002_kpi_data_models.py
```

本地已有数据库执行：

```bash
cd backend
python3 -m alembic -c alembic.ini current
python3 -m alembic -c alembic.ini upgrade head
python3 -m alembic -c alembic.ini current
```

Render PostgreSQL 在部署完成并线上 smoke 通过后，进入 Render Shell 执行同样的 `upgrade head`。

## 边界

本阶段不做：

- KPI 聚合 API
- KPI 前端仪表盘
- 真实影像 / 随访 / QA 数据导入
- 医院设备接口
- 旧病例真实写库
- 药物剂量或处方逻辑
