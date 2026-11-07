"""Bound login input before FastAPI's automatic OAuth form parsing.

Both browser FormData and OAuth URL-encoded clients remain supported. This
route class is deliberately limited to POST /auth/login; attachment, speech,
signup and other request bodies retain their existing contracts.
"""
import anyio
from fastapi import HTTPException, Request
from fastapi.routing import APIRoute
from starlette.requests import ClientDisconnect


MAX_LOGIN_BODY_BYTES = 16 * 1024
MAX_LOGIN_FIELDS = 6  # The six fields in OAuth2PasswordRequestForm.
MAX_LOGIN_FIELD_BYTES = 4 * 1024
LOGIN_BODY_TIMEOUT_SECONDS = 5
FORM_MEDIA_TYPES = {"application/x-www-form-urlencoded", "multipart/form-data"}


async def bounded_login_request(request: Request) -> Request:
    """Read a small body once, then expose only those bytes to the parser."""
    content_types = request.headers.getlist("content-type")
    if (len(content_types) != 1
            or content_types[0].split(";", 1)[0].strip().lower() not in FORM_MEDIA_TYPES):
        raise HTTPException(415, "Login requires form data")
    encodings = request.headers.getlist("content-encoding")
    if encodings and (len(encodings) != 1 or encodings[0].strip().lower() != "identity"):
        raise HTTPException(415, "Encoded login bodies are not supported")

    lengths = request.headers.getlist("content-length")
    declared_length = None
    if lengths:
        value = lengths[0].strip()
        if len(lengths) != 1 or not value or not value.isascii() or not value.isdecimal():
            raise HTTPException(400, "Invalid Content-Length")
        # Compare before int(), including excessive digit counts.
        value = value.lstrip("0") or "0"
        if len(value) > 5 or int(value) > MAX_LOGIN_BODY_BYTES:
            raise HTTPException(413, "Login form is too large")
        declared_length = int(value)

    body = bytearray()
    try:
        with anyio.fail_after(LOGIN_BODY_TIMEOUT_SECONDS):
            async for chunk in request.stream():
                if len(chunk) > MAX_LOGIN_BODY_BYTES - len(body):
                    raise HTTPException(413, "Login form is too large")
                body.extend(chunk)
    except TimeoutError:
        raise HTTPException(408, "Login body read timed out") from None
    except ClientDisconnect:
        raise HTTPException(400, "Incomplete login body") from None

    if declared_length is not None and declared_length != len(body):
        raise HTTPException(400, "Content-Length does not match login body")
    payload = bytes(body)
    del body
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": payload, "more_body": False}

    return Request(request.scope, receive=receive)


class LoginFormRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        if self.path != "/auth/login" or "POST" not in self.methods:
            return handler

        async def guarded(request: Request):
            bounded = await bounded_login_request(request)
            # This executes BEFORE the original handler, which otherwise parses
            # OAuth2PasswordRequestForm before calling route dependencies.
            # Starlette >=1.3.1 enforces both limits for both accepted encodings.
            try:
                form = await bounded.form(
                    max_files=0,
                    max_fields=MAX_LOGIN_FIELDS,
                    max_part_size=MAX_LOGIN_FIELD_BYTES,
                )
            except (ValueError, LookupError):
                raise HTTPException(400, "Invalid login form") from None
            try:
                return await handler(bounded)
            finally:
                await form.close()

        return guarded
