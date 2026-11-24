import logging
import re
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from grow8_common import db, messaging
from grow8_common.logging import configure_logging

from app.core.body_limit import BodySizeLimitMiddleware, UploadLimit
from app.core.config import get_api_settings
from app.core.exceptions import register_exception_handlers
from app.dependencies.request import REQUEST_ID_HEADER, register_request_id_middleware
from app.routers import (
    admin,
    applications,
    auth,
    contributors,
    creators,
    feedback,
    notifications,
    opportunities,
    reference,
    reports,
    submissions,
)
from app.services import submission_rules
from app.services.resume_service import MAX_BYTES as RESUME_MAX_BYTES

API_PREFIX = "/api/v1"

# Upload bodies are size-checked before FastAPI reads them (app/core/body_limit.py).
UPLOAD_LIMITS = (
    UploadLimit(
        method="POST",
        path=re.compile(re.escape(f"{API_PREFIX}/opportunities/") + r"[0-9]+/applications"),
        # Resume file plus multipart boundaries and application fields.
        max_bytes=RESUME_MAX_BYTES + 64 * 1024,
        code="RESUME_TOO_LARGE",
        message="A resume can be at most 10 MB",
    ),
    UploadLimit(
        method="PUT",
        path=re.compile(re.escape(f"{API_PREFIX}{contributors.RESUME_PATH}")),
        # the file plus room for the multipart boundaries and part headers
        max_bytes=RESUME_MAX_BYTES + 64 * 1024,
        code="RESUME_TOO_LARGE",
        message="A resume can be at most 10 MB",
    ),
    UploadLimit(
        method="POST",
        path=re.compile(
            re.escape(API_PREFIX)
            + submissions.SUBMISSION_PATH.replace("{application_id}", "[0-9]+")
        ),
        max_bytes=submission_rules.MAX_REQUEST_BYTES,
        code="ATTACHMENT_TOO_LARGE",
        message=(
            f"A submission can have at most {submission_rules.MAX_FILES} files "
            f"of {submission_rules.MAX_FILE_BYTES // (1024 * 1024)} MB each"
        ),
    ),
)

logger = logging.getLogger(__name__)


def _check(name: str, probe: Callable[[], None]) -> str:
    try:
        probe()
        return "ok"
    except Exception as exc:  # health must report, never raise
        logger.warning("health check %s failed: %s", name, type(exc).__name__)
        return "unavailable"


def _ping_rabbitmq() -> None:
    messaging.connect(socket_timeout=3).close()


def create_app() -> FastAPI:
    settings = get_api_settings()
    configure_logging(settings.log_level, service="api")
    _ = settings.effective_jwt_secret  # fail fast if production has no JWT_SECRET

    app = FastAPI(title="GROW8 API", version="0.1.0")
    # Added before CORS so CORS wraps it and its 411/413 responses stay readable.
    app.add_middleware(BodySizeLimitMiddleware, limits=UPLOAD_LIMITS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Content-Disposition carries a download's file name (resumes, attachments);
        # browsers hide it from cross-origin JavaScript unless it is exposed.
        expose_headers=[REQUEST_ID_HEADER, "Content-Disposition"],
    )
    register_request_id_middleware(app)
    register_exception_handlers(app)

    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(reference.router, prefix=API_PREFIX)
    app.include_router(opportunities.router, prefix=API_PREFIX)
    app.include_router(applications.router, prefix=API_PREFIX)
    app.include_router(contributors.router, prefix=API_PREFIX)
    app.include_router(creators.router, prefix=API_PREFIX)
    app.include_router(submissions.router, prefix=API_PREFIX)
    app.include_router(notifications.router, prefix=API_PREFIX)
    app.include_router(feedback.router, prefix=API_PREFIX)
    app.include_router(reports.router, prefix=API_PREFIX)
    app.include_router(admin.router, prefix=API_PREFIX)

    @app.get("/health", tags=["health"])
    def health() -> JSONResponse:
        checks = {"mysql": _check("mysql", db.ping), "rabbitmq": _check("rabbitmq", _ping_rabbitmq)}
        healthy = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={"status": "ok" if healthy else "degraded", "checks": checks},
        )

    return app


app = create_app()
