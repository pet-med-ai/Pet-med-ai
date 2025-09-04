# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from typing import List, Optional

from db import SessionLocal, Base, engine
from models import Case
from auth_jwt import router as auth_router, get_current_user
from pydantic import BaseModel

# ----------------------------------------------------------------------
# 初始化 DB
# ----------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pet Med AI Backend with JWT")

# ----------------------------------------------------------------------
# CORS
# ----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 上线时改为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# DB 依赖
# ----------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------------------------------------
# 健康检查
# ----------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"ok": True}

# ----------------------------------------------------------------------
# 引入 Auth 路由
# ----------------------------------------------------------------------
# 覆盖 SECRET_KEY（从 Render 环境变量）
if os.getenv("SECRET_KEY"):
    import auth_jwt
    auth_jwt.SECRET_KEY = os.getenv("SECRET_KEY")

app.include_router(auth_router)

# ----------------------------------------------------------------------
# Pydantic 模型
# ----------------------------------------------------------------------
class CaseCreate(BaseModel):
    patient_name: str
    species: Optional[str] = "dog"
    sex: Optional[str] = None
    age_info: Optional[str] = None
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None

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

# ----------------------------------------------------------------------
# 简单规则占位：/analyze（可选加保护）
# ----------------------------------------------------------------------
@app.post("/analyze", response_model=AnalyzeOut)
def analyze(data: AnalyzeIn):
    cc = (data.chief_complaint or "").lower()
    ddx, plan = [], []
    prognosis = "总体预后良好；需结合影像与实验室检查。"

    if "vomit" in cc or "呕吐" in cc:
        ddx += ["胃肠炎", "胃异物", "胰腺炎"]
        plan += ["补液", "抗吐药", "腹部影像"]

    analysis = "可能的鉴别诊断：\n- " + "\n- ".join(ddx) if ddx else "需进一步检查。"
    treatment = "建议治疗：\n- " + "\n- ".join(plan) if plan else "建议完善检查。"

    return AnalyzeOut(analysis=analysis, treatment=treatment, prognosis=prognosis)

# ----------------------------------------------------------------------
# 病例 CRUD（需登录）
# ----------------------------------------------------------------------
@app.post("/cases", response_model=CaseOut, status_code=201)
def create_case(data: CaseCreate,
                db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    obj = Case(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.get("/cases", response_model=List[CaseOut])
def list_cases(db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    return db.query(Case).order_by(Case.id.desc()).all()

@app.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int,
             db: Session = Depends(get_db),
             user=Depends(get_current_user)):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return obj

@app.delete("/cases/{case_id}", status_code=204)
def delete_case(case_id: int,
                db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(obj)
    db.commit()
    return Response(status_code=204)
