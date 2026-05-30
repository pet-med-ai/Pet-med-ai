# KPI 聚合 API V1

## 阶段定位

本阶段把已经建立的 KPI 数据模型接入只读聚合 API。

本阶段做：

```txt
GET /api/kpi/cases
GET /api/kpi/imaging
GET /api/kpi/followups
GET /api/kpi/qa
GET /api/kpi/dashboard
```

本阶段不做：

```txt
前端 KPI Dashboard 页面
写库
QA 自动工单
医院设备接入
收费系统对账
旧病例真实导入
```

## 鉴权

所有 `/api/kpi/*` 接口都需要登录 token，并且只统计当前用户 owner_id 范围内的病例及相关 KPI 数据。

## 时间窗口

通用参数：

```txt
start=YYYY-MM-DD 或 ISO datetime
end=YYYY-MM-DD 或 ISO datetime
```

如果不传，默认最近 30 天。

## 接口

### GET /api/kpi/cases

返回病例完整度与平均结案时长占位。

V1 完整度使用当前 Case 表已有字段：

```txt
patient_name
species
chief_complaint
weight
exam_findings
analysis
care_plan = treatment 或 prognosis
```

注意：真实体温、过敏史、收费单、closed_at/status 还没有建模，所以平均结案时长在 V1 返回 unavailable。

### GET /api/kpi/imaging

基于：

```txt
imaging_studies
imaging_billing
```

返回：

```txt
repeat_imaging.rate
duplicate_imaging_share.share
```

### GET /api/kpi/followups

基于：

```txt
followups
```

返回：

```txt
followup_compliance.rate
bands.same_day
bands.within_1_day
bands.within_2_days
bands.overdue_or_missing
```

### GET /api/kpi/qa

基于：

```txt
qa_audit
cases
```

返回：

```txt
qa_audit_coverage.rate
severity_counts
status_counts
```

### GET /api/kpi/dashboard

聚合以上四组接口，返回一页仪表所需的 6 个 KPI 卡片和 sections 明细。

## 响应安全边界

本阶段所有 KPI API 都是只读：

```txt
writes_database = false
不会创建病例
不会修改随访
不会修改影像
不会生成 QA 工单
```

## 后续阶段

```txt
KPI Dashboard 前端 V1
KPI 异常触发表 V1
KPI mock seed / demo data V1
QA 自动工单 V1
```
