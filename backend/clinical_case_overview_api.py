"""Authenticated read-only saved visit inventory, synthetic environments only."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from auth_jwt import get_current_user
from case_attachment_store import AttachmentError
import clinical_case_overview as service

router = APIRouter(prefix='/api/cases', tags=['visit-overview'])


@router.get('/{case_id}/visit-overview')
def overview(case_id: int, include_followup_plan: bool = False, user=Depends(get_current_user)):
    headers = {'Cache-Control': 'private, no-store', 'X-PMAI-Writes-Database': 'false'}
    try:
        return JSONResponse(service.overview(user.id, case_id, include_followup_plan), headers=headers)
    except AttachmentError as exc:
        return JSONResponse({'detail': 'visit_overview_data_unreadable' if exc.status == 422 else exc.code},
                            status_code=409 if exc.status == 422 else exc.status, headers=headers)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return JSONResponse({'detail': 'visit_overview_data_unreadable'}, status_code=409, headers=headers)
    except (OSError, SQLAlchemyError):
        return JSONResponse({'detail': 'visit_overview_read_failed'}, status_code=503, headers=headers)
