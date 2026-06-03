# EMR Webhook receipt persistence V1

## 1. 阶段定位

本阶段把 `POST /api/webhooks/emr/dry-run` 的 receipt / idempotency / validation report 从进程内存升级为 `webhook_inbox` 持久化记录。

它仍然不是 EMR 真实入库。

```txt
会写入：webhook_inbox
不会写入：cases / consult_sessions / audit_log
不会下载：attachments
不会创建：Pet-Med-AI 病例
```

## 2. 输入

沿用 EMR Webhook dry-run V1 的请求头：

```txt
X-PMAI-Timestamp
X-PMAI-Signature
Idempotency-Key
```

请求体仍然是 EMR case / encounter JSON。

## 3. 持久化字段

`webhook_inbox` 写入：

```txt
receipt_id
source = emr
event_type = case.upsert
idempotency_key
payload_hash
signature_hash
external_case_id
external_encounter_id
status = accepted / rejected
dry_run = true
validation_errors
validation_warnings
mapped_case_preview
payload
error_code
error_message
received_at
processed_at
```

重复 `Idempotency-Key` 不新增记录，返回原 `receipt_id` 和 `status=duplicate`。

## 4. 响应约定

首次有效请求返回 HTTP 202：

```json
{
  "message": "emr_webhook_dry_run",
  "status": "accepted",
  "receipt_id": "rcpt_xxx",
  "writes_database": true,
  "writes_webhook_inbox": true,
  "writes_case_database": false,
  "creates_case": false,
  "downloads_attachments": false,
  "receipt_persisted": true
}
```

重复请求返回 HTTP 202：

```json
{
  "status": "duplicate",
  "receipt_id": "rcpt_xxx",
  "receipt_persisted": true
}
```

## 5. 安全边界

本阶段禁止：

```txt
根据 webhook 创建病例
更新病例
写 audit_log
下载附件
暴露真实 /api/webhooks/emr 入库端点
```

## 6. 验收

本地：

```bash
python3 scripts/validate_emr_webhook_receipt_persistence.py
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

线上：

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

## 7. 下一阶段

```txt
EMR -> Case 映射 dry-run V1
```

也就是读取 `webhook_inbox` 里的 payload，生成更完整的 CaseCreate preview / import plan，但仍不创建病例。
