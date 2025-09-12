# backend/main.py
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import os

from sqlalchemy.orm import Session
from sqlalchemy import inspect
from pydantic import BaseModel

from db import SessionLocal, Base, engine
from models import Case
from auth_jwt import router as auth_router, get_current_user

# ---------- 初始化 ----------
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pet Med AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 生产建议收紧到你的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查（与 render.yaml 的 / 一致；也提供 /healthz 以备需要）
@app.get("/", tags=["health"])
def root():
    return {"ok": True}

@app.get("/healthz", tags=["health"])
def healthz():
    return {"ok": True}

# 覆盖 auth_jwt 的 SECRET_KEY（从环境变量）
if os.getenv("SECRET_KEY"):
    import auth_jwt as auth_jwt_mod
    auth_jwt_mod.SECRET_KEY = os.getenv("SECRET_KEY")

# 统一挂载 Auth 路由（保持你原来逻辑，路径保持不变，如 /auth/login 等）
app.include_router(auth_router)

# DB 会话依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Pydantic IO ----------
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
    species: Optional[str] = None
    age_info: Optional[str] = None

class AnalyzeOut(BaseModel):
    analysis: str
    treatment: str
    prognosis: str

# ---------- 统一前缀 /api ----------
api = APIRouter(prefix="/api", tags=["cases"])

# 即时分析（与前端 /api/analyze 对齐）
@api.post("/analyze", response_model=AnalyzeOut, tags=["analyze"])
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

# 工具：检测是否有软删字段
def supports_soft_delete() -> bool:
    insp = inspect(Case)
    return "deleted_at" in insp.columns

# 列表（支持 q / page / page_size；保持与前端解析一致：返回 {items,total}）
from sqlalchemy import or_, func

@api.get("/cases", response_model=dict)
def list_cases(
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    query = db.query(Case)
    if supports_soft_delete() and not include_deleted:
        query = query.filter(Case.deleted_at.is_(None))

    if q:
        key = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Case.patient_name.ilike(key),
                Case.species.ilike(key),
                Case.chief_complaint.ilike(key),
            )
        )

    total = query.with_entities(func.count(Case.id)).scalar() or 0
    items = (
        query.order_by(Case.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [CaseOut.model_validate(i).model_dump() for i in items], "total": total}

@api.post("/cases", response_model=CaseOut, status_code=201)
def create_case(
    data: CaseCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = Case(**data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@api.get("/cases/{case_id}", response_model=CaseOut)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return obj

@api.put("/cases/{case_id}", response_model=CaseOut)
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

# 删除：有 deleted_at 就软删；没有就硬删（与前端“撤销”兼容性说明见下）
@api.delete("/cases/{case_id}", status_code=204)
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")

    if supports_soft_delete():
        from datetime import datetime
        obj.deleted_at = datetime.utcnow()
        db.add(obj); db.commit()
        return Response(status_code=204)
    else:
        db.delete(obj); db.commit()
        return Response(status_code=204)

# 还原：只有当模型含 deleted_at 时才工作；否则返回 404
@api.post("/cases/{case_id}/restore", response_model=CaseOut)
def restore_case(
    case_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    if not supports_soft_delete():
        raise HTTPException(status_code=404, detail="Restore not supported (no deleted_at column)")

    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    obj.deleted_at = None
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

# 再分析并写回（与你前端 handleReAnalyze 调用完全一致）
@api.post("/cases/{case_id}/analyze", response_model=CaseOut)
def reanalyze_case(
    case_id: int,
    payload: AnalyzeIn,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")

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

    obj.analysis = f"[Auto] 根据主诉『{obj.chief_complaint or '无'}』生成的分析示例。"
    obj.treatment = "示例治疗建议：对症支持、必要时完善影像/实验室检查。"
    obj.prognosis = "示例预后：需随访。"

    db.add(obj); db.commit(); db.refresh(obj)
    return obj

# 将 /api 路由挂载到应用
app.include_router(api)

# 本地调试
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
