import pytest
from grow8_common.models import ReviewDecision

from app.services.feedback_rules import (
    FeedbackStatus,
    feedback_status,
    participant_role,
    review_refusal,
    subject_of,
    visible_to,
)

CONTRIBUTOR, OWNER, STRANGER = 5, 2, 3
APPROVED, REJECTED, PENDING = (
    FeedbackStatus.APPROVED,
    FeedbackStatus.REJECTED,
    FeedbackStatus.PENDING,
)


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (None, PENDING),
        (ReviewDecision.APPROVED, APPROVED),
        (ReviewDecision.REJECTED, REJECTED),
    ],
)
def test_status_comes_from_the_review(decision, expected) -> None:
    assert feedback_status(decision) == expected


@pytest.mark.parametrize(
    ("user_id", "expected"),
    [(CONTRIBUTOR, "contributor"), (OWNER, "creator"), (STRANGER, None)],
)
def test_participant_role(user_id: int, expected: str | None) -> None:
    assert participant_role(user_id, CONTRIBUTOR, OWNER) == expected


def test_the_subject_is_always_the_other_participant() -> None:
    assert subject_of("contributor", CONTRIBUTOR, OWNER) == OWNER
    assert subject_of("creator", CONTRIBUTOR, OWNER) == CONTRIBUTOR


@pytest.mark.parametrize("status", list(FeedbackStatus))
def test_the_author_always_sees_their_feedback(status: FeedbackStatus) -> None:
    assert visible_to(CONTRIBUTOR, CONTRIBUTOR, OWNER, status)


@pytest.mark.parametrize(
    ("status", "expected"), [(PENDING, False), (REJECTED, False), (APPROVED, True)]
)
def test_the_subject_sees_it_only_once_approved(status: FeedbackStatus, expected: bool) -> None:
    assert visible_to(OWNER, CONTRIBUTOR, OWNER, status) is expected


@pytest.mark.parametrize("status", list(FeedbackStatus))
def test_nobody_else_sees_it(status: FeedbackStatus) -> None:
    assert not visible_to(STRANGER, CONTRIBUTOR, OWNER, status)


@pytest.mark.parametrize("reason", [None, "", "  \n"])
def test_rejecting_needs_a_reason(reason: str | None) -> None:
    assert review_refusal(ReviewDecision.REJECTED, reason) == "REJECTION_REASON_REQUIRED"


def test_rejecting_with_a_reason_is_allowed() -> None:
    assert review_refusal(ReviewDecision.REJECTED, "Personal remarks") is None


@pytest.mark.parametrize("reason", [None, "Fair and specific"])
def test_a_reason_is_optional_when_approving(reason: str | None) -> None:
    assert review_refusal(ReviewDecision.APPROVED, reason) is None
