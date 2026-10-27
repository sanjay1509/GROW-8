from collections.abc import Iterator

from grow8_common.db import get_sessionmaker
from sqlalchemy.orm import Session


def get_db() -> Iterator[Session]:
    """One session per request; anything not committed is rolled back on close."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
