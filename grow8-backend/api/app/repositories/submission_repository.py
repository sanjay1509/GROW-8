"""Work submissions, their attachments and verifications (ADRs 0012, 0013). Locking the
application and the opportunity's status is done with application_repository /
opportunity_repository."""

from collections.abc import Sequence

from grow8_common.models import (
    Application,
    ContributorProfile,
    CreatorOrganization,
    Opportunity,
    ReviewDecision,
    SubmissionAttachment,
    WorkSubmission,
    WorkVerification,
)
from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

# Everything a submission response shows and everything deciding who may see it needs:
# the application with its opportunity, organization and applicant, the attachments
# and the verification.
_EAGER = (
    joinedload(WorkSubmission.application).options(
        joinedload(Application.opportunity).joinedload(Opportunity.organization),
        joinedload(Application.contributor).joinedload(ContributorProfile.user),
    ),
    selectinload(WorkSubmission.attachments),
    selectinload(WorkSubmission.verification),
)

# Status filter value (verification_rules.SubmissionStatus) -> condition. "awaiting"
# means no verification row yet, so the query outer-joins work_verification.
_STATUS_CONDITIONS: dict[str, ColumnElement[bool]] = {
    "awaiting": WorkVerification.verification_id.is_(None),
    "approved": WorkVerification.decision == ReviewDecision.APPROVED,
    "rejected": WorkVerification.decision == ReviewDecision.REJECTED,
}


def _by_id(submission_id: int) -> Select[tuple[WorkSubmission]]:
    return (
        select(WorkSubmission).options(*_EAGER).where(WorkSubmission.submission_id == submission_id)
    )


def get(session: Session, submission_id: int) -> WorkSubmission | None:
    """The submission with everything needed to show it and to decide who may see it."""
    return session.scalars(_by_id(submission_id)).unique().first()


def get_for_update(session: Session, submission_id: int) -> WorkSubmission | None:
    """Load and row-lock the submission (only its own row) until the transaction ends,
    so two verifications of it are serialized."""
    stmt = _by_id(submission_id).with_for_update(of=WorkSubmission)
    return session.scalars(stmt).unique().first()


def get_for_application(session: Session, application_id: int) -> WorkSubmission | None:
    """The application's submission (at most one)."""
    stmt = (
        select(WorkSubmission)
        .options(*_EAGER)
        .where(WorkSubmission.application_id == application_id)
    )
    return session.scalars(stmt).unique().first()


def get_attachment(
    session: Session, submission_id: int, attachment_id: int
) -> SubmissionAttachment | None:
    """The attachment, only if it belongs to that submission."""
    stmt = select(SubmissionAttachment).where(
        SubmissionAttachment.attachment_id == attachment_id,
        SubmissionAttachment.submission_id == submission_id,
    )
    return session.scalars(stmt).first()


def is_verified(session: Session, submission_id: int) -> bool:
    """Whether the submission already has a verification. A locking read (FOR SHARE),
    so it sees one committed after this transaction's snapshot was taken; call it
    while holding the submission's row lock."""
    stmt = (
        select(WorkVerification.verification_id)
        .where(WorkVerification.submission_id == submission_id)
        .with_for_update(read=True)
    )
    return session.scalar(stmt) is not None


def add(session: Session, submission: WorkSubmission) -> WorkSubmission:
    """Insert the submission and the attachments added to it. Flushes, so the triggers
    and unique keys are checked here (the caller maps their errors)."""
    session.add(submission)
    session.flush()
    return submission


def add_verification(session: Session, verification: WorkVerification) -> WorkVerification:
    """Insert the verification. Flushes, so trg_work_verification_bi and
    uq_work_verification_submission are checked here (the caller maps their errors)."""
    session.add(verification)
    session.flush()
    return verification


def list_received(
    session: Session,
    owner_user_id: int,
    opportunity_id: int | None,
    statuses: Sequence[str],
    limit: int,
    offset: int,
) -> tuple[Sequence[WorkSubmission], int]:
    """One page of submissions to opportunities of organizations the user owns
    (optionally just one of them), oldest first, plus the total. `statuses` are
    "awaiting", "approved" and "rejected"; none means all."""
    conds: list[ColumnElement[bool]] = [CreatorOrganization.owner_user_id == owner_user_id]
    if opportunity_id is not None:
        conds.append(Application.opportunity_id == opportunity_id)
    if statuses:
        conds.append(or_(*(_STATUS_CONDITIONS[s] for s in statuses)))

    def scoped(stmt: Select) -> Select:
        return (
            stmt.join(WorkSubmission.application)
            .join(Application.opportunity)
            .join(Opportunity.organization)
            .outerjoin(WorkSubmission.verification)
            .where(*conds)
        )

    total = session.scalar(scoped(select(func.count(WorkSubmission.submission_id)))) or 0
    stmt = (
        scoped(select(WorkSubmission))
        .options(*_EAGER)
        .order_by(WorkSubmission.submitted_at, WorkSubmission.submission_id)
        .limit(limit)
        .offset(offset)
    )
    return session.scalars(stmt).unique().all(), total
