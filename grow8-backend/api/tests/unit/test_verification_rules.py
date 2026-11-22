from decimal import Decimal

import pytest
from grow8_common.models import ReviewDecision

from app.services.verification_rules import (
    SubmissionStatus,
    WorkStatus,
    submission_status,
    verification_refusal,
    work_status,
)

CLAIMED = Decimal("6.50")
APPROVED = ReviewDecision.APPROVED
REJECTED = ReviewDecision.REJECTED


@pytest.mark.parametrize("hours", ["0.01", "5.00", "6.50"])
def test_approving_up_to_the_hours_claimed_is_allowed(hours: str) -> None:
    assert verification_refusal(APPROVED, Decimal(hours), CLAIMED, None) is None


def test_approving_more_than_claimed_is_refused() -> None:
    assert (
        verification_refusal(APPROVED, Decimal("6.51"), CLAIMED, "great")
        == "VERIFIED_HOURS_EXCEED_CLAIMED"
    )


def test_a_comment_is_optional_when_approving() -> None:
    assert verification_refusal(APPROVED, CLAIMED, CLAIMED, None) is None
    assert verification_refusal(APPROVED, CLAIMED, CLAIMED, "Thanks!") is None


@pytest.mark.parametrize("comment", [None, "", "   \n\t"])
def test_rejecting_needs_a_comment(comment: str | None) -> None:
    assert verification_refusal(REJECTED, None, CLAIMED, comment) == "REJECTION_COMMENT_REQUIRED"


def test_rejecting_with_a_comment_is_allowed() -> None:
    assert verification_refusal(REJECTED, None, CLAIMED, "Half the sheet is missing.") is None


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (None, SubmissionStatus.AWAITING),
        (APPROVED, SubmissionStatus.APPROVED),
        (REJECTED, SubmissionStatus.REJECTED),
    ],
)
def test_submission_status_comes_from_the_decision(
    decision: ReviewDecision | None, expected: SubmissionStatus
) -> None:
    assert submission_status(decision) == expected


@pytest.mark.parametrize(
    ("submitted", "decision", "expected"),
    [
        (False, None, WorkStatus.NOT_SUBMITTED),
        (True, None, WorkStatus.AWAITING_VERIFICATION),
        (True, APPROVED, WorkStatus.COMPLETED),
        (True, REJECTED, WorkStatus.WORK_REJECTED),
    ],
)
def test_work_status(
    submitted: bool, decision: ReviewDecision | None, expected: WorkStatus
) -> None:
    assert work_status(submitted, decision) == expected
