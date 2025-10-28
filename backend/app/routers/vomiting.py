from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from ..kb_loader import get_vomiting_payload, get_prompts_by_ids, KBLoadError

router = APIRouter(prefix="/api/v1", tags=["vomiting"])

from fastapi import APIRouter, HTTPException

@router.get("/kb/{symptom}/tree")
def api_kb_tree(symptom: str, locale: str = "zh", embed: str = "prompts"):
    if symptom != "vomiting":
        raise HTTPException(status_code=404, detail="symptom not available yet")
    from ..kb_loader import get_vomiting_payload
    return get_vomiting_payload(locale=locale, embed_prompts=(embed != "ids"))

@router.get("/vomiting/tree")
def api_vomiting_tree(locale: str = "zh", embed: Optional[str] = "prompts"):
    """
    GET /api/v1/vomiting/tree?locale=zh&embed=prompts
    - locale: zh | en
    - embed: 'prompts'（默认，返回展开问句） | 'ids'（仅返回 questions_ref）
    """
    try:
        return get_vomiting_payload(locale=locale, embed_prompts=(embed != "ids"))
    except KBLoadError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prompts")
def api_prompts(ids: List[str] = Query(..., description="重复 ids 参数，如 ?ids=Q1&ids=Q2"),
                locale: str = "zh"):
    try:
        return {"prompts": get_prompts_by_ids(ids, locale=locale)}
    except KBLoadError as e:
        raise HTTPException(status_code=500, detail=str(e))
