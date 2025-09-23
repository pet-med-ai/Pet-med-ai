from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware   # ← 新增

from .routers import vomiting

app = FastAPI(title="pet-med-ai backend")

# 在创建 app 后立刻添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # 前端 dev 地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(vomiting.router)

# 健康检查
@app.get("/healthz")
def healthz():
    return {"ok": True}
