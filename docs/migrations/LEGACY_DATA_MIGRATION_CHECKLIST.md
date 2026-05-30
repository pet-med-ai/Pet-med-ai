# 旧系统数据迁移清单与 CSV 样板 V1

> 阶段定位：本阶段只做迁移执行清单、字段映射模板、病例导入 CSV 样板和试点抽查模板。  
> 不写真实导入脚本，不改数据库，不做 Alembic 迁移，不跑生产导入。

## 目标

把旧系统病例、影像元数据、随访数据安全、可回滚地迁到 Pet-Med-AI，保证数据质量、最小停机，并形成后续 dry-run / 正式导入脚本的输入标准。

## 快速行动卡：6 步迁移流程

### 1. 评估：现状盘点 → 目标定义

必须完成：

- 明确迁移范围：
  - 病例主体
  - 就诊记录
  - 医嘱 / 诊断
  - 影像元数据，先不搬原始大文件本体
  - 收费与收款流水，如本阶段范围需要
  - 随访计划
- 列出数据字典：
  - 字段名
  - 类型
  - 单位
  - 是否允许为空
  - 唯一键
  - 业务约束
- 选定主键策略：
  - 统一使用 `case_id`
  - 建议字符串，不带业务含义
  - 便于幂等导入
- 确定验收口径：
  - 样本抽查标准
  - 通过率阈值
  - 业务签字人

可选：

- 风险分级表：红 / 橙 / 黄
- 停机窗口方案
- 旧系统只读窗口方案

### 2. 字段映射与清洗：Mapping → Transform

必须完成：

- 字段对照表：旧字段 → 新字段
- 类型转换规则：
  - string
  - integer
  - float
  - date
  - datetime
  - boolean
  - json
- 编码与格式统一：
  - UTF-8
  - 日期：`YYYY-MM-DD`
  - 时间：ISO 8601，例如 `2026-05-25T10:12:30+08:00`
  - 时区统一，建议 `+08:00` 或 UTC
- 单位统一：
  - 体重统一为 kg
  - 长度统一为 cm / mm
  - 温度统一为 ℃
- 物种词表：
  - `dog`
  - `cat`
  - `rabbit`
  - `bird`
  - `reptile`
  - `ferret`
  - `rodent`
  - `other`
- 生成幂等键：
  - 建议 `sha256(case_id + updated_at)`
  - 或 `sha256(source_system + source_primary_id + updated_at)`

可选：

- 医生姓名标准化
- 诊断本地短码
- 未来再对齐 SNOMED / LOINC / DICOM / FHIR 术语

### 3. 构建 / 验证：脚本与校验器

必须完成：

- 迁移脚本支持分块导入：
  - 建议每批 1,000 行
  - 每批有批次号
  - 失败行落地 CSV
- 失败行记录内容：
  - 行号
  - `case_id`
  - 字段名
  - 原值
  - 错误原因
  - 修复建议
- 预校验器覆盖：
  - 类型
  - 必填
  - 唯一性
  - 外键关联
  - 业务规则
- 业务规则示例：
  - 随访到期日不得早于就诊日期
  - 体重不得小于等于 0
  - `species` 必须在标准词表内
  - `updated_at` 不得早于 `created_at`
- 回滚快照：
  - 导入前目标库备份
  - 或 shadow table
  - 或批次回滚表

可选：

- append-only 审计日志：
  - 批次号
  - 触发人
  - 时间
  - 通过率
  - 失败数
  - 输入文件 hash

### 4. 小批试点：Dry-run → Pilot

必须完成：

- 选 100–500 条做全链路干跑：
  - 抽取
  - 清洗
  - 预校验
  - 导入
  - 前端可见
  - 业务抽查
- 影像处理：
  - 第一阶段只接入外链
  - 格式：PACS / 网盘 / 对象存储 URL + 访问凭证或授权说明
  - 不直接搬原始 DICOM 大文件
- 形成《试点问题单》：
  - 字段缺失
  - 值域不符
  - 类型错误
  - 旧系统脏数据
  - 前端展示问题

可选：

- 门诊并行 1–3 天：
  - 旧系统主用
  - 新系统跟跑
  - 抽查比对

### 5. 切换：Cut-over

必须完成：

- 旧系统进入只读窗口
- 导出增量数据
- 导入增量
- 校验通过
- 放开新系统写入
- 设置回滚阈值：
  - 抽查失败率超过阈值
  - 核心表数量不一致
  - 关键字段缺失率超过阈值
  - 影像外链不可达率超过阈值
