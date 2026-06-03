# 审计日志只追加 API V1

## 阶段定位

本阶段在已经完成的 `audit_log` 数据模型基础上，新增一个只追加 API：

```txt
POST /api/audit-log
```

本阶段只做审计事件创建，不做 AI 建议覆核 UI、不做 EMR Webhook、不做 Pulse KB Patch 审核流程。

## API 目标

所有模型建议、人工覆核、EMR dry-run、KB Patch 审核等后续动作，都可以统一通过审计日志追加记录。

原则：

```txt
只追加
不提供 update
不提供 delete
如需修正，新增一条补充审计记录
```

## 请求

```http
POST /api/audit-log
Authorization: Bearer <token>
Content-Type: application/json
```

示例：

```json
{
  "request_id": "smoke-audit-001",
  "patient_token": "tok_demo",
  "clinician_id": "EMP00123",
  "model_version": "pet-med-ai@2026.06.01",
  "confidence": 0.82,
  "suggested_action": "建议：根据主诉与风险提示完善检查计划。",
  "action_taken": "accepted",
  "override_reason": "与临床体征一致",
  "note": "已与宠主沟通并记录后续随访。",
  "case_id": 123,
  "session_uid": "optional-session-id",
  "event_type": "ai_review",
  "source": "pet-med-ai",
  "metadata": {
    "ui": "ai_consult"
  }
}
```

## 字段规则

| 字段 | 必填 | 说明 |
|---|---:|---|
| `request_id` | 是 | 一次调用 / 一次业务动作 ID |
| `clinician_id` | 是 | 临床人员 ID，可先用账号 / 工号 |
| `action_taken` | 是 | accepted / modified / rejected / reviewed 等 |
| `confidence` | 否 | 0–1 |
| `case_id` | 否 | 若提供，必须属于当前登录用户 |
| `metadata` | 否 | 附加上下文，写入数据库 `metadata` JSON 字段 |

## 返回

```json
{
  "message": "created",
  "mode": "append_only",
  "log_id": "...",
  "request_id": "smoke-audit-001",
  "append_only": true,
  "can_update": false,
  "can_delete": false
}
```

## 安全边界

V1 不提供：

```txt
PUT /api/audit-log
DELETE /api/audit-log
PATCH /api/audit-log
```

FastAPI 对这些方法应返回 405。

## 验收

```bash
python3 scripts/validate_audit_log_api.py
python3 -m py_compile backend/audit_log_api.py backend/main.py scripts/validate_audit_log_api.py
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

## 后续阶段

```txt
AI 建议人工覆核 UI V1
EMR Webhook dry-run 接收端 V1
Pulse KB Patch dry-run / 审核流程 V1
```
