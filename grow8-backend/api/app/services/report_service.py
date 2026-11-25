"""Contributors report opportunities; admins dismiss reports or take the opportunity
down (ADR 0016).

Every rule is checked here first for a clear error, and again by the database
(trg_opportunity_report_bi, uq_opportunity_report_reporter, uq_report_review_report,
chk_report_review_reason), so a race ends in the same error, never a 500.
"""

from collections.abc import Callable
from datetime import datetime

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
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.exceptions import AppError, ConflictError, NotFoundError, UnprocessableError
from app.core.time import utcnow
from app.events.publisher import EventPublisher
from app.repositories import opportunity_repository, report_repository
from app.repositories.db_errors import duplicate_key, trigger_rule
from app.schemas.common import Page
from app.schemas.report import (
    AdminReportParams,
    AdminReportRead,
    MyReportParams,
    ReportCreate,
    ReportRead,
    ReportReviewCreate,
    TakedownRead,
)
from app.services import report_rules

_CONFLICT_MESSAGES = {
    "OPPORTUNITY_CANCELLED": "This opportunity is cancelled",
    "WORK_ALREADY_SUBMITTED": (
        "Work has already been submitted for this opportunity, so it can't be taken down"
    ),
}


def _now() -> datetime:
    # DATETIME columns have no fractional seconds; drop them rather than let MySQL round.
    return utcnow().replace(microsecond=0)


def _opportunity_not_found() -> NotFoundError:
    return NotFoundError("Opportunity not found", code="OPPORTUNITY_NOT_FOUND")


def _report_not_found() -> NotFoundError:
    return NotFoundError("Report not found", code="REPORT_NOT_FOUND")


def _cancelled() -> ConflictError:
    return ConflictError(_CONFLICT_MESSAGES["OPPORTUNITY_CANCELLED"], code="OPPORTUNITY_CANCELLED")


def _already_reported() -> ConflictError:
    return ConflictError(
        "You have already reported this opportunity", code="OPPORTUNITY_ALREADY_REPORTED"
    )


def _already_reviewed() -> ConflictError:
    return ConflictError("This report has already been reviewed", code="REPORT_ALREADY_REVIEWED")


def _commit(session: Session, insert: Callable[[], object], errors: dict[str, AppError]) -> None:
    """Run the repository insert and commit, turning a broken database rule into the
    matching error. `errors` maps a trigger rule or unique key name to the error."""
    try:
        insert()
        session.commit()
    except DBAPIError as exc:
        session.rollback()
        rule = trigger_rule(exc)
        for name, error in errors.items():
            if rule == name or duplicate_key(exc, name):
                raise error from exc
        raise


# ---------------------------------------------------------------------------
# Contributors
# ---------------------------------------------------------------------------


def submit(
    session: Session,
    contributor: UserAccount,
    opportunity_id: int,
    data: ReportCreate,
    publisher: EventPublisher,
    correlation_id: str | None,
) -> ReportRead:
    """Report a published opportunity, once. The admins are told."""
    # Shared lock on the status: a takedown or cancel in progress finishes first, so a
    # report either lands before it (and is upheld with the rest) or sees the cancel.
    status = opportunity_repository.lock_status_for_share(session, opportunity_id)
    if status is None or status == OpportunityStatus.DRAFT:
        raise _opportunity_not_found()
    if not report_rules.can_be_reported(status):
        raise _cancelled()
    if report_repository.exists_for_reporter(session, opportunity_id, contributor.user_id):
        raise _already_reported()

    report = OpportunityReport(
        opportunity_id=opportunity_id,
        reporter_user_id=contributor.user_id,
        reason=data.reason,
        details=data.details,
        created_at=_now(),
    )
    _commit(
        session,
        lambda: report_repository.add(session, report),
        {
            "report_requires_published": _cancelled(),
            "uq_opportunity_report_reporter": _already_reported(),
        },
    )

    publisher.publish(
        OpportunityReportedPayload(
            report_id=report.report_id,
            opportunity_id=opportunity_id,
            opportunity_title=report.opportunity.title,
            reason=report.reason.value,
            open_reports=report_repository.count_open(session, opportunity_id),
        ),
        EventType.OPPORTUNITY_REPORTED,
        correlation_id,
    )
    return ReportRead.from_model(report)


