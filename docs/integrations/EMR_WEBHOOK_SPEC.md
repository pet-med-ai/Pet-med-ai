# EMR Webhook 规范文档 V1

> 阶段定位：本阶段只定义院内 EMR / HIS / PMS 向 Pet-Med-AI 推送病例事件的安全接口规范。  
> 当前 V1 **不新增后端接口、不写数据库、不创建病例、不接附件下载、不执行真实同步**。  
> 后续实现时，必须先做 dry-run 接收端，再做 inbox / receipt 模型，最后才考虑真实入库。

---

## 1. 目标

EMR 在病例创建、更新、出院、随访、影像/检验报告完成等事件发生时，向 Pet-Med-AI 推送一条 JSON 事件。

Pet-Med-AI 接收端应按以下顺序处理：

```txt
接收 HTTP POST
→ 校验 HTTPS / Content-Type
→ 校验 timestamp 时间窗
→ 使用 HMAC-SHA256 验签
→ 校验 Idempotency-Key 幂等键
→ 返回 receipt_id
→ dry-run 阶段只返回 preview / validation report
→ 后续 inbox 阶段再入站留痕
→ 最后才允许异步映射为 Case / diagnostics / attachments
```

---

## 2. 当前系统边界

### 2.1 V1 只做规范

本阶段只新增本文件：

```txt
docs/integrations/EMR_WEBHOOK_SPEC.md
```

本阶段不做：

```txt
POST /api/webhooks/emr/dry-run
POST /api/webhooks/emr
Webhook inbox 表
receipt 表
Case 写入
附件抓取
EMR 自动同步
队列 / DLQ
```

### 2.2 后续推荐阶段

```txt
1. EMR Webhook 规范文档 V1                         ← 当前阶段
2. EMR Webhook dry-run 接收端 V1                   ← 验签 + 幂等 + 不写库
3. Webhook inbox / receipt 数据模型 V1             ← Alembic 新表
4. EMR → CaseCreate 映射 dry-run V1                ← 返回 mapped_case_preview
5. EMR Webhook 真实入站 V1                         ← 只入 inbox / queue
6. EMR → Case 异步写库 V1                          ← 最后做，需审计与回滚
```

---

## 3. Endpoint 设计

### 3.1 Dry-run 阶段接口

后续第一个代码阶段建议实现：

```txt
POST /api/webhooks/emr/dry-run
```

用途：

```txt
验签
验 timestamp
验幂等
校验 payload 结构
生成 receipt_id
返回 validation report / mapped_case_preview
不写 Case
不创建病例
不抓取附件
```

### 3.2 真实入站接口

后续真实入站阶段再开放：

```txt
POST /api/webhooks/emr
```

用途：

```txt
验证通过后写入 webhook inbox / receipt
返回 202 Accepted
由后台 worker 异步处理
```

---

## 4. 必须请求头

所有请求头区分大小写。

```txt
Content-Type: application/json
X-PMAI-Timestamp: 2026-06-02T08:30:15Z
X-PMAI-Signature: sha256=<HEX_DIGEST>
Idempotency-Key: <uuid-v4-or-stable-event-key>
```

### 4.1 X-PMAI-Timestamp

要求：

```txt
ISO 8601 UTC 时间
建议格式：YYYY-MM-DDTHH:MM:SSZ
服务端允许时间窗：±300 秒
超过时间窗返回 401
```

目的：

```txt
防止旧请求被重放
降低签名泄漏后的重放风险
```

### 4.2 X-PMAI-Signature

签名算法：

```txt
HMAC-SHA256(secret, timestamp + "." + raw_body)
```

签名头格式：

```txt
sha256=<hex_digest>
```

注意：

```txt
必须使用原始 body bytes 验签。
不要先 JSON parse 再重新 dump 后验签。
不要只签 body，不签 timestamp。
```

### 4.3 Idempotency-Key

要求：

```txt
同一个 EMR 事件必须使用同一个 Idempotency-Key
同一个 key 重放时不能重复创建业务记录
建议保存窗口：至少 24 小时；真实入库阶段建议长期保留 receipt
```

推荐来源：

```txt
EMR event_id
或 case_id + encounter_id + event_type + updated_at 的稳定 hash
```

---

## 5. 环境变量

后续代码阶段建议使用：

