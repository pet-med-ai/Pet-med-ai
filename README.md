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
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# 模拟诊断逻辑树结构（简化）
logic_tree = {
    "持续性瘙痒": {
        "是": {
            "question": "近期是否仍发现跳蚤、螨虫或耳垢增多？",
            "options": ["是", "否"],
            "followUp": {
                "是": "可能寄生虫感染（疥螨、耳螨）",
                "否": "持续瘙痒但无寄生虫证据，建议检查过敏或感染"
            }
        },
        "否": "优先考虑寄生虫性皮肤病（跳蚤/螨虫）"
    },
    "季节性瘙痒": {
        "是": "考虑季节性特应性皮炎",
        "否": {
            "question": "是否近期更换饮食或接触新环境？",
            "options": ["是", "否"],
            "followUp": {
                "是": "可能为食物或接触性过敏",
                "否": "建议进一步过敏原筛查"
            }
        }
    }
}

class PathInput(BaseModel):
    history: List[str]

@router.get("/init")
def get_root(chief: Optional[str] = "itching"):
    return {
        "question": "宠物是否存在以下情况？",
        "options": list(logic_tree.keys())
    }

@router.post("/next")
def get_next_step(data: PathInput):
    current = logic_tree
    for i, answer in enumerate(data.history):
        if isinstance(current, dict) and answer in current:
            current = current[answer]
        elif isinstance(current, dict) and "followUp" in current and answer in current["followUp"]:
            current = current["followUp"][answer]
        else:
            return {"error": "无效路径", "at": i, "value": answer}

    if isinstance(current, str):
        return {"diagnosis": current}
    elif isinstance(current, dict) and "question" in current:
        return {"question": current["question"], "options": current["options"]}
    else:
        return {"diagnosis": current}
