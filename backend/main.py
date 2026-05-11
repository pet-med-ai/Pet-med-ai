# backend/main.py
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # ← 新增：用于挂载静态目录
from pathlib import Path                    # ← 新增：定位 knowledge-base 目录
from typing import Optional, List, Dict, Any
import os
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import inspect
from pydantic import BaseModel, Field

from db import SessionLocal, Base, engine
from models import Case, ConsultSession
from auth_jwt import router as auth_router, get_current_user
try:
    from backend.orchestrator import run_agent
except ModuleNotFoundError:
    from orchestrator import run_agent
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

# === 新增：挂载知识库静态目录为 /kb（只读） =========================
# 目录定位：backend/main.py 的上一级是 backend，再上一级是仓库根目录
KB_DIR = Path(__file__).resolve().parents[1] / "knowledge-base"
app.mount("/kb", StaticFiles(directory=str(KB_DIR), html=False), name="kb")
# 现在可通过 /kb/tags.yaml、/kb/neurology/seizure.json 等路径直接访问
# ===============================================================

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

class AIConsultIn(BaseModel):
    text: str

class AIConsultAnswer(BaseModel):
    question: str
    answer: str

class AIConsultDynamicIn(BaseModel):
    text: str
    answers: Optional[List[AIConsultAnswer]] = None

class AIConsultSessionCreateIn(BaseModel):
    text: str

class AIConsultSessionAnswerIn(BaseModel):
    answer: str
    question: Optional[str] = None

class AIConsultSessionOut(BaseModel):
    session_id: str
    text: str
    answers: List[Dict[str, str]] = Field(default_factory=list)
    result: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# ---------- 统一前缀 /api ----------
api = APIRouter(prefix="/api", tags=["cases"])
# --- triage (hospital) ---
from app.triage_vomiting import triage_vomiting, VomitingTriageInput as _VTInput

class VomitingTriageIn(BaseModel):
    duration_hours: Optional[float] = None
    vomit_count_24h: Optional[int] = None
    energy_level: Optional[str] = None  # normal|reduced|severe
    blood: Optional[str] = None         # none|fresh|coffee_ground
    abd_distension: Optional[bool] = None
    unproductive_retching: Optional[bool] = None
    suspected_toxin: Optional[bool] = None
    urine: Optional[str] = None         # normal|oliguria|anuria|unknown
    black_stool: Optional[bool] = None
    locale: Optional[str] = "zh"

@api.post("/triage/vomiting", tags=["triage"])
def triage_vomiting_api(
    data: VomitingTriageIn,
    user = Depends(get_current_user),
):
    try:
        inp = _VTInput(
            duration_hours=data.duration_hours,
            vomit_count_24h=data.vomit_count_24h,
            energy_level=data.energy_level,
            blood=data.blood,
            abd_distension=data.abd_distension,
            unproductive_retching=data.unproductive_retching,
            suspected_toxin=data.suspected_toxin,
            urine=data.urine,
            black_stool=data.black_stool,
        )
        return triage_vomiting(inp, locale=data.locale or "zh")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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

    analysis = f"[Auto] 根据主诉『{obj.chief_complaint or '无'}』生成的分析示例。"
    treatment = "示例治疗建议：对症支持、必要时完善影像/实验室检查。"
    prognosis = "示例预后：需随访。"

    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.post("/ai/consult", tags=["ai"])
@app.post("/api/ai/consult", tags=["ai"])
async def ai_consult(data: AIConsultIn):
    result = run_agent(data.text)
    if isinstance(result, dict):
        try:
            from backend.dynamic_consult import clean_consult_result
        except ModuleNotFoundError:
            from dynamic_consult import clean_consult_result
        return clean_consult_result(result, data.text, [])
    return result


@app.post("/ai/consult/dynamic", tags=["ai"])
@app.post("/api/ai/consult/dynamic", tags=["ai"])
async def ai_consult_dynamic(data: AIConsultDynamicIn):
    try:
        from backend.dynamic_consult import run_dynamic_consult
    except ModuleNotFoundError:
        from dynamic_consult import run_dynamic_consult

    answers = [
        item.model_dump()
        for item in (data.answers or [])
    ]

    return run_dynamic_consult(data.text, answers)


