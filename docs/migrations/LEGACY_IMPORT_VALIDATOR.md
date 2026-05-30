# 旧病例导入预校验器 V1

本阶段只做 CSV dry-run 校验，不写数据库、不调用后端 API、不创建病例。

## 目标

在正式导入旧系统数据前，先发现：

- 表头缺失或拼写错误
- 必填字段为空
- `case_id` 重复
- 日期 / 时间格式错误
- `species` 值域未映射
- `status` 值域未映射
- `weight_kg` 单位或数字异常
- 影像数量逻辑异常
- 随访日期早于就诊日期
- `created_at / updated_at` 顺序异常

## 命令

在项目根目录执行：

```bash
python3 scripts/validate_legacy_cases_csv.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv
```

指定错误文件和报告：

```bash
python3 scripts/validate_legacy_cases_csv.py legacy_cases.csv \
  --errors-out migration_errors_$(date +%Y%m%d).csv \
  --report-out migration_report_$(date +%Y%m%d).json
```

生成带 `idempotency_key` 的规范化 CSV：

```bash
python3 scripts/validate_legacy_cases_csv.py legacy_cases.csv \
  --normalized-out legacy_cases_normalized.csv
```

## 退出码

| 退出码 | 含义 |
|---:|---|
| 0 | 校验通过 |
| 1 | 文件读取失败 / 文件不存在 |
| 2 | CSV 内容存在校验错误 |

## 错误 CSV 字段

```csv
row_number,case_id,field,original_value,error_code,error_reason,suggestion
```

每一行代表一个字段级错误，便于人工修复后重新跑校验。

## 当前支持的表头

```csv
case_id,visit_date,pet_name,species,weight_kg,clinician,primary_dx,imaging_count,imaging_repeat_count,follow_up_due,follow_up_done,status,created_at,updated_at
```

默认允许额外列。若要强制完全等于模板表头：

```bash
python3 scripts/validate_legacy_cases_csv.py legacy_cases.csv --strict-header
```

## 当前值域

`species` 建议使用 Pet-Med-AI 内部值：

```txt
dog, cat, rabbit, bird, avian, reptile, turtle, snake, lizard,
amphibian, ferret, rodent, guinea_pig, hamster, chinchilla,
rat, mouse, hedgehog, sugar_glider, fish, other
```

`status` 建议使用：

```txt
active, closed, archived, inactive, deleted, draft
```

## 非目标

本阶段不做：

- 真实导入数据库
- 写 `cases` 表
- 调用 `/api/cases`
- 上传影像大文件
- 迁移收费流水
- 修改 Alembic
- 修改后端业务代码

下一阶段可以做：

```txt
旧病例导入 dry-run V1：
读取校验通过的 CSV，模拟映射为 CaseCreate payload，并输出将导入的 JSONL，不写数据库。
```
