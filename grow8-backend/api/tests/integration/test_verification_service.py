"""verification_service and the submission reads against the seeded test database
(ADR 0013).

Seeded: opportunity 1 is open and belongs to organization 1, owned by Priya Nair
(user 2); Daniel Okafor (user 3) owns organization 2. Alex Chen is user 5, Jordan Lee
user 6. 002_seed.sql has no applications, so each test inserts an accepted application
and its submission (6.50 hours claimed) directly.
"""

import threading
from collections.abc import Iterator
from decimal import Decimal

import pymysql
import pytest
from grow8_common.db import get_sessionmaker
from grow8_common.events import EventType, WorkRejectedPayload, WorkVerifiedPayload
from grow8_common.models import ReviewDecision, UserAccount, WorkVerification
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.repositories import submission_repository
from app.schemas.submission import ReceivedSubmissionParams, VerificationCreate
from app.services import submission_service, verification_service
from app.services.verification_rules import SubmissionStatus
from tests.fakes import FakePublisher

APPROVE = VerificationCreate(decision="approved", verified_hours=Decimal("6"), comment="Thanks!")
REJECT = VerificationCreate(decision="rejected", comment="Half the recipes are missing.")


def _submission(
    conn: pymysql.Connection,
    contributor_id: int = 5,
    submitted_at: str = "2026-10-15 10:00:00",
    opportunity_id: int = 1,
) -> int:
    """An accepted application with submitted work; returns the submission id."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO application (opportunity_id, contributor_id, status, submitted_at, "
            "decided_at) VALUES (%s, %s, 'accepted', '2026-10-14 10:00:00', "
            "'2026-10-14 12:00:00')",
            (opportunity_id, contributor_id),
        )
        cur.execute(
            "INSERT INTO work_submission (application_id, description, hours_claimed, "
            "submitted_at) VALUES (%s, 'Typed up 40 recipes.', 6.50, %s)",
            (cur.lastrowid, submitted_at),
        )
        return cur.lastrowid


@pytest.fixture(autouse=True)
def _room_for_three(seeded_db: pymysql.Connection) -> None:
    """Some tests accept three applicants to opportunity 1."""
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET applicant_limit = 3 WHERE opportunity_id = 1")


@pytest.fixture
def session(seeded_db: pymysql.Connection) -> Iterator[Session]:
    with get_sessionmaker()() as s:
        yield s


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture
def submission_id(seeded_db: pymysql.Connection) -> int:
    return _submission(seeded_db)


def _user(session: Session, user_id: int) -> UserAccount:
    user = session.get(UserAccount, user_id)
    assert user is not None
    return user


def _verify(
    session: Session,
    publisher: FakePublisher,
    submission_id: int,
    data: VerificationCreate = APPROVE,
    creator_id: int = 2,
):
    return verification_service.verify(
        session, _user(session, creator_id), submission_id, data, publisher, "req-1"
    )


def _code(exc_info: pytest.ExceptionInfo[AppError]) -> tuple[int, str]:
    return exc_info.value.status_code, exc_info.value.code


def _count_verifications(session: Session) -> int:
    session.rollback()  # end the transaction so the count sees committed rows
    return session.scalar(select(func.count(WorkVerification.verification_id))) or 0


# ---------------------------------------------------------------------------
# Verifying
# ---------------------------------------------------------------------------


def test_approving_records_the_hours_and_publishes_work_verified(
    session, publisher, submission_id
) -> None:
    result = _verify(session, publisher, submission_id)

    assert result.status == SubmissionStatus.APPROVED
    assert result.verification is not None
    assert result.verification.decision == ReviewDecision.APPROVED
    assert result.verification.verified_hours == Decimal("6.00")
    assert result.verification.comment == "Thanks!"

    [event] = publisher.events
    assert event.event_type == EventType.WORK_VERIFIED
    assert event.correlation_id == "req-1"
    payload = WorkVerifiedPayload.model_validate(event.payload)
    row = session.scalars(select(WorkVerification)).one()
    assert payload == WorkVerifiedPayload(
        verification_id=row.verification_id,
        submission_id=submission_id,
        application_id=result.application_id,
        opportunity_id=1,
        organization_id=1,
        opportunity_title="Digitize paper recipe archive",
        contributor_id=5,
        verified_hours=Decimal("6.00"),
    )
    assert row.verified_by_user_id == 2


def test_rejecting_records_the_comment_and_publishes_work_rejected(
    session, publisher, submission_id
) -> None:
    result = _verify(session, publisher, submission_id, REJECT)

    assert result.status == SubmissionStatus.REJECTED
    assert result.verification.verified_hours is None
    assert result.verification.comment == "Half the recipes are missing."

    [event] = publisher.events
    assert event.event_type == EventType.WORK_REJECTED
    payload = WorkRejectedPayload.model_validate(event.payload)
    assert (payload.submission_id, payload.contributor_id, payload.comment) == (
        submission_id,
        5,
        "Half the recipes are missing.",
    )


def test_all_the_hours_claimed_can_be_verified(session, publisher, submission_id) -> None:
    data = VerificationCreate(decision="approved", verified_hours=Decimal("6.50"))
    assert _verify(session, publisher, submission_id, data).verification.verified_hours == Decimal(
        "6.50"
    )


def test_more_hours_than_claimed_are_refused(session, publisher, submission_id) -> None:
    data = VerificationCreate(decision="approved", verified_hours=Decimal("6.51"))

    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, submission_id, data)

    assert _code(exc_info) == (422, "VERIFIED_HOURS_EXCEED_CLAIMED")
    assert _count_verifications(session) == 0
    assert publisher.events == []


@pytest.mark.parametrize("comment", [None, "   "])
def test_rejecting_needs_a_comment(session, publisher, submission_id, comment) -> None:
    data = VerificationCreate(decision="rejected", comment=comment)

    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, submission_id, data)

    assert _code(exc_info) == (422, "REJECTION_COMMENT_REQUIRED")
    assert _count_verifications(session) == 0


@pytest.mark.parametrize("second", [APPROVE, REJECT])
def test_each_submission_is_verified_once(session, publisher, submission_id, second) -> None:
    _verify(session, publisher, submission_id, REJECT)

    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, submission_id, second)

    assert _code(exc_info) == (409, "SUBMISSION_ALREADY_VERIFIED")
    assert _count_verifications(session) == 1
    assert len(publisher.events) == 1


@pytest.mark.parametrize("user_id", [3])  # owns another organization
def test_another_creator_cannot_verify(session, publisher, submission_id, user_id) -> None:
    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, submission_id, creator_id=user_id)

    assert _code(exc_info) == (404, "SUBMISSION_NOT_FOUND")
    assert _count_verifications(session) == 0


def test_a_missing_submission_is_not_found(session, publisher) -> None:
    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, 999_999)
    assert _code(exc_info) == (404, "SUBMISSION_NOT_FOUND")


def test_a_cancelled_opportunity_takes_no_verification(
    seeded_db, session, publisher, submission_id
) -> None:
    # Cancelling is refused once work is submitted (ADR 0011), so set it directly.
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 1")

    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, submission_id)

    assert _code(exc_info) == (409, "OPPORTUNITY_CANCELLED")
    assert _count_verifications(session) == 0


def test_a_closed_opportunity_still_takes_verification(
    seeded_db, session, publisher, submission_id
) -> None:
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'closed' WHERE opportunity_id = 1")

    assert _verify(session, publisher, submission_id).status == SubmissionStatus.APPROVED


def test_already_verified_is_reported_before_a_bad_input(session, publisher, submission_id) -> None:
    _verify(session, publisher, submission_id)
    data = VerificationCreate(decision="approved", verified_hours=Decimal("99"))

    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, submission_id, data)

    assert _code(exc_info) == (409, "SUBMISSION_ALREADY_VERIFIED")


# ---------------------------------------------------------------------------
# Races and database backstops
# ---------------------------------------------------------------------------


def test_a_concurrent_decision_waits_for_the_lock_and_sees_the_first(
    seeded_db, publisher, submission_id
) -> None:
    """Two real transactions. The second one has already taken its snapshot when the
    first commits, so only the locking reads let it see the verification."""
    maker = get_sessionmaker()
    with maker() as first, maker() as second:
        creator_in_second = _user(second, 2)  # starts the second transaction's snapshot

        # The first transaction holds the submission's lock with its row inserted.
        submission_repository.get_for_update(first, submission_id)
        submission_repository.add_verification(
            first,
            WorkVerification(
                submission_id=submission_id,
                verified_by_user_id=2,
                decision=ReviewDecision.REJECTED,
                comment="First.",
            ),
        )

        outcome: list[object] = []

        def decide_second() -> None:
            try:
                verification_service.verify(
                    second, creator_in_second, submission_id, APPROVE, publisher, None
                )
                outcome.append("verified")
            except AppError as exc:
                # No __cause__: refused by the check, not by the unique-key backstop.
                outcome.append((exc.code, exc.__cause__ is None))

        thread = threading.Thread(target=decide_second)
        thread.start()
        thread.join(timeout=1)
        assert thread.is_alive(), "the second decision should wait for the first's lock"

        first.commit()
        thread.join(timeout=30)

    assert outcome == [("SUBMISSION_ALREADY_VERIFIED", True)]
    assert publisher.events == []


def test_a_race_on_the_unique_key_still_reports_already_verified(
    session, publisher, submission_id, monkeypatch: pytest.MonkeyPatch
) -> None:
    _verify(session, publisher, submission_id)
    # As if the check ran before a concurrent verification committed.
    monkeypatch.setattr(submission_repository, "is_verified", lambda s, i: False)

    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, submission_id, REJECT)

    assert _code(exc_info) == (409, "SUBMISSION_ALREADY_VERIFIED")
    assert _count_verifications(session) == 1


def test_the_trigger_backstop_hides_the_submission_from_another_creator(
    session, publisher, submission_id, monkeypatch: pytest.MonkeyPatch
) -> None:
    # As if the ownership check had passed: trg_work_verification_bi still refuses.
    monkeypatch.setattr(verification_service, "_owns", lambda s, u: True)

    with pytest.raises(AppError) as exc_info:
        _verify(session, publisher, submission_id, creator_id=3)

    assert _code(exc_info) == (404, "SUBMISSION_NOT_FOUND")
    assert _count_verifications(session) == 0


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("user_id", [5, 2])  # the applicant and the owning creator
def test_the_applicant_and_the_owner_see_the_decision(
    session, publisher, submission_id, user_id
) -> None:
    verified = _verify(session, publisher, submission_id, REJECT)

    assert submission_service.get(session, _user(session, user_id), submission_id) == verified


@pytest.mark.parametrize("user_id", [3, 6])  # another creator, another contributor
def test_nobody_else_sees_the_submission(session, submission_id, user_id) -> None:
    with pytest.raises(AppError) as exc_info:
        submission_service.get(session, _user(session, user_id), submission_id)
    assert _code(exc_info) == (404, "SUBMISSION_NOT_FOUND")


def _received(session: Session, creator_id: int = 2, **params) -> list[tuple[int, str]]:
    page = submission_service.list_received(
        session, _user(session, creator_id), ReceivedSubmissionParams(**params)
    )
    return [(s.submission_id, s.status.value) for s in page.items]


def test_review_queue_is_oldest_first_and_filters_by_status(seeded_db, session, publisher) -> None:
    newest = _submission(seeded_db, 5, "2026-10-15 12:00:00")
    oldest = _submission(seeded_db, 6, "2026-10-15 08:00:00")
    middle = _submission(seeded_db, 7, "2026-10-15 10:00:00")
    _verify(session, publisher, middle)
    _verify(session, publisher, newest, REJECT)

    assert _received(session) == [(oldest, "awaiting"), (middle, "approved"), (newest, "rejected")]
    assert _received(session, status=["awaiting"]) == [(oldest, "awaiting")]
    assert _received(session, status=["approved", "rejected"]) == [
        (middle, "approved"),
        (newest, "rejected"),
    ]


def test_review_queue_shows_only_your_opportunities(seeded_db, session) -> None:
    mine = _submission(seeded_db, 5)

    assert _received(session, creator_id=2) == [(mine, "awaiting")]
    assert _received(session, creator_id=2, opportunity_id=1) == [(mine, "awaiting")]
    assert _received(session, creator_id=3) == []
    # Someone else's opportunity id matches nothing rather than leaking anything.
    assert _received(session, creator_id=3, opportunity_id=1) == []


def test_review_queue_is_paginated(seeded_db, session) -> None:
    ids = [
        _submission(seeded_db, user_id, f"2026-10-15 0{hour}:00:00")
        for hour, user_id in ((1, 5), (2, 6), (3, 7))
    ]
    page = submission_service.list_received(
        session, _user(session, 2), ReceivedSubmissionParams(limit=2, offset=1)
    )

    assert [s.submission_id for s in page.items] == ids[1:]
    assert (page.total, page.limit, page.offset) == (3, 2, 1)
