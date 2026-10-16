from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration read from environment variables only (see .env.example)."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_database: str = "grow8"
    mysql_user: str = "grow8"
    mysql_password: str

    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_vhost: str = "/"
    rabbitmq_user: str = "grow8"
    rabbitmq_password: str
    rabbitmq_exchange: str = "grow8.events"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
