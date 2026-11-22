"""Feedback between the two people on an application, admin review, and ratings
(ADR 0015).

Every rule is checked here first for a clear error, and again by the database
(trg_feedback_bi, uq_feedback_application_author, uq_admin_review_feedback), so a race
ends in the same error, never a 500.
"""

from collections.abc import Callable
from datetime import datetime

from grow8_common.events import (
    EventType,
    FeedbackApprovedPayload,
    FeedbackRejectedPayload,
    FeedbackSubmittedPayload,
)
from grow8_common.models import AdminReview, Application, Feedback, ReviewDecision, UserAccount
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.exceptions import AppError, ConflictError, NotFoundError, UnprocessableError
from app.core.time import utcnow
from app.events.publisher import EventPublisher
from app.repositories import application_repository, feedback_repository, user_repository
from app.repositories.db_errors import duplicate_key, trigger_rule
from app.schemas.common import Page
from app.schemas.feedback import (
    AdminFeedbackParams,
    ApplicationFeedback,
    FeedbackCreate,
    FeedbackRead,
    ReviewCreate,
    UserRating,
)
from app.services import feedback_rules
from app.services.feedback_rules import ParticipantRole


def _now() -> datetime:
    # DATETIME columns have no fractional seconds; drop them rather than let MySQL round.
    return utcnow().replace(microsecond=0)


def _application_not_found() -> NotFoundError:
    return NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")


def _feedback_not_found() -> NotFoundError:
    return NotFoundError("Feedback not found", code="FEEDBACK_NOT_FOUND")


def _already_submitted() -> ConflictError:
    return ConflictError(
        "You have already left feedback on this application", code="FEEDBACK_ALREADY_SUBMITTED"
    )


def _already_reviewed() -> ConflictError:
    return ConflictError(
        "This feedback has already been reviewed", code="FEEDBACK_ALREADY_REVIEWED"
    )


def _role(application: Application, user: UserAccount) -> ParticipantRole | None:
    return feedback_rules.participant_role(
        user.user_id,
        application.contributor_id,
        application.opportunity.organization.owner_user_id,
    )


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
# Participants
# ---------------------------------------------------------------------------


def _check_can_give(session: Session, application: Application, author: UserAccount) -> None:
    submission = application.submission
    if submission is None or submission.verification is None:
        raise ConflictError(
            "Feedback can be left once the work has been verified", code="WORK_NOT_VERIFIED"
        )
    if feedback_repository.exists_for_author(session, application.application_id, author.user_id):
        raise _already_submitted()


def submit(
    session: Session,
    author: UserAccount,
    application_id: int,
    data: FeedbackCreate,
    publisher: EventPublisher,
    correlation_id: str | None,
) -> FeedbackRead:
    """Leave feedback about the other participant on an application whose work has been
    verified. Once per author per application. It waits for an admin's review, and the
    admins are told."""
    application = application_repository.get(session, application_id)
    role = _role(application, author) if application else None
    if application is None or role is None:
        raise _application_not_found()
    _check_can_give(session, application, author)

    owner_id = application.opportunity.organization.owner_user_id
    feedback = Feedback(
        application_id=application.application_id,
        author_user_id=author.user_id,
        subject_user_id=feedback_rules.subject_of(role, application.contributor_id, owner_id),
        rating=data.rating,
        comment=data.comment,
        reports_discrepancy=data.reports_discrepancy,
        created_at=_now(),
    )
    _commit(
        session,
        lambda: feedback_repository.add(session, feedback),
        {
            "feedback_participants": _application_not_found(),
            "uq_feedback_application_author": _already_submitted(),
        },
    )

    publisher.publish(
        FeedbackSubmittedPayload(
            feedback_id=feedback.feedback_id,
            application_id=application.application_id,
            opportunity_id=application.opportunity_id,
            opportunity_title=application.opportunity.title,
            author_user_id=author.user_id,
            author_name=author.full_name,
            author_role=role,
            subject_user_id=feedback.subject_user_id,
            rating=feedback.rating,
            reports_discrepancy=feedback.reports_discrepancy,
        ),
        EventType.FEEDBACK_SUBMITTED,
        correlation_id,
    )
    # The author, subject and (empty) review load on first access.
    return FeedbackRead.from_model(feedback)


