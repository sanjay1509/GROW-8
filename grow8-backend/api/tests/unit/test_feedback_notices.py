"""grow8_common.notifications.feedback (ADR 0015): one notice per person per event,
whichever service sends it, and nothing for the subject of rejected feedback."""

import pytest
from grow8_common.events import FeedbackApprovedPayload, FeedbackRejectedPayload
from grow8_common.notifications.feedback import approved_notice, rejected_notice

CONTRIBUTOR, CREATOR = 5, 2
COMMON = {
    "feedback_id": 9,
    "application_id": 4,
    "opportunity_id": 1,
    "opportunity_title": "Recipes",
}


def _approved(author_role: str) -> FeedbackApprovedPayload:
    by_contributor = author_role == "contributor"
    return FeedbackApprovedPayload(
        **COMMON,
        author_user_id=CONTRIBUTOR if by_contributor else CREATOR,
        author_name="Alex Chen" if by_contributor else "Priya Nair",
        author_role=author_role,
        subject_user_id=CREATOR if by_contributor else CONTRIBUTOR,
        subject_name="Priya Nair" if by_contributor else "Alex Chen",
        rating=4,
    )


@pytest.mark.parametrize("author_role", ["contributor", "creator"])
def test_approval_reaches_both_people_once_across_the_two_services(author_role: str) -> None:
    payload = _approved(author_role)
    notices = [approved_notice(payload, side) for side in ("contributor", "creator")]

    assert sorted(n.user_id for n in notices) == [CREATOR, CONTRIBUTOR]
    by_user = {n.user_id: n for n in notices}
    assert by_user[payload.author_user_id].title == "Your feedback was published: Recipes"
    assert by_user[payload.subject_user_id].title == "New rating: Recipes"
    assert by_user[payload.subject_user_id].message == (
        f"{payload.author_name} rated you 4/5 for Recipes."
    )


@pytest.mark.parametrize(("author_role", "author_id"), [("contributor", 5), ("creator", 2)])
def test_rejection_reaches_only_the_author(author_role: str, author_id: int) -> None:
    payload = FeedbackRejectedPayload(
        **COMMON,
        author_user_id=author_id,
        author_role=author_role,
        subject_name="Someone",
        reason="Personal remarks.",
    )
    notices = [rejected_notice(payload, side) for side in ("contributor", "creator")]

    [notice] = [n for n in notices if n is not None]
    assert notice.user_id == author_id
    assert notice.message == (
        'An admin did not approve your feedback about Someone. Reason: "Personal remarks."'
    )
