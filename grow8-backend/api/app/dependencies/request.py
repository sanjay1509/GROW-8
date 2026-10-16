from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


def register_request_id_middleware(app: FastAPI) -> None:
    """Reuse the caller's X-Request-ID (if sane) or generate one; echo it back.
    It becomes the correlation_id of any event the request publishes."""

    @app.middleware("http")
    async def request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        rid = incoming if 0 < len(incoming) <= 64 and incoming.isprintable() else uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = rid
        return response


def get_request_id(request: Request) -> str:
    return request.state.request_id


RequestId = Annotated[str, Depends(get_request_id)]
