"""JWT routes for explicit synthetic follow-up-plan review and atomic confirmation."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError
from auth_jwt import get_current_user
import clinical_followup_plans as service

router = APIRouter(prefix='/api/cases/{case_id}/followup-plan', tags=['followup-plan'])
PRIVATE = {'Cache-Control': 'private, no-store'}


class Review(BaseModel):
    model_config = {'extra': 'forbid', 'strict': True}
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    operation: Literal['create', 'correct', 'withdraw']
    plan_id: int | None = Field(default=None, gt=0, le=2**53 - 1)
    expected_plan_token: str = Field(default='', max_length=64)
    expected_case_token: str = Field(pattern=r'^[a-f0-9]{64}$')
    expected_state_token: str = Field(pattern=r'^[a-f0-9]{64}$')
    data: dict | None = None
    reason: str = Field(default='', max_length=500)


class Confirm(Review):
    preview_token: str = Field(pattern=r'^[a-f0-9]{64}$')
    reviewed: Literal[True]

    @field_validator('reviewed', mode='before')
    @classmethod
    def explicit_review(cls, value):
        if value is not True: raise ValueError('Explicit boolean confirmation required')
        return value


def invoke(function, *args):
    try:
        return JSONResponse(function(*args), headers=PRIVATE)
    except service.PlanError as error:
        raise HTTPException(error.status, error.code, headers=PRIVATE) from None
    except (SQLAlchemyError, OSError):
        raise HTTPException(503, 'followup_database_unavailable', headers=PRIVATE) from None


@router.get('')
def listing(case_id: int, user=Depends(get_current_user)):
    return invoke(service.listing, user.id, case_id)


@router.post('/preview')
def preview(case_id: int, body: Review, user=Depends(get_current_user)):
    return invoke(service.preview, user.id, case_id, body.model_dump())


@router.post('/confirm')
def confirm(case_id: int, body: Confirm, user=Depends(get_current_user)):
    if body.reviewed is not True: raise HTTPException(422, 'followup_review_required', headers=PRIVATE)
    return invoke(service.commit, user.id, case_id, body.model_dump(exclude={'preview_token', 'reviewed'}), body.preview_token)


@router.get('/requests/{request_id}')
def status(case_id: int, request_id: str, user=Depends(get_current_user)):
    return invoke(service.status, user.id, case_id, request_id)
