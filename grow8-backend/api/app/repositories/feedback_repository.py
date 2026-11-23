"""Feedback, admin reviews and ratings (ADR 0015)."""

from collections.abc import Sequence
from decimal import Decimal

from grow8_common.models import AdminReview, Application, Feedback, Opportunity, ReviewDecision
from sqlalchemy import ColumnElement, Select, func, or_, select, text
from sqlalchemy.orm import Session, joinedload

# Everything a feedback response shows and everything deciding who may see it needs.
_EAGER = (
    joinedload(Feedback.application)
    .joinedload(Application.opportunity)
    .joinedload(Opportunity.organization),
    joinedload(Feedback.author),
    joinedload(Feedback.subject),
    joinedload(Feedback.review),
)

# Status filter value (feedback_rules.FeedbackStatus) -> condition. "pending" means no
# review row yet, so the queue outer-joins admin_review.
_STATUS_CONDITIONS: dict[str, ColumnElement[bool]] = {
    "pending": AdminReview.review_id.is_(None),
    "approved": AdminReview.decision == ReviewDecision.APPROVED,
    "rejected": AdminReview.decision == ReviewDecision.REJECTED,
}


def _by_id(feedback_id: int) -> Select[tuple[Feedback]]:
    return select(Feedback).options(*_EAGER).where(Feedback.feedback_id == feedback_id)


def get(session: Session, feedback_id: int) -> Feedback | None:
    return session.scalars(_by_id(feedback_id)).unique().first()


def get_for_update(session: Session, feedback_id: int) -> Feedback | None:
    """Load and row-lock the feedback (only its own row) until the transaction ends, so
    two reviews of it are serialized."""
    stmt = _by_id(feedback_id).with_for_update(of=Feedback)
    return session.scalars(stmt).unique().first()


def for_application(session: Session, application_id: int) -> Sequence[Feedback]:
    """The application's feedback: at most one per participant."""
    stmt = (
        select(Feedback)
        .options(*_EAGER)
        .where(Feedback.application_id == application_id)
        .order_by(Feedback.feedback_id)
    )
    return session.scalars(stmt).unique().all()


def exists_for_author(session: Session, application_id: int, author_user_id: int) -> bool:
    stmt = select(Feedback.feedback_id).where(
        Feedback.application_id == application_id, Feedback.author_user_id == author_user_id
    )
    return session.scalar(stmt) is not None


def is_reviewed(session: Session, feedback_id: int) -> bool:
    """Whether the feedback already has a review. A locking read (FOR SHARE), so it sees
    one committed after this transaction's snapshot was taken; call it while holding
    the feedback's row lock."""
    stmt = (
        select(AdminReview.review_id)
        .where(AdminReview.feedback_id == feedback_id)
        .with_for_update(read=True)
    )
    return session.scalar(stmt) is not None


def add(session: Session, feedback: Feedback) -> Feedback:
    """Insert the feedback. Flushes, so trg_feedback_bi and
    uq_feedback_application_author are checked here (the caller maps their errors)."""
    session.add(feedback)
    session.flush()
    return feedback


def add_review(session: Session, review: AdminReview) -> AdminReview:
    """Insert the review. Flushes, so uq_admin_review_feedback is checked here."""
    session.add(review)
    session.flush()
    return review


def list_for_admin(
    session: Session,
    statuses: Sequence[str],
    discrepancy: bool | None,
    limit: int,
    offset: int,
) -> tuple[Sequence[Feedback], int]:
    """One page of the review queue, discrepancy reports first, then oldest first, plus
    the total. `statuses` are "pending", "approved" and "rejected"; none means all."""
    conds: list[ColumnElement[bool]] = []
    if statuses:
        conds.append(or_(*(_STATUS_CONDITIONS[s] for s in statuses)))
    if discrepancy is not None:
        conds.append(Feedback.reports_discrepancy.is_(discrepancy))

    def scoped(stmt: Select) -> Select:
        return stmt.outerjoin(Feedback.review).where(*conds)

    total = session.scalar(scoped(select(func.count(Feedback.feedback_id)))) or 0
    stmt = (
        scoped(select(Feedback))
        .options(*_EAGER)
        .order_by(Feedback.reports_discrepancy.desc(), Feedback.created_at, Feedback.feedback_id)
        .limit(limit)
        .offset(offset)
    )
    return session.scalars(stmt).unique().all(), total


def user_rating(session: Session, user_id: int) -> tuple[Decimal | None, int]:
    """The user's average rating and approved feedback count, from v_user_rating (which
    counts approved feedback only). A user with none has no row: (None, 0)."""
    row = session.execute(
        text(
            "SELECT average_rating, approved_feedback_count FROM v_user_rating "
            "WHERE user_id = :user_id"
        ),
        {"user_id": user_id},
    ).first()
    if row is None:
        return None, 0
    return row.average_rating, int(row.approved_feedback_count)
