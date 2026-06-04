# EMR Webhook inbox detail UI V1

## 阶段定位

本阶段为 EMR Webhook inbox 的前端只读复核页面。

它承接：

```txt
EMR Webhook inbox review API V1
GET /api/webhooks/emr/inbox
GET /api/webhooks/emr/inbox/{receipt_id}
```

本阶段不新增后端 API、不新增数据库表、不创建病例、不下载附件。

## 前端路由

```txt
/webhooks/emr/inbox
```

## 页面能力

```txt
1. 登录后查看 EMR Webhook receipt 列表。
2. 按 status / dry_run / receipt_id / external_case_id / Idempotency-Key 筛选。
3. 点击 receipt 查看详情。
4. 展示 validation_errors / validation_warnings。
5. 展示 mapped_case_preview。
6. 默认隐藏原始 payload。
7. 勾选 include_payload=true 后才请求并展示 payload。
8. 页面明确显示：dry-run，只读，不创建病例。
```

## 安全边界

本页面只读：

```txt
不创建 Case
不更新 Case
不下载附件
不写 audit_log
不修改 webhook_inbox
不提供真实导入按钮
```

## 影响文件

```txt
frontend/src/pages/WebhookInboxPage.jsx
frontend/src/App.jsx
scripts/validate_webhook_inbox_ui.py
scripts/smoke_petmed.sh
docs/integrations/WEBHOOK_INBOX_DETAIL_UI_V1.md
```

## 本地验收

```bash
cd ~/Documents/Pet-med-ai
python3 scripts/validate_webhook_inbox_ui.py
```

前端构建：

```bash
cd ~/Documents/Pet-med-ai/frontend
npm run build
```

后端 smoke：

```bash
cd ~/Documents/Pet-med-ai
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

## 页面验收

```txt
1. 打开 /webhooks/emr/inbox。
2. 未登录时显示登录提示。
3. 登录后能看到 receipt 列表。
4. 点击“查看详情”能看到 validation report 与 mapped_case_preview。
5. 默认不显示 payload。
6. 勾选 include_payload 后才显示 payload。
7. 页面没有创建病例、真实导入、下载附件等按钮。
```

## 后续阶段

下一阶段可以考虑：

```txt
EMR Webhook inbox review action V1
```

该阶段才考虑人工标注 receipt 是否可进入真实导入队列，但仍应先做 dry-run / 审计，不直接创建病例。