def for_application(
    session: Session, user: UserAccount, application_id: int
) -> ApplicationFeedback:
    """The feedback on an application the caller may see: their own, in any status, and
    the other participant's about them once approved. To anyone else the application
    doesn't exist."""
    application = application_repository.get(session, application_id)
    if application is None or _role(application, user) is None:
        raise _application_not_found()

    given = received = None
    for feedback in feedback_repository.for_application(session, application_id):
        read = FeedbackRead.from_model(feedback)
        if not feedback_rules.visible_to(
            user.user_id, feedback.author_user_id, feedback.subject_user_id, read.status
        ):
            continue
        if feedback.author_user_id == user.user_id:
            given = read
        else:
            received = read
    return ApplicationFeedback(given=given, received=received)


# ---------------------------------------------------------------------------
# Admins
# ---------------------------------------------------------------------------


def list_for_admin(session: Session, params: AdminFeedbackParams) -> Page[FeedbackRead]:
    """The review queue: discrepancy reports first, then oldest first."""
    items, total = feedback_repository.list_for_admin(
        session,
        [s.value for s in params.status],
        params.discrepancy,
        params.limit,
        params.offset,
    )
    return Page[FeedbackRead](
        items=[FeedbackRead.from_model(f) for f in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def _check_can_review(session: Session, feedback: Feedback, data: ReviewCreate) -> None:
    """The caller holds the feedback's row lock."""
    if feedback_repository.is_reviewed(session, feedback.feedback_id):
        raise _already_reviewed()
    refusal = feedback_rules.review_refusal(data.decision, data.reason)
    if refusal:
        raise UnprocessableError("Say why the feedback is rejected in a reason", code=refusal)


def _publish_review(
    publisher: EventPublisher,
    feedback: Feedback,
    review: AdminReview,
    correlation_id: str | None,
) -> None:
    application = feedback.application
    role: ParticipantRole = (
        "contributor" if feedback.author_user_id == application.contributor_id else "creator"
    )
    common = {
        "feedback_id": feedback.feedback_id,
        "application_id": application.application_id,
        "opportunity_id": application.opportunity_id,
        "opportunity_title": application.opportunity.title,
        "author_user_id": feedback.author_user_id,
        "author_role": role,
    }
    if review.decision == ReviewDecision.APPROVED:
        payload = FeedbackApprovedPayload(
            **common,
            author_name=feedback.author.full_name,
            subject_user_id=feedback.subject_user_id,
            subject_name=feedback.subject.full_name,
            rating=feedback.rating,
        )
        publisher.publish(payload, EventType.FEEDBACK_APPROVED, correlation_id)
    else:
        payload = FeedbackRejectedPayload(
            **common, subject_name=feedback.subject.full_name, reason=review.reason or ""
        )
        publisher.publish(payload, EventType.FEEDBACK_REJECTED, correlation_id)


def review(
    session: Session,
    admin: UserAccount,
    feedback_id: int,
    data: ReviewCreate,
    publisher: EventPublisher,
    correlation_id: str | None,
) -> FeedbackRead:
    """Approve feedback, so it is published and counts toward the subject's rating, or
    reject it with a reason. Each feedback is reviewed once."""
    feedback = feedback_repository.get_for_update(session, feedback_id)
    if feedback is None:
        raise _feedback_not_found()
    _check_can_review(session, feedback, data)

    admin_review = AdminReview(
        feedback_id=feedback.feedback_id,
        admin_user_id=admin.user_id,
        decision=data.decision,
        reason=data.reason,
        reviewed_at=_now(),
    )
    _commit(
        session,
        lambda: feedback_repository.add_review(session, admin_review),
        {"uq_admin_review_feedback": _already_reviewed()},
    )
    # Sessions don't expire on commit, so attach the new row to the loaded feedback.
    set_committed_value(feedback, "review", admin_review)

    _publish_review(publisher, feedback, admin_review, correlation_id)
    return FeedbackRead.from_model(feedback)


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------


def rating(session: Session, user_id: int) -> UserRating:
    """A user's public rating, from approved feedback only."""
    user = user_repository.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise NotFoundError("User not found", code="USER_NOT_FOUND")
    average, count = feedback_repository.user_rating(session, user_id)
    return UserRating(user_id=user_id, average_rating=average, approved_feedback_count=count)
