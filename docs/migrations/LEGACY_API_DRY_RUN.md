# 旧病例导入 API dry-run V2

## 目标

把旧病例导入 API mock V1 升级为更完整的 dry-run batch report。

本阶段仍然是安全阶段：

- 不写数据库
- 不创建 Case
- 不调用 `/api/cases`
- 不修改 Alembic
- 不做真实导入

## 新增接口

```txt
POST /api/migrations/legacy-cases/dry-run
```

需要登录 token。

请求体示例：

```json
{
  "batch_id": "pilot-001",
  "records": [
    {
      "operation": "case_create",
      "dry_run": true,
      "legacy_case_id": "HS-2026-000123",
      "idempotency_key": "sha256...",
      "case_create": {
        "patient_name": "咪咪",
        "species": "cat",
        "chief_complaint": "旧系统导入病例：Acute gastroenteritis",
        "history": "【旧系统迁移记录】...",
        "exam_findings": "【旧系统影像/附件元数据】..."
      }
    }
  ],
  "options": {
    "chunk_size": 1000,
    "sample_limit": 5,
    "include_items": true
  }
}
```

## 响应字段

```json
{
  "message": "dry_run_report",
  "mode": "api_dry_run",
  "dry_run": true,
  "writes_database": false,
  "calls_case_create_api": false,
  "received": 1,
  "accepted": 1,
  "rejected": 0,
  "ready_for_import": true,
  "summary": {},
  "quality": {},
  "import_plan": {},
  "sample_payloads": [],
  "items": [],
  "errors": [],
  "warnings": []
}
```

## 重点字段说明

### `ready_for_import`

仅表示 dry-run API 没发现批次结构错误。

它不代表可以直接导入生产库。真实导入仍需：

1. CSV 校验通过
2. JSONL dry-run 通过
3. API dry-run 通过
4. 临床抽查签字
5. 目标库备份
6. 单独真实导入实现

### `quality.field_coverage`

统计 CaseCreate 字段在 accepted records 中的非空覆盖率。

用于判断旧库数据缺失风险，例如：

- `history`
- `exam_findings`
- `weight`
- `owner_phone`

### `import_plan`

仅用于计划评估，不执行导入。

包含：

- chunk_size
- chunks
- accepted_records
- can_promote_to_real_import=false

## V1 mock 兼容

旧接口仍保留：

```txt
POST /api/migrations/legacy-cases/mock
```

它继续返回 V1 所需字段：

- message=mocked
- writes_database=false
- calls_case_create_api=false
- accepted/rejected
- items/errors

但底层也复用 V2 dry-run report 逻辑。

## 验收

本地：

```bash
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

线上：

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

预期：

```txt
ALL PASS
```
