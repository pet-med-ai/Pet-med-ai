# backend/main.py
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # ← 新增：用于挂载静态目录
from pathlib import Path                    # ← 新增：定位 knowledge-base 目录
from typing import Optional, List, Dict, Any
import os
import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import inspect, text as sql_text
from pydantic import BaseModel, Field
from jose import jwt, JWTError

from db import SessionLocal, Base, engine
from models import Case, ConsultSession, User
from auth_jwt import router as auth_router, get_current_user
import auth_jwt as auth_jwt_mod
try:
    from backend.orchestrator import run_agent
except ModuleNotFoundError:
    from orchestrator import run_agent

try:
    from backend.species_context import normalize_species, species_context_line
except ModuleNotFoundError:
    from species_context import normalize_species, species_context_line


def _csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default

    values = []
    for item in raw.split(","):
        origin = item.strip().rstrip("/")
        if origin:
            values.append(origin)
    return values or default


def _is_production() -> bool:
    return (
        os.getenv("ENVIRONMENT", "").strip().lower() == "production"
        or os.getenv("RENDER", "").strip().lower() == "true"
    )


CORS_ORIGINS = _csv_env(
    "CORS_ORIGINS",
    [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://pet-med-ai-frontend-static.onrender.com",
    ],
)


# ---------- 初始化 ----------
Base.metadata.create_all(bind=engine)


def ensure_consult_session_columns():
    """
    create_all 不会给既有表补列；这里为线上 PostgreSQL / 本地 SQLite
    兜底补 owner_id 和 case_id，避免引入大迁移工程。
    """
    insp = inspect(engine)
    if not insp.has_table("consult_sessions"):
        return

    existing = {col["name"] for col in insp.get_columns("consult_sessions")}
    statements = []

    if "owner_id" not in existing:
        statements.append("ALTER TABLE consult_sessions ADD COLUMN owner_id INTEGER")
    if "case_id" not in existing:
        statements.append("ALTER TABLE consult_sessions ADD COLUMN case_id INTEGER")

    statements.extend([
        "CREATE INDEX IF NOT EXISTS ix_consult_sessions_owner_id ON consult_sessions (owner_id)",
        "CREATE INDEX IF NOT EXISTS ix_consult_sessions_case_id ON consult_sessions (case_id)",
    ])

    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(sql_text(stmt))


def ensure_case_extra_columns():
    # create_all 不会给既有 cases 表补列；这里为新增基础档案字段兜底补列。
    insp = inspect(engine)
    if not insp.has_table("cases"):
        return

    existing = {col["name"] for col in insp.get_columns("cases")}
    columns = {
        "breed": "VARCHAR(100)",
        "weight": "VARCHAR(50)",
        "coat_color": "VARCHAR(100)",
        "owner_name": "VARCHAR(100)",
        "owner_phone": "VARCHAR(50)",
    }

    statements = [
        f"ALTER TABLE cases ADD COLUMN {name} {ddl}"
        for name, ddl in columns.items()
        if name not in existing
    ]

    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(sql_text(stmt))


ensure_consult_session_columns()
ensure_case_extra_columns()

app = FastAPI(title="Pet Med AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
SECRET_KEY_FROM_ENV = os.getenv("SECRET_KEY", "").strip()
if SECRET_KEY_FROM_ENV:
    auth_jwt_mod.SECRET_KEY = SECRET_KEY_FROM_ENV
elif _is_production():
    raise RuntimeError("SECRET_KEY is required in production. Set it in Render backend Environment.")

# 统一挂载 Auth 路由（保持你原来逻辑，路径保持不变，如 /auth/login 等）
app.include_router(auth_router)


def _text_with_species(text: str, species: Optional[str] = None) -> str:
    base = (text or "").strip()
    species_value = (species or "").strip()
    if not species_value:
        return base
    lower = base.lower()
    if "物种：" in base or "物种:" in base or "species:" in lower or "species：" in lower:
        return base
    return f"物种：{species_value}\n{base}" if base else f"物种：{species_value}"


# DB 会话依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            auth_jwt_mod.SECRET_KEY,
            algorithms=[auth_jwt_mod.ALGORITHM],
        )
        email = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None

    return db.query(User).filter(User.email == email).first()


