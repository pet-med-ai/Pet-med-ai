# Opt-out Registry 规格 V1

> 阶段定位：本文件定义客户不同意 / 撤回数据使用后的登记字段和后续系统对接方式。  
> 本阶段只做规格，不新增数据库表。后续如需落库，应通过 Alembic 新增模型。

## 1. 目标

建立统一的 opt-out registry，供以下流程查询：

```txt
旧病例导入
EMR Webhook 入站
训练数据导出
影像 / 检验数据入训练池
Pulse / 知识库样本来源排除
人工标注任务分配
```

## 2. 最小字段

建议字段：

```csv
opt_out_id,request_type,scope,status,owner_name,owner_phone_hash,pet_name,case_id,patient_token,source_channel,requested_at,effective_at,deadline_30d,deadline_90d,created_by,reviewed_by,audit_log_id,notes
```

字段说明：

| 字段 | 含义 |
|---|---|
| opt_out_id | 撤回登记唯一 ID |
| request_type | decline / withdraw / restrict_training / restrict_export |
| scope | case_only / pet_all_cases / owner_all_pets / future_only |
| status | received / pending_verification / active / completed / rejected |
| owner_name | 主人姓名，可在后续落库时加密或脱敏 |
| owner_phone_hash | 主人电话 hash，不存明文电话优先 |
| pet_name | 宠物姓名 |
| case_id | Pet-Med-AI 病例 ID 或旧系统病例 ID |
| patient_token | 脱敏 token |
| source_channel | front_desk / phone / wechat / online_form / emr |
| requested_at | 收到请求时间 |
| effective_at | 生效时间 |
| deadline_30d | 停止新训练 / 新导出截止时间 |
| deadline_90d | 历史可移除数据标记不可用截止时间 |
| created_by | 登记人 |
| reviewed_by | 审核人 |
| audit_log_id | 关联审计日志 ID |
| notes | 备注 |

## 3. CSV 样板

```csv
opt_out_id,request_type,scope,status,owner_name,owner_phone_hash,pet_name,case_id,patient_token,source_channel,requested_at,effective_at,deadline_30d,deadline_90d,created_by,reviewed_by,audit_log_id,notes
OPT-2026-000001,withdraw,pet_all_cases,active,王小花,sha256_xxx,咪咪,HS-2026-000123,tok_pet_xxx,front_desk,2026-06-01T10:00:00+08:00,2026-06-01T10:00:00+08:00,2026-07-01T10:00:00+08:00,2026-08-30T10:00:00+08:00,frontdesk-001,compliance-001,,客户要求撤回 AI 训练用途
```

## 4. 查询规则

### 旧病例导入

```txt
若 case_id 或 patient_token 命中 active opt-out：
- 仍可导入临床病历，前提是医院有合法病历保存依据
- 但必须标记为 not_for_training
- 不进入训练导出
```

### EMR Webhook

```txt
Webhook payload 入站后：
- 使用 case_id / owner hash / patient_token 匹配 opt-out registry
- 命中后 receipt 正常返回
- 但 training_eligible=false
```

### 训练数据导出

```txt
导出前必须排除：
status in active/completed
scope 覆盖当前 case/pet/owner
```

## 5. 后续数据模型建议

后续可新增表：

```txt
opt_out_registry
```

建议只追加 / 不物理删除：

```txt
新增请求写新行
变更状态写审计日志
保留历史状态
```

## 6. 安全要求

```txt
owner_phone 优先保存 hash
不要把明文主人电话写入训练数据
不要把 opt-out registry 暴露给普通前端用户
所有查看 / 导出行为写入 audit_log
```
