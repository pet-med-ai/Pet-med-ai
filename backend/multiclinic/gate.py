"""Deny every unported backend route in the clinic read pilot, including aliases."""

from starlette.responses import JSONResponse
from .api import mode


async def scope_gate(request, call_next):
    selected = mode()
    if selected != "off":
        path = request.url.path
        allowed = path in ("/healthz", "/healthz/") or path.startswith("/api/v2/")
        if selected not in ("read_pilot", "treatment_pilot") or not allowed:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "This workflow is unavailable in clinic read pilot",
                    "code": "CLINIC_WORKFLOW_NOT_PORTED",
                },
                headers={"Cache-Control": "no-store"},
            )
    response = await call_next(request)
    if request.url.path.startswith("/api/v2/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response