def assert_consult_session_access(session: ConsultSession, user, allow_unowned: bool = True):
    owner_id = getattr(session, "owner_id", None)
    if owner_id is None and allow_unowned:
        return

    if not user or getattr(user, "id", None) != owner_id:
        raise HTTPException(status_code=404, detail="Consult session not found")


def _consult_text_with_species(text: str, species: Optional[str] = None) -> str:
    base = (text or "").strip()
    normalized = normalize_species(species, default="")
    if normalized and "物种" not in base and "species" not in base.lower():
        return f"物种：{normalized}\n{base}".strip()
    return base


def _format_agent_result_for_case(result: Dict[str, Any]):
    if not isinstance(result, dict):
        return AnalyzeOut(
            analysis="需进一步完善检查以明确病因。",
            treatment="建议结合体征、影像与实验室检查进一步判断。",
            prognosis="需随访；高风险或持续恶化时立即就诊。",
        )

    species_context = result.get("species_context") if isinstance(result.get("species_context"), dict) else {}
    disease_data = result.get("diseases") if isinstance(result.get("diseases"), dict) else {}
    diseases = disease_data.get("diseases") or []
    checks = disease_data.get("checks") or []
    actions = result.get("actions") or disease_data.get("actions") or []
    tree_path = result.get("tree_path") or []
    risk_level = result.get("risk_level") or "未知"

    analysis_parts = [f"风险等级：{risk_level}"]
    if species_context:
        analysis_parts.append(species_context_line(species_context))
    if tree_path:
        analysis_parts.append("诊断路径：" + " > ".join(str(x) for x in tree_path if str(x).strip()))
    if diseases:
        analysis_parts.append("可能的鉴别诊断：\n" + _format_consult_list(diseases))
    if checks:
        analysis_parts.append("建议检查：\n" + _format_consult_list(checks))

    treatment = (
        "建议处理/治疗：\n" + _format_consult_list(actions)
        if actions
        else "建议结合体征、影像与实验室检查进一步判断。"
    )

    prognosis_parts = [f"风险提示：{risk_level}"]
    if species_context.get("is_exotic"):
        prognosis_parts.append("异宠病例需把具体物种、饲养环境、进食排泄和体重变化纳入判断；AI 结果仅作辅助分诊。")
    else:
        prognosis_parts.append("需结合临床检查复核；高风险或持续恶化时立即就诊。")

    return AnalyzeOut(
        analysis="\n\n".join(part for part in analysis_parts if part),
        treatment=treatment,
        prognosis="\n\n".join(prognosis_parts),
    )




# ---------- Pydantic IO ----------
class CaseCreate(BaseModel):
    patient_name: str
    species: Optional[str] = "dog"
    sex: Optional[str] = None
    age_info: Optional[str] = None
    breed: Optional[str] = None
    weight: Optional[str] = None
    coat_color: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None

class CaseUpdate(BaseModel):
    patient_name: Optional[str] = None
    species: Optional[str] = None
    sex: Optional[str] = None
    age_info: Optional[str] = None
    breed: Optional[str] = None
    weight: Optional[str] = None
    coat_color: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
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
    species: Optional[str] = None

class AIConsultAnswer(BaseModel):
    question: str
    answer: str

class AIConsultDynamicIn(BaseModel):
    text: str
    species: Optional[str] = None
    answers: Optional[List[AIConsultAnswer]] = None
    structured_intake_answers: Optional[Dict[str, Any]] = None

class AIConsultSessionCreateIn(BaseModel):
    text: str
    species: Optional[str] = None

class AIConsultSessionAnswerIn(BaseModel):
    answer: str
    question: Optional[str] = None
    structured_intake_answers: Optional[Dict[str, Any]] = None

