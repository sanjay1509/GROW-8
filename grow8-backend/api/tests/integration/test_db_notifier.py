"""DbNotifier (grow8_common.notifications) against the seeded test database: what
contributor_service and creator_service store when they consume OPPORTUNITY_CREATED,
and that a redelivered event adds nothing. Seeded: Jordan Lee is user 6, Alex Chen
user 5; Sofia Martinez (user 4) owns organization 3."""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pymysql
import pytest
from grow8_common.db import get_sessionmaker
from grow8_common.models import Notification, NotificationType, UserAccount
from grow8_common.notifications import DbNotifier
from grow8_common.queries import find_active_owner, find_matching_contributors
from sqlalchemy import select, update
from sqlalchemy.orm import Session


@pytest.fixture
def session(seeded_db: pymysql.Connection) -> Iterator[Session]:
    with get_sessionmaker()() as s:
        yield s


def _deliver(session: Session, event_id: UUID, user_ids: list[int]) -> None:
    """One delivery of an event, as contributor_service handles it: notify, then commit."""
    notifier = DbNotifier(session, event_id, NotificationType.OPPORTUNITY_CREATED)
    for user_id in user_ids:
        notifier.notify(
            user_id, "New opportunity: Spring market", "Apply by 2026-11-20.", opportunity_id=15
        )
    session.commit()


def _stored(session: Session) -> list[Notification]:
    return list(session.scalars(select(Notification).order_by(Notification.user_id)))


def test_stores_one_unread_notification_per_user(session: Session) -> None:
    event_id = uuid4()
    _deliver(session, event_id, [5, 6])

    rows = _stored(session)
    assert [(n.user_id, n.event_id, n.opportunity_id, n.read_at) for n in rows] == [
        (5, str(event_id), 15, None),
        (6, str(event_id), 15, None),
    ]
    assert rows[0].notification_type is NotificationType.OPPORTUNITY_CREATED
    assert rows[0].title == "New opportunity: Spring market"


def test_redelivered_event_adds_nothing(session: Session) -> None:
    event_id = uuid4()
    _deliver(session, event_id, [6])
    _deliver(session, event_id, [6])
    assert len(_stored(session)) == 1


def test_a_new_event_for_the_same_user_is_a_new_notification(session: Session) -> None:
    _deliver(session, uuid4(), [6])
    _deliver(session, uuid4(), [6])
    assert len(_stored(session)) == 2


def test_nothing_is_stored_without_a_commit(session: Session) -> None:
    DbNotifier(session, uuid4(), NotificationType.OPPORTUNITY_CREATED).notify(6, "t", "m")
    session.rollback()
    assert _stored(session) == []


def test_text_longer_than_the_columns_is_shortened(session: Session) -> None:
    notifier = DbNotifier(session, uuid4(), NotificationType.OPPORTUNITY_CREATED)
    notifier.notify(6, "T" * 250, "M" * 600)
    session.commit()

    (row,) = _stored(session)
    assert (len(row.title), len(row.message)) == (200, 500)
    assert row.title.endswith("…")


def test_matched_contributors_for_draft_15_get_notified(session: Session) -> None:
    # The query and the notifier together, as the handler uses them.
    matches = find_matching_contributors(session, ["customer-service", "event-setup"])
    _deliver(session, uuid4(), [m.user_id for m in matches])
    assert [n.user_id for n in _stored(session)] == [6]


def test_the_same_event_notifies_contributors_and_the_creator_separately(
    session: Session,
) -> None:
    # Both services consume one OPPORTUNITY_CREATED: same event_id, different users.
    event_id = uuid4()
    _deliver(session, event_id, [6])
    owner_id = find_active_owner(session, 3)
    DbNotifier(session, event_id, NotificationType.OPPORTUNITY_PUBLISHED).notify(
        owner_id,
        "Your opportunity is live: Spring market",
        "Apply by 2026-11-20.",
        opportunity_id=15,
    )
    session.commit()

    assert [(n.user_id, n.notification_type) for n in _stored(session)] == [
        (4, NotificationType.OPPORTUNITY_PUBLISHED),
        (6, NotificationType.OPPORTUNITY_CREATED),
    ]


def test_find_active_owner(session: Session) -> None:
    assert find_active_owner(session, 3) == 4
    assert find_active_owner(session, 999) is None


def test_inactive_owner_is_not_found(session: Session) -> None:
    session.execute(update(UserAccount).where(UserAccount.user_id == 4).values(is_active=False))
    session.commit()
    assert find_active_owner(session, 3) is None
