"""Authenticated synthetic-only attachment routes. No URL ingestion or public files."""
from typing import Literal
from urllib.parse import unquote, quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from auth_jwt import get_current_user
import case_attachment_service as service
from case_attachment_store import AttachmentError, MAX_FILE, ensure_enabled

router = APIRouter(prefix="/api/cases/{case_id}/attachments", tags=["case-attachments"])


class Review(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    attachment_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_case_token: str = Field(pattern=r"^[a-f0-9]{64}$")
    operation: Literal["confirm", "update", "withdraw"]
    metadata: dict = Field(default_factory=dict)
    reason: str = Field(default="", max_length=500)


class Confirm(Review):
    preview_token: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed: Literal[True]


def invoke(fn, *args, **kwargs):
    try:
        ensure_enabled()
        return fn(*args, **kwargs)
    except AttachmentError as exc:
        raise HTTPException(exc.status, detail=exc.code) from None
    except (OSError, SQLAlchemyError):
        raise HTTPException(503, detail="attachment_storage_or_database_unavailable") from None


@router.get("")
def listing(case_id: int, user=Depends(get_current_user)):
    return invoke(service.listing, user.id, case_id)


@router.post("/uploads/{request_id}")
async def upload(case_id: int, request_id: str, request: Request, user=Depends(get_current_user)):
    # Authorize before receiving bytes; authorize/version-check again before write.
    invoke(service.listing, user.id, case_id)
    invoke(service.request_id, request_id)
    size = request.headers.get("content-length")
    if size and (not size.isdigit() or int(size) > MAX_FILE): raise HTTPException(413, detail="attachment_too_large")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_FILE: raise HTTPException(413, detail="attachment_too_large")
        data.extend(chunk)
    try: name = unquote(request.headers.get("x-attachment-filename", ""), errors="strict")
    except UnicodeError: raise HTTPException(422, detail="invalid_filename") from None
    return invoke(service.upload, user.id, case_id, request_id, request.headers.get("x-case-token", ""),
                  bytes(data), name, request.headers.get("content-type", ""))


@router.get("/uploads/{request_id}")
def upload_status(case_id: int, request_id: str, user=Depends(get_current_user)):
    return invoke(service.upload_status, user.id, case_id, request_id)


@router.post("/uploads/{request_id}/cancel")
def cancel(case_id: int, request_id: str, user=Depends(get_current_user)):
    return invoke(service.cancel, user.id, case_id, request_id)


@router.post("/preview")
def preview(case_id: int, body: Review, user=Depends(get_current_user)):
    return invoke(service.preview, user.id, case_id, body.model_dump())


@router.post("/confirm")
def confirm(case_id: int, body: Confirm, user=Depends(get_current_user)):
    return invoke(service.commit, user.id, case_id, body.model_dump(exclude={"preview_token", "reviewed"}), body.preview_token)


@router.get("/requests/{request_id}")
def operation_status(case_id: int, request_id: str, user=Depends(get_current_user)):
    return invoke(service.operation_status, user.id, case_id, request_id)


@router.get("/{attachment_id}/content")
def content(case_id: int, attachment_id: str, request_id: str, preview: bool = False, user=Depends(get_current_user)):
    data, item = invoke(service.download, user.id, case_id, attachment_id, request_id, preview_image=preview)
    disposition = "inline" if preview else "attachment"
    return Response(data, media_type=item["mime"] if preview else "application/octet-stream", headers={
        "Content-Disposition": disposition + "; filename*=UTF-8''" + quote(item["name"], safe=""),
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox", "X-Attachment-SHA256": item["sha256"]})
