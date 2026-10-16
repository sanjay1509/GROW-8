from functools import lru_cache

from grow8_common.config import Settings


class ApiSettings(Settings):
    """Shared settings plus API-only ones."""

    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_api_settings() -> ApiSettings:
    return ApiSettings()