class AIConsultSessionOut(BaseModel):
    session_id: str
    text: str
    answers: List[Dict[str, str]] = Field(default_factory=list)
    result: Dict[str, Any] = Field(default_factory=dict)
    case_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AIConsultSessionListItem(BaseModel):
    session_id: str
    text: str
    round: int = 1
    answered_count: int = 0
    risk_level: Optional[str] = None
    case_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AIConsultSessionListOut(BaseModel):
    items: List[AIConsultSessionListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20

class AIConsultSessionSaveCaseIn(BaseModel):
    patient_name: Optional[str] = None
    species: Optional[str] = "dog"
    sex: Optional[str] = None
    age_info: Optional[str] = None
    breed: Optional[str] = None
    weight: Optional[str] = None
    coat_color: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    exam_findings: Optional[str] = None
    structured_intake_answers: Optional[Dict[str, Any]] = None

class AIConsultSessionSaveCaseOut(BaseModel):
    case_id: int
    session_id: str
    message: str = "saved"

class AIConsultSessionDeleteOut(BaseModel):
    session_id: str
    message: str = "deleted"

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

def get_owned_case_or_404(
    db: Session,
    case_id: int,
    user,
    include_deleted: bool = False,
) -> Case:
    # 病例权限收口：当前用户只能访问自己的病例；无权限统一返回 404。
    query = db.query(Case).filter(Case.id == case_id, Case.owner_id == user.id)
    if supports_soft_delete() and not include_deleted:
        query = query.filter(Case.deleted_at.is_(None))

    obj = query.first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return obj

# 列表（支持 q / page / page_size；保持与前端解析一致：返回 {items,total}）
from sqlalchemy import or_, func


def _case_text_match(pattern: str):
    return or_(
        func.coalesce(Case.analysis, "").ilike(pattern),
        func.coalesce(Case.treatment, "").ilike(pattern),
        func.coalesce(Case.prognosis, "").ilike(pattern),
        func.coalesce(Case.history, "").ilike(pattern),
        func.coalesce(Case.exam_findings, "").ilike(pattern),
    )


def _case_risk_expr(risk: str):
    value = (risk or "all").strip().lower()
    high_expr = or_(
        _case_text_match("%高风险%"),
        _case_text_match("%风险等级：高%"),
        _case_text_match("%风险等级:高%"),
        _case_text_match("%风险提示：高%"),
        _case_text_match("%risk_level%high%"),
        _case_text_match("%high%"),
    )
    medium_expr = or_(
        _case_text_match("%中风险%"),
        _case_text_match("%风险等级：中%"),
        _case_text_match("%风险等级:中%"),
        _case_text_match("%风险提示：中%"),
        _case_text_match("%medium%"),
    )
    low_expr = or_(
        _case_text_match("%低风险%"),
        _case_text_match("%风险等级：低%"),
        _case_text_match("%风险等级:低%"),
        _case_text_match("%风险提示：低%"),
        _case_text_match("%low%"),
    )

    if value == "high":
        return high_expr
    if value == "medium":
        return medium_expr
    if value == "low":
        return low_expr
    if value == "unknown":
        return ~(or_(high_expr, medium_expr, low_expr))
    return None


def _case_source_expr(source: str):
    value = (source or "all").strip().lower()
    dynamic_expr = or_(
        func.coalesce(Case.history, "").ilike("%动态问诊%"),
        func.coalesce(Case.exam_findings, "").ilike("%原始会话%"),
        func.coalesce(Case.exam_findings, "").ilike("%动态问诊%"),
        func.coalesce(Case.prognosis, "").ilike("%后续追问%"),
    )

    if value == "dynamic":
        return dynamic_expr
    if value == "manual":
        return ~dynamic_expr
    return None

@api.get("/cases", response_model=dict)
def list_cases(
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    include_deleted: bool = False,
    risk: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    safe_page = max(1, page or 1)
    safe_page_size = max(1, min(page_size or 10, 200))

    query = db.query(Case).filter(Case.owner_id == user.id)
    if supports_soft_delete() and not include_deleted:
        query = query.filter(Case.deleted_at.is_(None))

    if q:
        key = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Case.patient_name.ilike(key),
                Case.species.ilike(key),
                Case.breed.ilike(key),
                Case.owner_name.ilike(key),
                Case.owner_phone.ilike(key),
                Case.chief_complaint.ilike(key),
            )
        )

    risk_expr = _case_risk_expr(risk or "all")
    if risk_expr is not None:
        query = query.filter(risk_expr)

    source_expr = _case_source_expr(source or "all")
    if source_expr is not None:
        query = query.filter(source_expr)

    total = query.with_entities(func.count(Case.id)).scalar() or 0
    items = (
        query.order_by(func.coalesce(Case.updated_at, Case.created_at).desc(), Case.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {"items": [CaseOut.model_validate(i).model_dump() for i in items], "total": total}

@api.post("/cases", response_model=CaseOut, status_code=201)
def create_case(
    data: CaseCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = Case(owner_id=user.id, **data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@api.get("/cases/{case_id}", response_model=CaseOut)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    return get_owned_case_or_404(db, case_id, user)

@api.put("/cases/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    data: CaseUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    obj = get_owned_case_or_404(db, case_id, user)
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
    obj = get_owned_case_or_404(db, case_id, user)

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

    obj = get_owned_case_or_404(db, case_id, user, include_deleted=True)
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
    obj = get_owned_case_or_404(db, case_id, user)

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
    text_for_ai = _text_with_species(data.text, data.species)
    result = run_agent(text_for_ai)
    if isinstance(result, dict):
        try:
            from backend.dynamic_consult import clean_consult_result
        except ModuleNotFoundError:
            from dynamic_consult import clean_consult_result
        return clean_consult_result(result, text_for_ai, [])
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
    answers_for_ai = _answers_with_structured_intake_context(answers, data.structured_intake_answers)

    text_for_ai = _text_with_species(data.text, data.species)
    result = run_dynamic_consult(text_for_ai, answers_for_ai)
    if isinstance(result, dict):
        if data.structured_intake_answers:
            result = _mark_structured_intake_context(result, True)
            dynamic = result.get("dynamic") if isinstance(result.get("dynamic"), dict) else {}
            dynamic["round"] = len(answers) + 1
            dynamic["answered_count"] = len(answers)
            result["dynamic"] = dynamic
    return result


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





def _structured_intake_answer_item(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    if not raw:
        return None

    template_key = str(raw.get("template_key") or "").strip().lower()
    category = str(raw.get("category") or "").strip().lower()

    if category == "companion" or template_key in ("dog", "cat"):
        try:
            from backend.companion_intake_templates import companion_intake_submission_to_answer
        except ModuleNotFoundError:
            from companion_intake_templates import companion_intake_submission_to_answer
        item = companion_intake_submission_to_answer(raw)
    else:
        try:
            from backend.exotic_intake_templates import structured_intake_submission_to_answer
        except ModuleNotFoundError:
            from exotic_intake_templates import structured_intake_submission_to_answer
        item = structured_intake_submission_to_answer(raw)

    if not isinstance(item, dict):
        return None

    question = str(item.get("question") or "").strip()
    answer = str(item.get("answer") or "").strip()
    if not question or not answer:
        return None

    return {
        "question": question,
        "answer": answer,
    }



def _format_structured_intake_history(raw: Optional[Dict[str, Any]]) -> str:
    if not raw or not isinstance(raw, dict):
        return ""

    template_key = str(raw.get("template_key") or "").strip().lower()
    category = str(raw.get("category") or "").strip().lower()

    if category == "companion" or template_key in ("dog", "cat"):
        try:
            from backend.companion_intake_templates import format_companion_intake_submission
        except ModuleNotFoundError:
            from companion_intake_templates import format_companion_intake_submission
        formatted = format_companion_intake_submission(raw)
        title = "犬猫结构化问诊记录"
    else:
        try:
            from backend.exotic_intake_templates import format_structured_intake_submission
        except ModuleNotFoundError:
            from exotic_intake_templates import format_structured_intake_submission
        formatted = format_structured_intake_submission(raw)
        title = "异宠结构化问诊记录"

    formatted = str(formatted or "").strip()
    if not formatted:
        return ""

    return f"【{title}】\n{formatted}"

def _answers_with_structured_intake_context(
    answers: List[Dict[str, str]],
    structured_intake_answers: Optional[Dict[str, Any]],
) -> List[Dict[str, str]]:
    # V2：结构化问诊答案只作为本轮 AI 上下文，不直接写入 session.answers。
    items = list(answers or [])
    structured_item = _structured_intake_answer_item(structured_intake_answers)
    if structured_item:
        items.append(structured_item)
    return items


def _mark_structured_intake_context(result: Dict[str, Any], used: bool) -> Dict[str, Any]:
    if not used or not isinstance(result, dict):
        return result

    dynamic = result.get("dynamic") if isinstance(result.get("dynamic"), dict) else {}
    dynamic["structured_intake_context"] = True
    result["dynamic"] = dynamic
    return result

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
        "case_id": getattr(session, "case_id", None),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def _consult_session_list_item(session: ConsultSession) -> Dict[str, Any]:
    result = session.result if isinstance(session.result, dict) else {}
    dynamic = result.get("dynamic") if isinstance(result.get("dynamic"), dict) else {}
    answers = session.answers if isinstance(session.answers, list) else []

    answered_count = dynamic.get("answered_count")
    if answered_count is None:
        answered_count = len(answers)

    round_no = dynamic.get("round")
    if round_no is None:
        round_no = int(answered_count or 0) + 1

    return {
        "session_id": session.session_uid,
        "text": session.text,
        "round": round_no,
        "answered_count": answered_count,
        "risk_level": result.get("risk_level"),
        "case_id": getattr(session, "case_id", None),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def _consult_session_risk_key(session: ConsultSession) -> str:
    result = session.result if isinstance(session.result, dict) else {}
    raw = str(result.get("risk_level") or "").strip()

    if "高" in raw or raw.lower() == "high":
        return "high"
    if "中" in raw or raw.lower() == "medium":
        return "medium"
    if "低" in raw or raw.lower() == "low":
        return "low"
    return "unknown"


def _consult_session_matches_filters(
    session: ConsultSession,
    risk: Optional[str],
    saved: Optional[str],
) -> bool:
    risk_value = (risk or "all").strip().lower()
    saved_value = (saved or "all").strip().lower()

    if risk_value not in ("all", "high", "medium", "low", "unknown"):
        risk_value = "all"
    if saved_value not in ("all", "saved", "unsaved"):
        saved_value = "all"

    if risk_value != "all" and _consult_session_risk_key(session) != risk_value:
        return False

    is_saved = bool(getattr(session, "case_id", None))
    if saved_value == "saved" and not is_saved:
        return False
    if saved_value == "unsaved" and is_saved:
        return False

    return True


@app.get("/ai/consult/sessions", response_model=AIConsultSessionListOut, tags=["ai"])
@app.get("/api/ai/consult/sessions", response_model=AIConsultSessionListOut, tags=["ai"])
def ai_consult_sessions_list(
    limit: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    risk: Optional[str] = None,
    saved: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    safe_page = max(1, page or 1)
    if limit is not None:
        safe_page_size = max(1, min(limit or 20, 100))
    else:
        safe_page_size = max(1, min(page_size or 20, 100))

    updated_expr = func.coalesce(ConsultSession.updated_at, ConsultSession.created_at)
    sessions = (
        db.query(ConsultSession)
        .filter(ConsultSession.owner_id == user.id)
        .order_by(updated_expr.desc(), ConsultSession.id.desc())
        .all()
    )

    filtered_sessions = [
        session
        for session in sessions
        if _consult_session_matches_filters(session, risk, saved)
    ]

    total = len(filtered_sessions)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    page_sessions = filtered_sessions[start:end]

    return {
        "items": [_consult_session_list_item(session) for session in page_sessions],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def _consult_item_label(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("name", "disease", "label", "title", "text", "question"):
            value = item.get(key)
            if value:
                return str(value).strip()
        return json.dumps(item, ensure_ascii=False)
    return str(item).strip()


def _format_consult_list(items: Any) -> str:
    if not items:
        return ""
    if isinstance(items, dict):
        if isinstance(items.get("questions"), list):
            items = items.get("questions")
        else:
            items = [items]
    if not isinstance(items, list):
        items = [items]

    lines = []
    for item in items:
        label = _consult_item_label(item)
        if label:
            lines.append(f"- {label}")
    return "\n".join(lines)


def _consult_session_to_case_fields(session: ConsultSession) -> Dict[str, str]:
    result = session.result if isinstance(session.result, dict) else {}
    answers = session.answers if isinstance(session.answers, list) else []

    disease_data = result.get("diseases") or {}
    if isinstance(disease_data, list):
        disease_list = disease_data
        checks = []
        disease_actions = []
    elif isinstance(disease_data, dict):
        disease_list = disease_data.get("diseases") or []
        checks = disease_data.get("checks") or []
        disease_actions = disease_data.get("actions") or []
    else:
        disease_list = []
        checks = []
        disease_actions = []

    actions = result.get("actions") or disease_actions or []
    next_questions = _extract_session_questions(result)
    tree_path = result.get("tree_path") or []
    risk_level = result.get("risk_level") or "未知"

    history_lines = ["【动态问诊追问记录】"]
    if answers:
        for idx, item in enumerate(answers, 1):
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            history_lines.append(f"{idx}. 问：{question or '未记录'}")
            history_lines.append(f"   答：{answer or '未记录'}")
    else:
        history_lines.append("尚未回答追问。")

    analysis_parts = [f"风险等级：{risk_level}"]
    if tree_path:
        analysis_parts.append("诊断路径：" + " > ".join(str(x) for x in tree_path if str(x).strip()))

    disease_text = _format_consult_list(disease_list)
    if disease_text:
        analysis_parts.append("可能的鉴别诊断：\n" + disease_text)

    checks_text = _format_consult_list(checks)
    if checks_text:
        analysis_parts.append("建议检查：\n" + checks_text)

    if not disease_text and not checks_text and result.get("analysis"):
        analysis_parts.append(str(result.get("analysis")))

    treatment_text = _format_consult_list(actions)
    if treatment_text:
        treatment = "建议处理/治疗：\n" + treatment_text
    else:
        treatment = str(result.get("treatment") or "建议结合体征、影像与实验室检查进一步判断。")

    prognosis_parts = [f"风险提示：{risk_level}"]
    next_questions_text = _format_consult_list(next_questions)
    if next_questions_text:
        prognosis_parts.append("后续追问/随访重点：\n" + next_questions_text)
    if result.get("prognosis"):
        prognosis_parts.append(str(result.get("prognosis")))

    return {
        "history": "\n".join(history_lines),
        "analysis": "\n\n".join(part for part in analysis_parts if part),
        "treatment": treatment,
        "prognosis": "\n\n".join(part for part in prognosis_parts if part),
    }


@app.delete("/api/ai/consult/session/{session_id}", response_model=AIConsultSessionDeleteOut, tags=["ai"])
def ai_consult_session_delete(
    session_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    session = db.query(ConsultSession).filter(ConsultSession.session_uid == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Consult session not found")
    assert_consult_session_access(session, user, allow_unowned=False)

    if getattr(session, "case_id", None):
        raise HTTPException(status_code=400, detail="Saved consult session cannot be deleted")

    db.delete(session)
    db.commit()

    return {
        "session_id": session_id,
        "message": "deleted",
    }


@app.post("/api/ai/consult/session/{session_id}/preview-case", response_model=dict, tags=["ai"])
def ai_consult_session_preview_case(
    session_id: str,
    data: AIConsultSessionSaveCaseIn,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """
    保存前预览：复用 save-case 的同一套 ConsultSession -> Case 字段转换逻辑，
    不写数据库，只返回即将写入病例的 history / analysis / treatment / prognosis。
    """
    session = db.query(ConsultSession).filter(ConsultSession.session_uid == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Consult session not found")
    assert_consult_session_access(session, user, allow_unowned=True)

    case_fields = _consult_session_to_case_fields(session)

    structured_intake_answers = getattr(data, "structured_intake_answers", None)
    structured_history = _format_structured_intake_history(structured_intake_answers)
    if structured_history:
        current_history = str(case_fields.get("history") or "").strip()
        case_fields["history"] = "\n\n".join(part for part in [current_history, structured_history] if part)

    patient_name = (data.patient_name or "").strip() or "未命名病例"
    species_value = (data.species or "dog").strip() or "dog"
    sex_value = (data.sex or "").strip() or None
    age_value = (data.age_info or "").strip() or None
    breed_value = (data.breed or "").strip() or None
    weight_value = (data.weight or "").strip() or None
    coat_value = (data.coat_color or "").strip() or None
    owner_name_value = (data.owner_name or "").strip() or None
    owner_phone_value = (data.owner_phone or "").strip() or None
    exam_value = (data.exam_findings or "").strip() or f"由动态问诊生成；原始会话：{session.session_uid}"

    return {
        "session_id": session.session_uid,
        "case_id": getattr(session, "case_id", None),
        "patient_name": patient_name[:255],
        "species": species_value[:50],
        "sex": sex_value[:10] if sex_value else None,
        "age_info": age_value[:50] if age_value else None,
        "breed": breed_value[:100] if breed_value else None,
        "weight": weight_value[:50] if weight_value else None,
        "coat_color": coat_value[:100] if coat_value else None,
        "owner_name": owner_name_value[:100] if owner_name_value else None,
        "owner_phone": owner_phone_value[:50] if owner_phone_value else None,
        "chief_complaint": session.text,
        "history": case_fields["history"],
        "exam_findings": exam_value,
        "analysis": case_fields["analysis"],
        "treatment": case_fields["treatment"],
        "prognosis": case_fields["prognosis"],
        "structured_history_appended": bool(structured_history),
        "message": "preview",
    }


@app.post("/api/ai/consult/session/{session_id}/save-case", response_model=AIConsultSessionSaveCaseOut, tags=["ai"])
def ai_consult_session_save_case(
    session_id: str,
    data: AIConsultSessionSaveCaseIn,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    session = db.query(ConsultSession).filter(ConsultSession.session_uid == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Consult session not found")
    assert_consult_session_access(session, user, allow_unowned=True)

    if getattr(session, "case_id", None):
        return {
            "case_id": session.case_id,
            "session_id": session.session_uid,
            "message": "already_saved",
        }

    if getattr(session, "owner_id", None) is None:
        session.owner_id = user.id

    case_fields = _consult_session_to_case_fields(session)

    structured_intake_answers = getattr(data, "structured_intake_answers", None)
    structured_history = _format_structured_intake_history(structured_intake_answers)
    if structured_history:
        current_history = str(case_fields.get("history") or "").strip()
        case_fields["history"] = "\n\n".join(part for part in [current_history, structured_history] if part)

    patient_name = (data.patient_name or "").strip() or "未命名病例"
    species_value = (data.species or "dog").strip() or "dog"
    sex_value = (data.sex or "").strip() or None
    age_value = (data.age_info or "").strip() or None
    breed_value = (data.breed or "").strip() or None
    weight_value = (data.weight or "").strip() or None
    coat_value = (data.coat_color or "").strip() or None
    owner_name_value = (data.owner_name or "").strip() or None
    owner_phone_value = (data.owner_phone or "").strip() or None
    exam_value = (data.exam_findings or "").strip() or f"由动态问诊生成；原始会话：{session.session_uid}"

    obj = Case(
        owner_id=getattr(user, "id", None),
        patient_name=patient_name[:255],
        species=species_value[:50],
        sex=sex_value[:10] if sex_value else None,
        age_info=age_value[:50] if age_value else None,
        breed=breed_value[:100] if breed_value else None,
        weight=weight_value[:50] if weight_value else None,
        coat_color=coat_value[:100] if coat_value else None,
        owner_name=owner_name_value[:100] if owner_name_value else None,
        owner_phone=owner_phone_value[:50] if owner_phone_value else None,
        chief_complaint=session.text,
        history=case_fields["history"],
        exam_findings=exam_value,
        analysis=case_fields["analysis"],
        treatment=case_fields["treatment"],
        prognosis=case_fields["prognosis"],
    )

    db.add(obj)
    db.flush()

    session.case_id = obj.id
    session.updated_at = datetime.utcnow()
    db.add(session)

    db.commit()
    db.refresh(obj)

    return {
        "case_id": obj.id,
        "session_id": session.session_uid,
        "message": "saved",
    }


@app.post("/api/ai/consult/session/{session_id}/update-case", response_model=AIConsultSessionSaveCaseOut, tags=["ai"])
def ai_consult_session_update_case(
    session_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    session = db.query(ConsultSession).filter(ConsultSession.session_uid == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Consult session not found")
    assert_consult_session_access(session, user, allow_unowned=False)

    if not getattr(session, "case_id", None):
        raise HTTPException(status_code=400, detail="Consult session is not bound to a case")

    obj = db.get(Case, session.case_id)
    if not obj or getattr(obj, "owner_id", None) != getattr(user, "id", None):
        raise HTTPException(status_code=404, detail="Case not found")

    case_fields = _consult_session_to_case_fields(session)

    obj.chief_complaint = session.text
    obj.history = case_fields["history"]
    obj.analysis = case_fields["analysis"]
    obj.treatment = case_fields["treatment"]
    obj.prognosis = case_fields["prognosis"]

    source_line = f"由动态问诊更新；原始会话：{session.session_uid}"
    current_exam = (obj.exam_findings or "").strip()
    if current_exam:
        if "原始会话" not in current_exam:
            obj.exam_findings = f"{current_exam}\n{source_line}"
    else:
        obj.exam_findings = source_line

    obj.updated_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()

    db.add(obj)
    db.add(session)
    db.commit()
    db.refresh(obj)

    return {
        "case_id": obj.id,
        "session_id": session.session_uid,
        "message": "updated",
    }


@app.post("/ai/consult/session", response_model=AIConsultSessionOut, tags=["ai"])
@app.post("/api/ai/consult/session", response_model=AIConsultSessionOut, tags=["ai"])
async def ai_consult_session_create(
    data: AIConsultSessionCreateIn,
    db: Session = Depends(get_db),
    user = Depends(get_optional_current_user),
):
    text = (data.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    text = _text_with_species(text, data.species)
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
        owner_id=getattr(user, "id", None) if user else None,
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
    user = Depends(get_optional_current_user),
):
    session = db.query(ConsultSession).filter(ConsultSession.session_uid == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Consult session not found")
    assert_consult_session_access(session, user, allow_unowned=True)

    return _consult_session_payload(session)


@app.post("/ai/consult/session/{session_id}/answer", response_model=AIConsultSessionOut, tags=["ai"])
@app.post("/api/ai/consult/session/{session_id}/answer", response_model=AIConsultSessionOut, tags=["ai"])
def ai_consult_session_answer(
    session_id: str,
    data: AIConsultSessionAnswerIn,
    db: Session = Depends(get_db),
    user = Depends(get_optional_current_user),
):
    session = db.query(ConsultSession).filter(ConsultSession.session_uid == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Consult session not found")
    assert_consult_session_access(session, user, allow_unowned=True)

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

    answers_for_ai = _answers_with_structured_intake_context(answers, data.structured_intake_answers)
    result = run_dynamic_consult(session.text, answers_for_ai)
    result = _stamp_session_dynamic(result, session.session_uid, len(answers))
    result = _mark_structured_intake_context(result, bool(data.structured_intake_answers))

    session.answers = answers
    session.result = result
    session.updated_at = datetime.utcnow()

    db.add(session)
    db.commit()
    db.refresh(session)

    return _consult_session_payload(session)

try:
    from backend.legacy_import_mock import router as legacy_import_mock_router
except ModuleNotFoundError:
    from legacy_import_mock import router as legacy_import_mock_router

# 将 /api 路由挂载到应用
app.include_router(api)
app.include_router(legacy_import_mock_router)

# 本地调试
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
