"""Pure feedback rules (no DB, no HTTP) so they are easy to unit test (ADR 0015).

A feedback's status is derived, never stored: pending until it has an `admin_review`
row, then the review's decision (the same rule as v_feedback_status).
"""

from enum import StrEnum
from typing import Literal

from grow8_common.models import ReviewDecision

ParticipantRole = Literal["contributor", "creator"]


class FeedbackStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def feedback_status(decision: ReviewDecision | None) -> FeedbackStatus:
    """A feedback's status from its review's decision (None: not reviewed yet)."""
    if decision is None:
        return FeedbackStatus.PENDING
    return FeedbackStatus(decision.value)


def participant_role(
    user_id: int, contributor_id: int, owner_user_id: int
) -> ParticipantRole | None:
    """Which side of the application the user is on, or None if they aren't on it.
    The applicant and the owning creator are always different people (roles differ)."""
    if user_id == contributor_id:
        return "contributor"
    if user_id == owner_user_id:
        return "creator"
    return None


def subject_of(role: ParticipantRole, contributor_id: int, owner_user_id: int) -> int:
    """Feedback is always about the other participant."""
    return owner_user_id if role == "contributor" else contributor_id


def visible_to(
    user_id: int, author_user_id: int, subject_user_id: int, status: FeedbackStatus
) -> bool:
    """The author always sees their own feedback; the subject only once an admin has
    approved it, so pending and rejected feedback stays hidden from them."""
    if user_id == author_user_id:
        return True
    return user_id == subject_user_id and status == FeedbackStatus.APPROVED


def review_refusal(decision: ReviewDecision, reason: str | None) -> str | None:
    """Error code for why this review can't be recorded, or None if it can. Rejecting
    needs a reason, so the author learns why."""
    if decision == ReviewDecision.REJECTED and not (reason and reason.strip()):
        return "REJECTION_REASON_REQUIRED"
    return None
