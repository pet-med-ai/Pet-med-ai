# backend/main.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, Integer, DateTime, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session

# ------------------------------------------------------------------------------
# 数据库：Render 上建议在后端服务 Environment 设置 DATABASE_URL=postgresql://...
# 未设置时默认落地到本地 sqlite 文件 ./app.db
# ------------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./app.db"
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

# ------------------------------------------------------------------------------
# 表模型
# ------------------------------------------------------------------------------
class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # 如需用户体系，后续加 owner_id 外键
    patient_name: Mapped[str] = mapped_column(String(255), index=True)
    species: Mapped[str] = mapped_column(String(50), default="dog")          # dog/cat/other
    sex: Mapped[Optional[str]] = mapped_column(String(10), default=None)
    age_info: Mapped[Optional[str]] = mapped_column(String(50), default=None)

    chief_complaint: Mapped[str] = mapped_column(Text)                       # 主诉
    history: Mapped[Optional[str]] = mapped_column(Text, default=None)       # 既往史
    exam_findings: Mapped[Optional[str]] = mapped_column(Text, default=None) # 体检/化验摘要

    analysis: Mapped[Optional[str]] = mapped_column(Text, default=None)      # 分析结果
    treatment: Mapped[Optional[str]] = mapped_column(Text, default=None)     # 治疗建议
    prognosis: Mapped[Optional[str]] = mapped_column(Text, default=None)     # 预后

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# ------------------------------------------------------------------------------
# Pydantic 模型
# ------------------------------------------------------------------------------
class CaseBase(BaseModel):
    patient_name: str = Field(..., description="病例名/宠物名")
    species: str = Field("dog", description="物种：dog/cat/other")
    sex: Optional[str] = None
    age_info: Optional[str] = None
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    # 可选更新字段
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

class CaseOut(CaseBase):
    id: int
    analysis: Optional[str] = None
    treatment: Optional[str] = None
    prognosis: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class AnalyzeIn(BaseModel):
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None
    species: Optional[str] = "dog"
    age_info: Optional[str] = None

class AnalyzeOut(BaseModel):
    analysis: str
    treatment: str
    prognosis: str

# ------------------------------------------------------------------------------
# FastAPI & CORS
# ------------------------------------------------------------------------------
app = FastAPI(title="Pet Med AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 上线建议改成你的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 依赖
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 首次自动建表（生产建议 Alembic 迁移）
Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------------------------
# 健康检查
# ------------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"ok": True}

# ------------------------------------------------------------------------------
# /analyze 占位分析逻辑（后续可替换为你的 AI 推理）
# ------------------------------------------------------------------------------
@app.post("/analyze", response_model=AnalyzeOut)
def analyze(data: AnalyzeIn):
    cc = (data.chief_complaint or "").lower()
    hx = (data.history or "").lower()
    ex = (data.exam_findings or "").lower()

    ddx, plan = [], []
    px = "总体预后良好；需结合影像与实验室检查动态评估。"

    if "vomit" in cc or "呕吐" in cc:
        ddx += ["胃肠炎", "胃/肠异物", "胰腺炎"]
        plan += [
            "补液与电解质平衡",
            "胃黏膜保护（硫糖铝）",
            "抗吐（马罗匹坦/昂丹司琼）",
            "必要时腹部超声、犬特异性脂肪酶 cPL",
        ]
    if "diarrhea" in cc or "腹泻" in cc:
        ddx += ["应激性结肠炎", "寄生虫/贾第鞭毛虫", "食物反应/IBD"]
        plan += ["粪检+寄生虫筛查", "益生菌", "短期肠道处方粮"]
    if "itch" in cc or "瘙痒" in cc:
        ddx += ["特应性皮炎", "食物过敏", "疥/蠕形螨"]
        plan += ["皮肤刮片/寄生虫检查", "按培养结果抗菌/抗真菌", "依适应证短期止痒"]

    if "bilirubin" in ex or "胆红素" in ex:
        ddx.append("肝胆疾病/胆汁淤积")
    if "lipase" in ex or "脂肪酶" in ex:
        ddx.append("胰腺炎可能")

    analysis = "可能的鉴别诊断：\n- " + "\n- ".join(dict.fromkeys(ddx)) if ddx else "需进一步完善检查以明确病因。"
    treatment = "建议的下一步处理/治疗：\n- " + "\n- ".join(dict.fromkeys(plan)) if plan else "建议完善血常规/生化/电解质/影像后再定方案。"

    return AnalyzeOut(analysis=analysis, treatment=treatment, prognosis=px)

# ------------------------------------------------------------------------------
# 病例 CRUD
# ------------------------------------------------------------------------------
@app.post("/cases", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(data: CaseCreate, db: Session = Depends(get_db)):
    obj = Case(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.get("/cases", response_model=List[CaseOut])
def list_cases(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    stmt = select(Case).order_by(Case.id.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()

@app.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int, db: Session = Depends(get_db)):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return obj

@app.put("/cases/{case_id}", response_model=CaseOut)
def update_case(case_id: int, data: CaseUpdate, db: Session = Depends(get_db)):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    for k, v in updates.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.delete("/cases/{case_id}", status_code=204)
def delete_case(case_id: int, db: Session = Depends(get_db)):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(obj)
    db.commit()
    return Response(status_code=204)

# 分析并写回该病例
@app.post("/cases/{case_id}/analyze", response_model=CaseOut)
def analyze_and_save(case_id: int, data: AnalyzeIn, db: Session = Depends(get_db)):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    res = analyze(data)
    obj.analysis, obj.treatment, obj.prognosis = res.analysis, res.treatment, res.prognosis
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