def list_mine(
    session: Session, contributor: UserAccount, params: MyReportParams
) -> Page[ReportRead]:
    """Your reports, newest first."""
    items, total = report_repository.list_for_reporter(
        session, contributor.user_id, params.limit, params.offset
    )
    return Page[ReportRead](
        items=[ReportRead.from_model(r) for r in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


# ---------------------------------------------------------------------------
# Creators
# ---------------------------------------------------------------------------


def takedown_for_creator(
    session: Session, creator: UserAccount, opportunity_id: int
) -> TakedownRead:
    """Why the creator's own opportunity was taken down: when, the admin's reason (the
    same for every report it upheld) and the report categories. Reporters stay anonymous,
    so their own words and their number are never included (ADR 0016 decision 2)."""
    opportunity = opportunity_repository.get(session, opportunity_id)
    if opportunity is None or opportunity.organization.owner_user_id != creator.user_id:
        raise _opportunity_not_found()
    upheld = report_repository.upheld_on(session, opportunity_id)
    if not upheld:
        raise NotFoundError("This opportunity was not taken down", code="TAKEDOWN_NOT_FOUND")
    _, taken_down_at, admin_reason = upheld[0]
    return TakedownRead(
        opportunity_id=opportunity_id,
        taken_down_at=taken_down_at,
        admin_reason=admin_reason or "",
        reasons=sorted({reason for reason, _, _ in upheld}),
    )


# ---------------------------------------------------------------------------
# Admins
# ---------------------------------------------------------------------------


def list_for_admin(session: Session, params: AdminReportParams) -> Page[AdminReportRead]:
    """The review queue: most-reported opportunities first, then the oldest report."""
    rows, total = report_repository.list_for_admin(
        session,
        [s.value for s in params.status],
        params.opportunity_id,
        params.limit,
        params.offset,
    )
    return Page[AdminReportRead](
        items=[AdminReportRead.from_report(report, count) for report, count in rows],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def _take_down(
    session: Session, admin: UserAccount, opportunity: Opportunity, reason: str
) -> list[ReportReview]:
    """Cancel the opportunity and uphold every pending report on it, the one being
    reviewed included. The caller holds the opportunity's and the report's locks."""
    refusal = report_rules.takedown_refusal(
        opportunity.status,
        report_repository.has_submission_locking(session, opportunity.opportunity_id),
    )
    if refusal:
        raise ConflictError(_CONFLICT_MESSAGES[refusal], code=refusal)

    now = _now()
    pending = report_repository.pending_for_opportunity_for_update(
        session, opportunity.opportunity_id
    )
    opportunity.status = OpportunityStatus.CANCELLED
    return [
        ReportReview(
            report_id=report.report_id,
            admin_user_id=admin.user_id,
            decision=ReportDecision.UPHELD,
            reason=reason,
            reviewed_at=now,
        )
        for report in pending
    ]


def _dismiss(admin: UserAccount, report_id: int, reason: str | None) -> list[ReportReview]:
    return [
        ReportReview(
            report_id=report_id,
            admin_user_id=admin.user_id,
            decision=ReportDecision.DISMISSED,
            reason=reason,
            reviewed_at=_now(),
        )
    ]


def _publish_review(
    session: Session,
    publisher: EventPublisher,
    opportunity: Opportunity,
    report: OpportunityReport,
    own: ReportReview,
    reviews: list[ReportReview],
    correlation_id: str | None,
) -> None:
    if own.decision == ReportDecision.UPHELD:
        payload = OpportunityTakenDownPayload(
            opportunity_id=opportunity.opportunity_id,
            organization_id=opportunity.organization_id,
            title=opportunity.title,
            reason=own.reason or "",
            reporter_user_ids=report_repository.reporters_of(
                session, [r.report_id for r in reviews]
            ),
        )
        publisher.publish(payload, EventType.OPPORTUNITY_TAKEN_DOWN, correlation_id)
    else:
        payload = ReportDismissedPayload(
            report_id=report.report_id,
            opportunity_id=opportunity.opportunity_id,
            opportunity_title=opportunity.title,
            reporter_user_id=report.reporter_user_id,
            reason=own.reason,
        )
        publisher.publish(payload, EventType.REPORT_DISMISSED, correlation_id)


def review(
    session: Session,
    admin: UserAccount,
    report_id: int,
    data: ReportReviewCreate,
    publisher: EventPublisher,
    correlation_id: str | None,
) -> AdminReportRead:
    """Dismiss a report, or uphold it and take the opportunity down. Each report is
    reviewed once; a takedown upholds every pending report on the opportunity."""
    opportunity_id = report_repository.opportunity_id_of(session, report_id)
    if opportunity_id is None:
        raise _report_not_found()
    # Lock order: the opportunity first, then the report (ADR 0016 decision 5).
    opportunity = opportunity_repository.get_for_update(session, opportunity_id)
    report = report_repository.get_for_update(session, report_id)
    if opportunity is None or report is None:
        raise _report_not_found()

    if report_repository.is_reviewed(session, report_id):
        raise _already_reviewed()
    refusal = report_rules.review_refusal(data.decision, data.reason)
    if refusal:
        raise UnprocessableError("Say why the opportunity is taken down in a reason", code=refusal)

    if data.decision == ReportDecision.UPHELD:
        reviews = _take_down(session, admin, opportunity, data.reason or "")
    else:
        reviews = _dismiss(admin, report_id, data.reason)
    _commit(
        session,
        lambda: report_repository.add_reviews(session, reviews),
        {"uq_report_review_report": _already_reviewed()},
    )
    own = next(r for r in reviews if r.report_id == report_id)
    # Sessions don't expire on commit, so attach the new row to the loaded report.
    set_committed_value(report, "review", own)

    _publish_review(session, publisher, opportunity, report, own, reviews, correlation_id)
    return AdminReportRead.from_report(
        report, report_repository.count_open(session, opportunity_id)
    )
