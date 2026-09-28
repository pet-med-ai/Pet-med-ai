"""Clinician-entered calendar-date plans. No schema changes or delivery jobs."""
from datetime import date, datetime, time
import hashlib
import hmac
import json
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import AuditLog, Case, FollowUp
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import AuditLog, Case, FollowUp

router = APIRouter(prefix="/api/cases", tags=["follow-up-plan"])
SOURCE = "manual-follow-up-m6"
EVENT = "follow_up_plan"
TOKEN = r"^[0-9a-f]{64}$"
REQUEST_ID = r"^[0-9a-f]{32}$"
MAX_PLANS = 200


class PlanPreviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["create", "replace", "cancel"]
    expected_state_token: str = Field(pattern=TOKEN, strict=True)
    due_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", strict=True)
    note: Optional[str] = Field(default=None, max_length=8000, strict=True)


class PlanConfirmIn(PlanPreviewIn):
    expected_preview_token: str = Field(pattern=TOKEN, strict=True)
    request_id: str = Field(pattern=REQUEST_ID, strict=True)


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def _log_id(case_id, user_id, request_id):
    return _hash([SOURCE, int(case_id), str(user_id), request_id])


def _owned_case(db, case_id, user, *, lock=False):
    query = db.query(Case).filter(Case.id == case_id, Case.owner_id == user.id,
                                 Case.deleted_at.is_(None))
    if lock:
        query = query.with_for_update()
    case = query.first()
    if case is None:
        raise HTTPException(404, "Case not found")
    return case


def _iso(value):
    return value.isoformat() if value is not None else None


