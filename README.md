## Hi there 👋

<!--
**pet-med-ai/Pet-med-ai** is a ✨ _special_ ✨ repository because its `README.md` (this file) appears on your GitHub profile.

Here are some ideas to get you started:

- 🔭 I’m currently working on ...
- 🌱 I’m currently learning ...
- 👯 I’m looking to collaborate on ...
- 🤔 I’m looking for help with ...
- 💬 Ask me about ...
- 📫 How to reach me: ...
- 😄 Pronouns: ...
- ⚡ Fun fact: ...
-->
# 🐾 Pet AI Diagnosis Tool

一个基于 React + FastAPI 构建的宠物智能辅助诊断系统，适用于宠物医院、兽医师辅助问诊、AI 临床决策支持等场景。

## 📦 项目特性

- ✳️ 主诉逻辑树结构（以“呕吐”为例，持续扩展中）
- 🤖 React 前端递归问诊组件（医疗风界面）
- 🧠 后端 FastAPI 智能分析服务（可与 AI 模型对接）
- 🔌 一键部署支持（Docker + Makefile）
- 🔁 模块化设计，支持多主诉扩展

---

## 🧰 技术栈

- 前端：React + Vite + JSX + Tailwind（可选）
- 后端：Python + FastAPI + Pydantic
- 部署：Docker, docker-compose, Makefile

---

## 🚀 快速开始

### 使用 Docker 一键部署

```bash
make up        # 构建并启动前后端
make down      # 停止所有服务
make logs      # 查看日志
```

默认服务地址：

- 🔵 后端接口：`http://localhost:8000/api/diagnose`
- 🟢 前端页面：`http://localhost:5173`

---

## 🧪 本地开发调试

前端开发（端口 5173）：

```bash
cd frontend
npm install
npm run dev
```

后端开发（端口 8000）：

```bash
cd backend
uvicorn app.main:app --reload
```

---

## 📁 项目结构

```
pet-ai-diagnosis/
├── backend/              # FastAPI 后端
│   └── Dockerfile
├── frontend/             # React 前端
│   └── Dockerfile
├── logic-tree/           # 主诉逻辑结构定义（JSON / YAML）
├── docker-compose.yml
├── .env
├── Makefile
├── README.md
└── README-local.md
```

---

## 🧠 当前已实现主诉

- 🟩 呕吐（逻辑树、组件、API 完整）
- ⬜ 瘙痒掉毛（开发中）
- ⬜ 咳嗽（计划中）

---

## 📌 开源协议

本项目采用 MIT License 开源，欢迎 Fork 与参与贡献。

---

## 📬 联系作者

GitHub: [pet-med-ai](https://github.com/pet-med-ai)
