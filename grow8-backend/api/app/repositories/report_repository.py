"""Opportunity reports and their reviews (ADR 0016). Locking the opportunity row is
done with opportunity_repository: every review locks the opportunity first, then the
report (see ADR 0016 decision 5)."""

from collections.abc import Sequence
from datetime import datetime

from grow8_common.models import (
    Application,
    Opportunity,
    OpportunityReport,
    ReportDecision,
    ReportReason,
    ReportReview,
    WorkSubmission,
)
from grow8_common.models.users import CreatorOrganization
from sqlalchemy import ColumnElement, Select, exists, func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

_EAGER = (
    joinedload(OpportunityReport.opportunity)
    .joinedload(Opportunity.organization)
    .joinedload(CreatorOrganization.owner),
    joinedload(OpportunityReport.reporter),
    joinedload(OpportunityReport.review),
)

# Status filter value (report_rules.ReportStatus) -> condition. "pending" means no
# review row yet, so the queue outer-joins report_review.
_STATUS_CONDITIONS: dict[str, ColumnElement[bool]] = {
    "pending": ReportReview.review_id.is_(None),
    "upheld": ReportReview.decision == ReportDecision.UPHELD,
    "dismissed": ReportReview.decision == ReportDecision.DISMISSED,
}


def _by_id(report_id: int) -> Select[tuple[OpportunityReport]]:
    return (
        select(OpportunityReport).options(*_EAGER).where(OpportunityReport.report_id == report_id)
    )


def get(session: Session, report_id: int) -> OpportunityReport | None:
    return session.scalars(_by_id(report_id)).unique().first()


def opportunity_id_of(session: Session, report_id: int) -> int | None:
    """Only the report's opportunity_id, so the opportunity can be locked before anything
    about it is loaded (a later locking read wouldn't refresh an already-loaded row)."""
    stmt = select(OpportunityReport.opportunity_id).where(OpportunityReport.report_id == report_id)
    return session.scalar(stmt)


def get_for_update(session: Session, report_id: int) -> OpportunityReport | None:
    """Load and row-lock the report (only its own row). Lock the opportunity first."""
    stmt = _by_id(report_id).with_for_update(of=OpportunityReport)
    return session.scalars(stmt).unique().first()


def is_reviewed(session: Session, report_id: int) -> bool:
    """A locking read (FOR SHARE), so it sees a review committed after this
    transaction's snapshot was taken."""
    stmt = (
        select(ReportReview.review_id)
        .where(ReportReview.report_id == report_id)
        .with_for_update(read=True)
    )
    return session.scalar(stmt) is not None


def exists_for_reporter(session: Session, opportunity_id: int, reporter_user_id: int) -> bool:
    stmt = select(OpportunityReport.report_id).where(
        OpportunityReport.opportunity_id == opportunity_id,
        OpportunityReport.reporter_user_id == reporter_user_id,
    )
    return session.scalar(stmt) is not None


def pending_for_opportunity_for_update(
    session: Session, opportunity_id: int
) -> Sequence[OpportunityReport]:
    """The opportunity's reports that have no review yet, row-locked. A locking read, so
    it sees reports and reviews committed after this transaction's snapshot."""
    stmt = (
        select(OpportunityReport)
        .outerjoin(OpportunityReport.review)
        .where(
            OpportunityReport.opportunity_id == opportunity_id,
            ReportReview.review_id.is_(None),
        )
        .order_by(OpportunityReport.report_id)
        .with_for_update(of=OpportunityReport)
    )
    return session.scalars(stmt).all()


def has_submission_locking(session: Session, opportunity_id: int) -> bool:
    """Whether work was submitted for any application to the opportunity. A locking read
    (FOR SHARE), so it sees a submission committed after this transaction's snapshot."""
    stmt = (
        select(WorkSubmission.submission_id)
        .join(Application, Application.application_id == WorkSubmission.application_id)
        .where(Application.opportunity_id == opportunity_id)
        .limit(1)
        .with_for_update(read=True)
    )
    return session.scalar(stmt) is not None


def reporters_of(session: Session, report_ids: Sequence[int]) -> list[int]:
    """The distinct reporters of these reports, in id order."""
    if not report_ids:
        return []
    stmt = (
        select(OpportunityReport.reporter_user_id)
        .where(OpportunityReport.report_id.in_(report_ids))
        .distinct()
        .order_by(OpportunityReport.reporter_user_id)
    )
    return list(session.scalars(stmt))


