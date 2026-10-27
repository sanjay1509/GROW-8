"""Rules the notification table enforces (db/init/001_schema.sql), checked against the
seeded test database. Seeded: Jordan Lee is user 6, Alex Chen user 5; draft 15 has no
applications."""

from collections.abc import Iterator

import pymysql
import pytest
from grow8_common.db import get_sessionmaker
from grow8_common.models import Notification, NotificationType
from sqlalchemy import select
from sqlalchemy.orm import Session

EVENT_ID = "6f1c2a4e-8b1d-4c3e-9f20-1a2b3c4d5e6f"

INSERT = (
    "INSERT {ignore} INTO notification "
    "(user_id, event_id, notification_type, title, message, opportunity_id) "
    "VALUES (%s, %s, 'opportunity_created', 'New opportunity', 'Apply soon.', 15)"
)


def _count(conn: pymysql.Connection, event_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM notification WHERE event_id = %s", (event_id,))
        return cur.fetchone()[0]


@pytest.fixture
def session(seeded_db: pymysql.Connection) -> Iterator[Session]:
    with get_sessionmaker()() as s:
        yield s


def test_same_event_for_same_user_is_stored_once(seeded_db: pymysql.Connection) -> None:
    with seeded_db.cursor() as cur:
        cur.execute(INSERT.format(ignore=""), (6, EVENT_ID))
        # a redelivered event: the consumers' INSERT IGNORE skips it
        cur.execute(INSERT.format(ignore="IGNORE"), (6, EVENT_ID))
        assert cur.rowcount == 0
        with pytest.raises(pymysql.IntegrityError):
            cur.execute(INSERT.format(ignore=""), (6, EVENT_ID))
    assert _count(seeded_db, EVENT_ID) == 1


def test_same_event_notifies_each_user_once(seeded_db: pymysql.Connection) -> None:
    with seeded_db.cursor() as cur:
        cur.execute(INSERT.format(ignore=""), (5, EVENT_ID))
        cur.execute(INSERT.format(ignore=""), (6, EVENT_ID))
    assert _count(seeded_db, EVENT_ID) == 2


def test_deleting_the_opportunity_keeps_the_notification(seeded_db: pymysql.Connection) -> None:
    with seeded_db.cursor() as cur:
        cur.execute(INSERT.format(ignore=""), (6, EVENT_ID))
        cur.execute("DELETE FROM opportunity WHERE opportunity_id = 15")
        cur.execute(
            "SELECT opportunity_id, title FROM notification WHERE event_id = %s", (EVENT_ID,)
        )
        assert cur.fetchone() == (None, "New opportunity")


def test_orm_round_trip_starts_unread(session: Session) -> None:
    session.add(
        Notification(
            user_id=6,
            event_id=EVENT_ID,
            notification_type=NotificationType.OPPORTUNITY_CREATED,
            title="New opportunity",
            message="Apply soon.",
            opportunity_id=15,
        )
    )
    session.commit()

    stored = session.scalars(select(Notification).where(Notification.user_id == 6)).one()
    assert stored.notification_type is NotificationType.OPPORTUNITY_CREATED
    assert stored.read_at is None
    assert stored.created_at is not None
