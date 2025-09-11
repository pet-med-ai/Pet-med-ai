# backend/routers/cases.py
# 完整可用：FastAPI 路由（CRUD + 软删除/还原 + 搜索分页 + 再分析）
# ---------------------------------------------------------------
# 如项目里已经有 db.py / models.py：
# 1) 用 from db import SessionLocal, Base, engine
# 2) 用 from models import Case  并删除本文件中 Case 模型定义
# ---------------------------------------------------------------

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, or_, func
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy import create_engine

# === 如果你已有 db.py，请改为：from db import SessionLocal, Base, engine ===
DATABASE_URL = "sqlite:///./app.db"  # 替换为你的真实数据库URL（如 Postgres）
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# === 如果你已有 models.Case，请删除下面这个模型定义 ===
class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String(255), index=True, nullable=False)
    species = Column(String(50), index=True, default="dog")  # dog/cat/other
    sex = Column(String(50), nullable=True)
    age_info = Column(String(50), nullable=True)

    chief_complaint = Column(Text, nullable=True)
    history = Column(Text, nullable=True)
    exam_findings = Column(Text, nullable=True)

    analysis = Column(Text, nullable=True)
    treatment = Column(Text, nullable=True)
    prognosis = Column(Text, nullable=True)

    # 可选：附件（如你的后端已有独立文件表，可自行调整）
    attachments = Column(JSON, nullable=True)

    # 软删除标记
    deleted_at = Column(DateTime, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# 首次运行可自动建表（如果你使用 Alembic，可移除这句）
Base.metadata.create_all(bind=engine)

# ---- Pydantic Schemas ----
class CaseCreate(BaseModel):
    patient_name: str
    species: str = Field(default="dog")
    sex: Optional[str] = None
    age_info: Optional[str] = None
    chief_complaint: Optional[str] = None
    history: Optional[str] = None
    exam_findings: Optional[str] = None
    # 可选
    attachments: Optional[list] = None


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
    attachments: Optional[list] = None


class CaseOut(BaseModel):
    id: int
    patient_name: str
    species: str
    sex: Optional[str]
    age_info: Optional[str]
    chief_complaint: Optional[str]
    history: Optional[str]
    exam_findings: Optional[str]
    analysis: Optional[str]
    treatment: Optional[str]
    prognosis: Optional[str]
    attachments: Optional[list]
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True


class AnalyzeIn(BaseModel):
    chief_complaint: Optional[str] = None
    history: Optional[str] = None
    exam_findings: Optional[str] = None
    species: Optional[str] = None
    age_info: Optional[str] = None


router = APIRouter(prefix="/api", tags=["cases"])


# ---- DB 依赖 ----
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- 工具函数 ----
def _apply_search(query, q: Optional[str]):
    if q:
        key = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Case.patient_name.ilike(key),
                Case.species.ilike(key),
                Case.chief_complaint.ilike(key),
            )
        )
    return query


# =========================
#          路由
# =========================

@router.get("/cases", response_model=dict)
def list_cases(
    q: Optional[str] = Query(default=None, description="关键词：病例名/物种/主诉"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=500),
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    base_q = db.query(Case)
    if not include_deleted:
        base_q = base_q.filter(Case.deleted_at.is_(None))

    base_q = _apply_search(base_q, q)

    total = base_q.with_entities(func.count(Case.id)).scalar() or 0
    items = (
        base_q.order_by(Case.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [CaseOut.model_validate(i).model_dump() for i in items], "total": total}


@router.post("/cases", response_model=CaseOut)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    obj = Case(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CaseOut.model_validate(obj)


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int, db: Session = Depends(get_db)):
    obj = db.query(Case).filter(Case.id == case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseOut.model_validate(obj)


@router.put("/cases/{case_id}", response_model=CaseOut)
def update_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)):
    obj = db.query(Case).filter(Case.id == case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CaseOut.model_validate(obj)


@router.delete("/cases/{case_id}", response_model=dict)
def soft_delete_case(case_id: int, db: Session = Depends(get_db)):
    obj = db.query(Case).filter(Case.id == case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    if obj.deleted_at:
        return {"ok": True, "message": "already deleted", "id": case_id}

    obj.deleted_at = datetime.utcnow()
    db.add(obj)
    db.commit()
    return {"ok": True, "id": case_id, "deleted_at": obj.deleted_at.isoformat()}


@router.post("/cases/{case_id}/restore", response_model=CaseOut)
def restore_case(case_id: int, db: Session = Depends(get_db)):
    obj = db.query(Case).filter(Case.id == case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    if obj.deleted_at is None:
        return CaseOut.model_validate(obj)

    obj.deleted_at = None
    obj.updated_at = datetime.utcnow()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CaseOut.model_validate(obj)


@router.post("/cases/{case_id}/analyze", response_model=CaseOut)
def reanalyze_case(case_id: int, payload: AnalyzeIn, db: Session = Depends(get_db)):
    """
    演示版：根据输入把 analysis/treatment/prognosis 简单写回。
    如你已有独立的 /api/analyze，可在这里调用你的分析服务。
    """
    obj = db.query(Case).filter(Case.id == case_id, Case.deleted_at.is_(None)).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")

    # 可选择同步这几个字段（保持前端看到的内容最新）
    if payload.chief_complaint is not None:
        obj.chief_complaint = payload.chief_complaint
    if payload.history is not None:
        obj.history = payload.history
    if payload.exam_findings is not None:
        obj.exam_findings = payload.exam_findings
    if payload.species is not None:
        obj.species = payload.species
    if payload.age_info is not None:
        obj.age_info = payload.age_info

    # 这里用非常朴素的“分析”占位，实际可替换为你的大模型/规则引擎结果
    obj.analysis = f"[Auto] 根据主诉『{obj.chief_complaint or '无'}』生成的分析示例。"
    obj.treatment = "示例治疗建议：对症支持、必要时完善影像/实验室检查。"
    obj.prognosis = "示例预后：需随访。"

    obj.updated_at = datetime.utcnow()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CaseOut.model_validate(obj)
