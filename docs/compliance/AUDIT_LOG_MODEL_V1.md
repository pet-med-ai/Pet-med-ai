# 审计日志数据模型 V1

## 阶段定位

本阶段只新增 append-only 审计日志的数据模型和 Alembic 迁移。

本阶段做：

```txt
- 新增 SQLAlchemy ORM 模型 AuditLog
- 新增 Alembic 迁移 0003_audit_log
- 新增 audit_log 表结构说明
- 新增本地校验脚本
- smoke 增加审计日志模型校验
```

本阶段不做：

```txt
- 不新增 POST /api/audit-log
- 不改前端 AI 建议覆核 UI
- 不写审计记录
- 不提供 update / delete 接口
- 不接对象存储 WORM
```

## 表名

```txt
audit_log
```

## 设计原则

```txt
1. append-only：应用层后续只允许新增，不提供更新/删除接口。
2. 可追溯：记录 request_id、clinician_id、model_version、建议、最终动作、覆盖理由。
3. 可关联：可选关联 case_id、session_uid。
4. 可扩展：metadata JSON 用于保存后续 EMR webhook、KB patch、AI review 的上下文摘要。
5. 兼容 SQLite / PostgreSQL：log_id 使用 String(64)，由应用层生成 uuid4 hex。
```

## V1 字段

```txt
log_id                String(64) primary key
request_id            String(100) required
patient_token          String(255) optional
clinician_id           String(100) required
model_version          String(100) optional
confidence             Float optional, 0..1
suggested_action       Text optional
action_taken           String(100) required
override_reason        Text optional
note                   Text optional
case_id                optional FK cases.id SET NULL
session_uid            String(64) optional
event_type             String(100), default ai_review
source                 String(100), default pet-med-ai
metadata               JSON optional
created_at             DateTime required
```

## 典型用途

```txt
AI 建议人工覆核
EMR webhook 接收回执
Pulse KB patch 临床签字
旧病例导入批次审计
重要病例修改审计
```

## 后续阶段

下一阶段建议：

```txt
审计日志只追加 API V1
```

目标：新增 `POST /api/audit-log`，只允许创建审计记录，不提供 update/delete。
