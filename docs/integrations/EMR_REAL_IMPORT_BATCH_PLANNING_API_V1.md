# EMR real import batch planning API V1

阶段目标：把已经人工复核为 `ready_for_import` 的 EMR Webhook receipts 组织成一个真实导入候选批次，但仍然不执行真实导入。

## 安全边界

本阶段会写：

```txt
emr_import_batches
emr_import_batch_receipts
audit_log
```

本阶段不会：

```txt
创建 Case
更新 Case
下载附件
执行真实导入
消费队列
绕过 Go / No-Go Runbook
```

API 返回必须包含：

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

## API

### POST /api/emr/import-batches/plan

用途：从已复核的 `webhook_inbox` receipts 创建候选批次。

请求示例：

```json
{
  "batch_id": "emr_batch_smoke_001",
  "source_system": "emr",
  "receipt_ids": ["rcpt_xxx"],
  "freeze": true,
  "created_by": "HS-0001",
  "clinical_signoff_id": "SIGNOFF-PENDING",
  "rollback_snapshot_id": "SNAPSHOT-PENDING",
  "note": "Pilot planning only; no Case write.",
  "metadata": {"ui": "webhook_inbox"}
}
```

前置条件：

```txt
receipt 必须存在
receipt 必须 dry_run=true
receipt.status 必须是 ready_for_import
receipt 不得已经属于其他 batch
```

### GET /api/emr/import-batches

分页查看导入候选批次。

### GET /api/emr/import-batches/{batch_id}

查看批次详情和批次内 receipt 快照。

## 后续阶段

下一阶段可做：

```txt
EMR real import batch planning UI V1
```

之后仍需单独做：

```txt
临床签字 API
rollback snapshot API
真实 import execution API
post-import monitoring
```

真实执行导入之前，必须完成 Go / No-Go Runbook、临床签字和回滚快照。
