import logging
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from tenacity import before_sleep_log, retry, wait_exponential

from grow8_common.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=3600)


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
