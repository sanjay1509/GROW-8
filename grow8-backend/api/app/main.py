import logging
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from grow8_common import db, messaging
from grow8_common.logging import configure_logging

from app.core.config import get_api_settings
from app.core.exceptions import register_exception_handlers
from app.dependencies.request import REQUEST_ID_HEADER, register_request_id_middleware
from app.routers import auth

API_PREFIX = "/api/v1"

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    register_request_id_middleware(app)
    register_exception_handlers(app)

    app.include_router(auth.router, prefix=API_PREFIX)

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
