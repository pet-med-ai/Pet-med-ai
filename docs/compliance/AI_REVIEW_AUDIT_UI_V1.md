# AI 建议人工覆核 UI V1

## 阶段定位

本阶段把已经完成的 append-only 审计接口接入前端 AI 问诊结果区：

```txt
AI 结果展示
→ 医生选择“接受 / 修改 / 拒绝”
→ 填写临床签名与理由
→ POST /api/audit-log
→ 审计写入成功后才允许保存问诊为病例 / 更新病例
```

本阶段不新增数据库字段，不新增 Alembic migration，不修改审计日志模型。

## 前置条件

已完成：

```txt
客户数据使用同意与撤回 SOP V1
审计日志数据模型 V1
审计日志只追加 API V1
```

后端已提供：

```txt
POST /api/audit-log
```

并且不提供 update / delete 审计接口。

## UI 行为

AI 结果区新增：

```txt
AI 建议人工覆核
模型建议摘要
临床人员 ID
处理动作：接受建议 / 接受并修改 / 拒绝并替代
修改 / 拒绝理由
补充说明 / 替代方案
确认覆核并写入审计
```

规则：

```txt
1. 未登录时提示先登录。
2. 有 AI 结果但未完成覆核时，保存问诊为病例会被拦截。
3. 接受并修改 / 拒绝并替代时，理由必填，补充说明至少 10 字。
4. 写入审计成功后显示 log_id。
5. 提交后不可更改；如需补充，后续应新增一条审计记录。
```

## Audit payload

前端提交到：

```txt
POST /api/audit-log
```

示例字段：

```json
{
  "request_id": "ui-review-sessionid-1680000000000",
  "patient_token": "consult:abcd1234",
  "clinician_id": "HS-0001",
  "model_version": "pet-med-ai-frontend-review-v1",
  "confidence": 0.85,
  "suggested_action": "风险等级 / 分析 / 治疗建议 / 预后摘要",
  "action_taken": "modified",
  "override_reason": "影像学不一致",
  "note": "医生补充的临床判断与替代方案",
  "case_id": 123,
  "session_uid": "consult-session-uid",
  "event_type": "ai_review",
  "source": "pet-med-ai-frontend",
  "metadata": {
    "ui_version": "ai-review-audit-ui-v1"
  }
}
```

## 验收标准

本地：

```bash
python3 scripts/validate_ai_review_audit_ui.py
cd frontend && npm run build
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

手动：

```txt
1. 登录
2. 提交一次 AI 问诊
3. AI 结果区出现“AI 建议人工覆核”
4. 不覆核直接点“保存前预览”会提示先写入审计
5. 填写 clinician_id，选择接受建议，点击“确认覆核并写入审计”
6. 返回 log_id
7. 保存前预览按钮可用
```

线上：

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

## 后续阶段

下一阶段可做：

```txt
AI 建议人工覆核 UI V2：
把审计记录与病例保存流程绑定得更细，包括修改后的建议自动写入病史 / analysis preview。
```
