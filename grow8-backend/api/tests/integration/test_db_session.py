"""The shared engine pins every connection to UTC, whatever the MySQL server's time
zone: the triggers compare the API's utcnow() values with NOW()."""

import pymysql
from grow8_common.db import get_engine
from sqlalchemy import text


def test_sessions_run_in_utc(seeded_db: pymysql.Connection) -> None:
    with get_engine().connect() as conn:
        zone, drift = conn.execute(
            text("SELECT @@session.time_zone, TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW())")
        ).one()

    assert zone == "+00:00"
    assert drift == 0
