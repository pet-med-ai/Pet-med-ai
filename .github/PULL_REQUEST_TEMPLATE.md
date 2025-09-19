# 📦 清理与优化项目根目录

## 📝 变更内容
- 移除项目根目录下的多余前端配置文件：
  - `index.html`
  - `package.json`
  - `vite.config.js`
- 确认前端唯一入口在 `frontend/` 文件夹内（`frontend/src/`，`frontend/public/`）
- 保留必要的根目录文件：
  - `README.md`（文档说明）
  - `render.yaml`（部署配置）
  - `.python-version`（后端环境版本）
- 保持 backend/ 与 frontend/ 的目录职责清晰，避免混淆

## 📂 优化后目录结构（核心部分）

