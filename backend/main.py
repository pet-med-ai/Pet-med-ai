# backend/main.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .db import Base, engine, get_session
from . import models, schemas, crud
from .auth import router as auth_router

app = FastAPI(title="Pet Med AI Backend")
# 定义请求数据结构
class CaseData(BaseModel):
    chief_complaint: str
    history: str
    exam_findings: str
# 创建表（生产建议 Alembic 迁移，这里为简化直接建表）
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 上线建议改成前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"ok": True}

# === Auth ===
app.include_router(auth_router)

# === 病例 CRUD ===
@app.post("/cases", response_model=schemas.CaseOut)
def create_case(
    data: schemas.CaseCreate,
    db: Session = Depends(get_session),
    # 简化：传查询参数 owner_id；后续用真实鉴权从 token 中取
    owner_id: int = 1
):
    case_obj = crud.create_case(db, owner_id=owner_id, data=data)
    return case_obj

@app.get("/cases", response_model=List[schemas.CaseOut])
def list_my_cases(
    db: Session = Depends(get_session),
    owner_id: int = 1,
    limit: int = 50, offset: int = 0
):
    return crud.list_cases(db, owner_id=owner_id, limit=limit, offset=offset)

@app.get("/cases/{case_id}", response_model=schemas.CaseOut)
def get_one_case(case_id: int, db: Session = Depends(get_session), owner_id: int = 1):
    case_obj = crud.get_case(db, case_id, owner_id)
    if not case_obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return case_obj

# === 病历分析（分析/治疗/预后 一体化）===
@app.post("/analyze", response_model=schemas.AnalyzeOut)
def analyze(data: schemas.AnalyzeIn):
    """
    先用规则/模板做占位，后续可换成你的 AI 推理逻辑。
    """
    # 极简示例规则：根据主诉/既往史/化验摘要拼出建议
    cc = (data.chief_complaint or "").lower()
    hx = (data.history or "").lower()
    ex = (data.exam_findings or "").lower()
    sp = (data.species or "dog").lower()

    ddx = []  # 鉴别诊断
    plan = [] # 处理方案
    px  = "总体预后良好（需结合影像/实验室结果进一步评估）。"

    if "vomit" in cc or "呕吐" in cc:
        ddx += ["胃肠炎", "胃异物/肠异物", "胰腺炎", "肝胆疾病/胆汁反流"]
        plan += ["补液+胃黏膜保护（如硫糖铝）", "抗吐（昂丹司琼/马罗匹坦）", "低脂易消化饮食", "必要时腹部超声/特异性脂肪酶"]
    if "diarrhea" in cc or "腹泻" in cc:
        ddx += ["应激性结肠炎", "寄生虫/贾第鞭毛虫", "食物反应/IBD"]
        plan += ["粪检+寄生虫筛查", "益生菌", "短期肠道处方粮"]
    if "itch" in cc or "瘙痒" in cc:
        ddx += ["特应性皮炎", "食物过敏", "疥螨/蠕形螨"]
        plan += ["皮肤刮片/寄生虫检查", "短期止痒（如阿扑吗啡/奥拉替尼/赛妥敏依照适应证）", "洗护+二线抗菌/抗真菌按培养结果"]

    # 结合化验关键词
    if "胆红素" in ex or "bilirubin" in ex:
        ddx.append("肝胆疾病/胆汁淤积")
    if "lipase" in ex or "脂肪酶" in ex:
        ddx.append("胰腺炎可能")

    # 最终文案
    analysis = "可能的鉴别诊断：\n- " + "\n- ".join(dict.fromkeys(ddx)) if ddx else "需进一步完善检查以明确病因。"
    treatment = "建议的下一步处理/治疗：\n- " + "\n- ".join(dict.fromkeys(plan)) if plan else "建议完善基础检查（血常规、生化、电解质、腹部影像）后再定方案。"
    prognosis = px

    return schemas.AnalyzeOut(analysis=analysis, treatment=treatment, prognosis=prognosis)

# === 可选：把分析结果写回病例 ===
@app.post("/cases/{case_id}/analyze", response_model=schemas.CaseOut)
def analyze_and_save(case_id: int, data: schemas.AnalyzeIn, db: Session = Depends(get_session), owner_id: int = 1):
    case_obj = crud.get_case(db, case_id, owner_id)
    if not case_obj:
        raise HTTPException(status_code=404, detail="Case not found")
    r = analyze(data)
    case_obj = crud.save_analysis(db, case_obj, r.analysis, r.treatment, r.prognosis)
    return case_obj
