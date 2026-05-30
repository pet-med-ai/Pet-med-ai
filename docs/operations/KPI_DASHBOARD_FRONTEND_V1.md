# KPI Dashboard 前端 V1

## 阶段定位

本阶段新增一个只读前端仪表盘页面 `/kpi`，连接现有 KPI 聚合 API：

```txt
GET /api/kpi/dashboard
```

本阶段不新增数据库表、不新增 Alembic migration、不写 KPI 数据、不引入图表依赖。

## 前端能力

```txt
- 时间范围筛选：近 7 天 / 近 30 天 / 自定义日期
- 顶部 2×3 KPI 卡：病例完整度、影像复拍、回访合规、平均结案时长、重复影像占比、QA 覆盖
- 病例字段完整度 panel
- 影像复拍 / 重复影像 panel
- 回访合规 panel
- QA 审计覆盖 panel
- 异常触发表 Top20
- 异常项可跳转病例详情 /cases/:id
```

## 技术边界

```txt
- 使用现有 axios api 实例和 JWT 拦截器
- 无新增 npm 依赖
- 无 ECharts / Ant Design
- 使用 inline style，后续 UI 重构时再迁入统一设计系统
```

## 验收

```bash
cd ~/Documents/Pet-med-ai
python3 scripts/validate_kpi_dashboard_frontend.py

cd frontend
npm run build
```

后端正常运行时手动访问：

```txt
http://127.0.0.1:5173/kpi
```

线上部署后访问：

```txt
https://pet-med-ai-frontend-static.onrender.com/kpi
```
