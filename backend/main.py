# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Pet Med AI Backend")

# 允许前端域名（先放开，线上可改成你的前端域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 上线建议改为 ["https://pet-med-ai-frontend-v6.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- 健康检查 ----------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"ok": True}


# --------- /analyze 数据模型 ----------
class AnalyzeIn(BaseModel):
    chief_complaint: str               # 主诉（必填）
    history: Optional[str] = None      # 既往史
    exam_findings: Optional[str] = None  # 体检/化验摘要
    species: Optional[str] = "dog"
    age_info: Optional[str] = None

class AnalyzeOut(BaseModel):
    analysis: str
    treatment: str
    prognosis: str


# --------- /analyze 业务接口 ----------
@app.post("/analyze", response_model=AnalyzeOut)
def analyze(data: AnalyzeIn):
    """
    简易规则占位：根据主诉/化验关键词给出三段文本。
    后续可替换为你的 AI 推理逻辑。
    """
    cc = (data.chief_complaint or "").lower()
    hx = (data.history or "").lower()
    ex = (data.exam_findings or "").lower()

    ddx = []   # 鉴别诊断
    plan = []  # 处理/治疗建议
    px  = "总体预后良好；需结合影像与实验室检查动态评估。"

    if "vomit" in cc or "呕吐" in cc:
        ddx += ["胃肠炎", "胃异物/肠异物", "胰腺炎"]
        plan += ["补液与电解质平衡", "胃黏膜保护（硫糖铝）", "抗吐（马罗匹坦/昂丹司琼）",
                 "必要时腹部超声、犬特异性脂肪酶 cPL"]

    if "diarrhea" in cc or "腹泻" in cc:
        ddx += ["应激性结肠炎", "寄生虫/贾第鞭毛虫", "食物反应/IBD"]
        plan += ["粪检+寄生虫筛查", "益生菌", "短期肠道处方粮"]

    if "itch" in cc or "瘙痒" in cc:
        ddx += ["特应性皮炎", "食物过敏", "疥螨/蠕形螨"]
        plan += ["皮肤刮片/寄生虫检查", "按培养结果抗菌/抗真菌", "短期止痒（依适应证）"]

    if "bilirubin" in ex or "胆红素" in ex:
        ddx.append("肝胆疾病/胆汁淤积")
    if "lipase" in ex or "脂肪酶" in ex:
        ddx.append("胰腺炎可能")

    analysis = "可能的鉴别诊断：\n- " + "\n- ".join(dict.fromkeys(ddx)) if ddx else "需进一步完善检查以明确病因。"
    treatment = "建议的下一步处理/治疗：\n- " + "\n- ".join(dict.fromkeys(plan)) if plan else "建议完善血常规/生化/电解质/影像检查后再定方案。"

    return AnalyzeOut(analysis=analysis, treatment=treatment, prognosis=px)
