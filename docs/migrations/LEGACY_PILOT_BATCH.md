# 旧病例导入 pilot batch V1

## 定位

本阶段用于把真实旧库导出的 100-200 条样本跑完整 dry-run 链路：

1. CSV 预校验
2. CaseCreate JSONL 映射
3. API dry-run 批次报告
4. `pilot_review_checklist.csv` 临床抽查清单
5. `clinical_signoff.md` 签字记录模板

仍然不写数据库、不调用 `/api/cases`、不创建病例。

## 运行方式

本地离线生成 artifacts：

```bash
cd ~/Documents/Pet-med-ai

python3 scripts/run_legacy_pilot_batch.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv \
  --work-dir /tmp/petmed_legacy_pilot
```

带后端 API dry-run：

```bash
cd ~/Documents/Pet-med-ai

python3 scripts/run_legacy_pilot_batch.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv \
  --work-dir /tmp/petmed_legacy_pilot \
  --base-url http://127.0.0.1:8000 \
  --token "$PETMED_TOKEN" \
  --batch-id pilot-001 \
  --sample-size 200 \
  --include-items
```

## 输出文件

默认输出到 `docs/migrations/pilot_runs/pilot_YYYYMMDD_HHMMSS/`，也可以用 `--work-dir` 指定。

生成文件：

```txt
migration_errors.csv
legacy_case_payloads.jsonl
legacy_case_payload_report.json
api_dry_run_request.json
api_dry_run_report.json
pilot_review_checklist.csv
clinical_signoff.md
pilot_report.json
```

## 质量门槛

pilot batch 通过的最低条件：

```txt
CSV 校验 0 errors
JSONL payload_rows = CSV 有效行数
API dry-run writes_database = false
API dry-run calls_case_create_api = false
API dry-run rejected = 0
review checklist 已生成
临床抽查签字通过
```

## 安全边界

本阶段不会：

```txt
写数据库
调用 /api/cases
创建病例
覆盖现有病例
修改 Alembic
处理影像大文件
导入收费流水
```

## 下一阶段

pilot batch V1 完成后，下一阶段可以做：

```txt
旧病例导入临床签字与回滚 Runbook V1
```

或者进入：

```txt
Alembic V2：移除启动补表 / 补列兜底逻辑
```

不要直接跳到真实导入。
