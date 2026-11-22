"""feedback_service against the seeded test database (ADR 0015).

Seeded: Ada Admin is user 1. Opportunity 1 belongs to organization 1, owned by Priya
Nair (user 2); Daniel Okafor (user 3) owns organization 2. Contributors: Alex Chen (5),
Jordan Lee (6), Sam Patel (7). 002_seed.sql has no applications, so each test inserts
an accepted application to opportunity 1 with submitted work and, unless told not to,
Priya's verification of it.
"""

import threading
from collections.abc import Iterator
from decimal import Decimal

import pymysql
import pytest
from grow8_common.db import get_sessionmaker
from grow8_common.events import (
    EventType,
    FeedbackApprovedPayload,
    FeedbackRejectedPayload,
    FeedbackSubmittedPayload,
)
from grow8_common.models import AdminReview, Feedback, ReviewDecision, UserAccount
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.repositories import feedback_repository
from app.schemas.feedback import AdminFeedbackParams, FeedbackCreate, ReviewCreate
from app.services import feedback_service
from app.services.feedback_rules import FeedbackStatus
from tests.fakes import FakePublisher

ADMIN, OWNER, OTHER_CREATOR = 1, 2, 3
ALEX, JORDAN, SAM = 5, 6, 7

GOOD = FeedbackCreate(rating=5, comment="Clear instructions, great to work with.")
APPROVE = ReviewCreate(decision="approved")
REJECT = ReviewCreate(decision="rejected", reason="Personal remarks about the other person.")


