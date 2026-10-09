"""Authenticated CW-B18 GET; all responses, including auth/parameter errors, private."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from auth_jwt import get_current_user
import clinical_followup_plan_queue as service
import clinical_followup_contact_queue as contact_service
from clinical_followup_plans import PlanError

PRIVATE = {'Cache-Control': 'private, no-store'}


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def handler(request):
            try:
                response = await original(request)
            except HTTPException as error:
                return JSONResponse({'detail': error.detail}, status_code=error.status_code,
                                    headers={**(error.headers or {}), **PRIVATE})
            response.headers.update(PRIVATE)
            return response
        return handler


router = APIRouter(prefix='/api/followup-plan-queue', tags=['followup-plan-queue'], route_class=PrivateRoute)


@router.get('')
def listing(request: Request, user=Depends(get_current_user)):
    try:
        pairs = request.query_params.multi_items()
        if len(pairs) != len(dict(pairs)): raise PlanError('followup_queue_invalid_parameters', 422)
        params = dict(pairs)
        target = contact_service if 'include_followup_contacts' in params else service
        return JSONResponse(target.listing(user.id, params), headers=PRIVATE)
    except PlanError as error:
        raise HTTPException(error.status, error.code, headers=PRIVATE) from None
    except (SQLAlchemyError, OSError):
        raise HTTPException(503, 'followup_queue_database_unavailable', headers=PRIVATE) from None
