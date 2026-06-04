# EMR real import batch planning UI V1

## 阶段定位

本阶段新增前端 planning 页面：

```txt
/emr/import-batches
```

用于从已经人工复核为 `ready_for_import` 的 `webhook_inbox` receipts 创建真实导入候选批次。

## 安全边界

本阶段会调用：

```txt
POST /api/emr/import-batches/plan
GET /api/emr/import-batches
GET /api/emr/import-batches/{batch_id}
```

后端 V1 会写：

```txt
emr_import_batches
emr_import_batch_receipts
audit_log
```

但仍然不会：

```txt
创建 Case
更新 Case
下载附件
执行真实导入
消费队列
```

页面必须明确显示：

```txt
writes_emr_import_batches=true
writes_emr_import_batch_receipts=true
writes_audit_log=true
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
can_execute_import=false
```

## 页面功能

```txt
1. 未登录显示登录提示。
2. 登录后自动拉取 status=ready_for_import 的 webhook inbox receipts。
3. 支持勾选 receipts。
4. 填写 created_by、clinical_signoff_id、rollback_snapshot_id、note。
5. 调用 /api/emr/import-batches/plan 创建候选 batch。
6. 查看 batch 列表。
7. 查看 batch 详情和 receipts 快照。
8. 页面没有真实导入按钮。
```

## 验收

```bash
python3 scripts/validate_emr_import_batch_planning_ui.py

cd frontend
npm run build

BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

线上：

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

前端手动验收：

```txt
https://pet-med-ai-frontend-static.onrender.com/emr/import-batches
```

登录后确认：

```txt
1. 可看到 ready_for_import receipts。
2. 可创建 frozen batch。
3. 可查看 batch detail。
4. 页面明确显示 planning only / 不创建病例。
```

## 后续阶段

下一阶段才考虑：

```txt
EMR real import batch execution dry-run V1
```

即使进入 execution dry-run，也仍然应先返回 import diff / rollback plan，不直接写 Case。
