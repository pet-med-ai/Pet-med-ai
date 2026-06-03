# Webhook inbox / receipt 数据模型 V1

## 阶段定位

本阶段把 EMR Webhook dry-run V1 的 receipt / idempotency / validation report 从“内存概念”升级为可持久化的数据模型。

本阶段只做数据模型和 Alembic migration：

```txt
不修改 EMR dry-run endpoint 的写库行为
不创建病例
不下载附件
不写 audit_log
不新增真实入库流程
```

## 新增表

```txt
webhook_inbox
```

## 目标

用于后续阶段：

```txt
1. EMR Webhook receipt 持久化
2. Idempotency-Key 全局去重
3. payload_hash / signature_hash 追踪
4. dry-run validation report 留痕
5. mapped_case_preview 留痕
6. 后续 async processor / DLQ / replay 的基础
```

## 核心字段

| 字段 | 用途 |
|---|---|
| receipt_id | 接收回执 ID，主键，返回给 EMR 发送端 |
| source | 数据来源，例如 emr、his、lis |
| event_type | 外部事件类型，例如 case.created / case.updated / encounter.updated |
| idempotency_key | 幂等键，唯一索引 |
| payload_hash | 原始 payload 的 hash，用于排查同键不同内容 |
| signature_hash | 签名摘要，可用于安全审计 |
| external_case_id | EMR 侧病例 ID |
| external_encounter_id | EMR 侧就诊 ID |
| case_id | 后续真实入库后可关联 Pet-Med-AI Case |
| status | received / accepted / duplicate / rejected / processed / failed / dead_letter |
| dry_run | 是否 dry-run |
| validation_errors | 验证错误列表 |
| validation_warnings | 验证警告列表 |
| mapped_case_preview | EMR payload 到 CaseCreate 的映射预览 |
| payload | 入站 payload JSON，后续可按合规策略调整为脱敏 payload |
| error_code / error_message | 失败原因 |
| received_at / processed_at | 接收与处理时间 |
| created_at / updated_at | 审计时间 |

## 状态建议

```txt
received：接收完成，待处理
accepted：dry-run 校验通过
duplicate：幂等重复
rejected：验签 / schema / 业务规则失败
processed：后续真实处理成功
failed：处理失败，可重试
dead_letter：超过重试上限，进入人工处理
```

## 安全边界

本表不代表真实病例已经入库。

```txt
webhook_inbox 存在记录
≠
cases 已创建 / 更新
```

真实写 Case 必须后续通过独立阶段实现，并且需要：

```txt
审计日志
回滚方案
幂等策略
临床验收
线上 smoke
```

## Alembic

本阶段新增 migration：

```txt
backend/migrations/versions/0004_webhook_inbox_receipts.py
```

本地已有数据库升级：

```bash
cd backend
python3 -m alembic -c alembic.ini upgrade head
python3 -m alembic -c alembic.ini current
```

预期：

```txt
0004_webhook_inbox_receipts (head)
```

Render PostgreSQL 也必须在后端 Shell 中执行同样的 `upgrade head`。

## 后续阶段

建议下一阶段：

```txt
EMR Webhook receipt persistence V1
```

目标是让：

```txt
POST /api/webhooks/emr/dry-run
```

在不创建病例的前提下，把 receipt 和 validation report 写入 `webhook_inbox`。
