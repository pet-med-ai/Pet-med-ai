# backend/main.py
from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from db import SessionLocal, Base, engine
from models import Case
from sqlalchemy.orm import Session

# 如使用 Alembic 管表，可以不强制建表；本地/SQLite 可保留这一行兜底
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pet Med AI Backend (analyze & save)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 上线建议改成前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- 依赖：获取 DB 会话 --------------------
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------- 健康检查 --------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"ok": True}

# -------------------- I/O 模型 --------------------
class AnalyzeIn(BaseModel):
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None

class AnalyzeOut(BaseModel):
    analysis: str
    treatment: str
    prognosis: str

class CaseOut(BaseModel):
    id: int
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None
    analysis: Optional[str] = None
    treatment: Optional[str] = None
    prognosis: Optional[str] = None
    class Config:
        from_attributes = True
class CaseUpdate(BaseModel):
    # 全部为可选字段，按需更新
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
from fastapi import Response

@app.put("/cases/{case_id}", response_model=CaseOut)
def update_case(case_id: int, data: CaseUpdate, db: Session = Depends(get_db)):
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")

    # 仅更新传入的字段
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

# -------------------- 规则占位：生成三段文本 --------------------
def rule_infer(data: AnalyzeIn) -> AnalyzeOut:
    cc = (data.chief_complaint or "").lower()
    ex = (data.exam_findings or "").lower()
    ddx, plan = [], []
    px = "总体预后良好；需结合影像与实验室检查动态评估。"

    if "vomit" in cc or "呕吐" in cc:
        ddx += ["胃肠炎", "胃/肠异物", "胰腺炎"]
        plan += ["补液与电解质", "胃黏膜保护（硫糖铝）", "抗吐（马罗匹坦/昂丹司琼）", "必要时腹超与犬特异性脂肪酶 cPL"]
    if "diarrhea" in cc or "腹泻" in cc:
        ddx += ["应激性结肠炎", "寄生虫/贾第鞭毛虫", "食物反应/IBD"]
        plan += ["粪检寄生虫筛查", "益生菌", "短期肠道处方粮"]
    if "bilirubin" in ex or "胆红素" in ex:
        ddx.append("肝胆疾病/胆汁淤积")

    analysis = "可能的鉴别诊断：\n- " + "\n- ".join(dict.fromkeys(ddx)) if ddx else "需完善检查以明确病因。"
    treatment = "建议的下一步处理/治疗：\n- " + "\n- ".join(dict.fromkeys(plan)) if plan else "建议完善血常规/生化/电解质/影像检查后再定方案。"
    return AnalyzeOut(analysis=analysis, treatment=treatment, prognosis=px)

# -------------------- 关键接口：/analyze（分析并写库） --------------------
@app.post("/analyze", response_model=AnalyzeOut)
def analyze_and_save(data: AnalyzeIn, db: Session = Depends(get_db)):
    # 1) 规则/模型推理
    out = rule_infer(data)

    # 2) 写入数据库（models.Case 结构与你当前 models.py 对齐）
    rec = Case(
        chief_complaint=data.chief_complaint,
        history=data.history,
        exam_findings=data.exam_findings,
        analysis=out.analysis,
        treatment=out.treatment,
        prognosis=out.prognosis,
    )
    db.add(rec)
    db.commit()

    return out

# -------------------- 辅助：病例列表与详情 --------------------
@app.get("/cases", response_model=List[CaseOut])
def list_cases(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    q = db.query(Case).order_by(Case.id.desc()).limit(limit).offset(offset).all()
    return q

@app.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int, db: Session = Depends(get_db)):
    rec = db.get(Case, case_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Case not found")
    return rec
