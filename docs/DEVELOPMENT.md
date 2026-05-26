# Pet-Med-AI Development Guide

本文件是 Pet-Med-AI 的开发规范。目标是避免本地临时文件、补丁脚本、未追踪文件影响后续商业部署。

## 1. 基本原则

### 1.1 GitHub 是唯一正式代码源头

线上部署只应依赖：

```text
GitHub main 分支
Render 环境变量
Render PostgreSQL
```

VS Code 和 Mac 本地文件只是开发环境，不是生产资产。

### 1.2 一个阶段一个 commit

每个开发阶段都应该有明确目标，例如：

```text
feat: extend case basic information
feat: enhance consult history list
fix: improve auth error messages
```

不要把多个阶段混在一个 commit 里。

### 1.3 禁止 `git add .`

项目本地长期存在未追踪文件，必须精确 add：

```bash
git add backend/main.py frontend/src/App.jsx
```

不要执行：

```bash
git add .
```

## 2. 每次开发前

确认状态：

```bash
cd ~/Documents/Pet-med-ai
git status -sb
git log --oneline -5
```

确认当前分支：

```text
main
```

如果看到：

```text
## main...origin/main
```

说明本地和远端同步。

如果看到：

```text
[ahead 1]
```

先确认是否需要 push。

如果看到：

```text
[behind 1]
```

先拉取或确认远端变化后再继续。

## 3. 每次开发后

执行：

```bash
git diff --check
git status --short -- <target-files>
```

只 add 目标文件：

```bash
git add <target-files>
git commit -m "<message>"
git push origin main
```

推送后确认：

```bash
git log --oneline -5
git status --short -- <target-files>
```

## 4. Smoke test

本地后端启动后：

```bash
cd ~/Documents/Pet-med-ai
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
```

线上部署后：

```bash
cd ~/Documents/Pet-med-ai
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

必须看到：

```text
ALL PASS
```

## 5. 不应提交的文件

不要提交：

```text
app.db
backend/app.db
*.db
*.sqlite
.env
.env.*
frontend/.env.development
frontend/package-lock.json   # 除非明确进入依赖锁定阶段
node_modules/
dist/
__pycache__/
*.bak
*.save
.DS_Store
Downloads 里的 petmed_*_apply.py
```

如果需要保留长期脚本，应放到：

```text
scripts/
```

例如当前正式保留：

```text
scripts/smoke_petmed.sh
```

## 6. 推荐目录职责

```text
backend/                  FastAPI 后端正式代码
frontend/src/             React 前端正式代码
frontend/src/pages/       页面组件
scripts/                  正式开发/测试脚本
docs/                     部署和开发文档
knowledge-base/           医学知识库资料
```

## 7. 临时脚本处理

开发过程中生成的 apply 脚本，例如：

```text
petmed_case_basic_info_v1_apply.py
petmed_auth_ux_v1_apply.py
```

只属于阶段性补丁工具，不应进入正式仓库。已经沉淀成长期价值的脚本，才放入 `scripts/`。

## 8. 当前核心验收链路

每次改动核心功能后，至少确认：

```text
1. 登录 / 注册
2. 创建动态问诊
3. 提交追问
4. 保存问诊为病例
5. 读取病例详情
6. 从病例详情恢复来源问诊
7. 继续追问并更新绑定病例
8. 用户 B 不能读取用户 A 的问诊和病例
9. smoke_petmed.sh ALL PASS
```

## 9. 后续建议阶段

建议后续按优先级继续：

```text
1. .gitignore / docs 定期维护
2. Alembic 数据库迁移体系
3. 病例列表分页与服务端筛选
4. 问诊历史分页
5. 多症状医学问诊扩展
6. 文件上传 / 化验单 / 影像资料
7. 正式 CORS 白名单与生产安全配置
```
