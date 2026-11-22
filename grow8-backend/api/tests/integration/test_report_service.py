"""report_service against the seeded test database (ADR 0016).

Seeded: Ada Admin is user 1. Opportunities 1 and 4 are open and belong to Maple Street
Bakery (Priya Nair, user 2); 15 is a draft. Contributors: Alex Chen (5), Jordan Lee
(6), Sam Patel (7). "Now" comes from the real clock here; nothing depends on it.
"""

import threading
from collections.abc import Iterator

import pymysql
import pytest
from grow8_common.db import get_sessionmaker
from grow8_common.events import (
    EventType,
    OpportunityReportedPayload,
    OpportunityTakenDownPayload,
    ReportDismissedPayload,
)
from grow8_common.models import (
    Opportunity,
    OpportunityReport,
    OpportunityStatus,
    ReportDecision,
    ReportReview,
    UserAccount,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.repositories import opportunity_repository, report_repository
from app.schemas.application import Decision
from app.schemas.report import AdminReportParams, MyReportParams, ReportCreate, ReportReviewCreate
from app.services import application_service, report_service
from app.services.report_rules import ReportStatus
from tests.fakes import FakePublisher

ADMIN, OWNER = 1, 2
ALEX, JORDAN, SAM = 5, 6, 7

MISLEADING = ReportCreate(reason="misleading_terms", details="The pay is listed as $25/h.")
UPHOLD = ReportReviewCreate(decision="upheld", reason="The pay is not what was advertised.")
DISMISS = ReportReviewCreate(decision="dismissed")


@pytest.fixture
def session(seeded_db: pymysql.Connection) -> Iterator[Session]:
    with get_sessionmaker()() as s:
        yield s


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


def _user(session: Session, user_id: int) -> UserAccount:
    user = session.get(UserAccount, user_id)
    assert user is not None
    return user


def _report(session, publisher, opportunity_id=1, reporter=ALEX, data=MISLEADING):
    return report_service.submit(
        session, _user(session, reporter), opportunity_id, data, publisher, "req-1"
    )


def _review(session, publisher, report_id, data=UPHOLD):
    return report_service.review(
        session, _user(session, ADMIN), report_id, data, publisher, "req-2"
    )


def _code(exc_info: pytest.ExceptionInfo[AppError]) -> tuple[int, str]:
    return exc_info.value.status_code, exc_info.value.code


def _fresh(session: Session) -> Session:
    session.rollback()  # end the transaction so reads see committed rows
    return session


def _status(session: Session, opportunity_id: int) -> OpportunityStatus:
    return _fresh(session).scalar(
        select(Opportunity.status).where(Opportunity.opportunity_id == opportunity_id)
    )


def _statuses(session: Session) -> dict[int, str]:
    """report_id -> status, for every report."""
    reports = _fresh(session).scalars(select(OpportunityReport)).all()
    return {r.report_id: (r.review.decision.value if r.review else "pending") for r in reports}


def _application(conn: pymysql.Connection, contributor_id: int, status: str) -> int:
    decided = None if status == "pending" else "2026-10-14 12:00:00"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO application (opportunity_id, contributor_id, status, submitted_at, "
            "decided_at) VALUES (1, %s, %s, '2026-10-14 10:00:00', %s)",
            (contributor_id, status, decided),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def test_a_contributor_reports_an_opportunity(session, publisher) -> None:
    result = _report(session, publisher)

    assert (result.opportunity.opportunity_id, result.reason.value) == (1, "misleading_terms")
    assert (result.status, result.review) == (ReportStatus.PENDING, None)
    assert result.details == "The pay is listed as $25/h."

    [event] = publisher.events
    assert event.event_type == EventType.OPPORTUNITY_REPORTED
    assert OpportunityReportedPayload.model_validate(event.payload) == OpportunityReportedPayload(
        report_id=result.report_id,
        opportunity_id=1,
        opportunity_title="Digitize paper recipe archive",
        reason="misleading_terms",
        open_reports=1,
    )


def test_the_event_counts_the_open_reports(session, publisher) -> None:
    _report(session, publisher, reporter=ALEX)
    _report(session, publisher, reporter=JORDAN)

    payload = OpportunityReportedPayload.model_validate(publisher.events[-1].payload)
    assert payload.open_reports == 2


def test_a_closed_opportunity_can_still_be_reported(seeded_db, session, publisher) -> None:
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'closed' WHERE opportunity_id = 1")
    assert _report(session, publisher).status == ReportStatus.PENDING


@pytest.mark.parametrize("opportunity_id", [15, 999_999])  # a draft, a missing one
def test_drafts_and_missing_opportunities_are_not_found(session, publisher, opportunity_id) -> None:
    with pytest.raises(AppError) as exc_info:
        _report(session, publisher, opportunity_id)
    assert _code(exc_info) == (404, "OPPORTUNITY_NOT_FOUND")


def test_a_cancelled_opportunity_cannot_be_reported(seeded_db, session, publisher) -> None:
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 1")

    with pytest.raises(AppError) as exc_info:
        _report(session, publisher)

    assert _code(exc_info) == (409, "OPPORTUNITY_CANCELLED")


def test_one_report_per_contributor(session, publisher) -> None:
    _report(session, publisher)

    with pytest.raises(AppError) as exc_info:
        _report(session, publisher, data=ReportCreate(reason="other"))

    assert _code(exc_info) == (409, "OPPORTUNITY_ALREADY_REPORTED")
    _report(session, publisher, opportunity_id=4)  # another opportunity is fine


def test_a_race_on_the_unique_key_still_reports_already_reported(
    session, publisher, monkeypatch: pytest.MonkeyPatch
) -> None:
    _report(session, publisher)
    monkeypatch.setattr(report_repository, "exists_for_reporter", lambda s, o, u: False)

    with pytest.raises(AppError) as exc_info:
        _report(session, publisher)

    assert _code(exc_info) == (409, "OPPORTUNITY_ALREADY_REPORTED")


def test_the_trigger_backstop_refuses_a_cancelled_opportunity(
    seeded_db, session, publisher, monkeypatch: pytest.MonkeyPatch
) -> None:
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 1")
    # As if the status check ran before the cancel: trg_opportunity_report_bi refuses.
    monkeypatch.setattr(
        opportunity_repository, "lock_status_for_share", lambda s, o: OpportunityStatus.OPEN
    )

    with pytest.raises(AppError) as exc_info:
        _report(session, publisher)

    assert _code(exc_info) == (409, "OPPORTUNITY_CANCELLED")


def test_my_reports_newest_first_with_the_decision(session, publisher) -> None:
    first = _report(session, publisher, opportunity_id=1)
    second = _report(session, publisher, opportunity_id=4)
    _review(session, publisher, first.report_id, DISMISS)

    page = report_service.list_mine(session, _user(session, ALEX), MyReportParams())

    assert [(r.report_id, r.status.value) for r in page.items] == [
        (second.report_id, "pending"),
        (first.report_id, "dismissed"),
    ]
    assert report_service.list_mine(session, _user(session, JORDAN), MyReportParams()).total == 0


# ---------------------------------------------------------------------------
# Dismissing
# ---------------------------------------------------------------------------


def test_dismissing_affects_one_report_only(session, publisher) -> None:
    alex = _report(session, publisher, reporter=ALEX)
    jordan = _report(session, publisher, reporter=JORDAN)
    reason = ReportReviewCreate(decision="dismissed", reason="  The hours are listed.  ")

    result = _review(session, publisher, alex.report_id, reason)

    assert result.status == ReportStatus.DISMISSED
    assert result.review.reason == "The hours are listed."
    assert result.open_reports_on_opportunity == 1
    assert _statuses(session) == {alex.report_id: "dismissed", jordan.report_id: "pending"}
    assert _status(session, 1) == OpportunityStatus.OPEN

    event = publisher.events[-1]
    assert event.event_type == EventType.REPORT_DISMISSED
    assert ReportDismissedPayload.model_validate(event.payload) == ReportDismissedPayload(
        report_id=alex.report_id,
        opportunity_id=1,
        opportunity_title="Digitize paper recipe archive",
        reporter_user_id=ALEX,
        reason="The hours are listed.",
    )


# ---------------------------------------------------------------------------
# Taking down
# ---------------------------------------------------------------------------


def test_upholding_takes_the_opportunity_down_and_clears_its_reports(
    seeded_db, session, publisher
) -> None:
    pending_app = _application(seeded_db, SAM, "pending")
    alex = _report(session, publisher, reporter=ALEX)
    jordan = _report(session, publisher, reporter=JORDAN)
    sam = _report(session, publisher, reporter=SAM)
    elsewhere = _report(session, publisher, opportunity_id=4, reporter=ALEX)
    _review(session, publisher, sam.report_id, DISMISS)

    result = _review(session, publisher, jordan.report_id)

    assert result.status == ReportStatus.UPHELD
    assert result.open_reports_on_opportunity == 0
    assert _status(session, 1) == OpportunityStatus.CANCELLED
    assert _statuses(session) == {
        alex.report_id: "upheld",  # upheld with the reviewed one
        jordan.report_id: "upheld",
        sam.report_id: "dismissed",  # already decided: untouched
        elsewhere.report_id: "pending",  # another opportunity: untouched
    }
    reviews = session.scalars(
        select(ReportReview).where(ReportReview.decision == ReportDecision.UPHELD)
    ).all()
    assert {(r.admin_user_id, r.reason) for r in reviews} == {
        (ADMIN, "The pay is not what was advertised.")
    }

    event = publisher.events[-1]
    assert event.event_type == EventType.OPPORTUNITY_TAKEN_DOWN
    assert OpportunityTakenDownPayload.model_validate(event.payload) == OpportunityTakenDownPayload(
        opportunity_id=1,
        organization_id=1,
        title="Digitize paper recipe archive",
        reason="The pay is not what was advertised.",
        reporter_user_ids=[ALEX, JORDAN],  # not Sam, whose report was dismissed
    )

    # Applications keep their status and can't be decided any more (ADR 0011).
    with pytest.raises(AppError) as exc_info:
        application_service.decide(
            _fresh(session), _user(session, OWNER), pending_app, Decision.ACCEPTED, publisher, None
        )
    assert _code(exc_info) == (409, "OPPORTUNITY_CANCELLED")


@pytest.mark.parametrize("reason", [None, "   "])
def test_a_takedown_needs_a_reason(session, publisher, reason) -> None:
    report = _report(session, publisher)

    with pytest.raises(AppError) as exc_info:
        _review(
            session,
            publisher,
            report.report_id,
            ReportReviewCreate(decision="upheld", reason=reason),
        )

    assert _code(exc_info) == (422, "TAKEDOWN_REASON_REQUIRED")
    assert _status(session, 1) == OpportunityStatus.OPEN


def test_no_takedown_once_work_is_submitted(seeded_db, session, publisher) -> None:
    application_id = _application(seeded_db, SAM, "accepted")
    with seeded_db.cursor() as cur:
        cur.execute(
            "INSERT INTO work_submission (application_id, description, hours_claimed) "
            "VALUES (%s, 'Done.', 3)",
            (application_id,),
        )
    report = _report(session, publisher)

    with pytest.raises(AppError) as exc_info:
        _review(session, publisher, report.report_id)

    assert _code(exc_info) == (409, "WORK_ALREADY_SUBMITTED")
    assert _status(session, 1) == OpportunityStatus.OPEN
    assert _statuses(session) == {report.report_id: "pending"}
    # The admin can still dismiss it.
    assert _review(session, publisher, report.report_id, DISMISS).status == ReportStatus.DISMISSED


def test_no_takedown_of_an_opportunity_its_creator_cancelled(seeded_db, session, publisher) -> None:
    report = _report(session, publisher)
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 1")

    with pytest.raises(AppError) as exc_info:
        _review(session, publisher, report.report_id)

    assert _code(exc_info) == (409, "OPPORTUNITY_CANCELLED")
    assert _review(session, publisher, report.report_id, DISMISS).status == ReportStatus.DISMISSED


@pytest.mark.parametrize("second", [UPHOLD, DISMISS])
def test_each_report_is_reviewed_once(session, publisher, second) -> None:
    alex = _report(session, publisher, reporter=ALEX)
    jordan = _report(session, publisher, reporter=JORDAN)
    _review(session, publisher, alex.report_id)  # upholds Jordan's report too

    for report_id in (alex.report_id, jordan.report_id):
        with pytest.raises(AppError) as exc_info:
            _review(session, publisher, report_id, second)
        assert _code(exc_info) == (409, "REPORT_ALREADY_REVIEWED")


def test_a_missing_report(session, publisher) -> None:
    with pytest.raises(AppError) as exc_info:
        _review(session, publisher, 999_999)
    assert _code(exc_info) == (404, "REPORT_NOT_FOUND")


def test_a_race_on_the_unique_key_still_reports_already_reviewed(
    session, publisher, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = _report(session, publisher)
    _review(session, publisher, report.report_id, DISMISS)
    monkeypatch.setattr(report_repository, "is_reviewed", lambda s, i: False)

    with pytest.raises(AppError) as exc_info:
        _review(session, publisher, report.report_id, DISMISS)

    assert _code(exc_info) == (409, "REPORT_ALREADY_REVIEWED")


# ---------------------------------------------------------------------------
# Races with real transactions
# ---------------------------------------------------------------------------


def _start_takedown(first: Session, report_id: int) -> Opportunity:
    """In `first`, take the locks a real takedown takes first: opportunity 1, then the
    reviewed report."""
    opportunity = opportunity_repository.get_for_update(first, 1)
    report_repository.get_for_update(first, report_id)
    return opportunity


def _finish_takedown(first: Session, opportunity: Opportunity) -> None:
    """In `first`, uphold every pending report (locking them) and cancel, uncommitted."""
    reviews = [
        ReportReview(report_id=r.report_id, admin_user_id=ADMIN, decision="upheld", reason="First.")
        for r in report_repository.pending_for_opportunity_for_update(first, 1)
    ]
    opportunity.status = OpportunityStatus.CANCELLED
    report_repository.add_reviews(first, reviews)


def _run_blocked(action) -> tuple[list[object], threading.Thread]:
    """Start `action` in a thread, check it is waiting for a lock, and return the list
    that receives its outcome, and the thread."""
    outcome: list[object] = []

    def run() -> None:
        try:
            action()
            outcome.append("done")
        except AppError as exc:
            # No __cause__: refused by the service's check, not by a database backstop.
            outcome.append((exc.code, exc.__cause__ is None))

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=1)
    assert thread.is_alive(), "the second transaction should wait for the first's lock"
    return outcome, thread


def test_two_admins_upholding_different_reports_do_not_deadlock(session, publisher) -> None:
    """Admin A upholds Alex's report while admin B upholds Jordan's, on the same
    opportunity, interleaved the dangerous way: A has locked the opportunity and Alex's
    report, B starts, and only then does A lock the other pending reports (Jordan's).
    Had B locked Jordan's report before waiting for the opportunity, the two would
    deadlock here. Locking the opportunity first, B just waits, then finds Jordan's
    report already upheld by A's takedown."""
    alex = _report(session, publisher, reporter=ALEX).report_id
    jordan = _report(session, publisher, reporter=JORDAN).report_id
    publisher.events.clear()
    maker = get_sessionmaker()
    with maker() as first, maker() as second:
        admin_in_second = _user(second, ADMIN)  # starts the second transaction's snapshot
        opportunity = _start_takedown(first, alex)

        outcome, thread = _run_blocked(
            lambda: report_service.review(second, admin_in_second, jordan, UPHOLD, publisher, None)
        )
        _finish_takedown(first, opportunity)  # locks Jordan's report while B waits
        first.commit()
        thread.join(timeout=30)

    assert outcome == [("REPORT_ALREADY_REVIEWED", True)]
    assert publisher.events == []
    assert _statuses(session) == {alex: "upheld", jordan: "upheld"}


def test_a_report_racing_a_takedown_sees_the_cancel(session, publisher) -> None:
    alex = _report(session, publisher, reporter=ALEX).report_id
    publisher.events.clear()
    maker = get_sessionmaker()
    with maker() as first, maker() as second:
        jordan_in_second = _user(second, JORDAN)
        _finish_takedown(first, _start_takedown(first, alex))

        outcome, thread = _run_blocked(
            lambda: report_service.submit(second, jordan_in_second, 1, MISLEADING, publisher, None)
        )
        first.commit()
        thread.join(timeout=30)

    assert outcome == [("OPPORTUNITY_CANCELLED", True)]
    assert _fresh(session).scalar(select(func.count()).select_from(OpportunityReport)) == 1


# ---------------------------------------------------------------------------
# Admin queue
# ---------------------------------------------------------------------------


def _queue(session: Session, **params) -> list[tuple[int, str, int]]:
    page = report_service.list_for_admin(_fresh(session), AdminReportParams(**params))
    return [(r.report_id, r.status.value, r.open_reports_on_opportunity) for r in page.items]


def _report_at(conn: pymysql.Connection, opportunity_id: int, reporter: int, at: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO opportunity_report (opportunity_id, reporter_user_id, reason, "
            "created_at) VALUES (%s, %s, 'other', %s)",
            (opportunity_id, reporter, at),
        )
        return cur.lastrowid


def test_queue_shows_the_most_reported_opportunity_first(seeded_db, session, publisher) -> None:
    oldest_on_4 = _report_at(seeded_db, 4, ALEX, "2026-10-01 09:00:00")
    on_1_a = _report_at(seeded_db, 1, JORDAN, "2026-10-02 09:00:00")
    on_1_b = _report_at(seeded_db, 1, SAM, "2026-10-03 09:00:00")
    dismissed_on_4 = _report_at(seeded_db, 4, JORDAN, "2026-09-01 09:00:00")
    _review(session, publisher, dismissed_on_4, DISMISS)

    assert _queue(session, status=["pending"]) == [
        (on_1_a, "pending", 2),  # opportunity 1 has two open reports
        (on_1_b, "pending", 2),
        (oldest_on_4, "pending", 1),
    ]
    assert _queue(session, status=["dismissed"]) == [(dismissed_on_4, "dismissed", 1)]
    assert [r[0] for r in _queue(session, opportunity_id=4)] == [dismissed_on_4, oldest_on_4]

    page = report_service.list_for_admin(
        session, AdminReportParams(status=["pending"], limit=1, offset=2)
    )
    assert [r.report_id for r in page.items] == [oldest_on_4]
    assert page.total == 3
    assert page.items[0].reporter.full_name == "Alex Chen"  # admins see who reported
