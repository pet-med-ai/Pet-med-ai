# Pet-Med-AI Integration API Draft V1

> 状态：草案，不代表当前后端已经实现。
>
> 目标：为未来医院设备网关、检验设备、影像设备、PACS/LIS/HIS 接入 Pet-Med-AI 定义统一 API 方向。

## 1. API 设计原则

```text
1. 只接收结果，不控制设备。
2. 所有写入接口必须鉴权。
3. 所有写入接口必须支持幂等。
4. 原始 payload 需要可追溯。
5. 设备数据优先通过 accession_id 匹配病例。
6. 匹配失败进入待匹配队列，不丢弃。
7. 影像大文件不直接塞进 PostgreSQL。
8. AI 只读取标准化摘要，不直接依赖厂商原始协议。
```

## 2. 认证方式草案

请求头：

```http
Authorization: Bearer <gateway_token>
X-PetMed-Gateway-Id: clinic-001-gateway-01
X-PetMed-Idempotency-Key: sha256:<payload-hash>
Content-Type: application/json
```

后续可升级：

```text
mTLS
HMAC-SHA256 请求签名
IP allowlist
Token 轮换
```

## 3. 统一字段

所有接口建议包含：

```json
{
  "source": "device_gateway",
  "gateway_id": "clinic-001-gateway-01",
  "device_uid": "lab-mindray-bc-001",
  "device_name": "Mindray BC-xxxx",
  "external_patient_id": "PMS-000123",
  "case_id": 88,
  "visit_id": "VIS-20260528-000088",
  "accession_id": "PM-20260528-000088-01",
  "collected_at": "2026-05-28T10:30:00+08:00",
  "received_at": "2026-05-28T10:31:00+08:00"
}
```

## 4. Endpoint 草案

### 4.1 设备事件

```http
POST /api/integrations/device-events
```

用于网关心跳、设备上线、设备错误、接口状态。

请求示例：

```json
{
  "event_type": "gateway_heartbeat",
  "gateway_id": "clinic-001-gateway-01",
  "device_uid": "lab-mindray-bc-001",
  "status": "online",
  "occurred_at": "2026-05-28T10:30:00+08:00",
  "metadata": {
    "ip": "192.168.1.20",
    "software_version": "1.0.0"
  }
}
```

响应示例：

```json
{
  "ok": true,
  "event_id": 1001,
  "message": "accepted"
}
```

### 4.2 检验结果接入

```http
POST /api/integrations/lab-results
```

请求示例：

```json
{
  "source": "lab_analyzer",
  "gateway_id": "clinic-001-gateway-01",
  "device_uid": "lab-mindray-bc-001",
  "device_name": "Mindray BC-xxxx",
  "case_id": 88,
  "visit_id": "VIS-20260528-000088",
  "accession_id": "PM-20260528-000088-01",
  "specimen": "whole_blood",
  "panel_code": "CBC",
  "panel_name": "血常规",
  "collected_at": "2026-05-28T10:30:00+08:00",
  "reported_at": "2026-05-28T10:33:00+08:00",
  "results": [
    {
      "code": "WBC",
      "name": "白细胞",
      "value": 18.2,
      "unit": "10^9/L",
      "reference_range": "6.0-17.0",
      "flag": "H"
    },
    {
      "code": "RBC",
      "name": "红细胞",
      "value": 5.8,
      "unit": "10^12/L",
      "reference_range": "5.5-8.5",
      "flag": "N"
    }
  ],
  "conclusion": "白细胞轻度升高。",
  "raw_payload_ref": "raw/lab/20260528/abc.hl7"
}
```

响应示例：

```json
{
  "ok": true,
  "diagnostic_report_id": 501,
  "matched_case_id": 88,
  "status": "matched"
}
```

匹配失败响应：

```json
{
  "ok": true,
  "diagnostic_report_id": 501,
  "matched_case_id": null,
  "status": "pending_match",
  "message": "No case matched by accession_id"
}
```

### 4.3 影像 study 接入

```http
POST /api/integrations/imaging-studies
```

请求示例：

