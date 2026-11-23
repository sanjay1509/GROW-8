"""What the participants are told when an admin reviews feedback (ADR 0015).

FEEDBACK_APPROVED and FEEDBACK_REJECTED go to both creator_service and
contributor_service. Each service passes its own side, and gets back the notice for
the participant on that side, or None when that participant isn't told anything. So
every person gets exactly one notification per event, worded the same way whichever
service sends it.
"""

from dataclasses import dataclass
from typing import Literal

from grow8_common.events import FeedbackApprovedPayload, FeedbackRejectedPayload

Side = Literal["contributor", "creator"]


@dataclass(frozen=True)
class Notice:
    user_id: int
    title: str
    message: str


def approved_notice(payload: FeedbackApprovedPayload, side: Side) -> Notice:
    """The author is told it was published; the subject that they received a rating.
    The two are always on different sides, so each side has exactly one of them."""
    if payload.author_role == side:
        return Notice(
            payload.author_user_id,
            f"Your feedback was published: {payload.opportunity_title}",
            f"An admin approved your feedback about {payload.subject_name}. "
            "It now counts toward their rating.",
        )
    return Notice(
        payload.subject_user_id,
        f"New rating: {payload.opportunity_title}",
        f"{payload.author_name} rated you {payload.rating}/5 for {payload.opportunity_title}.",
    )


def rejected_notice(payload: FeedbackRejectedPayload, side: Side) -> Notice | None:
    """Only the author is told, with the admin's reason. The subject never hears about
    feedback that doesn't count, so the other side gets None."""
    if payload.author_role != side:
        return None
    return Notice(
        payload.author_user_id,
        f"Your feedback was not published: {payload.opportunity_title}",
        f"An admin did not approve your feedback about {payload.subject_name}. "
        f'Reason: "{payload.reason}"',
    )