```txt
PMAI_WEBHOOK_SECRET=<shared-secret>
PMAI_WEBHOOK_TIMESTAMP_WINDOW_SEC=300
PMAI_WEBHOOK_MAX_BODY_BYTES=1048576
```

生产环境原则：

```txt
生产环境缺 PMAI_WEBHOOK_SECRET 时，不允许启用真实 webhook。
dry-run 可在本地使用测试 secret。
secret 只能放 Render Environment，不写入仓库。
```

---

## 6. 推荐 Payload

```json
{
  "event_id": "EVT-2026-000123-0001",
  "event_type": "case.updated",
  "event_seq": 12,
  "case_id": "CASE-2026-000123",
  "pet": {
    "name": "咪咪",
    "species": "cat",
    "dob": "2023-09-01",
    "weight_kg": 3.2
  },
  "owner": {
    "id": "OWNER-8891",
    "name": "王小花",
    "phone": "+86-13900000000"
  },
  "encounter": {
    "encounter_id": "ENC-7788",
    "status": "updated",
    "chief_complaint": "呕吐、腹泻、食欲差",
    "vitals": {
      "temp_c": 39.2,
      "hr": 160,
      "rr": 32,
      "weight_kg": 3.1,
      "bcs": 4
    },
    "diagnosis_codes": ["K52.9", "R11"],
    "procedures": ["US-ABDOMEN", "CBC", "BIOCHEM"],
    "meds": [
      {"name": "多西环素", "dose": "5 mg/kg", "route": "PO", "freq": "q12h"},
      {"name": "奥美拉唑", "dose": "1 mg/kg", "route": "PO", "freq": "q24h"}
    ]
  },
  "attachments": [
    {
      "type": "image",
      "modality": "US",
      "presigned_url": "https://files.example.com/presigned/abc123.jpg",
      "expires_at": "2026-06-02T09:00:00Z"
    }
  ],
  "clinician": {
    "id": "CLN-1001",
    "name": "赵海生"
  },
  "timestamps": {
    "created_at": "2026-05-25T09:12:33Z",
    "updated_at": "2026-05-25T10:05:11Z"
  }
}
```

---

## 7. 字段映射草案

### 7.1 EMR → CaseCreate preview

| EMR 字段 | Pet-Med-AI 字段 | 规则 |
|---|---|---|
| `case_id` | `history` | 写入旧系统 / EMR 外部 ID，不直接覆盖 Pet-Med-AI 自增 ID |
| `pet.name` | `patient_name` | 空值时使用“未命名病例” |
| `pet.species` | `species` | 映射到 dog / cat / rabbit / bird / reptile / ferret / rodent / other |
| `pet.weight_kg` 或 `encounter.vitals.weight_kg` | `weight` | 格式化为 `3.2kg` |
| `owner.name` | `owner_name` | 可空 |
| `owner.phone` | `owner_phone` | 可空 |
| `encounter.chief_complaint` | `chief_complaint` | 必填；为空则 dry-run 报错 |
| `encounter.vitals` | `exam_findings` | 转为文本摘要 |
| `encounter.diagnosis_codes` | `analysis` / future DiagnosticReport | V1 不直接写 analysis；dry-run 只返回 preview |
| `encounter.meds` | future treatment / medication model | V1 不自动处方 |
| `attachments[]` | future Attachment / ImagingStudy | V1 只保留 metadata，不下载文件 |

### 7.2 附件处理原则

```txt
V1 dry-run：只校验附件 metadata，不下载。
后续 inbox：可保存附件 URL / hash / expires_at。
真实附件抓取：必须异步 worker 处理，失败入 retry / DLQ。
不要把大文件 base64 放进 JSON。
```

---

## 8. 返回格式

