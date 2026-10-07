"""Authenticated, default-off read-only comparison endpoints."""
from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from auth_jwt import get_current_user
from case_attachment_store import AttachmentError
import clinical_lab_comparison as service

router = APIRouter(prefix='/api/cases', tags=['lab-comparison'])


def response(action):
    headers = {'Cache-Control': 'private, no-store', 'X-PMAI-Writes-Database': 'false'}
    try:
        return JSONResponse(action(), headers=headers)
    except AttachmentError as exc:
        unreadable = (exc.status == 422 and exc.code != 'lab_comparison_invalid_request') or exc.code == 'visit_overview_data_unreadable'
        return JSONResponse({'detail': 'lab_comparison_data_unreadable' if unreadable else exc.code},
                            status_code=409 if unreadable else exc.status, headers=headers)
    except (KeyError, TypeError, ValueError, AttributeError, ArithmeticError):
        return JSONResponse({'detail': 'lab_comparison_data_unreadable'}, status_code=409, headers=headers)
    except (OSError, SQLAlchemyError):
        return JSONResponse({'detail': 'lab_comparison_read_failed'}, status_code=503, headers=headers)


@router.get('/{case_id}/lab-comparison')
def read(case_id: int, user=Depends(get_current_user)):
    return response(lambda: service.read(user.id, case_id))


@router.post('/{case_id}/lab-comparison/preview')
def preview(case_id: int, body: dict = Body(...), user=Depends(get_current_user)):
    return response(lambda: service.preview(user.id, case_id, body))