def _application(
    conn: pymysql.Connection, contributor_id: int = ALEX, verification: str | None = "approved"
) -> int:
    """An accepted application to opportunity 1 with submitted work, verified with
    `verification` ("approved", "rejected", or None for not yet; "none" for no work)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO application (opportunity_id, contributor_id, status, submitted_at, "
            "decided_at) VALUES (1, %s, 'accepted', '2026-10-14 10:00:00', "
            "'2026-10-14 12:00:00')",
            (contributor_id,),
        )
        application_id = cur.lastrowid
        if verification == "none":
            return application_id
        cur.execute(
            "INSERT INTO work_submission (application_id, description, hours_claimed, "
            "submitted_at) VALUES (%s, 'Typed up 40 recipes.', 6.50, '2026-10-15 10:00:00')",
            (application_id,),
        )
        if verification is not None:
            hours = "6.00" if verification == "approved" else None
            cur.execute(
                "INSERT INTO work_verification (submission_id, verified_by_user_id, decision, "
                "verified_hours, comment) VALUES (%s, %s, %s, %s, 'Checked.')",
                (cur.lastrowid, OWNER, verification, hours),
            )
        return application_id


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
def application_id(seeded_db: pymysql.Connection) -> int:
    return _application(seeded_db)


def _user(session: Session, user_id: int) -> UserAccount:
    user = session.get(UserAccount, user_id)
    assert user is not None
    return user


def _give(session, publisher, application_id, author_id=ALEX, data=GOOD):
    return feedback_service.submit(
        session, _user(session, author_id), application_id, data, publisher, "req-1"
    )


def _review(session, publisher, feedback_id, data=APPROVE):
    return feedback_service.review(
        session, _user(session, ADMIN), feedback_id, data, publisher, "req-2"
    )


def _code(exc_info: pytest.ExceptionInfo[AppError]) -> tuple[int, str]:
    return exc_info.value.status_code, exc_info.value.code


def _count(session: Session, model: type) -> int:
    session.rollback()  # end the transaction so the count sees committed rows
    return session.scalar(select(func.count()).select_from(model)) or 0


# ---------------------------------------------------------------------------
# Giving feedback
# ---------------------------------------------------------------------------


def test_the_contributor_rates_the_creator(session, publisher, application_id) -> None:
    result = _give(session, publisher, application_id)

    assert (result.author.user_id, result.subject.user_id) == (ALEX, OWNER)
    assert (result.author.full_name, result.subject.full_name) == ("Alex Chen", "Priya Nair")
    assert (result.rating, result.status, result.review) == (5, FeedbackStatus.PENDING, None)
    assert result.opportunity.title == "Digitize paper recipe archive"

    [event] = publisher.events
    assert event.event_type == EventType.FEEDBACK_SUBMITTED
    assert FeedbackSubmittedPayload.model_validate(event.payload) == FeedbackSubmittedPayload(
        feedback_id=result.feedback_id,
        application_id=application_id,
        opportunity_id=1,
        opportunity_title="Digitize paper recipe archive",
        author_user_id=ALEX,
        author_name="Alex Chen",
        author_role="contributor",
        subject_user_id=OWNER,
        rating=5,
        reports_discrepancy=False,
    )


def test_the_creator_rates_the_contributor(session, publisher, application_id) -> None:
    data = FeedbackCreate(rating=2, comment="Missed a day.", reports_discrepancy=True)
    result = _give(session, publisher, application_id, OWNER, data)

    assert (result.author.user_id, result.subject.user_id) == (OWNER, ALEX)
    assert result.reports_discrepancy is True
    payload = FeedbackSubmittedPayload.model_validate(publisher.events[0].payload)
    assert (payload.author_role, payload.reports_discrepancy) == ("creator", True)


def test_rejected_work_can_also_get_feedback(seeded_db, session, publisher) -> None:
    application_id = _application(seeded_db, verification="rejected")
    assert _give(session, publisher, application_id).status == FeedbackStatus.PENDING


@pytest.mark.parametrize("verification", ["none", None])  # no work, or work not verified
def test_feedback_waits_for_verified_work(seeded_db, session, publisher, verification) -> None:
    application_id = _application(seeded_db, verification=verification)

    with pytest.raises(AppError) as exc_info:
        _give(session, publisher, application_id)

    assert _code(exc_info) == (409, "WORK_NOT_VERIFIED")
    assert _count(session, Feedback) == 0
    assert publisher.events == []


def test_one_feedback_per_author(session, publisher, application_id) -> None:
    _give(session, publisher, application_id)
    _give(session, publisher, application_id, OWNER)  # the other participant still can

    with pytest.raises(AppError) as exc_info:
        _give(session, publisher, application_id, data=FeedbackCreate(rating=1))

    assert _code(exc_info) == (409, "FEEDBACK_ALREADY_SUBMITTED")
    assert _count(session, Feedback) == 2


@pytest.mark.parametrize("user_id", [ADMIN, OTHER_CREATOR, JORDAN])
def test_only_participants_give_feedback(session, publisher, application_id, user_id) -> None:
    with pytest.raises(AppError) as exc_info:
        _give(session, publisher, application_id, user_id)
    assert _code(exc_info) == (404, "APPLICATION_NOT_FOUND")


def test_a_missing_application(session, publisher) -> None:
    with pytest.raises(AppError) as exc_info:
        _give(session, publisher, 999_999)
    assert _code(exc_info) == (404, "APPLICATION_NOT_FOUND")


def test_a_race_on_the_unique_key_still_reports_already_submitted(
    session, publisher, application_id, monkeypatch: pytest.MonkeyPatch
) -> None:
    _give(session, publisher, application_id)
    # As if the check ran before a concurrent submission committed.
    monkeypatch.setattr(feedback_repository, "exists_for_author", lambda s, a, u: False)

    with pytest.raises(AppError) as exc_info:
        _give(session, publisher, application_id)

    assert _code(exc_info) == (409, "FEEDBACK_ALREADY_SUBMITTED")
    assert _count(session, Feedback) == 1


def test_the_trigger_backstop_hides_the_application_from_others(
    session, publisher, application_id, monkeypatch: pytest.MonkeyPatch
) -> None:
    # As if the participant check had passed: trg_feedback_bi still refuses.
    monkeypatch.setattr(feedback_service, "_role", lambda a, u: "contributor")

    with pytest.raises(AppError) as exc_info:
        _give(session, publisher, application_id, JORDAN)

    assert _code(exc_info) == (404, "APPLICATION_NOT_FOUND")
    assert _count(session, Feedback) == 0


# ---------------------------------------------------------------------------
# Who sees what
# ---------------------------------------------------------------------------


def _seen(session: Session, user_id: int, application_id: int) -> tuple:
    seen = feedback_service.for_application(session, _user(session, user_id), application_id)
    return (
        seen.given and (seen.given.author.user_id, seen.given.status.value),
        seen.received and (seen.received.author.user_id, seen.received.status.value),
    )


def test_pending_feedback_is_seen_by_its_author_only(session, publisher, application_id) -> None:
    _give(session, publisher, application_id)

    assert _seen(session, ALEX, application_id) == ((ALEX, "pending"), None)
    assert _seen(session, OWNER, application_id) == (None, None)


def test_approved_feedback_is_seen_by_the_subject(session, publisher, application_id) -> None:
    feedback = _give(session, publisher, application_id)
    _review(session, publisher, feedback.feedback_id)

    assert _seen(session, ALEX, application_id) == ((ALEX, "approved"), None)
    assert _seen(session, OWNER, application_id) == (None, (ALEX, "approved"))


def test_rejected_feedback_stays_hidden_from_the_subject(
    session, publisher, application_id
) -> None:
    feedback = _give(session, publisher, application_id)
    _review(session, publisher, feedback.feedback_id, REJECT)

    seen = feedback_service.for_application(session, _user(session, ALEX), application_id)
    assert seen.given.status == FeedbackStatus.REJECTED
    assert seen.given.review.reason == "Personal remarks about the other person."
    assert _seen(session, OWNER, application_id) == (None, None)


def test_both_directions(session, publisher, application_id) -> None:
    from_alex = _give(session, publisher, application_id)
    _give(session, publisher, application_id, OWNER, FeedbackCreate(rating=4))
    _review(session, publisher, from_alex.feedback_id)

    assert _seen(session, ALEX, application_id) == ((ALEX, "approved"), None)
    assert _seen(session, OWNER, application_id) == ((OWNER, "pending"), (ALEX, "approved"))


@pytest.mark.parametrize("user_id", [ADMIN, OTHER_CREATOR, JORDAN])
def test_nobody_else_sees_the_feedback(session, application_id, user_id) -> None:
    with pytest.raises(AppError) as exc_info:
        feedback_service.for_application(session, _user(session, user_id), application_id)
    assert _code(exc_info) == (404, "APPLICATION_NOT_FOUND")


# ---------------------------------------------------------------------------
# Admin review
# ---------------------------------------------------------------------------


def test_approving_publishes_feedback_approved(session, publisher, application_id) -> None:
    feedback = _give(session, publisher, application_id)

    result = _review(session, publisher, feedback.feedback_id)

    assert result.status == FeedbackStatus.APPROVED
    assert (result.review.decision, result.review.reason) == (ReviewDecision.APPROVED, None)
    event = publisher.events[-1]
    assert event.event_type == EventType.FEEDBACK_APPROVED
    assert FeedbackApprovedPayload.model_validate(event.payload) == FeedbackApprovedPayload(
        feedback_id=feedback.feedback_id,
        application_id=application_id,
        opportunity_id=1,
        opportunity_title="Digitize paper recipe archive",
        author_user_id=ALEX,
        author_name="Alex Chen",
        author_role="contributor",
        subject_user_id=OWNER,
        subject_name="Priya Nair",
        rating=5,
    )
    assert session.scalars(select(AdminReview)).one().admin_user_id == ADMIN


def test_rejecting_publishes_feedback_rejected(session, publisher, application_id) -> None:
    feedback = _give(session, publisher, application_id, OWNER, FeedbackCreate(rating=1))

    result = _review(session, publisher, feedback.feedback_id, REJECT)

    assert result.status == FeedbackStatus.REJECTED
    event = publisher.events[-1]
    assert event.event_type == EventType.FEEDBACK_REJECTED
    payload = FeedbackRejectedPayload.model_validate(event.payload)
    assert (payload.author_user_id, payload.author_role, payload.subject_name) == (
        OWNER,
        "creator",
        "Alex Chen",
    )
    assert payload.reason == "Personal remarks about the other person."


@pytest.mark.parametrize("reason", [None, "   "])
def test_rejecting_needs_a_reason(session, publisher, application_id, reason) -> None:
    feedback = _give(session, publisher, application_id)

    with pytest.raises(AppError) as exc_info:
        _review(
            session,
            publisher,
            feedback.feedback_id,
            ReviewCreate(decision="rejected", reason=reason),
        )

    assert _code(exc_info) == (422, "REJECTION_REASON_REQUIRED")
    assert _count(session, AdminReview) == 0


@pytest.mark.parametrize("second", [APPROVE, REJECT])
def test_each_feedback_is_reviewed_once(session, publisher, application_id, second) -> None:
    feedback = _give(session, publisher, application_id)
    _review(session, publisher, feedback.feedback_id, REJECT)

    with pytest.raises(AppError) as exc_info:
        _review(session, publisher, feedback.feedback_id, second)

    assert _code(exc_info) == (409, "FEEDBACK_ALREADY_REVIEWED")
    assert _count(session, AdminReview) == 1


def test_a_missing_feedback(session, publisher) -> None:
    with pytest.raises(AppError) as exc_info:
        _review(session, publisher, 999_999)
    assert _code(exc_info) == (404, "FEEDBACK_NOT_FOUND")


def test_a_race_on_the_unique_key_still_reports_already_reviewed(
    session, publisher, application_id, monkeypatch: pytest.MonkeyPatch
) -> None:
    feedback = _give(session, publisher, application_id)
    _review(session, publisher, feedback.feedback_id)
    monkeypatch.setattr(feedback_repository, "is_reviewed", lambda s, i: False)

    with pytest.raises(AppError) as exc_info:
        _review(session, publisher, feedback.feedback_id, REJECT)

    assert _code(exc_info) == (409, "FEEDBACK_ALREADY_REVIEWED")
    assert _count(session, AdminReview) == 1


def test_a_concurrent_review_waits_for_the_lock_and_sees_the_first(
    session, publisher, application_id
) -> None:
    """Two real transactions. The second one has already taken its snapshot when the
    first commits, so only the locking reads let it see the review."""
    feedback_id = _give(session, publisher, application_id).feedback_id
    publisher.events.clear()
    maker = get_sessionmaker()
    with maker() as first, maker() as second:
        admin_in_second = _user(second, ADMIN)  # starts the second transaction's snapshot

        feedback_repository.get_for_update(first, feedback_id)
        feedback_repository.add_review(
            first,
            AdminReview(
                feedback_id=feedback_id, admin_user_id=ADMIN, decision="rejected", reason="First."
            ),
        )

        outcome: list[object] = []

        def review_second() -> None:
            try:
                feedback_service.review(
                    second, admin_in_second, feedback_id, APPROVE, publisher, None
                )
                outcome.append("reviewed")
            except AppError as exc:
                # No __cause__: refused by the check, not by the unique-key backstop.
                outcome.append((exc.code, exc.__cause__ is None))

        thread = threading.Thread(target=review_second)
        thread.start()
        thread.join(timeout=1)
        assert thread.is_alive(), "the second review should wait for the first's lock"

        first.commit()
        thread.join(timeout=30)

    assert outcome == [("FEEDBACK_ALREADY_REVIEWED", True)]
    assert publisher.events == []


# ---------------------------------------------------------------------------
# Admin queue
# ---------------------------------------------------------------------------


def _queue(session: Session, **params) -> list[tuple[int, str, bool]]:
    page = feedback_service.list_for_admin(session, AdminFeedbackParams(**params))
    return [(f.feedback_id, f.status.value, f.reports_discrepancy) for f in page.items]


def _feedback_at(
    conn: pymysql.Connection,
    application_id: int,
    author: int,
    subject: int,
    created_at: str,
    discrepancy: bool = False,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating, "
            "reports_discrepancy, created_at) VALUES (%s, %s, %s, 3, %s, %s)",
            (application_id, author, subject, discrepancy, created_at),
        )
        return cur.lastrowid


def test_queue_shows_discrepancies_first_then_oldest(seeded_db, session, publisher) -> None:
    first_app, second_app = _application(seeded_db, ALEX), _application(seeded_db, JORDAN)
    old = _feedback_at(seeded_db, first_app, ALEX, OWNER, "2026-10-16 08:00:00")
    new_discrepancy = _feedback_at(seeded_db, first_app, OWNER, ALEX, "2026-10-16 11:00:00", True)
    older_discrepancy = _feedback_at(
        seeded_db, second_app, JORDAN, OWNER, "2026-10-16 09:00:00", True
    )
    newest = _feedback_at(seeded_db, second_app, OWNER, JORDAN, "2026-10-16 10:00:00")
    _review(session, publisher, newest)

    assert _queue(session) == [
        (older_discrepancy, "pending", True),
        (new_discrepancy, "pending", True),
        (old, "pending", False),
        (newest, "approved", False),
    ]
    assert _queue(session, status=["pending"], discrepancy=False) == [(old, "pending", False)]
    assert _queue(session, status=["approved", "rejected"]) == [(newest, "approved", False)]
    assert [f[0] for f in _queue(session, discrepancy=True)] == [older_discrepancy, new_discrepancy]

    page = feedback_service.list_for_admin(session, AdminFeedbackParams(limit=2, offset=1))
    assert [f.feedback_id for f in page.items] == [new_discrepancy, old]
    assert page.total == 4


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------


def _rating(session: Session, user_id: int) -> tuple[Decimal | None, int]:
    session.rollback()
    r = feedback_service.rating(session, user_id)
    return r.average_rating, r.approved_feedback_count


def test_only_approved_feedback_counts_toward_a_rating(seeded_db, session, publisher) -> None:
    apps = [_application(seeded_db, c) for c in (ALEX, JORDAN, SAM)]
    approved_5 = _give(session, publisher, apps[0], ALEX, FeedbackCreate(rating=5))
    approved_4 = _give(session, publisher, apps[1], JORDAN, FeedbackCreate(rating=4))
    rejected_1 = _give(session, publisher, apps[2], SAM, FeedbackCreate(rating=1))

    assert _rating(session, OWNER) == (None, 0)  # all pending: nothing counts yet

    _review(session, publisher, rejected_1.feedback_id, REJECT)
    assert _rating(session, OWNER) == (None, 0)  # rejected never counts

    _review(session, publisher, approved_5.feedback_id)
    assert _rating(session, OWNER) == (Decimal("5.00"), 1)

    _review(session, publisher, approved_4.feedback_id)
    assert _rating(session, OWNER) == (Decimal("4.50"), 2)
    assert _rating(session, ALEX) == (None, 0)  # ratings are per subject


def test_rating_of_an_unknown_user(session) -> None:
    with pytest.raises(AppError) as exc_info:
        feedback_service.rating(session, 999_999)
    assert _code(exc_info) == (404, "USER_NOT_FOUND")
