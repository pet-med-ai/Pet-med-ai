from fastapi import FastAPI
from .routers import vomiting

app = FastAPI(title="pet-med-ai backend")

app.include_router(vomiting.router)

# 可选：健康检查
@app.get("/healthz")
def healthz():
    return {"ok": True}
