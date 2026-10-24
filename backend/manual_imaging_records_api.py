"""Authenticated, synthetic-only manual imaging workflow."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from auth_jwt import get_current_user
from case_attachment_store import AttachmentError
import manual_imaging_records as service

router = APIRouter(prefix='/api/cases/{case_id}/manual-imaging', tags=['manual-imaging'])


class Review(BaseModel):
    model_config = {'extra': 'forbid', 'strict': True}
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    attachment_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    expected_case_token: str = Field(pattern=r'^[a-f0-9]{64}$')
    operation: Literal['create', 'correct', 'withdraw']
    report_id: int | None = Field(default=None, gt=0)
    expected_report_token: str = Field(default='', max_length=64)
    data: dict | None = None
    reason: str = Field(default='', max_length=500)


class Confirm(Review):
    preview_token: str = Field(pattern=r'^[a-f0-9]{64}$')
    reviewed: Literal[True]


def invoke(fn, *args):
    try: return fn(*args)
    except AttachmentError as exc: raise HTTPException(exc.status, detail=exc.code) from None
    except (OSError, SQLAlchemyError): raise HTTPException(503, detail='manual_imaging_storage_or_database_unavailable') from None


@router.get('')
def listing(case_id: int, user=Depends(get_current_user)):
    return invoke(service.listing, user.id, case_id)


@router.post('/preview')
def preview(case_id: int, body: Review, user=Depends(get_current_user)):
    return invoke(service.preview, user.id, case_id, body.model_dump())


@router.post('/confirm')
def confirm(case_id: int, body: Confirm, user=Depends(get_current_user)):
    return invoke(service.commit, user.id, case_id, body.model_dump(exclude={'preview_token', 'reviewed'}), body.preview_token)


@router.get('/requests/{request_id}')
def status(case_id: int, request_id: str, user=Depends(get_current_user)):
    return invoke(service.status, user.id, case_id, request_id)