### 8.1 接受

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
```

```json
{
  "receipt_id": "rcpt_01J123ABCXYZ",
  "status": "accepted",
  "mode": "dry_run",
  "writes_database": false,
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 8.2 重复事件

```http
HTTP/1.1 202 Accepted
```

```json
{
  "receipt_id": "rcpt_01J123ABCXYZ",
  "status": "duplicate",
  "mode": "dry_run",
  "writes_database": false
}
```

### 8.3 常见错误

| HTTP | 场景 | 是否建议发送端重试 |
|---:|---|---|
| 400 | 缺请求头 / JSON 结构错误 | 否 |
| 401 | 签名错误 / timestamp 超窗 | 否 |
| 409 | 幂等冲突但 payload hash 不一致 | 否，需要人工排查 |
| 413 | body 超过限制 | 否 |
| 422 | payload 字段校验失败 | 否 |
| 429 | 限流 | 是 |
| 500 | 服务端错误 | 是 |
| 503 | 服务暂不可用 | 是 |

---

## 9. 可靠性与重试建议

发送端建议使用指数退避 + full jitter：

```txt
0s
2s
8s
32s
120s
最多 15 分钟
```

重试规则：

```txt
只对 5xx / 429 / 408 / 网络错误重试。
不要对 400 / 401 / 409 / 422 重试。
同一事件每次重试必须使用相同 Idempotency-Key。
```

顺序规则：

```txt
同一 case_id 内建议顺序投递。
如果无法保证顺序，必须带 event_seq。
接收端以后可按 case_id + event_seq 做乱序整序。
```

---

## 10. 审计与安全

后续代码阶段建议每次 webhook 事件都写入审计或 receipt：

```txt
receipt_id
idempotency_key
payload_hash
case_id
encounter_id
event_type
signature_status
validation_status
received_at
processed_at
error_code
```

审计原则：

```txt
只追加，不更新，不删除。
原始 payload 可先不长期保存；如果保存，必须脱敏并限制访问。
secret 不进入日志。
签名值不完整打印；最多打印 hash 前 8 位用于排查。
```

---

## 11. curl 联调样例

```bash
SECRET="replace_me"
BODY='{"case_id":"CASE-2026-000123","pet":{"name":"咪咪","species":"cat","dob":"2023-09-01","weight_kg":3.2},"owner":{"name":"王小花","phone":"+86-13900000000","id":"OWNER-8891"},"encounter":{"encounter_id":"ENC-7788","status":"updated","chief_complaint":"呕吐、腹泻、食欲差","vitals":{"temp_c":39.2,"hr":160,"rr":32,"weight_kg":3.1,"bcs":4},"diagnosis_codes":["K52.9","R11"],"procedures":["US-ABDOMEN","CBC","BIOCHEM"],"meds":[{"name":"多西环素","dose":"5 mg/kg","route":"PO","freq":"q12h"},{"name":"奥美拉唑","dose":"1 mg/kg","route":"PO","freq":"q24h"}]},"attachments":[{"presigned_url":"https://files.example.com/presigned/abc123.jpg"}],"clinician":{"id":"CLN-1001","name":"赵海生"},"timestamps":{"created_at":"2026-05-25T09:12:33Z","updated_at":"2026-05-25T10:05:11Z"}}'
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SIG="sha256=$(printf "%s.%s" "$TS" "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -binary | xxd -p -c 256)"

curl -i -X POST https://pet-med-ai-backend.onrender.com/api/webhooks/emr/dry-run \
  -H "Content-Type: application/json" \
  -H "X-PMAI-Timestamp: $TS" \
  -H "X-PMAI-Signature: $SIG" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  --data "$BODY"
```

---

## 12. 后续实现验收建议

### 12.1 EMR Webhook dry-run 接收端 V1

验收标准：

```txt
正确签名返回 202
错误签名返回 401
timestamp 超窗返回 401
缺 Idempotency-Key 返回 400
重复 Idempotency-Key 返回 duplicate
返回 receipt_id
writes_database=false
不创建 Case
smoke 覆盖
```

### 12.2 Webhook inbox / receipt 模型 V1

验收标准：

```txt
Alembic 新增 webhook_receipts / webhook_events 或类似表
receipt_id 唯一
idempotency_key 唯一
payload_hash 可查
status 可追踪
current=head
本地 / 线上 smoke ALL PASS
```

### 12.3 EMR → Case 映射 dry-run V1

验收标准：

```txt
返回 mapped_case_preview
不写数据库
不调用 /api/cases
字段映射错误返回 validation report
附件只显示 metadata
```

---

## 13. 禁止事项

```txt
不要在 V1 直接写 Case。
不要在验签前 parse JSON 后重新序列化参与签名。
不要把 webhook secret 写进仓库。
不要对 4xx 结构错误无限重试。
不要把影像 / PDF 大文件 base64 塞进 JSON。
不要让 webhook 同步阻塞 EMR 主流程。
不要绕过 audit_log / receipt 追踪直接落库。
```
