import logging
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from tenacity import before_sleep_log, retry, wait_exponential

from grow8_common.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> Engine:
    # Every DATETIME is UTC: the code writes utcnow(), and the triggers and column
    # defaults use NOW()/CURRENT_TIMESTAMP, which follow the session time zone. Pin it
    # to UTC so a server with a local time zone can't make a fresh application look
    # "future dated" to trg_application_bi (or date defaults in local time).
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"init_command": "SET time_zone = '+00:00'"},
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def ping() -> None:
    """Raise if MySQL is unreachable."""
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def wait_for_db() -> None:
    """Block until MySQL answers, backing off between attempts."""
    ping()
