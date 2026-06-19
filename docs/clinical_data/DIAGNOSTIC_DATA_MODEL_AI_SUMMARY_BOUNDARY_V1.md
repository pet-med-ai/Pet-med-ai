# Diagnostic Data Model AI Summary Boundary V1

## 1. 原则

AI 可以生成异常摘要草稿，但不能替代医生最终诊断。

AI summary 字段必须有状态：

```text
not_generated
draft
reviewed
rejected
```

## 2. 适用对象

- DiagnosticReport.ai_summary
- DiagnosticReport.abnormal_summary
- ImagingStudy.ai_summary

Observation 不建议直接存长 AI 诊断意见，可以存 abnormal_flag 和 interpretation draft。

## 3. 临床边界

AI 摘要可以做：

- 标出异常项
- 归纳趋势
- 提醒需要医生复核
- 生成病例摘要草稿
- 为 Clinical Docs 提供草稿内容

AI 摘要不可以做：

- 最终诊断
- 自动处方
- 自动治疗建议直接发客户
- 覆盖医生已审核结果
- 绕过医生写入 final clinical interpretation

## 4. 后续实现要求

后续实现必须包含：

- clinician review action
- accept / edit / reject
- audit log
- source data hash or reference
- no PHI in repo fixtures
