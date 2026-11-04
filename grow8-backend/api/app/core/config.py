from functools import lru_cache

from grow8_common.config import Settings

# Only used when JWT_SECRET is empty outside production, so a fresh checkout runs as-is.
_DEV_JWT_SECRET = "grow8-dev-only-insecure-jwt-secret-do-not-use-in-production"

JWT_ALGORITHM = "HS256"


class ApiSettings(Settings):
    """Shared settings plus API-only ones."""

    cors_origins: str = ""
    jwt_secret: str = ""
    access_token_expire_minutes: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_jwt_secret(self) -> str:
        if self.jwt_secret:
            return self.jwt_secret
        if self.app_env == "production":
            raise RuntimeError("JWT_SECRET must be set when APP_ENV=production")
        return _DEV_JWT_SECRET


@lru_cache
def get_api_settings() -> ApiSettings:
    return ApiSettings()
