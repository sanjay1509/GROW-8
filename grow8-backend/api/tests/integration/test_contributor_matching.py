"""Queries contributor_service runs when it consumes OPPORTUNITY_CREATED
(grow8_common.queries), checked against the seeded test database.

Seeded contributor skills: Alex (5) spreadsheets, data-cleaning, web-basics;
Jordan (6) customer-service, event-setup, food-handling; Sam (7) social-media,
graphic-design, photography."""

from collections.abc import Iterator

import pymysql
import pytest
from grow8_common.db import get_sessionmaker
from grow8_common.queries import find_matching_contributors, is_opportunity_open
from sqlalchemy.orm import Session


@pytest.fixture
def session(seeded_db: pymysql.Connection) -> Iterator[Session]:
    with get_sessionmaker()() as s:
        yield s


def test_matches_contributors_by_skill_best_match_first(session: Session) -> None:
    # Draft 15 (spring market) asks for customer-service and event-setup.
    matches = find_matching_contributors(session, ["customer-service", "event-setup"])
    assert [(m.user_id, m.matched_skill_codes) for m in matches] == [
        (6, ["customer-service", "event-setup"])
    ]


def test_more_matched_skills_rank_first(session: Session) -> None:
    matches = find_matching_contributors(session, ["spreadsheets", "data-cleaning", "photography"])
    assert [(m.user_id, len(m.matched_skill_codes)) for m in matches] == [(5, 2), (7, 1)]


def test_no_skills_listed_means_every_active_contributor(session: Session) -> None:
    assert [m.user_id for m in find_matching_contributors(session, [])] == [5, 6, 7]


def test_unknown_skill_matches_nobody(session: Session) -> None:
    assert find_matching_contributors(session, ["underwater-welding"]) == []


def test_inactive_contributors_are_not_notified(
    session: Session, seeded_db: pymysql.Connection
) -> None:
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE user_account SET is_active = FALSE WHERE user_id = 6")
    assert find_matching_contributors(session, ["event-setup"]) == []


def test_is_opportunity_open(session: Session) -> None:
    assert is_opportunity_open(session, 1) is True  # open
    assert is_opportunity_open(session, 11) is False  # closed
    assert is_opportunity_open(session, 15) is False  # still a draft
    assert is_opportunity_open(session, 9999) is False  # does not exist
