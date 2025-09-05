# backend/main.py
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

# ★ 导入统一使用 backend. 前缀
from backend.db import SessionLocal, Base, engine
from backend.models import Case
from auth_jwt import router as auth_router, get_current_user


# ---------------------- DB 初始化（Alembic 时可省） ----------------------
Base.metadata.create_all(bind=engine)

# ---------------------- FastAPI & CORS ----------------------
app = FastAPI(title="Pet Med AI Backend (JWT + Cases)")

app.add_middleware(
    CORSMiddleware,
    # 上线建议改成你的前端域名：["https://pet-med-ai-frontend-v6.onrender.com"]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------- DB 会话依赖 ----------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------- 健康检查 ----------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"ok": True}

# ---------------------- 注册 Auth 路由 & SECRET_KEY 覆盖 ----------------------
if os.getenv("SECRET_KEY"):
    # 覆盖 auth_jwt 内的 SECRET_KEY（从环境变量）
    import backend.auth_jwt as auth_jwt
    auth_jwt.SECRET_KEY = os.getenv("SECRET_KEY")

app.include_router(auth_router)

# ---------------------- Pydantic I/O 模型 ----------------------
class CaseCreate(BaseModel):
    patient_name: str
    species: Optional[str] = "dog"
    sex: Optional[str] = None
    age_info: Optional[str] = None
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None

class CaseUpdate(BaseModel):
    patient_name: Optional[str] = None
    species: Optional[str] = None
    sex: Optional[str] = None
    age_info: Optional[str] = None
    chief_complaint: Optional[str] = None
    history: Optional[str] = None
    exam_findings: Optional[str] = None
    analysis: Optional[str] = None
    treatment: Optional[str] = None
    prognosis: Optional[str] = None

class CaseOut(CaseCreate):
    id: int
    analysis: Optional[str] = None
    treatment: Optional[str] = None
    prognosis: Optional[str] = None
    class Config:
        from_attributes = True

class AnalyzeIn(BaseModel):
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None

class AnalyzeOut(BaseModel):
    analysis: str
    treatment: str
    prognosis: str

# ---------------------- /analyze（示例规则；如需保护可加 user 依赖） ----------------------
@app.post("/analyze", response_model=AnalyzeOut)
def analyze(data: AnalyzeIn):
    cc = (data.chief_complaint or "").lower()
    ex = (data.exam_findings or "").lower()
    ddx, plan = [], []
    prognosis = "总体预后良好；需结合影像与实验室检查。"

    if "vomit" in cc or "呕吐" in cc:
        ddx += ["胃肠炎", "胃/肠异物", "胰腺炎"]
        plan += ["补液", "抗吐药（马罗匹坦/昂丹司琼）", "腹部影像/犬特异性脂肪酶 cPL"]
    if "diarrhea" in cc or "腹泻" in cc:
        ddx += ["应激性结肠炎", "寄生虫/贾第鞭毛虫", "食物反应/IBD"]
        plan += ["粪检寄生虫筛查", "益生菌", "短期肠道处方粮"]
    if "bilirubin" in ex or "胆红素" in ex:
        ddx.append("肝胆疾病/胆汁淤积")

    analysis = "可能的鉴别诊断：\n- " + "\n- ".join(dict.fromkeys(ddx)) if ddx else "需进一步完善检查以明确病因。"
    treatment = "建议的处理/治疗：\n- " + "\n- ".join(dict.fromkeys(plan)) if plan else "建议完善血常规/生化/电解质/影像后再定方案。"
    return AnalyzeOut(analysis=analysis, treatment=treatment, prognosis=prognosis)

# ---------------------- 病例 CRUD（全部需要登录） ----------------------
@app.post("/cases", response_model=CaseOut, status_code=201)
def create_case(
    data: CaseCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),   # 需登录
):
    obj = Case(**data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.get("/cases", response_model=List[CaseOut])
def list_cases(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return db.query(Case).order_by(Case.id.desc()).all()

@app.get("/cases/{case_id}", response_model=CaseOut)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return obj

@app.put("/cases/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    data: CaseUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.delete("/cases/{case_id}", status_code=204)
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(obj); db.commit()
    return Response(status_code=204)