def _row(row):
    return {"id": row.id, "case_id": row.case_id, "due_at_stored": _iso(row.due_date),
            "due_date": row.due_date.date().isoformat(), "note": row.note,
            "status": row.status, "done_at": _iso(row.done_at), "channel": row.channel,
            "owner": row.owner, "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}


def _rows(db, case):
    rows = db.query(FollowUp).filter(FollowUp.case_id == case.id).order_by(FollowUp.id).limit(MAX_PLANS + 1).all()
    if len(rows) > MAX_PLANS:
        raise HTTPException(409, "复查历史超过首版处理上限，请单独核对；没有修改历史记录。")
    return rows


def _state_token(case, rows):
    return _hash({"case_id": case.id, "owner_id": case.owner_id,
                  "case_updated_at": _iso(case.updated_at), "plans": [_row(row) for row in rows]})


def _valid_receipt(log, case, user):
    data = log.extra_data if isinstance(log.extra_data, dict) else {}
    receipt = data.get("receipt")
    if not isinstance(receipt, dict) or data.get("version") != 1:
        return None
    request_id = receipt.get("request_id")
    if (not isinstance(request_id, str) or len(request_id) != 32 or
            any(ch not in "0123456789abcdef" for ch in request_id) or
            log.log_id != _log_id(case.id, user.id, request_id) or
            log.source != SOURCE or log.event_type != EVENT or
            log.case_id != case.id or log.clinician_id != str(user.id) or
            receipt.get("case_id") != case.id or receipt.get("account_id") != str(user.id)):
        return None
    return receipt


def plan_state(db, case, user):
    rows = _rows(db, case)
    logs = db.query(AuditLog).filter(AuditLog.case_id == case.id, AuditLog.source == SOURCE,
                                    AuditLog.event_type == EVENT).limit(MAX_PLANS * 2 + 1).all()
    created, cancelled = {}, {}
    for log in logs:
        receipt = _valid_receipt(log, case, user)
        if receipt:
            for field, target in (("after", created), ("cancelled", cancelled)):
                item = receipt.get(field)
                if isinstance(item, dict) and isinstance(item.get("id"), int):
                    target[item["id"]] = item
    expected = {**created, **cancelled}
    items = []
    for row in rows:
        item = _row(row)
        # A bare legacy row or a client-supplied generic audit event cannot be
        # silently adopted as a clinician-reviewed M6 plan.
        managed = (expected.get(row.id) == item and row.id in created and
                   row.status in {"due", "cancelled"} and row.done_at is None and
                   row.due_date.time() == time.min and row.owner == str(user.id))
        items.append({**item, "managed": managed})
    due = [item for item in items if item["status"] == "due"]
    conflict = any(not item["managed"] for item in items) or len(due) > 1 or len(logs) > MAX_PLANS * 2
    return {"case_id": case.id, "account_id": str(user.id), "patient_name": case.patient_name,
            "state_token": _state_token(case, rows), "items": items,
            "current": due[0] if len(due) == 1 and not conflict else None,
            "can_write": not conflict,
            "conflict": "存在历史或无法解释的复查记录，请单独核对；当前不能修改或导出复查安排。" if conflict else "",
            "writes_database": False}


def _proposal(state, data):
    if not state["can_write"]:
        raise HTTPException(409, state["conflict"])
    if not hmac.compare_digest(data.expected_state_token, state["state_token"]):
        raise HTTPException(409, "病例或复查计划已变化，请重新读取并核对。")
    before = state["current"]
    if data.action == "create" and before is not None:
        raise HTTPException(409, "已有当前复查计划，请核对后更正。")
    if data.action != "create" and before is None:
        raise HTTPException(409, "没有可更正或撤销的当前复查计划。")
    proposed = None
    if data.action == "cancel":
        if data.due_date is not None or data.note is not None:
            raise HTTPException(422, "撤销请求不能附带新计划。")
    else:
        try:
            parsed = date.fromisoformat(data.due_date or "")
            assert parsed.isoformat() == data.due_date
        except (ValueError, AssertionError):
            raise HTTPException(422, "请填写有效的复查日期。")
        if not data.note or not data.note.strip():
            raise HTTPException(422, "请填写医生复查说明。")
        if any(not (ch in "\t\r\n" or "\x20" <= ch <= "\ud7ff" or "\ue000" <= ch <= "\ufffd" or
                    "\U00010000" <= ch <= "\U0010ffff") for ch in data.note):
            raise HTTPException(422, "复查说明含文书不支持的控制字符，请核对。")
        proposed = {"due_date": parsed.isoformat(), "note": data.note}
        if before and all(before[key] == value for key, value in proposed.items()):
            raise HTTPException(400, "没有需要保存的修改。")
    result = {"case_id": state["case_id"], "patient_name": state["patient_name"],
              "state_token": state["state_token"], "action": data.action,
              "before": before, "proposed": proposed, "writes_database": False}
    return {**result, "preview_token": _hash(result)}


def _unavailable(db):
    db.rollback()
    raise HTTPException(503, "复查计划服务暂不可用，请保留输入并核对结果；不能视为没有复查安排。")


@router.get("/{case_id}/follow-up", response_model=dict)
def get_plan_state(case_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return plan_state(db, _owned_case(db, case_id, user), user)
    except SQLAlchemyError:
        _unavailable(db)


@router.post("/{case_id}/follow-up/preview", response_model=dict)
def preview_plan(case_id: int, data: PlanPreviewIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return _proposal(plan_state(db, _owned_case(db, case_id, user), user), data)
    except SQLAlchemyError:
        _unavailable(db)


@router.get("/{case_id}/follow-up/receipts/{request_id}", response_model=dict)
def get_receipt(case_id: int, request_id: str = Path(pattern=REQUEST_ID),
                db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        case = _owned_case(db, case_id, user)
        log = db.get(AuditLog, _log_id(case.id, user.id, request_id))
        receipt = _valid_receipt(log, case, user) if log else None
        if log and receipt is None:
            raise HTTPException(409, "操作回执无法核实，请保留待核对请求。")
        return {"case_id": case.id, "request_id": request_id,
                "status": "committed" if receipt else "not_found", "receipt": receipt,
                "writes_database": False}
    except SQLAlchemyError:
        _unavailable(db)


@router.post("/{case_id}/follow-up/confirm", response_model=dict)
def confirm_plan(case_id: int, data: PlanConfirmIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        case = _owned_case(db, case_id, user, lock=True)
        log_id = _log_id(case.id, user.id, data.request_id)
        request_hash = _hash(data.model_dump())
        existing = db.get(AuditLog, log_id)
        if existing:
            receipt = _valid_receipt(existing, case, user)
            if receipt is None or existing.extra_data.get("request_hash") != request_hash:
                raise HTTPException(409, "请求标识已使用且内容不同，请核对原操作回执。")
            return {"receipt": receipt, "replayed": True, "writes_database": False}
        state = plan_state(db, case, user)
        preview = _proposal(state, data)
        if not hmac.compare_digest(preview["preview_token"], data.expected_preview_token):
            raise HTTPException(409, "本次内容与已核对计划不一致，请重新预览。")
        if len(state["items"]) >= MAX_PLANS and data.action != "cancel":
            raise HTTPException(409, "复查历史达到首版上限，请单独核对。")
        now = datetime.utcnow()
        previous = db.get(FollowUp, state["current"]["id"]) if state["current"] else None
        if previous:
            previous.status = "cancelled"
            previous.updated_at = now
        new = None
        if preview["proposed"]:
            # Calendar date stored at naive midnight, NOT an appointment instant
            # or UTC conversion. Historical timestamp rows are never rewritten.
            new = FollowUp(case_id=case.id, due_date=datetime.combine(date.fromisoformat(data.due_date), time.min),
                           note=data.note, status="due", owner=str(user.id), channel="clinic",
                           created_at=now, updated_at=now)
            db.add(new)
        db.flush()
        receipt = {"case_id": case.id, "account_id": str(user.id), "request_id": data.request_id,
                   "action": data.action, "before": preview["before"], "after": _row(new) if new else None,
                   "cancelled": _row(previous) if previous else None, "committed_at": now.isoformat(),
                   "before_state_token": state["state_token"], "after_state_token": _state_token(case, _rows(db, case)),
                   "request_hash": request_hash}
        db.add(AuditLog(log_id=log_id, request_id=data.request_id, clinician_id=str(user.id),
                        action_taken=data.action, case_id=case.id, event_type=EVENT, source=SOURCE,
                        extra_data={"version": 1, "request_hash": request_hash, "receipt": receipt}, created_at=now))
        db.commit()
        return {"receipt": receipt, "replayed": False, "writes_database": True}
    except SQLAlchemyError:
        _unavailable(db)


def document_follow_up(db, case, user):
    try:
        state = plan_state(db, case, user)
    except SQLAlchemyError:
        _unavailable(db)
    if state["conflict"]:
        raise HTTPException(409, state["conflict"])
    current = state["current"]
    if current:
        text = f"复查日期（北京时间日历日期）：{current['due_date']}\n医生复查说明：\n{current['note']}"
    elif state["items"]:
        text = "当前无有效复查安排；此前计划已撤销，请医生补充确认。"
    else:
        text = "未单独记录复查安排，请医生补充确认"
    return text.replace("\r\n", "\n").replace("\r", "\n"), state["state_token"]
