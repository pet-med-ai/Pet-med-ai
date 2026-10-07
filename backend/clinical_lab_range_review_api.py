"""Authenticated saved-result comparison, explicitly enabled synthetic environments only."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from auth_jwt import get_current_user
from case_attachment_store import AttachmentError
import clinical_lab_range_review as service

router = APIRouter(prefix='/api/cases', tags=['lab-range-review'])


@router.get('/{case_id}/lab-range-review')
def review(case_id: int, user=Depends(get_current_user)):
    headers = {'Cache-Control': 'private, no-store', 'X-PMAI-Writes-Database': 'false'}
    try:
        return JSONResponse(service.review(user.id, case_id), headers=headers)
    except AttachmentError as exc:
        unreadable = exc.status == 422 or exc.code == 'visit_overview_data_unreadable'
        return JSONResponse({'detail': 'lab_range_review_data_unreadable' if unreadable else exc.code},
                            status_code=409 if unreadable else exc.status, headers=headers)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return JSONResponse({'detail': 'lab_range_review_data_unreadable'}, status_code=409, headers=headers)
    except (OSError, SQLAlchemyError):
        return JSONResponse({'detail': 'lab_range_review_read_failed'}, status_code=503, headers=headers)
