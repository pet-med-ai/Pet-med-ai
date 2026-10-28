"""Authenticated read-only saved visit inventory, synthetic environments only."""
from fastapi import APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from auth_jwt import get_current_user
from case_attachment_store import AttachmentError
import clinical_case_overview as service

PRIVATE = {'Cache-Control': 'private, no-store', 'X-PMAI-Writes-Database': 'false'}


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def handler(request):
            try:
                response = await original(request)
            except RequestValidationError as error:
                response = await request_validation_exception_handler(request, error)
            except HTTPException as error:
                response = await http_exception_handler(request, error)
            response.headers.update(PRIVATE)
            return response
        return handler


router = APIRouter(prefix='/api/cases', tags=['visit-overview'], route_class=PrivateRoute)


@router.get('/{case_id}/visit-overview')
def overview(case_id: int, include_followup_plan: bool = False,
             include_followup_contacts: bool = False, user=Depends(get_current_user)):
    headers = PRIVATE
    try:
        return JSONResponse(service.overview(user.id, case_id, include_followup_plan, include_followup_contacts), headers=headers)
    except AttachmentError as exc:
        if exc.code == 'visit_overview_invalid_parameters':
            return JSONResponse({'detail': exc.code}, status_code=422, headers=headers)
        return JSONResponse({'detail': 'visit_overview_data_unreadable' if exc.status == 422 else exc.code},
                            status_code=409 if exc.status == 422 else exc.status, headers=headers)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return JSONResponse({'detail': 'visit_overview_data_unreadable'}, status_code=409, headers=headers)
    except (OSError, SQLAlchemyError):
        return JSONResponse({'detail': 'visit_overview_read_failed'}, status_code=503, headers=headers)
