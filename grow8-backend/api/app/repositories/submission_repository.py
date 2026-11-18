"""Work submissions and their attachments (ADR 0012). Locking the application and the
opportunity's status is done with application_repository / opportunity_repository."""

from grow8_common.models import SubmissionAttachment, WorkSubmission
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload


def get_for_application(session: Session, application_id: int) -> WorkSubmission | None:
    """The application's submission (at most one) with its attachments."""
    stmt = (
        select(WorkSubmission)
        .options(selectinload(WorkSubmission.attachments))
        .where(WorkSubmission.application_id == application_id)
    )
    return session.scalars(stmt).first()


def get_attachment(
    session: Session, submission_id: int, attachment_id: int
) -> SubmissionAttachment | None:
    """The attachment, only if it belongs to that submission."""
    stmt = select(SubmissionAttachment).where(
        SubmissionAttachment.attachment_id == attachment_id,
        SubmissionAttachment.submission_id == submission_id,
    )
    return session.scalars(stmt).first()


def add(session: Session, submission: WorkSubmission) -> WorkSubmission:
    """Insert the submission and the attachments added to it. Flushes, so the triggers
    and unique keys are checked here (the caller maps their errors)."""
    session.add(submission)
    session.flush()
    return submission