- 临床签字：
  - 科室代表
  - 负责人
  - 医生代表

可选：

- 蓝绿切换
- shadow table
- 夜间低峰执行

### 6. 上线后监测：Post-go-live

必须完成：

- 数据质量看板：
  - 缺失率
  - 重复率
  - 影像外链可达率
  - 随访合规率
  - 导入失败率
- 幂等保护：
  - 重复文件 / 重复行再次导入不产生副本
  - 依 `idempotency_key` 拦截
- 审计追踪：
  - 批次留痕
  - 异常报警
  - 修复记录

可选：

- 每周复盘
- 词表优化
- 定期再清洗任务

## 病例导入 CSV 表头

```csv
case_id,visit_date,pet_name,species,weight_kg,clinician,primary_dx,imaging_count,imaging_repeat_count,follow_up_due,follow_up_done,status,created_at,updated_at
```

示例：

```csv
HS-2026-000123,2026-05-25,咪咪,cat,3.20,Dr.Zhao,Acute gastroenteritis,2,0,2026-06-01,,active,2026-05-25T10:12:30+08:00,2026-05-25T10:12:30+08:00
```

## Excel 实用公式

### 每行完整度评分

示例：统计 `B2:G2`、`I2`、`L2` 共 8 项的非空占比。

```excel
=COUNTA(B2:G2,I2,L2)/8
```

### 影像复拍率

```excel
=SUM(J:J)/SUM(I:I)
```

### 回访合规率

如果 `follow_up_done` 是完成日期，`follow_up_due` 是到期日期，可按实际列微调：

```excel
=COUNTIFS(K:K,"<>",K:K,"<="&J:J)/COUNTIF(J:J,"<>")
```

如果把“回访完成与否 / 晚点天数”设计为单独列，按实际列名调整范围。

## 小批干跑落地方式

### 干跑步骤

1. 抽取 200 条样本。
2. 跑预校验脚本。
3. 输出校验报告：
   - 空值
   - 类型错误
   - 重复
   - 外键缺失
   - 业务规则错误
4. 输出错误明细 CSV。
5. 修复 mapping / clean rules。
6. 重新 dry-run。
7. 导入测试库。
8. 前端抽查。
9. 临床签字。

### 失败行 CSV 字段

建议字段：

```csv
batch_id,row_number,case_id,field_name,raw_value,error_code,error_reason,fix_suggestion,created_at
```

### 数据库错误日志表草案

后续正式脚本可建 append-only 日志表：

```txt
migration_error_log
- id
- batch_id
- row_number
- source_file
- case_id
- field_name
- raw_value
- error_code
- error_reason
- fix_suggestion
- created_at
```

## 临床签字要求

建议抽查比例：

- 至少 5%
- 或至少 200 条
- 取两者较大者

抽查内容：

- 病例基础信息正确
- 主诉 / 病史 / 体检化验摘要正确
- 诊断字段正确
- 影像外链能打开
- 随访日期正确
- 关键词可检索
- 前端展示无乱码

签字角色：

- 门诊负责人
- 医生代表
- 数据迁移负责人
- 系统负责人

## MVP：现在就能做的最小交付

本阶段交付 4 个文件：

```txt
docs/migrations/LEGACY_DATA_MIGRATION_CHECKLIST.md
docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv
docs/migrations/LEGACY_FIELD_MAPPING_TEMPLATE.csv
docs/migrations/PILOT_CHECKLIST_TEMPLATE.csv
```

后续阶段再做：

```txt
scripts/validate_legacy_cases_csv.py
scripts/import_legacy_cases_dry_run.py
scripts/import_legacy_cases.py
```

## 容易踩坑

### 时区混乱

导入前统一 `created_at` / `updated_at` 时区。建议全部写入 `+08:00` 或 UTC，再由前端呈现本地时间。

### 重复与幂等

用：

```txt
case_id + updated_at
```

或：

```txt
source_system + source_primary_id + updated_at
```

生成 idempotency key。导入前先查再写。

### 影像不先搬原文件

第一阶段只接入外链和影像元数据。等系统稳定后，再考虑冷数据归档和 DICOM 存储。

### 值域统一

`species` 必须使用标准词表。不要出现：

```txt
狗狗
犬
小狗
猫咪
兔兔
```

这些应该在清洗时统一为：

```txt
dog
cat
rabbit
```

### 财务流水晚点做

财务流水涉及账期、撤销、冲正、退款、不可逆项目。不要和病例主体迁移混在第一阶段。
