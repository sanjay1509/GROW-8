"""submission_repository against the seeded test database (ADR 0012).

The tests start from 002_seed.sql, which has no applications, so each test adds its
own: Alex Chen (user 5) and Jordan Lee (user 6) applying to opportunity 1 (open,
organization 1, limit 2).
"""

from collections.abc import Iterator
from decimal import Decimal

import pymysql
import pytest
from grow8_common.db import get_sessionmaker
from grow8_common.models import SubmissionAttachment, WorkSubmission
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.repositories import submission_repository
from app.repositories.db_errors import duplicate_key, trigger_rule


def _application(conn: pymysql.Connection, contributor_id: int, status: str) -> int:
    decided = None if status == "pending" else "2026-10-14 12:00:00"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO application (opportunity_id, contributor_id, status, submitted_at, "
            "decided_at) VALUES (1, %s, %s, '2026-10-14 10:00:00', %s)",
            (contributor_id, status, decided),
        )
        return cur.lastrowid


@pytest.fixture
def session(seeded_db: pymysql.Connection) -> Iterator[Session]:
    with get_sessionmaker()() as s:
        yield s


def _submission(application_id: int, *file_names: str) -> WorkSubmission:
    submission = WorkSubmission(
        application_id=application_id,
        description="Typed up 40 recipes.",
        hours_claimed=Decimal("6.50"),
    )
    for i, name in enumerate(file_names):
        submission.attachments.append(
            SubmissionAttachment(
                file_name=name,
                content_type="application/pdf",
                size_bytes=100 + i,
                storage_key=f"submissions/{i:032x}",
            )
        )
    return submission


def test_adds_a_submission_with_its_attachments(
    seeded_db: pymysql.Connection, session: Session
) -> None:
    application_id = _application(seeded_db, 5, "accepted")

    added = submission_repository.add(session, _submission(application_id, "a.pdf", "b.pdf"))
    session.commit()
    session.expunge_all()

    stored = submission_repository.get_for_application(session, application_id)
    assert stored is not None
    assert stored.submission_id == added.submission_id
    assert stored.hours_claimed == Decimal("6.50")
    assert [a.file_name for a in stored.attachments] == ["a.pdf", "b.pdf"]
    assert all(a.submission_id == stored.submission_id for a in stored.attachments)


def test_no_submission_yet_is_none(seeded_db: pymysql.Connection, session: Session) -> None:
    application_id = _application(seeded_db, 5, "accepted")
    assert submission_repository.get_for_application(session, application_id) is None


def test_an_attachment_is_found_only_through_its_own_submission(
    seeded_db: pymysql.Connection, session: Session
) -> None:
    alex = submission_repository.add(
        session, _submission(_application(seeded_db, 5, "accepted"), "a.pdf")
    )
    jordan = submission_repository.add(session, _submission(_application(seeded_db, 6, "accepted")))
    session.commit()
    attachment_id = alex.attachments[0].attachment_id

    found = submission_repository.get_attachment(session, alex.submission_id, attachment_id)
    assert found is not None and found.file_name == "a.pdf"
    assert (
        submission_repository.get_attachment(session, jordan.submission_id, attachment_id) is None
    )
    assert submission_repository.get_attachment(session, alex.submission_id, 999_999) is None


def test_the_trigger_refuses_work_for_an_application_that_is_not_accepted(
    seeded_db: pymysql.Connection, session: Session
) -> None:
    application_id = _application(seeded_db, 5, "pending")

    with pytest.raises(DBAPIError) as exc_info:
        submission_repository.add(session, _submission(application_id))

    assert trigger_rule(exc_info.value) == "submission_requires_accepted"


def test_a_second_submission_breaks_the_unique_key(
    seeded_db: pymysql.Connection, session: Session
) -> None:
    application_id = _application(seeded_db, 5, "accepted")
    submission_repository.add(session, _submission(application_id))
    session.commit()

    with pytest.raises(DBAPIError) as exc_info:
        submission_repository.add(session, _submission(application_id))

    assert duplicate_key(exc_info.value, "uq_work_submission_application")
