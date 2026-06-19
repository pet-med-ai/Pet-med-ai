# Diagnostic Data Model Dry-run Fixtures Plan V1

## 1. 目标

为下一阶段 dry-run parser 和 read-only preview 准备脱敏样例。

## 2. Lab fixture

建议样例：

```text
CBC panel
Biochemistry panel
Urinalysis panel
```

字段必须覆盖：

- report_type
- source_type
- status
- observation display_name
- value_numeric
- unit
- reference_low
- reference_high
- abnormal_flag

## 3. Imaging fixture

建议样例：

```text
X-ray report metadata
Ultrasound report metadata
```

字段必须覆盖：

- modality
- body_region
- study_date
- report_text
- abnormal_flag
- ai_summary_status

## 4. 禁止内容

Fixtures 不允许包含：

- 真实客户姓名
- 真实手机号
- 真实病例号
- 真实医院 DICOM UID
- 真实外部附件 URL
- secrets
