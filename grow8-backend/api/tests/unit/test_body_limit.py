"""The upload size middleware: path patterns, per-route codes, 411 and 413."""

import re
from collections.abc import Iterator

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.body_limit import BodySizeLimitMiddleware, UploadLimit
from app.main import UPLOAD_LIMITS

LIMITS = (
    UploadLimit("PUT", re.compile(r"/resume"), 10, "RESUME_TOO_LARGE", "resume too large"),
    UploadLimit(
        "POST",
        re.compile(r"/applications/[0-9]+/submission"),
        20,
        "ATTACHMENT_TOO_LARGE",
        "submission too large",
    ),
)


async def _echo(request: Request) -> PlainTextResponse:
    return PlainTextResponse(f"read {len(await request.body())}")


@pytest.fixture
def client() -> TestClient:
    app = Starlette(
        routes=[
            Route("/resume", _echo, methods=["PUT"]),
            Route("/applications/{application_id}/submission", _echo, methods=["GET", "POST"]),
            Route("/applications/{application_id}/submission/extra", _echo, methods=["POST"]),
        ]
    )
    app.add_middleware(BodySizeLimitMiddleware, limits=LIMITS)
    return TestClient(app)


def _code(response) -> str:
    return response.json()["error"]["code"]


def test_a_body_within_the_limit_reaches_the_route(client: TestClient) -> None:
    response = client.post("/applications/7/submission", content=b"x" * 20)
    assert response.status_code == 200
    assert response.text == "read 20"


def test_a_route_with_an_id_gets_its_own_limit_and_code(client: TestClient) -> None:
    response = client.post("/applications/7/submission", content=b"x" * 21)
    assert response.status_code == 413
    assert _code(response) == "ATTACHMENT_TOO_LARGE"
    assert response.json()["error"]["message"] == "submission too large"


def test_each_route_keeps_its_own_code(client: TestClient) -> None:
    response = client.put("/resume", content=b"x" * 11)
    assert response.status_code == 413
    assert _code(response) == "RESUME_TOO_LARGE"


def test_an_upload_without_content_length_is_refused(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:  # a generator body is sent chunked, without a length
        yield b"x"

    response = client.post("/applications/7/submission", content=chunks())
    assert response.status_code == 411
    assert _code(response) == "LENGTH_REQUIRED"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/applications/7/submission"),  # other method
        ("POST", "/applications/7/submission/extra"),  # the pattern must match the whole path
    ],
)
def test_other_requests_are_not_limited(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path, content=b"x" * 100)
    assert response.status_code == 200


def test_app_limits_cover_the_resume_and_submission_routes() -> None:
    def limit_for(method: str, path: str) -> UploadLimit | None:
        return next(
            (lim for lim in UPLOAD_LIMITS if lim.method == method and lim.path.fullmatch(path)),
            None,
        )

    resume = limit_for("PUT", "/api/v1/contributors/me/resume")
    submission = limit_for("POST", "/api/v1/applications/42/submission")

    assert resume is not None and resume.code == "RESUME_TOO_LARGE"
    assert submission is not None and submission.code == "ATTACHMENT_TOO_LARGE"
    assert submission.max_bytes > 5 * 5 * 1024 * 1024
    assert limit_for("POST", "/api/v1/applications/abc/submission") is None
