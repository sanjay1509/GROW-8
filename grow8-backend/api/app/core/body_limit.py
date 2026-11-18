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
import re
from collections.abc import Sequence
from dataclasses import dataclass

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.exceptions import error_body


@dataclass(frozen=True)
class UploadLimit:
    """An upload route and how large its body may be. `path` must match the whole
    request path, so routes with ids are written as patterns (e.g. `.../\\d+/...`)."""

    method: str
    path: re.Pattern[str]
    max_bytes: int
    code: str  # the 413's error code
    message: str


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, limits: Sequence[UploadLimit]) -> None:
        self.app = app
        self.limits = tuple(limits)

    def _limit_for(self, scope: Scope) -> UploadLimit | None:
        if scope["type"] != "http":
            return None
        for limit in self.limits:
            if limit.method == scope["method"] and limit.path.fullmatch(scope["path"]):
                return limit
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = self._limit_for(scope)
        if limit is not None:
            declared = dict(scope["headers"]).get(b"content-length", b"")
            if not declared.isdigit():
                await self._reject(
                    send, 411, "LENGTH_REQUIRED", "Send the upload with a Content-Length header"
                )
                return
            if int(declared) > limit.max_bytes:
                await self._reject(send, 413, limit.code, limit.message)
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
