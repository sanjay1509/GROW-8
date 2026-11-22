"""The owning creator approves or rejects submitted work (ADR 0013).

Every rule is checked here first for a clear error, and again by the database
(trg_work_verification_bi, uq_work_verification_submission), so a race ends in the same
error, never a 500.
"""

from datetime import datetime

from grow8_common.events import EventType, WorkRejectedPayload, WorkVerifiedPayload
from grow8_common.models import (
    OpportunityStatus,
    ReviewDecision,
    UserAccount,
    WorkSubmission,
    WorkVerification,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.exceptions import AppError, ConflictError, NotFoundError, UnprocessableError
from app.core.time import utcnow
from app.events.publisher import EventPublisher
from app.repositories import opportunity_repository, submission_repository
from app.repositories.db_errors import duplicate_key, trigger_rule
from app.schemas.submission import SubmissionRead, VerificationCreate
from app.services import verification_rules

_DUPLICATE_KEY = "uq_work_verification_submission"

_REFUSALS = {
    "VERIFIED_HOURS_EXCEED_CLAIMED": "Verified hours can't be more than the hours claimed",
    "REJECTION_COMMENT_REQUIRED": "Say why the work is rejected in a comment",
}


def _now() -> datetime:
    # DATETIME columns have no fractional seconds; drop them rather than let MySQL round.
    return utcnow().replace(microsecond=0)


def _not_found() -> NotFoundError:
    return NotFoundError("Submission not found", code="SUBMISSION_NOT_FOUND")


def _already_verified() -> ConflictError:
    return ConflictError(
        "This submission has already been verified", code="SUBMISSION_ALREADY_VERIFIED"
    )


def _owns(submission: WorkSubmission, user: UserAccount) -> bool:
    return submission.application.opportunity.organization.owner_user_id == user.user_id


def _error_from_db(exc: DBAPIError) -> AppError | None:
    if trigger_rule(exc) == "verifier_not_owner":
        return _not_found()
    if duplicate_key(exc, _DUPLICATE_KEY):
        return _already_verified()
    return None


def _check_can_verify(
    session: Session, submission: WorkSubmission, data: VerificationCreate
) -> None:
    """The rules, in the order a creator would want to hear about them. The caller holds
    the submission's row lock."""
    if submission_repository.is_verified(session, submission.submission_id):
        raise _already_verified()
    # Shared lock, after the submission's: a concurrent cancel waits for this decision,
    # or this sees the cancel (the same idea as deciding an application, ADR 0011).
    if (
        opportunity_repository.lock_status_for_share(session, submission.application.opportunity_id)
        == OpportunityStatus.CANCELLED
    ):
        raise ConflictError(
            "This opportunity was cancelled, so its work can't be verified",
            code="OPPORTUNITY_CANCELLED",
        )
    refusal = verification_rules.verification_refusal(
        data.decision, data.verified_hours, submission.hours_claimed, data.comment
    )
    if refusal:
        raise UnprocessableError(_REFUSALS[refusal], code=refusal)


def _insert(session: Session, verification: WorkVerification) -> None:
    """Insert and commit, turning a broken database rule into the matching error."""
    try:
        submission_repository.add_verification(session, verification)
        session.commit()
    except DBAPIError as exc:
        session.rollback()
        error = _error_from_db(exc)
        if error is None:
            raise
        raise error from exc


def _publish(
    publisher: EventPublisher,
    submission: WorkSubmission,
    verification: WorkVerification,
    correlation_id: str | None,
) -> None:
    application = submission.application
    common = {
        "verification_id": verification.verification_id,
        "submission_id": submission.submission_id,
        "application_id": application.application_id,
        "opportunity_id": application.opportunity_id,
        "organization_id": application.opportunity.organization_id,
        "opportunity_title": application.opportunity.title,
        "contributor_id": application.contributor_id,
    }
    if verification.decision == ReviewDecision.APPROVED:
        payload = WorkVerifiedPayload(**common, verified_hours=verification.verified_hours)
        publisher.publish(payload, EventType.WORK_VERIFIED, correlation_id)
    else:
        payload = WorkRejectedPayload(**common, comment=verification.comment or "")
        publisher.publish(payload, EventType.WORK_REJECTED, correlation_id)


def verify(
    session: Session,
    creator: UserAccount,
    submission_id: int,
    data: VerificationCreate,
    publisher: EventPublisher,
    correlation_id: str | None,
) -> SubmissionRead:
    """Approve the work with the hours you verify, or reject it with a comment. Only
    the creator who owns the opportunity decides, once per submission. The contributor
    is told the outcome."""
    submission = submission_repository.get_for_update(session, submission_id)
    if submission is None or not _owns(submission, creator):
        raise _not_found()
    _check_can_verify(session, submission, data)

    verification = WorkVerification(
        submission_id=submission.submission_id,
        verified_by_user_id=creator.user_id,
        decision=data.decision,
        verified_hours=data.verified_hours,
        comment=data.comment,
        verified_at=_now(),
    )
    _insert(session, verification)
    # Sessions don't expire on commit, so attach the new row to the loaded submission.
    set_committed_value(submission, "verification", verification)

    _publish(publisher, submission, verification, correlation_id)
    return SubmissionRead.from_model(submission)
