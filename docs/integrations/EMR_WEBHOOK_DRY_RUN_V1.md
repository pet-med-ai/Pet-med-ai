# EMR Webhook dry-run 接收端 V1

## 阶段定位

本阶段实现：

```txt
POST /api/webhooks/emr/dry-run
```

只用于联调和安全握手：

```txt
验签
验 timestamp 时间窗
验 Idempotency-Key
解析 payload
返回 receipt_id
返回 mapped_case_preview
```

本阶段明确不做：

```txt
不创建 Case
不创建 ConsultSession
不下载附件
不写 audit_log
不写 Webhook inbox
不写数据库
```

真实入站和持久化要等后续阶段：

```txt
EMR Webhook inbox / receipt 模型 V1
EMR -> Case 映射 dry-run V1
EMR 真实入队 V1
```

## 请求地址

```txt
POST /api/webhooks/emr/dry-run
```

## 请求头

```txt
Content-Type: application/json
X-PMAI-Timestamp: 2026-06-02T08:30:15Z
X-PMAI-Signature: sha256=<hmac_sha256_hex>
Idempotency-Key: <uuid-or-stable-event-id>
```

签名消息：

```txt
timestamp + "." + raw_body
```

算法：

```txt
HMAC-SHA256
```

V1 dry-run 默认允许 smoke secret：

```txt
petmed-emr-webhook-dry-run-secret-v1
```

如果后续配置 `PMAI_WEBHOOK_SECRET`，dry-run endpoint 也会接受该 secret。真实入站 endpoint 不应使用默认 secret。

## 返回示例

```json
{
  "message": "emr_webhook_dry_run",
  "status": "accepted",
  "receipt_id": "rcpt_xxx",
  "dry_run": true,
  "writes_database": false,
  "creates_case": false,
  "downloads_attachments": false,
  "validation": {
    "accepted": true,
    "errors": [],
    "warnings": []
  },
  "mapped_case_preview": {
    "patient_name": "咪咪",
    "species": "cat",
    "weight": "3.1kg",
    "chief_complaint": "呕吐、腹泻、食欲差"
  }
}
```

重复 `Idempotency-Key` 会返回：

```json
{
  "status": "duplicate",
  "dry_run": true,
  "writes_database": false
}
```

## 错误码

```txt
400 missing required webhook headers
400 bad timestamp
400 invalid json
401 timestamp outside allowed window
401 bad signature
413 webhook payload too large for dry-run
```

## curl 联调提示

本阶段 smoke 会自动生成签名并调用 endpoint。

手工联调可按 `docs/integrations/EMR_WEBHOOK_SPEC.md` 的 curl 样例生成 `X-PMAI-Signature`。
