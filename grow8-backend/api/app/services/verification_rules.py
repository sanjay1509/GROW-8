"""Pure work-verification rules (no DB, no HTTP) so they are easy to unit test (ADR 0013).

The statuses here are derived, never stored: a submission is awaiting until it has a
`work_verification` row, and the row's decision says the rest.
"""

from decimal import Decimal
from enum import StrEnum

from grow8_common.models import ReviewDecision


class SubmissionStatus(StrEnum):
    AWAITING = "awaiting"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkStatus(StrEnum):
    """Where an application's work stands, shown on every application."""

    NOT_SUBMITTED = "not_submitted"
    AWAITING_VERIFICATION = "awaiting_verification"
    COMPLETED = "completed"
    WORK_REJECTED = "work_rejected"


def submission_status(decision: ReviewDecision | None) -> SubmissionStatus:
    """A submission's status from its verification's decision (None: not verified yet)."""
    if decision is None:
        return SubmissionStatus.AWAITING
    return SubmissionStatus(decision.value)


_WORK_STATUS = {
    SubmissionStatus.AWAITING: WorkStatus.AWAITING_VERIFICATION,
    SubmissionStatus.APPROVED: WorkStatus.COMPLETED,
    SubmissionStatus.REJECTED: WorkStatus.WORK_REJECTED,
}


def work_status(submitted: bool, decision: ReviewDecision | None) -> WorkStatus:
    """An application's work status: whether work was submitted and, if so, what the
    creator decided. Approved work counts as completed."""
    if not submitted:
        return WorkStatus.NOT_SUBMITTED
    return _WORK_STATUS[submission_status(decision)]


def verification_refusal(
    decision: ReviewDecision,
    verified_hours: Decimal | None,
    hours_claimed: Decimal,
    comment: str | None,
) -> str | None:
    """Error code for why this decision can't be recorded, or None if it can.

    Approving verifies at most the hours claimed (fewer is fine). Rejecting needs a
    comment, so the contributor learns why. Whether hours are present at all for each
    decision is checked by the request schema."""
    if decision == ReviewDecision.APPROVED:
        if verified_hours is not None and verified_hours > hours_claimed:
            return "VERIFIED_HOURS_EXCEED_CLAIMED"
        return None
    if not (comment and comment.strip()):
        return "REJECTION_COMMENT_REQUIRED"
    return None
