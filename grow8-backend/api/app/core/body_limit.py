"""Reject oversized upload bodies before FastAPI reads them.

FastAPI parses a multipart body (spooling it to a temporary file) before the endpoint
or any dependency runs, so a size check there comes after the whole upload arrived.
This ASGI middleware checks Content-Length first, per (method, path):

- missing Content-Length -> 411 (browsers always send it for form uploads; a chunked
  body of unknown size could otherwise be arbitrarily large);
- Content-Length over the limit -> 413.

The server (uvicorn) refuses a body longer than its Content-Length, so the declared
length bounds what is read. The service still checks the actual file size.
"""

import json
from collections.abc import Mapping

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.exceptions import error_body


class BodySizeLimitMiddleware:
    def __init__(
        self, app: ASGIApp, limits: Mapping[tuple[str, str], int], code: str, message: str
    ) -> None:
        self.app = app
        self.limits = dict(limits)
        self.code = code
        self.message = message

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = (
            self.limits.get((scope["method"], scope["path"])) if scope["type"] == "http" else None
        )
        if limit is not None:
            declared = dict(scope["headers"]).get(b"content-length", b"")
            if not declared.isdigit():
                await self._reject(
                    send, 411, "LENGTH_REQUIRED", "Send the upload with a Content-Length header"
                )
                return
            if int(declared) > limit:
                await self._reject(send, 413, self.code, self.message)
                return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(send: Send, status: int, code: str, message: str) -> None:
        body = json.dumps(error_body(code, message)).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