def count_open(session: Session, opportunity_id: int) -> int:
    """Pending reports on the opportunity."""
    stmt = (
        select(func.count(OpportunityReport.report_id))
        .outerjoin(OpportunityReport.review)
        .where(
            OpportunityReport.opportunity_id == opportunity_id,
            ReportReview.review_id.is_(None),
        )
    )
    return session.scalar(stmt) or 0


def add(session: Session, report: OpportunityReport) -> OpportunityReport:
    """Insert the report. Flushes, so trg_opportunity_report_bi and
    uq_opportunity_report_reporter are checked here (the caller maps their errors)."""
    session.add(report)
    session.flush()
    return report


def add_reviews(session: Session, reviews: Sequence[ReportReview]) -> None:
    """Insert the reviews. Flushes, so uq_report_review_report is checked here."""
    session.add_all(reviews)
    session.flush()


def _open_count_by_opportunity() -> Select:
    """opportunity_id -> number of pending reports, as a subquery."""
    pending = aliased(OpportunityReport)
    reviewed = aliased(ReportReview)
    return (
        select(pending.opportunity_id, func.count(pending.report_id).label("open_reports"))
        .where(~exists().where(reviewed.report_id == pending.report_id))
        .group_by(pending.opportunity_id)
    )


def list_for_admin(
    session: Session,
    statuses: Sequence[str],
    opportunity_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[OpportunityReport, int]], int]:
    """One page of the review queue with each report's open-report count for its
    opportunity, plus the total. The most-reported opportunities come first, then the
    oldest report. `statuses` are "pending", "upheld" and "dismissed"; none means all."""
    conds: list[ColumnElement[bool]] = []
    if statuses:
        conds.append(or_(*(_STATUS_CONDITIONS[s] for s in statuses)))
    if opportunity_id is not None:
        conds.append(OpportunityReport.opportunity_id == opportunity_id)

    total = (
        session.scalar(
            select(func.count(OpportunityReport.report_id))
            .outerjoin(OpportunityReport.review)
            .where(*conds)
        )
        or 0
    )
    counts = _open_count_by_opportunity().subquery()
    open_reports = func.coalesce(counts.c.open_reports, 0)
    stmt = (
        select(OpportunityReport, open_reports)
        .outerjoin(OpportunityReport.review)
        .outerjoin(counts, counts.c.opportunity_id == OpportunityReport.opportunity_id)
        .options(*_EAGER)
        .where(*conds)
        .order_by(open_reports.desc(), OpportunityReport.created_at, OpportunityReport.report_id)
        .limit(limit)
        .offset(offset)
    )
    rows = session.execute(stmt).unique().all()
    return [(report, int(count)) for report, count in rows], total


def list_for_reporter(
    session: Session, reporter_user_id: int, limit: int, offset: int
) -> tuple[Sequence[OpportunityReport], int]:
    """One page of a contributor's own reports, newest first, plus the total."""
    cond = OpportunityReport.reporter_user_id == reporter_user_id
    total = session.scalar(select(func.count(OpportunityReport.report_id)).where(cond)) or 0
    stmt = (
        select(OpportunityReport)
        .options(*_EAGER)
        .where(cond)
        .order_by(OpportunityReport.created_at.desc(), OpportunityReport.report_id.desc())
        .limit(limit)
        .offset(offset)
    )
    return session.scalars(stmt).unique().all(), total


def upheld_on(
    session: Session, opportunity_id: int
) -> list[tuple[ReportReason, datetime, str | None]]:
    """(reason, reviewed_at, admin reason) for every upheld report on the opportunity."""
    stmt = (
        select(OpportunityReport.reason, ReportReview.reviewed_at, ReportReview.reason)
        .join(ReportReview, ReportReview.report_id == OpportunityReport.report_id)
        .where(
            OpportunityReport.opportunity_id == opportunity_id,
            ReportReview.decision == ReportDecision.UPHELD,
        )
        .order_by(ReportReview.reviewed_at, OpportunityReport.report_id)
    )
    return [(r[0], r[1], r[2]) for r in session.execute(stmt).all()]
