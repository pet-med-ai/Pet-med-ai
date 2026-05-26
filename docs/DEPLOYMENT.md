# Pet-Med-AI Deployment Guide

本文件是 Pet-Med-AI 的部署资产说明。后期商业部署时，以 GitHub `main` 分支、Render 服务配置、Render PostgreSQL 和本文件为准。

## 1. 正式部署资产

正式部署依赖：

- GitHub repo: `pet-med-ai / Pet-med-ai`
- Render Backend: `pet-med-ai-backend`
- Render Frontend Static Site: `pet-med-ai-frontend-static`
- Render PostgreSQL: `pet-med-ai-db`
- Backend URL: `https://pet-med-ai-backend.onrender.com`
- Frontend URL: `https://pet-med-ai-frontend-static.onrender.com`

本地开发工具，例如 VS Code、Mac 本地临时文件、Downloads 里的补丁脚本，不是正式部署资产。

## 2. 本地开发地址

Backend:

```bash
cd ~/Documents/Pet-med-ai/backend
python3 -m uvicorn main:app --reload --port 8000
```

本地后端地址：

```text
http://127.0.0.1:8000
```

Frontend:

```bash
cd ~/Documents/Pet-med-ai/frontend
rm -rf node_modules/.vite
VITE_API_BASE=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173 --force
```

本地前端地址：

```text
http://127.0.0.1:5173
```

## 3. Render 环境变量

### Backend: `pet-med-ai-backend`

必须配置：

```text
PYTHON_VERSION=3.11.9
DATABASE_URL=<Render PostgreSQL Internal Database URL>
SECRET_KEY=<production secret>
```

说明：

- `DATABASE_URL` 必须指向 Render PostgreSQL。
- 如果没有 `DATABASE_URL`，后端会回退到 SQLite，本地可以，但线上不适合作为商业部署。
- `SECRET_KEY` 必须在线上固定配置，避免部署后 token 校验不稳定。
- 不要把 `DATABASE_URL` 或 `SECRET_KEY` 写进 GitHub。

### Frontend: `pet-med-ai-frontend-static`

必须配置：

```text
VITE_API_BASE=https://pet-med-ai-backend.onrender.com
```

修改前端环境变量后，需要重新构建前端。建议使用：

```text
Manual Deploy → Clear build cache & deploy
```

## 4. 部署流程

### 4.1 提交代码

只提交本阶段明确修改的文件。不要执行：

```bash
git add .
```

推荐流程：

```bash
git diff --check
git status --short -- <target-files>
git add <target-files>
git commit -m "<message>"
git push origin main
```

### 4.2 Render 部署

Backend:

```text
pet-med-ai-backend → Events → Deploy live
```

Frontend:

```text
pet-med-ai-frontend-static → Events → Your site is live
```

如果前端没有更新：

```text
Manual Deploy → Clear build cache & deploy
```

## 5. 部署后验收

### 5.1 健康检查

```bash
curl -sS "https://pet-med-ai-backend.onrender.com/healthz"
```

预期：

```json
{"ok":true}
```

### 5.2 线上 smoke test

```bash
cd ~/Documents/Pet-med-ai
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

预期：

```text
ALL PASS
```

Smoke test 会验证：

- 注册 / 登录
- 创建动态问诊
- 提交追问
- 保存问诊为病例
- 历史会话返回 `case_id`
- 重复保存返回 `already_saved`
- 继续追问后更新绑定病例
- 病例详情读取
- 用户隔离
- 病例权限收口
- 新增基础信息字段保存与读取

## 6. 当前核心功能闭环

当前生产链路：

```text
用户登录
→ 创建动态问诊
→ 多轮追问
→ 保存问诊为病例
→ 病例详情结构化展示
→ 从病例详情恢复来源问诊
→ 继续追问
→ 更新绑定病例
→ 病例与问诊均按用户隔离
```

## 7. 重要注意事项

不要提交以下内容：

```text
app.db
*.db
.env
.env.*
frontend/.env.development
node_modules/
dist/
__pycache__/
*.bak
*.save
临时 apply.py 补丁脚本
```

如果需要示例环境变量，提交 `.env.example`，不要提交真实 `.env`。

## 8. render.yaml 说明

`render.yaml` 已对齐当前真实 Render 服务名和主要构建配置：

```text
Backend: pet-med-ai-backend
Frontend: pet-med-ai-frontend-static
Database: pet-med-ai-db
```

当前 `render.yaml` 包含：

```text
pet-med-ai-backend
pet-med-ai-frontend-static
VITE_API_BASE=https://pet-med-ai-backend.onrender.com
DATABASE_URL sync:false
SECRET_KEY sync:false
```

数据库 `pet-med-ai-db` 目前仍由 Render Dashboard 管理，不在 Blueprint 中创建或修改。这样可以避免误改数据库 plan、region 或连接配置。

如果未来决定完全使用 Blueprint 管理数据库，需要单独确认：

```text
1. 数据库 plan
2. region
3. 备份策略
4. 迁移策略
5. 是否会影响现有生产数据
```