def _extract_session_questions(result: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(result, dict):
        return []

    raw = result.get("next_questions") or {}

    if isinstance(raw, list):
        return [str(q).strip() for q in raw if str(q).strip()]

    if isinstance(raw, dict):
        questions = raw.get("questions") or []
        if isinstance(questions, list):
            return [str(q).strip() for q in questions if str(q).strip()]

    return []


def _first_session_question(result: Optional[Dict[str, Any]]) -> str:
    questions = _extract_session_questions(result)
    return questions[0] if questions else ""


def _stamp_session_dynamic(
    result: Dict[str, Any],
    session_id: str,
    answered_count: int,
) -> Dict[str, Any]:
    dynamic = result.get("dynamic") if isinstance(result.get("dynamic"), dict) else {}
    dynamic.update({
        "mode": "dynamic_consult_session_v1",
        "session_id": session_id,
        "round": answered_count + 1,
        "answered_count": answered_count,
        "persisted": True,
    })
    result["dynamic"] = dynamic
    return result


def _consult_session_payload(session: ConsultSession) -> Dict[str, Any]:
    return {
        "session_id": session.session_uid,
        "text": session.text,
        "answers": session.answers or [],
        "result": session.result or {},
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@app.post("/ai/consult/session", response_model=AIConsultSessionOut, tags=["ai"])
@app.post("/api/ai/consult/session", response_model=AIConsultSessionOut, tags=["ai"])
async def ai_consult_session_create(
    data: AIConsultSessionCreateIn,
    db: Session = Depends(get_db),
):
    text = (data.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    result = run_agent(text)
    if not isinstance(result, dict):
        result = {
            "risk_level": "中",
            "tree_path": [],
            "diseases": {},
            "next_questions": {
                "questions": ["请补充目前精神、食欲、呕吐次数和腹部状态。"]
            },
            "actions": ["建议结合体征与实验室检查进一步判断。"],
        }

    try:
        from backend.dynamic_consult import clean_consult_result
    except ModuleNotFoundError:
        from dynamic_consult import clean_consult_result

    result = clean_consult_result(result, text, [])
    session_id = uuid4().hex
    result = _stamp_session_dynamic(result, session_id, 0)

    session = ConsultSession(
        session_uid=session_id,
        text=text,
        answers=[],
        result=result,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return _consult_session_payload(session)


@app.get("/ai/consult/session/{session_id}", response_model=AIConsultSessionOut, tags=["ai"])
@app.get("/api/ai/consult/session/{session_id}", response_model=AIConsultSessionOut, tags=["ai"])
def ai_consult_session_get(
    session_id: str,
    db: Session = Depends(get_db),
):
    session = db.query(ConsultSession).filter(ConsultSession.session_uid == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Consult session not found")

    return _consult_session_payload(session)


@app.post("/ai/consult/session/{session_id}/answer", response_model=AIConsultSessionOut, tags=["ai"])
@app.post("/api/ai/consult/session/{session_id}/answer", response_model=AIConsultSessionOut, tags=["ai"])
def ai_consult_session_answer(
    session_id: str,
    data: AIConsultSessionAnswerIn,
    db: Session = Depends(get_db),
):
    session = db.query(ConsultSession).filter(ConsultSession.session_uid == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Consult session not found")

    answer = (data.answer or "").strip()
    if not answer:
        raise HTTPException(status_code=400, detail="answer is required")

    question = (data.question or "").strip() or _first_session_question(session.result)
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    answers = list(session.answers or [])
    answers.append({
        "question": question,
        "answer": answer,
    })

    try:
        from backend.dynamic_consult import run_dynamic_consult
    except ModuleNotFoundError:
        from dynamic_consult import run_dynamic_consult

    result = run_dynamic_consult(session.text, answers)
    result = _stamp_session_dynamic(result, session.session_uid, len(answers))

    session.answers = answers
    session.result = result
    session.updated_at = datetime.utcnow()

    db.add(session)
    db.commit()
    db.refresh(session)

    return _consult_session_payload(session)

# 将 /api 路由挂载到应用
app.include_router(api)

# 本地调试
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
