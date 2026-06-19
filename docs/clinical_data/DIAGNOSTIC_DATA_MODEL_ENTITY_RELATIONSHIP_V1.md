# Diagnostic Data Model Entity Relationship V1

## 1. 目标关系

```text
Case
 ├── DiagnosticReport
 │    └── Observation
 └── ImagingStudy
```

## 2. Case

Case 是临床数据中枢。

DiagnosticReport、Observation、ImagingStudy 必须能够回到 Case，并且必须通过 Case 所属用户 / 诊所进行访问控制。

## 3. DiagnosticReport

DiagnosticReport 表示一次诊断报告或一次诊断数据集合。

典型来源：

- manual
- emr_dry_run
- lab_device_dry_run
- device_gateway_dry_run
- future controlled real ingest

DiagnosticReport 可以包含多个 Observation。

## 4. Observation

Observation 表示单项结构化指标。

例如：

- WBC
- ALT
- CREA
- GLU
- 体温
- 心率
- 呼吸
- 血压
- 设备读数

Observation 应该属于 DiagnosticReport，同时保留 case_id 便于按病例查询。

## 5. ImagingStudy

ImagingStudy 表示一次影像检查或影像报告元数据。

例如：

- X-ray
- Ultrasound
- CT
- MRI
- Dental radiograph

ImagingStudy 先只设计元数据和报告文本，不进入真实 DICOM 影像存储实现。

## 6. 访问控制原则

所有诊断数据访问必须满足：

```text
current_user -> owns Case -> can read linked diagnostic data
```

跨用户、跨诊所访问必须返回 404 或等价的 owner-scoped not found。