```json
{
  "source": "dicom",
  "gateway_id": "clinic-001-gateway-01",
  "device_uid": "dr-room-1",
  "device_name": "DR Room 1",
  "case_id": 88,
  "visit_id": "VIS-20260528-000088",
  "accession_id": "PM-20260528-000088-02",
  "modality": "DX",
  "study_uid": "1.2.840.113619.2.55.3.604688435.123.202605281100",
  "study_datetime": "2026-05-28T11:00:00+08:00",
  "series": [
    {
      "series_uid": "1.2.840.series.1",
      "series_number": 1,
      "modality": "DX",
      "body_part": "CHEST",
      "instance_count": 2
    }
  ],
  "series_count": 1,
  "instance_count": 2,
  "viewer_url": "https://pacs.example/viewer?study=...",
  "thumbnail_url": "https://pacs.example/thumbs/study.jpg",
  "dicomweb_endpoint": "https://pacs.example/dicomweb",
  "raw_payload_ref": "raw/dicom/20260528/study.json"
}
```

响应示例：

```json
{
  "ok": true,
  "imaging_study_id": 701,
  "matched_case_id": 88,
  "status": "matched"
}
```

### 4.4 文件 / 报告附件接入

```http
POST /api/integrations/files
```

V1 可以先只接 metadata + 预签名 URL，后续再做 multipart 上传。

请求示例：

```json
{
  "source": "device_gateway",
  "gateway_id": "clinic-001-gateway-01",
  "case_id": 88,
  "accession_id": "PM-20260528-000088-03",
  "file_type": "pdf_report",
  "name": "CBC_report.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 124000,
  "sha256": "abc123...",
  "storage_url": "https://storage.example/reports/CBC_report.pdf",
  "raw_payload_ref": "raw/files/20260528/CBC_report.pdf"
}
```

响应示例：

```json
{
  "ok": true,
  "attachment_id": "att_001",
  "matched_case_id": 88,
  "status": "matched"
}
```

### 4.5 病例诊断数据查询

```http
GET /api/cases/{case_id}/diagnostics
```

响应示例：

```json
{
  "case_id": 88,
  "diagnostic_reports": [
    {
      "id": 501,
      "report_type": "laboratory",
      "panel_name": "血常规",
      "reported_at": "2026-05-28T10:33:00+08:00",
      "abnormal_summary": ["WBC 升高"],
      "observation_count": 12
    }
  ],
  "imaging_studies": [
    {
      "id": 701,
      "modality": "DX",
      "study_datetime": "2026-05-28T11:00:00+08:00",
      "viewer_url": "https://pacs.example/viewer?study=...",
      "thumbnail_url": "https://pacs.example/thumbs/study.jpg"
    }
  ],
  "pending_matches": []
}
```

## 5. 状态码草案

| HTTP | 场景 |
|---|---|
| 200 | 幂等重复提交，返回已有结果 |
| 201 | 新数据创建成功 |
| 202 | 已接收，但等待匹配或异步处理 |
| 400 | payload 格式错误 |
| 401 | 未认证 |
| 403 | 网关无权限 |
| 404 | 指定 case_id 不存在或无权访问 |
| 409 | idempotency_key 冲突 |
| 422 | 字段语义校验失败 |
| 500 | 服务端错误 |

## 6. 幂等规则

推荐 idempotency_key：

```text
sha256(gateway_id + device_uid + message_uid + payload_hash)
```

同一个 key 重复提交应返回同一个处理结果，不重复创建报告。

## 7. 原始 payload 留档

每条设备消息建议保留：

```text
raw_payload_hash
raw_payload_ref
message_type
device_uid
received_at
processed_at
status
error_message
```

这样后续厂商排查时能追溯原始 HL7 / CSV / DICOM metadata。

## 8. Mock smoke 计划

未来实现 API 后，应新增：

```text
scripts/smoke_integrations.sh
```

覆盖：

```text
1. 创建设备事件
2. 上传 CBC mock lab result
3. 上传 DX mock imaging study
4. 查询 /api/cases/{case_id}/diagnostics
5. 验证用户隔离
6. 验证幂等重复提交
7. 验证 pending_match
```

## 9. V1 不实现的内容

```text
1. 不直接接实时监护数据流
2. 不做 DICOM viewer
3. 不替代 PACS
4. 不替代 LIS
5. 不做设备控制
6. 不做自动收费
7. 不做药物剂量
```
